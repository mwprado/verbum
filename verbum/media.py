"""Read embedded resources from a VLF, independent of source format."""
import json
from contextlib import closing
from .core import connect_read
from .resources import get_embedded_media as get_media

def entry_media(registry, dictionary, entry_id):
    manifest, path = registry.dictionary(dictionary)
    with closing(connect_read(path)) as db:
        row = db.execute("SELECT payload FROM entries WHERE id=?", (entry_id,)).fetchone()
    if row is None:
        raise ValueError("Unknown entry ID")
    return manifest, json.loads(row[0]).get("media", [])
