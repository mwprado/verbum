"""Source-specific import adapters. No arbitrary pickle deserialization."""
import base64
import gzip
import io
import json
import pickle
import shutil
import subprocess
import unicodedata
from pathlib import Path


def _longman_source(source):
    path = Path(source).expanduser().resolve()
    fs = path / "fs.skn"
    required = (
        "dirs.skn/config.cft", "dirs.skn/NAME.tda", "dirs.skn/dirs.dat",
        "files.skn/config.cft", "files.skn/NAME.tda", "files.skn/files.dat",
        "files.skn/CONTENT.tda", "files.skn/CONTENT.tda.tdz",
    )
    missing = [name for name in required if not (fs / name).is_file()]
    if missing:
        raise ValueError("Diretório LDOCE5 inválido; faltando: " + ", ".join(missing))
    return path

def _longman_metadata(source):
    from .catalog import read_catalog
    metadata = next(dict(m) for m in read_catalog() if m["origin"] == "longman")
    metadata["source_path"] = str(_longman_source(source))
    metadata["source_format"] = "longman"
    metadata["capabilities"] = [
        "definitions", "examples", "grammar", "variants",
        "source-xml", "media-references", "embedded-media"
    ]
    return metadata

def longman_entries(source, cancel=None):
    from .core import check_cancel
    path = _longman_source(source)
    command = shutil.which("verbum-ldoce5-export")
    if command is None:
        raise ValueError(
            "Longman LDOCE5 requer o conversor GPL incluído no pacote Verbum "
            "(comando verbum-ldoce5-export)."
        )
    process = subprocess.Popen(
        [command, str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    try:
        for line in process.stdout:
            check_cancel(cancel)
            line = line.strip()
            if line:
                yield json.loads(line)
        error = process.stderr.read().strip()
        code = process.wait()
        if code:
            raise ValueError(error or f"Conversor LDOCE5 terminou com código {code}")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

class _LongmanMediaLoader:
    def __init__(self, source):
        command = shutil.which("verbum-ldoce5-media")
        if command is None:
            raise ValueError(
                "O pacote Verbum não contém o leitor de mídia LDOCE5 "
                "(comando verbum-ldoce5-media)."
            )
        self.process = subprocess.Popen(
            [command, str(_longman_source(source))],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )

    def __call__(self, archive, name):
        request = json.dumps({"archive": archive, "name": name}, separators=(",", ":"))
        self.process.stdin.write(request + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            error = self.process.stderr.read().strip()
            raise ValueError(error or "O leitor de mídia LDOCE5 terminou inesperadamente.")
        response = json.loads(line)
        if not response.get("ok"):
            detail = response.get("error") or "Falha ao ler recurso LDOCE5."
            raise ValueError(detail + f" [recurso: {archive}/{name}]")
        return base64.b64decode(response["data"], validate=True), response["mime"]

    def close(self):
        if self.process.poll() is None:
            try:
                self.process.stdin.close()
            except OSError:
                pass
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()


class _RestrictedUnpickler(pickle.Unpickler):
    """Unpickler that never resolves globals, classes or functions."""
    def find_class(self, module, name):
        raise pickle.UnpicklingError(
            "objetos Python externos não são permitidos: " + module + "." + name
        )


def _validate_pickle_value(value, *, depth=0, items=None):
    if items is None:
        items = [0]
    if depth > 64:
        raise ValueError("Pickle legado excede a profundidade estrutural permitida.")
    items[0] += 1
    if items[0] > 5_000_000:
        raise ValueError("Pickle legado contém objetos demais.")
    if value is None or isinstance(value, (str, bytes, int, float, bool)):
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _validate_pickle_value(item, depth=depth + 1, items=items)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, (str, int, float, bool, bytes)):
                raise ValueError("Pickle legado contém chave de tipo não permitido.")
            _validate_pickle_value(item, depth=depth + 1, items=items)
        return
    raise ValueError("Pickle legado contém tipo não permitido: " + type(value).__name__)


def _load_legacy_pickle(source):
    path = Path(source).expanduser().resolve()
    raw = path.read_bytes()
    if len(raw) > 2 * 1024 * 1024 * 1024:
        raise ValueError("Pickle legado excede 2 GiB.")
    if path.suffix.lower() in (".pklz", ".gz") or raw.startswith(b"\x1f\x8b"):
        try:
            raw = gzip.decompress(raw)
        except OSError as exc:
            raise ValueError("Arquivo PKLZ/GZip inválido.") from exc
    try:
        value = _RestrictedUnpickler(io.BytesIO(raw)).load()
    except (pickle.UnpicklingError, EOFError, AttributeError, ValueError, TypeError) as exc:
        raise ValueError("Pickle legado inválido ou não seguro: " + str(exc)) from exc
    _validate_pickle_value(value, items=[0])
    return value


def _json_safe_legacy(value):
    """Convert an already validated pickle tree into JSON-safe primitives."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, (list, tuple)):
        return [_json_safe_legacy(item) for item in value]
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if isinstance(key, bytes):
                key = key.decode("utf-8", errors="replace")
            elif not isinstance(key, str):
                key = str(key)
            result[key] = _json_safe_legacy(item)
        return result
    raise ValueError("Valor legado não pode ser convertido para JSON: " + type(value).__name__)


def _legacy_definition(value):
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, (list, tuple)):
        return "\n".join(filter(None, (_legacy_definition(item) for item in value)))
    if isinstance(value, dict):
        preferred = ("definition", "definitions", "descricao", "descrição", "meaning", "meanings", "text", "html")
        for key in preferred:
            if key in value:
                return _legacy_definition(value[key])
        return "\n".join(
            f"{_legacy_definition(key)}: {_legacy_definition(item)}"
            for key, item in value.items()
        )
    return str(value)


def _legacy_entry(record, lemma=None):
    if isinstance(record, dict):
        entry = _json_safe_legacy(record)
        candidate = entry.get("lemma") or entry.get("headword") or entry.get("word") or entry.get("termo") or lemma
        if candidate is None:
            raise ValueError("Registro Pickle sem lema.")
        if isinstance(candidate, bytes):
            candidate = candidate.decode("utf-8", errors="replace")
        candidate = str(candidate).strip()
        if not candidate:
            raise ValueError("Registro Pickle com lema vazio.")
        entry["lemma"] = candidate
        if not any(key in entry for key in ("definition", "definitions", "senses")):
            payload = {k: v for k, v in entry.items() if k != "lemma"}
            entry["definition"] = _legacy_definition(payload)
        return entry
    if lemma is None and isinstance(record, (list, tuple)) and len(record) >= 2:
        lemma, record = record[0], record[1:] if len(record) > 2 else record[1]
    if lemma is None:
        raise ValueError("Estrutura Pickle não contém lema identificável.")
    if isinstance(lemma, bytes):
        lemma = lemma.decode("utf-8", errors="replace")
    return {"lemma": str(lemma).strip(), "definition": _legacy_definition(_json_safe_legacy(record))}


def pickle_entries(source):
    value = _load_legacy_pickle(source)
    if isinstance(value, dict) and "entries" in value and isinstance(value["entries"], (list, tuple, dict)):
        value = value["entries"]
    if isinstance(value, dict):
        for lemma, record in value.items():
            yield _legacy_entry(record, lemma)
        return
    if isinstance(value, (list, tuple)):
        for record in value:
            yield _legacy_entry(record)
        return
    raise ValueError("Estrutura Pickle/PKLZ não suportada.")


def _pickle_metadata(source):
    path = Path(source).expanduser().resolve()
    stem = path.name
    for suffix in (".pklz", ".pickle", ".pkl", ".gz"):
        if stem.lower().endswith(suffix):
            stem = stem[:-len(suffix)]
            break
    title = stem.replace("_", " ").replace("-", " ").strip() or "Dicionário legado"
    ascii_stem = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode("ascii")
    origin_tail = "-".join(
        part for part in "".join(
            ch.lower() if ch.isalnum() else "-" for ch in ascii_stem
        ).split("-") if part
    )[:48]
    origin = "legacy-" + (origin_tail or "dictionary")
    return {
        "title": title,
        "language": "und",
        "origin": origin,
        "function": "general",
        "license": "unverified",
        "license_type": "unspecified",
        "access": "local",
        "source_path": str(path),
        "source_format": "pickle-legacy",
        "capabilities": ["definitions"],
    }


def json_entries(source, source_format=None):
    path = Path(source)
    with path.open(encoding="utf-8") as f:
        if source_format == "jsonl" or (source_format is None and path.suffix.lower() == ".jsonl"):
            for line in f:
                if line.strip():
                    yield json.loads(line)
        else:
            data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("JSON source must contain an array of entries")
            yield from data

def import_dictionary(registry, metadata, source, source_format="json", *, progress=None, cancel=None, rebuild=None):
    from .core import check_cancel
    check_cancel(cancel)
    if progress:
        progress("prepare", 0, None)
    if source_format == "bgl":
        from .bgl import import_bgl
        return import_bgl(registry, source, metadata, progress=progress, cancel=cancel, rebuild=rebuild)
    if source_format in ("pickle", "pklz"):
        if metadata is not None:
            raise ValueError("Pickle/PKLZ legado usa metadados gerados automaticamente; não informe manifesto.")
        return registry.import_entries(
            _pickle_metadata(source),
            pickle_entries(source),
            progress=progress,
            cancel=cancel,
            rebuild=rebuild,
        )
    if source_format == "longman":
        if metadata is not None:
            raise ValueError("Longman usa os metadados nativos do catálogo; não informe manifesto.")
        loader = _LongmanMediaLoader(source)
        try:
            return registry.import_entries(
                _longman_metadata(source),
                longman_entries(source, cancel=cancel),
                progress=progress,
                cancel=cancel,
                rebuild=rebuild,
                resource_loader=loader,
            )
        finally:
            loader.close()
    if metadata is None:
        raise ValueError("JSON/JSONL requires --manifest")
    if source_format not in ("json", "jsonl"):
        raise ValueError("Unsupported source format: " + source_format)
    from .catalog import distribution_info
    policy = distribution_info(metadata)
    if metadata.get("license_type") == "proprietary" or metadata.get("license", "").lower() == "proprietary":
        raise ValueError("Proprietary sources require a native importer; JSON compatibility is not supported")
    if policy["method"] != "import":
        raise ValueError("Use the corresponding installation method")
    metadata = dict(metadata, source_path=str(Path(source).expanduser().resolve()), source_format=source_format)
    return registry.import_entries(metadata, json_entries(source, source_format), progress=progress, cancel=cancel, rebuild=rebuild)

# Shared importer descriptions for clients. Only implemented formats are listed.
IMPORT_FORMATS = (
    {"id": "longman", "title": "Longman LDOCE5", "description": "Diretório original IDM/SKN", "directory": True, "manifest": False},
    {"id": "bgl", "title": "Babylon BGL", "description": "Arquivo original .bgl (requer PyGlossary)", "directory": False, "manifest": False},
    {"id": "pickle", "title": "Pickle / PKLZ legado", "description": "Arquivo .pkl, .pickle ou .pklz; desserialização restrita e conversão imediata para VLF", "directory": False, "manifest": False},
    {"id": "json", "title": "JSON", "description": "Arquivo estruturado com manifesto TOML", "directory": False, "manifest": True},
    {"id": "jsonl", "title": "JSON Lines", "description": "Arquivo de registros JSON com manifesto TOML", "directory": False, "manifest": True},
)
