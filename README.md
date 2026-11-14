# Verbum

Independent multilingual lexical service and native GTK4/libadwaita dictionary viewer. VLF (Verbum Lexical Format) uses SQLite, FTS5, JSON and content-addressed embedded resources. This repository does not include the original LDOCE5 Viewer archive reader or dictionary data.

## Run

Requires Python 3.9+ (tomli required below 3.11), GTK4, libadwaita and PyGObject for GUI. Run `python3 -m verbum gui`. Existing local registry and VLF files are reused. VLF v1 text remains readable; VLF v2 contains embedded audio and images. Convert legacy Longman archives using the separate GPL converter at https://github.com/mwprado/ldoce5viewer2/tree/dictviewer before using them here. No IDM/SKN reader is included.

BGL import optionally requires PyGlossary 5.x (separately licensed). JSON/JSONL import requires a TOML manifest. See docs/VERBUM.md.

MIT license applies to the original Verbum code, not dictionary data or third-party dependencies. Review dependency licensing before redistribution.
