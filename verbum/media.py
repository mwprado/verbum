"""Read VLF media, with compatibility fallback for older Longman imports."""
import base64
import json
import shutil
import subprocess
from contextlib import closing

from .core import connect_read
from .resources import get_embedded_media


def entry_media(registry, dictionary, entry_id):
    manifest, path = registry.dictionary(dictionary)
    with closing(connect_read(path)) as db:
        row = db.execute("SELECT payload FROM entries WHERE id=?", (entry_id,)).fetchone()
    if row is None:
        raise ValueError("Unknown entry ID")
    return manifest, json.loads(row[0]).get("media", [])


def _longman_fallback(source, archive, name):
    command = shutil.which("verbum-ldoce5-media")
    if command is None:
        raise ValueError("Leitor de mídia LDOCE5 não está instalado.")
    process = subprocess.Popen(
        [command, source],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    try:
        request = json.dumps({"archive": archive, "name": name}, separators=(",", ":"))
        process.stdin.write(request + "\n")
        process.stdin.flush()
        line = process.stdout.readline()
        if not line:
            error = process.stderr.read().strip()
            raise ValueError(error or "O leitor de mídia LDOCE5 terminou inesperadamente.")
        response = json.loads(line)
        if not response.get("ok"):
            raise ValueError(response.get("error") or "Falha ao ler recurso LDOCE5.")
        return base64.b64decode(response["data"], validate=True), response["mime"]
    finally:
        if process.poll() is None:
            try:
                process.stdin.close()
            except OSError:
                pass
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


def get_media(registry, dictionary, entry_id, index, fullsize=False):
    manifest, refs = entry_media(registry, dictionary, entry_id)
    if not isinstance(index, int) or not 0 <= index < len(refs):
        raise ValueError("Unknown media index")
    ref = refs[index]

    missing_key = "fullsize_missing" if fullsize else "missing"
    if ref.get(missing_key):
        raise ValueError("Recurso ausente na fonte original LDOCE5.")
    digest_key = "fullsize_sha256" if fullsize else "sha256"
    if ref.get(digest_key):
        return get_embedded_media(registry, dictionary, entry_id, index, fullsize)

    # Compatibility for VLF generations created before media embedding.
    if manifest.get("source_format") not in ("longman", "idm-skn"):
        raise ValueError("Recurso não incorporado; reconstrua o dicionário para incorporar a mídia.")

    source = manifest.get("source_path")
    if not source:
        raise ValueError("A base antiga não registra a pasta original do LDOCE5; reconstrua o dicionário.")

    if fullsize and ref.get("type") != "image":
        raise ValueError("Fullsize applies only to pictures")
    name = ref.get("fullsize") if fullsize else ref.get("name")
    if not name:
        raise ValueError("Recurso de mídia sem nome.")
    return _longman_fallback(source, ref["archive"], name)
