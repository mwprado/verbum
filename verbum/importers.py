"""Source-specific import adapters. No arbitrary pickle deserialization."""
import base64
import gzip
import io
import json
import pickle
import shutil
import subprocess
import unicodedata
import re
from datetime import datetime, timezone
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

def _write_unrecoverable_log(registry, source, result, corrupt):
    """Write a private JSONL recovery queue for irrecoverable source media."""
    if not corrupt:
        return None

    log_dir = Path(registry.root) / "logs"
    log_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

    created = datetime.now(timezone.utc)
    stamp = created.strftime("%Y%m%dT%H%M%S.%fZ")
    target = log_dir / ("longman-unrecoverable-" + stamp + ".jsonl")
    temp = target.with_suffix(target.suffix + ".tmp")

    header = {
        "record_type": "import",
        "format": "verbum-unrecoverable-media-log",
        "version": 1,
        "created_at": created.isoformat(),
        "source_format": "longman",
        "source_path": str(Path(source).expanduser().resolve()),
        "dictionary_slug": result.get("slug"),
        "vlf_path": result.get("path"),
        "count": len(corrupt),
    }

    lines = [json.dumps(header, ensure_ascii=False, sort_keys=True)]
    for (archive, name), reason in sorted(corrupt.items()):
        lines.append(json.dumps({
            "record_type": "resource",
            "archive": archive,
            "name": name,
            "media_type": "image" if archive == "picture" else "audio",
            "extension": Path(name).suffix.lower(),
            "reason": reason,
            "status": "pending",
        }, ensure_ascii=False, sort_keys=True))

    try:
        temp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        temp.chmod(0o600)
        temp.replace(target)
    finally:
        temp.unlink(missing_ok=True)
    return str(target)


class _LongmanMediaLoader:
    def __init__(self, source):
        command = shutil.which("verbum-ldoce5-media")
        if command is None:
            raise ValueError(
                "O pacote Verbum não contém o leitor de mídia LDOCE5 "
                "(comando verbum-ldoce5-media)."
            )
        self.missing = set()
        self.corrupt = {}
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
            if detail.startswith("missing media resource:"):
                self.missing.add((archive, name))
                return None
            if detail.startswith((
                "unrecoverable media record",
                "empty or truncated media record",
                "invalid MPEG audio record",
                "unsupported picture encoding",
                "invalid media record size",
            )):
                self.corrupt[(archive, name)] = detail
                return {"unavailable": True, "reason": detail}
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


class _LegacyProxy:
    """Inert stand-in for a class referenced by an old pickle."""
    __legacy_module__ = ""
    __legacy_name__ = ""

    def __new__(cls, *args, **kwargs):
        return object.__new__(cls)

    def __init__(self, *args, **kwargs):
        pass

    def __setstate__(self, state):
        if isinstance(state, dict):
            self.__dict__.update(state)
        else:
            self.__dict__["_legacy_state"] = state

    def __setitem__(self, key, value):
        self.__dict__.setdefault("_legacy_items", {})[key] = value

    def append(self, value):
        self.__dict__.setdefault("_legacy_sequence", []).append(value)


_LEGACY_PROXY_TYPES = {}


def _legacy_proxy_type(module, name):
    key = (str(module), str(name))
    cls = _LEGACY_PROXY_TYPES.get(key)
    if cls is None:
        safe = "".join(ch if ch.isalnum() else "_" for ch in name) or "Object"
        cls = type(
            "_Legacy_" + safe,
            (_LegacyProxy,),
            {"__legacy_module__": key[0], "__legacy_name__": key[1]},
        )
        _LEGACY_PROXY_TYPES[key] = cls
    return cls


def _legacy_reconstructor(cls, base, state):
    """Safe replacement for copyreg._reconstructor.

    It deliberately ignores the serialized base class and constructor state:
    only inert proxy classes created by this module may be instantiated.
    """
    if not isinstance(cls, type) or not issubclass(cls, _LegacyProxy):
        raise pickle.UnpicklingError("classe legada inválida")
    return object.__new__(cls)


class _RestrictedUnpickler(pickle.Unpickler):
    """Recover legacy data without importing or executing serialized classes."""
    _SAFE_BUILTINS = {
        "object": object,
        "set": set,
        "frozenset": frozenset,
    }

    def find_class(self, module, name):
        if module in ("copyreg", "copy_reg") and name == "_reconstructor":
            return _legacy_reconstructor
        if module in ("builtins", "__builtin__") and name in self._SAFE_BUILTINS:
            return self._SAFE_BUILTINS[name]
        # Do not import the referenced module. Unknown classes/functions are
        # represented by inert proxy types; REDUCE/NEWOBJ therefore cannot
        # execute the original application code.
        return _legacy_proxy_type(module, name)


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
    if isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            _validate_pickle_value(item, depth=depth + 1, items=items)
        return
    if isinstance(value, _LegacyProxy):
        _validate_pickle_value(value.__dict__, depth=depth + 1, items=items)
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
    return _json_safe_legacy(value)


def _json_safe_legacy(value):
    """Convert an already validated pickle tree into JSON-safe primitives."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe_legacy(item) for item in value]
    if isinstance(value, _LegacyProxy):
        attrs = {
            key: item for key, item in value.__dict__.items()
            if key not in ("_legacy_items", "_legacy_sequence", "_legacy_state")
        }
        if attrs:
            return _json_safe_legacy(attrs)
        if "_legacy_items" in value.__dict__:
            return _json_safe_legacy(value.__dict__["_legacy_items"])
        if "_legacy_sequence" in value.__dict__:
            return _json_safe_legacy(value.__dict__["_legacy_sequence"])
        if "_legacy_state" in value.__dict__:
            return _json_safe_legacy(value.__dict__["_legacy_state"])
        return {}
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
        preferred = (
            "definition", "definitions", "definicao", "definição",
            "descricao", "descrição", "meaning", "meanings", "text", "html"
        )
        for key in preferred:
            if key in value:
                return _legacy_definition(value[key])
        return "\n".join(
            f"{_legacy_definition(key)}: {_legacy_definition(item)}"
            for key, item in value.items()
        )
    return str(value)



_LEGACY_GRAMMAR_PREFIX = re.compile(
    r"^(?P<grammar>(?:Substantivo|Adjetivo|Advérbio|Verbo|Pronome|Preposição|"
    r"Conjunção|Interjeição|Artigo|Numeral)(?:\s+[A-Za-zÀ-ÖØ-öø-ÿ]+){0,4})\.\s+",
    re.IGNORECASE,
)
_LEGACY_SENSE_MARKER = re.compile(r"(?<!\S)(\d{1,3})\.\s+")
_LEGACY_EMBEDDED_HEADWORD = re.compile(
    r"(?:^|[.!?]\s+)"
    r"(?P<headword>[A-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ][A-Za-zÀ-ÖØ-öø-ÿ0-9'’()/-]*(?:\s+[A-Za-zÀ-ÖØ-öø-ÿ0-9'’()/-]+){0,9})"
    r"\.\s+1\.\s+"
)


def _legacy_tail_headwords(text):
    """Return embedded legacy headword titles without their definitions."""
    if not isinstance(text, str) or not text.strip():
        return []
    result = []
    seen = set()
    for match in _LEGACY_EMBEDDED_HEADWORD.finditer(text):
        headword = " ".join(match.group("headword").split()).strip()
        key = headword.casefold()
        if headword and key not in seen:
            seen.add(key)
            result.append(headword)
    return result


def _structure_legacy_definition(entry):
    """Conservatively recover lexical structure from a flattened legacy entry.

    The original text is retained as raw_definition.  Numbered senses are only
    accepted when they start at 1 and increase consecutively; a reset or jump
    ends the structured region instead of guessing across another embedded
    headword/section.
    """
    definition = entry.get("definition")
    if not isinstance(definition, str):
        return entry
    text = " ".join(definition.split())
    if not text:
        return entry

    rest = text
    etymology = None
    if rest.startswith("["):
        end = rest.find("]")
        if 0 < end <= 240:
            etymology = rest[1:end].strip()
            rest = rest[end + 1:].lstrip()
            if rest.startswith("."):
                rest = rest[1:].lstrip()

    grammar = None
    grammar_match = _LEGACY_GRAMMAR_PREFIX.match(rest)
    if grammar_match:
        grammar = grammar_match.group("grammar").strip()
        rest = rest[grammar_match.end():]

    markers = list(_LEGACY_SENSE_MARKER.finditer(rest))
    if not markers or int(markers[0].group(1)) != 1:
        if etymology or grammar:
            entry.setdefault("raw_definition", definition)
            if etymology:
                entry.setdefault("etymology", etymology)
            if grammar:
                current = entry.get("grammar")
                if not isinstance(current, dict):
                    current = {}
                    entry["grammar"] = current
                current.setdefault("pos", [grammar])
            entry["definition"] = rest.strip() or definition
        return entry

    accepted = [markers[0]]
    expected = 2
    stop = len(rest)
    for marker in markers[1:]:
        number = int(marker.group(1))
        if number != expected:
            stop = marker.start()
            break
        accepted.append(marker)
        expected += 1

    senses = []
    for index, marker in enumerate(accepted):
        end = accepted[index + 1].start() if index + 1 < len(accepted) else stop
        body_start = marker.end()
        raw_body = rest[body_start:end]
        leading = len(raw_body) - len(raw_body.lstrip())
        body = raw_body.strip()
        if index == len(accepted) - 1 and stop < len(rest):
            # If a numbered sequence restarts, the short title immediately
            # before the new "1." normally belongs to the next embedded entry.
            title = re.search(
                r"(?:^|[.!?]\s+)([A-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ][A-Za-zÀ-ÖØ-öø-ÿ'’ -]{1,80})\.\s*$",
                body,
            )
            if title:
                stop = body_start + leading + title.start(1)
                body = body[:title.start(1)].rstrip()
        if body:
            senses.append({
                "index": int(marker.group(1)),
                "definitions": [body],
            })

    if not senses:
        return entry

    entry.setdefault("raw_definition", definition)
    if etymology:
        entry.setdefault("etymology", etymology)
    if grammar:
        current = entry.get("grammar")
        if not isinstance(current, dict):
            current = {}
            entry["grammar"] = current
        current.setdefault("pos", [grammar])
    entry["senses"] = senses
    entry.pop("definition", None)
    tail = rest[stop:].strip()
    if tail:
        entry.setdefault("legacy_tail", tail)
        headwords = _legacy_tail_headwords(tail)
        if headwords:
            entry.setdefault("legacy_entries", headwords)
    return entry

_LEGACY_HOMOGRAPH_SUFFIX = re.compile(r"(?:\$(\d+)\$)+$")


def _clean_legacy_lemma(value):
    """Remove legacy homograph markers such as $1$ from display/search lemma.

    Older Aurélio data encoded the numbered homograph/entry at the end of the
    lexical key.  The cleaned lemma is used for display/search while the
    numeric marker is preserved separately as homograph.
    """
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    text = str(value).strip()
    match = _LEGACY_HOMOGRAPH_SUFFIX.search(text)
    if not match:
        return text, None
    clean = text[:match.start()].rstrip()
    if not clean:
        return text, None
    return clean, int(match.group(1))


def _legacy_entry(record, lemma=None):
    if isinstance(record, dict):
        entry = _json_safe_legacy(record)
        candidate = (
            entry.get("lema_original")
            or entry.get("lemma") or entry.get("headword") or entry.get("word")
            or entry.get("termo") or entry.get("verbete") or entry.get("palavra")
            or lemma
        )
        if candidate is None:
            raise ValueError("Registro Pickle sem lema.")
        raw_candidate = candidate.decode("utf-8", errors="replace") if isinstance(candidate, bytes) else str(candidate)
        candidate, homograph = _clean_legacy_lemma(raw_candidate)
        if not candidate:
            raise ValueError("Registro Pickle com lema vazio.")

        source_lemma = raw_candidate.strip()
        if homograph is None:
            for key in ("lemma", "headword", "word", "termo", "verbete", "palavra"):
                alternate = entry.get(key)
                if not isinstance(alternate, (str, bytes)):
                    continue
                raw_alternate = (
                    alternate.decode("utf-8", errors="replace")
                    if isinstance(alternate, bytes) else str(alternate)
                ).strip()
                clean_alternate, alternate_index = _clean_legacy_lemma(raw_alternate)
                if alternate_index is not None and clean_alternate == candidate:
                    homograph = alternate_index
                    source_lemma = raw_alternate
                    break

        if source_lemma != candidate:
            entry.setdefault("source_lemma", source_lemma)
        if homograph is not None:
            entry.setdefault("homograph", homograph)
        entry["lemma"] = candidate
        if not any(key in entry for key in ("definition", "definitions", "senses")):
            payload = {k: v for k, v in entry.items() if k != "lemma"}
            entry["definition"] = _legacy_definition(payload)
        return _structure_legacy_definition(entry)
    if lemma is None and isinstance(record, (list, tuple)) and len(record) >= 2:
        lemma, record = record[0], record[1:] if len(record) > 2 else record[1]
    if lemma is None:
        raise ValueError("Estrutura Pickle não contém lema identificável.")
    raw_lemma = lemma.decode("utf-8", errors="replace") if isinstance(lemma, bytes) else str(lemma)
    clean_lemma, homograph = _clean_legacy_lemma(raw_lemma)
    result = {
        "lemma": clean_lemma,
        "definition": _legacy_definition(_json_safe_legacy(record)),
    }
    if clean_lemma != raw_lemma.strip():
        result["source_lemma"] = raw_lemma.strip()
    if homograph is not None:
        result["homograph"] = homograph
    return _structure_legacy_definition(result)


def _looks_like_legacy_entry(value):
    """Distinguish one entry object from a top-level {lemma: record} map."""
    if not isinstance(value, dict):
        return False
    lemma_keys = ("lemma", "headword", "word", "termo", "verbete", "palavra")
    for key in lemma_keys:
        candidate = value.get(key)
        if isinstance(candidate, (str, bytes)) and candidate.strip():
            return True
    return False


def pickle_entries(source):
    value = _load_legacy_pickle(source)
    if isinstance(value, dict) and "entries" in value and isinstance(value["entries"], (list, tuple, dict)):
        value = value["entries"]
    if isinstance(value, dict):
        # A recovered class instance becomes its attribute dictionary.  A
        # dictionary keyed by lemmas may itself contain lemmas named
        # "palavra", "verbete" or "termo"; those values are records, not a
        # scalar headword field, and must not collapse the whole dictionary
        # into one entry.
        if _looks_like_legacy_entry(value):
            yield _legacy_entry(value)
            return
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
            result = registry.import_entries(
                _longman_metadata(source),
                longman_entries(source, cancel=cancel),
                progress=progress,
                cancel=cancel,
                rebuild=rebuild,
                resource_loader=loader,
            )
            result["missing_resources"] = len(loader.missing)
            result["corrupt_resources"] = len(loader.corrupt)
            if loader.corrupt:
                try:
                    result["corrupt_log"] = _write_unrecoverable_log(
                        registry, source, result, loader.corrupt
                    )
                except OSError as exc:
                    result["corrupt_log_error"] = str(exc)
            return result
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
