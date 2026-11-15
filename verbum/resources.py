"""Native VLF binary resources; no source-format dependencies."""
import hashlib
import json
from contextlib import closing
from .core import check_cancel, connect_read

MAX_RESOURCE_SIZE = 64 * 1024 * 1024


def _store_resource(db, content, mime, name):
    if not isinstance(content, bytes) or not content or len(content) > MAX_RESOURCE_SIZE:
        raise ValueError("Invalid resource size: " + str(name))
    if not isinstance(mime, str) or not mime.startswith(("audio/", "image/")):
        raise ValueError("Invalid resource MIME: " + str(name))
    digest = hashlib.sha256(content).hexdigest()
    db.execute(
        "INSERT OR IGNORE INTO resources VALUES (?,?,?)",
        (digest, mime, content),
    )
    stored = db.execute(
        "SELECT mime FROM resources WHERE sha256=?",
        (digest,),
    ).fetchone()
    if stored is None or stored[0] != mime:
        raise ValueError("Conflicting resource MIME: " + str(name))
    return digest


def _embed_loaded_resource(db, loaded, name):
    """Embed one loader result.

    Legacy loaders return (bytes, mime). New loaders may return a mapping with
    content/mime plus optional derived representations. This lets VLF preserve
    source bytes while preferring an open playback or display representation
    without changing the SQLite schema.
    """
    if isinstance(loaded, tuple) and len(loaded) == 2:
        content, mime = loaded
        digest = _store_resource(db, content, mime, name)
        return {"sha256": digest, "mime": mime}

    if not isinstance(loaded, dict):
        raise ValueError("Invalid resource loader result: " + str(name))

    content = loaded.get("content")
    mime = loaded.get("mime")
    original_digest = _store_resource(db, content, mime, name)

    representations = [{
        "role": "original",
        "sha256": original_digest,
        "mime": mime,
    }]
    preferred = {"sha256": original_digest, "mime": mime}

    derived = loaded.get("representations", [])
    if derived is None:
        derived = []
    if not isinstance(derived, list):
        raise ValueError("Invalid resource representations: " + str(name))

    preferred_seen = False
    for item in derived:
        if not isinstance(item, dict):
            raise ValueError("Invalid resource representation: " + str(name))
        rep_content = item.get("content")
        rep_mime = item.get("mime")
        rep_digest = _store_resource(db, rep_content, rep_mime, name)

        role = item.get("role", "derived")
        if not isinstance(role, str) or not role:
            raise ValueError("Invalid resource representation role: " + str(name))

        metadata = {
            "role": role,
            "sha256": rep_digest,
            "mime": rep_mime,
        }
        for key in ("codec", "container", "lossy", "source_sha256"):
            if key in item:
                metadata[key] = item[key]

        if item.get("preferred"):
            if preferred_seen:
                raise ValueError("Multiple preferred resource representations: " + str(name))
            preferred_seen = True
            metadata["preferred"] = True
            preferred = {"sha256": rep_digest, "mime": rep_mime}

        representations.append(metadata)

    result = dict(preferred)
    if len(representations) > 1:
        result["original_sha256"] = original_digest
        result["original_mime"] = mime
        result["representations"] = representations
    return result


def embed_resources(db, payload, loader, cache, cancel=None):
    """Embed referenced resources by content hash; keep original reference indices."""
    refs = []

    def embed(archive, name):
        check_cancel(cancel)
        key = (archive, name)
        if key not in cache:
            loaded = loader(archive, name)
            if loaded is None:
                cache[key] = None
                return None
            cache[key] = _embed_loaded_resource(db, loaded, name)
        return cache[key]

    for original in payload.get("media", []):
        ref = dict(original)
        embedded = embed(ref["archive"], ref["name"])
        if embedded:
            ref.update(embedded)
        else:
            ref["missing"] = True

        if ref.get("fullsize"):
            fullsize = embed(ref["archive"], ref["fullsize"])
            if fullsize:
                ref["fullsize_sha256"] = fullsize["sha256"]
                ref["fullsize_mime"] = fullsize["mime"]
                if fullsize.get("representations"):
                    ref["fullsize_original_sha256"] = fullsize["original_sha256"]
                    ref["fullsize_original_mime"] = fullsize["original_mime"]
                    ref["fullsize_representations"] = fullsize["representations"]
            else:
                ref["fullsize_missing"] = True
        refs.append(ref)
    return dict(payload, media=refs)


def get_embedded_media(registry, dictionary, entry_id, index, fullsize=False):
    _, path = registry.dictionary(dictionary)
    with closing(connect_read(path)) as db:
        row = db.execute("SELECT payload FROM entries WHERE id=?", (entry_id,)).fetchone()
        if row is None:
            raise ValueError("Unknown entry ID")
        refs = json.loads(row[0]).get("media", [])
        if not isinstance(index, int) or not 0 <= index < len(refs):
            raise ValueError("Unknown media index")
        ref = refs[index]
        if fullsize and ref.get("type") != "image":
            raise ValueError("Fullsize applies only to pictures")
        missing_key = "fullsize_missing" if fullsize else "missing"
        if ref.get(missing_key):
            raise ValueError("Recurso ausente na fonte original do dicionário.")
        digest = ref.get("fullsize_sha256" if fullsize else "sha256")
        if not digest:
            raise ValueError("Recurso não incorporado; converta a base original para VLF v2.")
        row = db.execute("SELECT content,mime FROM resources WHERE sha256=?", (digest,)).fetchone()
        if row is None:
            raise ValueError("Missing VLF resource")
        return row[0], row[1]
