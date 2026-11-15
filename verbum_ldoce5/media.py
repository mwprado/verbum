# SPDX-License-Identifier: GPL-3.0-or-later
"""Read LDOCE5 binary media through a deterministic archive index."""
import argparse
import base64
import hashlib
import json
import sys
import zlib
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from . import idmreader
from .export import validate_source

AUDIO_ARCHIVES = frozenset(("gb_hwd_pron", "us_hwd_pron", "exa_pron", "sfx", "sound"))
MEDIA_ARCHIVES = AUDIO_ARCHIVES | {"picture"}


_MPEG1_L3_BITRATES = (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0)
_MPEG2_L3_BITRATES = (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0)
_MPEG_SAMPLE_RATES = (44100, 48000, 32000)


def _mpeg_frame_length(data, offset):
    """Return an MPEG Layer III frame length, or None for an invalid header."""
    if offset < 0 or offset + 4 > len(data):
        return None
    b0, b1, b2, _b3 = data[offset:offset + 4]
    if b0 != 0xFF or (b1 & 0xE0) != 0xE0:
        return None

    version = (b1 >> 3) & 0x03
    layer = (b1 >> 1) & 0x03
    bitrate_index = (b2 >> 4) & 0x0F
    sample_index = (b2 >> 2) & 0x03
    padding = (b2 >> 1) & 0x01

    # MP3 = MPEG Layer III.  Version 01 and sample-rate index 11 are reserved.
    if version == 0x01 or layer != 0x01 or sample_index == 0x03:
        return None
    if bitrate_index in (0, 0x0F):
        return None

    if version == 0x03:  # MPEG-1
        bitrate = _MPEG1_L3_BITRATES[bitrate_index] * 1000
        sample_rate = _MPEG_SAMPLE_RATES[sample_index]
        return (144 * bitrate) // sample_rate + padding

    # MPEG-2 / MPEG-2.5 Layer III
    bitrate = _MPEG2_L3_BITRATES[bitrate_index] * 1000
    divisor = 2 if version == 0x02 else 4
    sample_rate = _MPEG_SAMPLE_RATES[sample_index] // divisor
    return (72 * bitrate) // sample_rate + padding


def _id3v2_end(data):
    if not data.startswith(b"ID3") or len(data) < 10:
        return 0
    size_bytes = data[6:10]
    if any(value & 0x80 for value in size_bytes):
        return 0
    size = 0
    for value in size_bytes:
        size = (size << 7) | value
    end = 10 + size
    return end if end <= len(data) else 0


def _validate_mpeg_audio(data):
    """Sanity-check extracted MP3 bytes without requiring an external decoder.

    Exact record length is checked separately.  Here we require at least two
    consecutive valid Layer III frames near the beginning, after an optional
    ID3v2 tag.  This catches wrong slices/offsets while accepting normal VBR MP3.
    """
    start = _id3v2_end(data)
    search_end = min(len(data) - 4, start + 4096)
    for pos in range(start, max(start, search_end) + 1):
        first = _mpeg_frame_length(data, pos)
        if not first:
            continue
        second_pos = pos + first
        second = _mpeg_frame_length(data, second_pos)
        if second and second_pos + second <= len(data):
            return True
    return False


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


def _append(index, key, location):
    key = key.strip("/")
    if key and location not in index[key]:
        index[key].append(location)


@lru_cache(maxsize=16)
def _archive_index(source, archive, signature):
    """Build a lossless index.

    The original viewer's filemap collapses resources to archive-specific
    logical names.  We retain those logical names *and* the complete physical
    IDM/SKN path so duplicate basenames can be disambiguated safely.
    """
    logical = defaultdict(list)
    full = defaultdict(list)
    basename = defaultdict(list)

    for dirs, name, location in idmreader.list_files(source, archive):
        clean_dirs = tuple(part for part in dirs if part)
        physical = "/".join((*clean_dirs, name))
        _append(full, physical, location)
        _append(basename, name, location)

        if archive == "picture" and clean_dirs:
            # Exact rule used by the original LDOCE5 filemap.
            _append(logical, clean_dirs[0] + "/" + name, location)
        else:
            # Audio and other binary assets use the filename in the original
            # filemap, even if the XML topic contains a deeper hierarchy.
            _append(logical, name, location)

    return (
        {key: tuple(value) for key, value in logical.items()},
        {key: tuple(value) for key, value in full.items()},
        {key: tuple(value) for key, value in basename.items()},
    )


def _unique_locations(locations):
    seen = set()
    result = []
    for location in locations:
        if location not in seen:
            seen.add(location)
            result.append(location)
    return tuple(result)


def _candidate_sets(source, archive, name, signature):
    logical, full, basename = _archive_index(source, archive, signature)
    requested = name.strip("/")
    parts = tuple(part for part in requested.split("/") if part)

    # 1. Exact physical path, if XML happens to match the SKN hierarchy.
    exact = _unique_locations(full.get(requested, ()))
    if exact:
        yield "exact", exact

    # 2. Archive-specific canonical key used by the original filemap.
    canonical = _unique_locations(logical.get(requested, ()))
    if canonical:
        yield "logical", canonical

    # 3. Preserve the XML hierarchy as a suffix.  SKN archives may have one
    # or more leading physical directories absent from the XML topic.
    if parts:
        for width in range(len(parts), 1, -1):
            tail = "/".join(parts[-width:])
            suffix = "/" + tail
            matches = []
            for path, locations in full.items():
                if path == tail or path.endswith(suffix):
                    matches.extend(locations)
            matches = _unique_locations(matches)
            if matches:
                yield "suffix:" + tail, matches

    # 4. Original viewer compatibility: basename lookup.
    leaf = parts[-1] if parts else requested
    by_name = _unique_locations(basename.get(leaf, ()))
    if by_name:
        yield "basename", by_name


@lru_cache(maxsize=4096)
def _location_digest(source, archive, signature, location):
    try:
        with idmreader.ArchiveReader(source, archive) as reader:
            data = reader.read(location)
    except zlib.error as exc:
        raise ValueError("unrecoverable media record") from exc
    if not data or len(data) != location[3]:
        raise ValueError("empty or truncated media record")
    return hashlib.sha256(data).digest()


def _collapse_identical(source, archive, signature, locations):
    """Return one location when all candidates contain identical bytes."""
    locations = _unique_locations(locations)
    if len(locations) <= 1:
        return locations[0] if locations else None
    digests = {
        _location_digest(source, archive, signature, location)
        for location in locations
    }
    if len(digests) == 1:
        return locations[0]
    return None


def _resolve_location(source, archive, name, signature):
    diagnostics = []
    original_fallback = None

    for rule, locations in _candidate_sets(source, archive, name, signature):
        if len(locations) == 1:
            return locations[0], rule

        location = _collapse_identical(source, archive, signature, locations)
        if location is not None:
            return location, rule + ":duplicate-identical"

        diagnostics.append((rule, len(locations)))

        # The original LDOCE5 filemap stores duplicate CDB keys in SKN scan
        # order. CDBReader starts at the common hash slot, therefore the
        # first inserted duplicate is the value returned by the original
        # application. Preserve that deterministic behavior only as the
        # final fallback, after path-aware disambiguation and byte-level
        # deduplication have both failed.
        if rule in ("logical", "basename") and original_fallback is None:
            original_fallback = locations[0]

    if original_fallback is not None:
        return original_fallback, "original-cdb-first"

    detail = ", ".join(f"{rule}={count}" for rule, count in diagnostics)
    raise ValueError(
        "missing media resource: "
        + archive + "/" + name
        + (f" [candidates: {detail}]" if detail else "")
    )


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
    location, _rule = _resolve_location(source, archive, name, signature)

    if any(value < 0 for value in location) or location[3] > 64 * 1024 * 1024:
        raise ValueError("invalid media record size")

    try:
        with idmreader.ArchiveReader(source, archive) as reader:
            data = reader.read(location)
    except zlib.error as exc:
        raise ValueError("unrecoverable media record") from exc
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
        if not _validate_mpeg_audio(data):
            raise ValueError("invalid MPEG audio record")
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
