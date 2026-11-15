# Verbum

Independent multilingual lexical service and native GTK4/libadwaita dictionary viewer.

VLF (Verbum Lexical Format) is Verbum's canonical local format. It uses SQLite, FTS5, JSON and SHA-256 content-addressed resources in one self-contained .vlf file. Audio and images are optional, so the same format supports text-only dictionaries, image-bearing dictionaries, audio-bearing dictionaries, or combinations of them.

See docs/VLF.md for the VLF v2 specification and docs/VERBUM.md for application details.

## Run

Requires Python 3.9+ (tomli required below 3.11), GTK4, libadwaita and PyGObject for the GUI.

~~~sh
python3 -m verbum gui
~~~

Existing local registry and VLF files are reused.

## Importers

The package includes the separate GPL LDOCE5 IDM/SKN converter component and the MIT Verbum application. No proprietary dictionary data is distributed.

BGL import uses separately licensed PyGlossary 5.x on supported Fedora builds. JSON/JSONL import requires a TOML manifest. Legacy Pickle/PKLZ is accepted only for restricted migration into VLF.

VLF can preserve original media and optional derived representations. For example, a future importer may preserve source MP3 bytes while preferring an Ogg/Opus derivative for playback. Conversion does not alter the licensing of the source content.

MIT license applies to the original Verbum code, not dictionary data or third-party dependencies. Review source/content licensing before redistribution.
