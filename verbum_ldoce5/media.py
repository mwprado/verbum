# SPDX-License-Identifier: GPL-3.0-or-later
"""Read LDOCE5 binary media for Verbum through a line-oriented subprocess API."""
import argparse
import base64
import json
import sys
import zlib
from functools import lru_cache
from pathlib import Path

from . import idmreader
from .export import validate_source

AUDIO_ARCHIVES = frozenset(("gb_hwd_pron", "us_hwd_pron", "exa_pron", "sfx", "sound"))
MEDIA_ARCHIVES = AUDIO_ARCHIVES | {"picture"}


def _archive_signature(source, archive):
    base = Path(source) / (archive + ".skn")
    files = [
        base / directory / name
        for directory, names in (
            ("dirs.skn", ("config.cft", "NAME.tda", "dirs.dat")),
            ("files.skn", ("config.cft", "NAME.tda", "files.dat", "CONTENT.tda", "CONTENT.tda.tdz")),
        )
        for name in names
    ]
    return tuple((p.stat().st_size, p.stat().st_mtime_ns) for p in files)


def _add_location(result, key, location):
    key = key.strip("/")
    if not key:
        return
    if key in result and result[key] != location:
        result[key] = None
    else:
        result[key] = location


@lru_cache(maxsize=16)
def _locations(source, archive, signature):
    result = {}
    full_paths = {}
    for dirs, name, location in idmreader.list_files(source, archive):
        clean_dirs = [part for part in dirs if part]
        full = "/".join((*clean_dirs, name))
        full_paths[full] = location
        # Fast aliases for the common layouts. Ambiguous aliases are
        # deliberately disabled rather than resolved arbitrarily.
        _add_location(result, full, location)
        if clean_dirs:
            _add_location(result, clean_dirs[-1] + "/" + name, location)
        _add_location(result, name, location)
    return result, full_paths


def _resolve_location(source, archive, name, signature):
    aliases, full_paths = _locations(source, archive, signature)

    location = aliases.get(name)
    if location is not None:
        return location

    # LDOCE5 XML sometimes stores a logical relative path such as
    # "thumbnail/abacus.jpg", while the SKN catalog contains one or more
    # additional leading directories. Resolve only when the requested
    # suffix identifies exactly one physical record.
    suffix = "/" + name.strip("/")
    matches = {
        location
        for path, location in full_paths.items()
        if path == name or path.endswith(suffix)
    }
    if len(matches) == 1:
        return next(iter(matches))

    # Compatibility with older importer generations that retained only
    # the basename. Accept it only when it identifies one record.
    basename = name.rsplit("/", 1)[-1]
    basename_matches = {
        location
        for path, location in full_paths.items()
        if path.rsplit("/", 1)[-1] == basename
    }
    if len(basename_matches) == 1:
        return next(iter(basename_matches))

    return None


def read_media(source, archive, name):
    if archive not in MEDIA_ARCHIVES:
        raise ValueError("unsupported media archive")
    source = str(validate_source(source))
    if not isinstance(name, str) or not name or "\\" in name or any(
        part in ("", ".", "..") for part in name.split("/")
    ):
        raise ValueError("invalid media name")
    parts = name.split("/")
    if archive == "picture":
        if len(parts) != 2 or parts[0] not in ("thumbnail", "fullsize"):
            raise ValueError("invalid picture name")

    signature = _archive_signature(source, archive)
    location = _resolve_location(source, archive, name, signature)
    if location is None:
        raise ValueError("missing or ambiguous media resource: " + archive + "/" + name)
    if any(value < 0 for value in location) or location[3] > 64 * 1024 * 1024:
        raise ValueError("invalid media record size")

    try:
        with idmreader.ArchiveReader(source, archive) as reader:
            data = reader.read(location)
    except zlib.error as exc:
        raise ValueError("corrupt media record") from exc
    if not data or len(data) != location[3]:
        raise ValueError("empty or truncated media record")

    if archive == "picture":
        if data.startswith(b"\xff\xd8\xff"):
            mime = "image/jpeg"
        elif data.startswith(b"\x89PNG\r\n\x1a\n"):
            mime = "image/png"
        elif data.startswith((b"GIF87a", b"GIF89a")):
            mime = "image/gif"
        else:
            raise ValueError("unsupported picture encoding")
    else:
        mime = "audio/mpeg"

    return data, mime


def serve(source):
    source = str(validate_source(source))
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            data, mime = read_media(source, request["archive"], request["name"])
            response = {
                "ok": True,
                "mime": mime,
                "data": base64.b64encode(data).decode("ascii"),
            }
        except Exception as exc:
            response = {"ok": False, "error": str(exc)}
        print(json.dumps(response, separators=(",", ":")), flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="verbum-ldoce5-media")
    parser.add_argument("source", help="Original LDOCE5 data directory")
    args = parser.parse_args(argv)
    try:
        serve(args.source)
        return 0
    except (OSError, ValueError) as exc:
        print(f"verbum-ldoce5-media: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
