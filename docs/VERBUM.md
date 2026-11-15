# Verbum 0.5.0

Verbum is a native GTK4/libadwaita lexical viewer and importer. Its canonical local format is VLF (Verbum Lexical Format).

The complete VLF v2 specification is in docs/VLF.md.

## VLF

VLF v2 is a self-contained SQLite file containing:

- dictionary manifest metadata;
- lexical entries stored as JSON;
- exact/prefix indexes and FTS5 search;
- content-addressed binary resources;
- optional audio and images;
- optional multiple representations of one logical media resource.

Media is not mandatory. A dictionary may contain only text, text plus images, text plus audio, or all of them.

Resources are deduplicated by SHA-256. When an importer provides multiple representations, VLF can preserve the original bytes and point normal playback/display to a preferred derivative, such as Ogg/Opus, without discarding the original.

## LDOCE5

The GPL LDOCE5 IDM/SKN converter is bundled with the Verbum package as a separate component. Proprietary dictionary data is never distributed with Verbum.

LDOCE5 imports preserve lexical content and embed available audio/images into VLF. Media referenced by the lexical source but absent from the physical archive is recorded explicitly as missing.

The LDOCE5 media reader also validates extracted MPEG Layer III records. For source blocks with a damaged zlib trailer, Verbum may recover a record from the raw DEFLATE stream only when the complete requested record is present in the recovered bytes. Missing bytes are never fabricated.

## Legacy dictionaries

Legacy PKL/PKLZ input is supported only as a migration source. Verbum uses a restricted unpickler and immediately converts recovered data into VLF. Pickle is not an operational Verbum format.

BGL import uses PyGlossary 5.x on supported Fedora builds.

## Local usage

~~~sh
python3 -m verbum list
python3 -m verbum search água
python3 -m verbum gui
python3 -m verbum install-desktop --default-bgl
~~~

Existing databases remain under ~/.local/share/verbum, or XDG_DATA_HOME/verbum when XDG_DATA_HOME is defined.

## Source independence

The intended architecture is:

~~~text
source formats -> importers -> VLF -> Verbum
~~~

Source formats include BGL, LDOCE5 IDM/SKN, legacy PKLZ, JSON/JSONL and future structured importers. Once resources are embedded successfully, the VLF is self-contained and normal use does not depend on the original dictionary directory.

Do not redistribute imported dictionary content unless its license permits redistribution.
