"""Source-specific import adapters. No arbitrary pickle deserialization."""
import json
import shutil
import subprocess
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
    metadata["capabilities"] = ["definitions", "examples", "grammar", "variants"]
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
    if source_format == "longman":
        if metadata is not None:
            raise ValueError("Longman usa os metadados nativos do catálogo; não informe manifesto.")
        return registry.import_entries(
            _longman_metadata(source),
            longman_entries(source, cancel=cancel),
            progress=progress,
            cancel=cancel,
            rebuild=rebuild,
        )
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
    {"id": "json", "title": "JSON", "description": "Arquivo estruturado com manifesto TOML", "directory": False, "manifest": True},
    {"id": "jsonl", "title": "JSON Lines", "description": "Arquivo de registros JSON com manifesto TOML", "directory": False, "manifest": True},
)
