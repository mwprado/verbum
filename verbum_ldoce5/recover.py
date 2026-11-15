# SPDX-License-Identifier: GPL-3.0-or-later
"""Recover LDOCE5 example audio from the official LDOCE Online service.

This is an operational recovery helper for users who already own/import an
LDOCE5 source. It never modifies the original IDM/SKN files or a published VLF.
Recovered files are written to Verbum's private recovery area and recorded in
the JSONL recovery log.
"""

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .media import _validate_mpeg_audio

MAX_MEDIA_SIZE = 64 * 1024 * 1024
DEFAULT_VERSION = "1.2.93"
OFFICIAL_BASE = "https://www.ldoceonline.com/media/english/exaProns/"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load_log(path):
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows or rows[0].get("record_type") != "import":
        raise ValueError("invalid Verbum recovery log")
    return rows


def _write_log(path, rows):
    temp = path.with_suffix(path.suffix + ".tmp")
    try:
        temp.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
            + "\n",
            encoding="utf-8",
        )
        temp.chmod(0o600)
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def _recovery_root(log_path, output_root=None):
    if output_root is not None:
        return Path(output_root).expanduser().resolve()
    if log_path.parent.name == "logs":
        return log_path.parent.parent / "recovery" / "longman"
    root = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    return root / "verbum" / "recovery" / "longman"


def _safe_leaf(name):
    leaf = Path(name).name
    if (
        not leaf
        or leaf in (".", "..")
        or "/" in leaf
        or "\\" in leaf
        or not leaf.lower().endswith(".mp3")
    ):
        raise ValueError("invalid LDOCE media filename")
    return leaf


def official_exa_pron_url(name, version=DEFAULT_VERSION):
    leaf = _safe_leaf(name)
    return OFFICIAL_BASE + quote(leaf, safe=".-_") + "?version=" + quote(str(version), safe=".")


def _download(url, opener=urlopen):
    request = Request(
        url,
        headers={
            "User-Agent": "Verbum-LDOCE5-Recovery/1.0",
            "Accept": "audio/mpeg,audio/*;q=0.9,*/*;q=0.1",
        },
        method="GET",
    )
    with opener(request, timeout=20) as response:
        data = response.read(MAX_MEDIA_SIZE + 1)
        if len(data) > MAX_MEDIA_SIZE:
            raise ValueError("downloaded media exceeds 64 MiB")
        if not data:
            raise ValueError("empty response")
        return data


def _ensure_extra_rows(rows, names):
    existing_exa = {
        _safe_leaf(row.get("name") or "")
        for row in rows[1:]
        if row.get("record_type") == "resource"
        and row.get("archive") == "exa_pron"
        and row.get("name")
    }
    for name in names:
        leaf = _safe_leaf(name)
        if leaf in existing_exa:
            continue
        rows.append({
            "record_type": "resource",
            "archive": "exa_pron",
            "name": name,
            "media_type": "audio",
            "extension": ".mp3",
            "reason": "manual recovery candidate",
            "status": "pending",
        })
        existing_exa.add(leaf)

    rows[0]["count"] = sum(
        1 for row in rows[1:] if row.get("record_type") == "resource"
    )


def recover_log(log_path, *, version=DEFAULT_VERSION, output_root=None,
                opener=urlopen, extra_names=()):
    log_path = Path(log_path).expanduser().resolve()
    rows = _load_log(log_path)
    _ensure_extra_rows(rows, extra_names)
    root = _recovery_root(log_path, output_root)
    results = []

    for row in rows[1:]:
        if row.get("record_type") != "resource":
            continue
        if row.get("archive") != "exa_pron":
            continue
        if row.get("status") not in ("pending", "failed"):
            continue

        name = row.get("name") or ""
        leaf = _safe_leaf(name)
        url = official_exa_pron_url(leaf, version)
        timestamp = _now()

        try:
            data = _download(url, opener=opener)
            if not _validate_mpeg_audio(data):
                raise ValueError("official response is not valid MPEG Layer III audio")

            target_dir = root / "exa_pron"
            target_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
            target = target_dir / leaf
            temp = target.with_suffix(target.suffix + ".tmp")
            try:
                temp.write_bytes(data)
                temp.chmod(0o600)
                temp.replace(target)
            finally:
                temp.unlink(missing_ok=True)

            row.update({
                "status": "recovered",
                "recovered_at": timestamp,
                "recovered_from": "ldoceonline.com",
                "recovered_url": url,
                "recovered_path": str(target),
                "recovered_mime": "audio/mpeg",
                "recovered_size": len(data),
                "recovered_sha256": hashlib.sha256(data).hexdigest(),
            })
            row.pop("last_recovery_error", None)
            results.append({
                "name": name,
                "status": "recovered",
                "path": str(target),
                "size": len(data),
                "sha256": row["recovered_sha256"],
                "url": url,
            })
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            row.update({
                "status": "failed",
                "last_recovery_at": timestamp,
                "last_recovery_error": str(exc),
                "recovery_url": url,
            })
            results.append({
                "name": name,
                "status": "failed",
                "error": str(exc),
                "url": url,
            })

    _write_log(log_path, rows)
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="verbum-ldoce5-recover",
        description=(
            "Recover unavailable LDOCE5 example audio from the official "
            "LDOCE Online media service without modifying the original source or VLF."
        ),
    )
    parser.add_argument("log", help="Verbum longman-unrecoverable-*.jsonl log")
    parser.add_argument(
        "--name",
        action="append",
        default=[],
        help="additional exa_pron MP3 logical name/basename to try; repeatable",
    )
    parser.add_argument(
        "--version",
        default=DEFAULT_VERSION,
        help="LDOCE Online media version query (default: %(default)s)",
    )
    parser.add_argument(
        "--output-dir",
        help="override private recovery directory",
    )
    args = parser.parse_args(argv)

    try:
        results = recover_log(
            args.log,
            version=args.version,
            output_root=args.output_dir,
            extra_names=args.name,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    if not results:
        print("No pending exa_pron resources to recover.")
        return 0

    failed = 0
    for result in results:
        if result["status"] == "recovered":
            print(
                "RECOVERED",
                result["name"],
                result["size"],
                result["sha256"],
                "->",
                result["path"],
            )
        else:
            failed += 1
            print("FAILED", result["name"], "->", result["error"])

    print(
        "Summary:",
        len(results) - failed,
        "recovered,",
        failed,
        "failed.",
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
