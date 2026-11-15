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


## Unrecoverable media log

Longman imports no longer discard the identity of individual media resources that cannot be recovered safely. When at least one such resource is encountered, Verbum writes a private JSONL recovery queue under `~/.local/share/verbum/logs/` (or `$XDG_DATA_HOME/verbum/logs/`).

Each resource record contains its source archive, logical name, failure reason and initial `pending` status. The log is intended for later batch extraction and testing with alternative decoders or media formats. It is not embedded into the VLF; the VLF separately retains the corrupt resource reference.


## Official LDOCE Online recovery

For a user-owned LDOCE5 installation, an `exa_pron` resource that is present in the IDM/SKN catalog but cannot be recovered safely from a damaged TDZ block can be retried against the official LDOCE Online example-pronunciation media service.

The command is:

~~~text
verbum-ldoce5-recover ~/.local/share/verbum/logs/longman-unrecoverable-*.jsonl
~~~

The helper only handles `exa_pron` MP3 resources. It derives the official URL from the resource basename, downloads the candidate, validates it as MPEG Layer III, calculates SHA-256 and writes it under the private Verbum recovery area:

~~~text
~/.local/share/verbum/recovery/longman/exa_pron/
~~~

The original LDOCE5 IDM/SKN tree and the published VLF are never modified.

Additional candidates may be supplied with repeated `--name` options. This is useful when a damaged TDZ block contains records that were discovered during forensic auditing but were not all present in the original JSONL log.

For the known block 2689 investigation:

~~~text
verbum-ldoce5-recover \
  ~/.local/share/verbum/logs/longman-unrecoverable-*.jsonl \
  --name p008-000599574.mp3 \
  --name p008-000599598.mp3 \
  --name p008-000599625.mp3 \
  --name p008-000599671.mp3 \
  --name p008-000599672.mp3
~~~

Successful records are marked `recovered` in the JSONL log and include `recovered_url`, `recovered_path`, `recovered_size`, `recovered_sha256` and `recovered_at`. Failed records are marked `failed` with the last recovery error and remain retryable by a later invocation.


### Legacy Aurélio homograph markers

Recovered Aurélio/Pickle records may encode the numbered homograph/entry in the lexical key as a trailing `$N# Verbum 0.5.0

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


## Unrecoverable media log

Longman imports no longer discard the identity of individual media resources that cannot be recovered safely. When at least one such resource is encountered, Verbum writes a private JSONL recovery queue under `~/.local/share/verbum/logs/` (or `$XDG_DATA_HOME/verbum/logs/`).

Each resource record contains its source archive, logical name, failure reason and initial `pending` status. The log is intended for later batch extraction and testing with alternative decoders or media formats. It is not embedded into the VLF; the VLF separately retains the corrupt resource reference.


## Official LDOCE Online recovery

For a user-owned LDOCE5 installation, an `exa_pron` resource that is present in the IDM/SKN catalog but cannot be recovered safely from a damaged TDZ block can be retried against the official LDOCE Online example-pronunciation media service.

The command is:

~~~text
verbum-ldoce5-recover ~/.local/share/verbum/logs/longman-unrecoverable-*.jsonl
~~~

The helper only handles `exa_pron` MP3 resources. It derives the official URL from the resource basename, downloads the candidate, validates it as MPEG Layer III, calculates SHA-256 and writes it under the private Verbum recovery area:

~~~text
~/.local/share/verbum/recovery/longman/exa_pron/
~~~

The original LDOCE5 IDM/SKN tree and the published VLF are never modified.

Additional candidates may be supplied with repeated `--name` options. This is useful when a damaged TDZ block contains records that were discovered during forensic auditing but were not all present in the original JSONL log.

For the known block 2689 investigation:

~~~text
verbum-ldoce5-recover \
  ~/.local/share/verbum/logs/longman-unrecoverable-*.jsonl \
  --name p008-000599574.mp3 \
  --name p008-000599598.mp3 \
  --name p008-000599625.mp3 \
  --name p008-000599671.mp3 \
  --name p008-000599672.mp3
~~~

Successful records are marked `recovered` in the JSONL log and include `recovered_url`, `recovered_path`, `recovered_size`, `recovered_sha256` and `recovered_at`. Failed records are marked `failed` with the last recovery error and remain retryable by a later invocation.


 marker, for example `Água$1# Verbum 0.5.0

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


## Unrecoverable media log

Longman imports no longer discard the identity of individual media resources that cannot be recovered safely. When at least one such resource is encountered, Verbum writes a private JSONL recovery queue under `~/.local/share/verbum/logs/` (or `$XDG_DATA_HOME/verbum/logs/`).

Each resource record contains its source archive, logical name, failure reason and initial `pending` status. The log is intended for later batch extraction and testing with alternative decoders or media formats. It is not embedded into the VLF; the VLF separately retains the corrupt resource reference.


## Official LDOCE Online recovery

For a user-owned LDOCE5 installation, an `exa_pron` resource that is present in the IDM/SKN catalog but cannot be recovered safely from a damaged TDZ block can be retried against the official LDOCE Online example-pronunciation media service.

The command is:

~~~text
verbum-ldoce5-recover ~/.local/share/verbum/logs/longman-unrecoverable-*.jsonl
~~~

The helper only handles `exa_pron` MP3 resources. It derives the official URL from the resource basename, downloads the candidate, validates it as MPEG Layer III, calculates SHA-256 and writes it under the private Verbum recovery area:

~~~text
~/.local/share/verbum/recovery/longman/exa_pron/
~~~

The original LDOCE5 IDM/SKN tree and the published VLF are never modified.

Additional candidates may be supplied with repeated `--name` options. This is useful when a damaged TDZ block contains records that were discovered during forensic auditing but were not all present in the original JSONL log.

For the known block 2689 investigation:

~~~text
verbum-ldoce5-recover \
  ~/.local/share/verbum/logs/longman-unrecoverable-*.jsonl \
  --name p008-000599574.mp3 \
  --name p008-000599598.mp3 \
  --name p008-000599625.mp3 \
  --name p008-000599671.mp3 \
  --name p008-000599672.mp3
~~~

Successful records are marked `recovered` in the JSONL log and include `recovered_url`, `recovered_path`, `recovered_size`, `recovered_sha256` and `recovered_at`. Failed records are marked `failed` with the last recovery error and remain retryable by a later invocation.


 or `Água$2# Verbum 0.5.0

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


## Unrecoverable media log

Longman imports no longer discard the identity of individual media resources that cannot be recovered safely. When at least one such resource is encountered, Verbum writes a private JSONL recovery queue under `~/.local/share/verbum/logs/` (or `$XDG_DATA_HOME/verbum/logs/`).

Each resource record contains its source archive, logical name, failure reason and initial `pending` status. The log is intended for later batch extraction and testing with alternative decoders or media formats. It is not embedded into the VLF; the VLF separately retains the corrupt resource reference.


## Official LDOCE Online recovery

For a user-owned LDOCE5 installation, an `exa_pron` resource that is present in the IDM/SKN catalog but cannot be recovered safely from a damaged TDZ block can be retried against the official LDOCE Online example-pronunciation media service.

The command is:

~~~text
verbum-ldoce5-recover ~/.local/share/verbum/logs/longman-unrecoverable-*.jsonl
~~~

The helper only handles `exa_pron` MP3 resources. It derives the official URL from the resource basename, downloads the candidate, validates it as MPEG Layer III, calculates SHA-256 and writes it under the private Verbum recovery area:

~~~text
~/.local/share/verbum/recovery/longman/exa_pron/
~~~

The original LDOCE5 IDM/SKN tree and the published VLF are never modified.

Additional candidates may be supplied with repeated `--name` options. This is useful when a damaged TDZ block contains records that were discovered during forensic auditing but were not all present in the original JSONL log.

For the known block 2689 investigation:

~~~text
verbum-ldoce5-recover \
  ~/.local/share/verbum/logs/longman-unrecoverable-*.jsonl \
  --name p008-000599574.mp3 \
  --name p008-000599598.mp3 \
  --name p008-000599625.mp3 \
  --name p008-000599671.mp3 \
  --name p008-000599672.mp3
~~~

Successful records are marked `recovered` in the JSONL log and include `recovered_url`, `recovered_path`, `recovered_size`, `recovered_sha256` and `recovered_at`. Failed records are marked `failed` with the last recovery error and remain retryable by a later invocation.


. In the modern Aurélio presentation, these numbered entries are shown as separate numbered headword blocks, while the senses inside each block have their own numbering. Verbum removes the implementation marker from the displayed/searchable lemma, preserves the marked form as `source_lemma`, and records the numeric value as `homograph`. When an unmarked `lema_original` is available, it remains the preferred lemma, but a matching marked legacy field is still inspected so the homograph index is not lost.


### Structured legacy dictionary presentation

Legacy PKLZ/Pickle entries are normalized conservatively before publication to VLF. When a flattened definition begins with an unambiguous etymology, grammatical category and a numbered sequence starting at 1, Verbum preserves the complete original text in `raw_definition` and additionally exposes `etymology`, `grammar` and structured `senses`. Sense numbering must increase consecutively; a reset or jump ends the structured region rather than allowing the importer to guess across another embedded headword or section.

The GTK detail view renders homograph numbers beside the headword and numbered senses as compact rows. Unclassified legacy tail material remains visible under “Outras entradas e locuções”, and etymology is presented as its own section.


The “Outras entradas e locuções” section is intentionally compact: only embedded headword/locution titles are exposed as `legacy_entries`. Their definitions remain preserved in `legacy_tail` and `raw_definition` but are not rendered in that section, avoiding an unreadable duplicate wall of text.


The GTK presentation of `legacy_entries` uses a compact three-column navigation grid. Only headword/locution titles are shown; each item is directly actionable and starts a new lexical search when selected. A count and short interaction hint are shown above the grid. Full embedded definitions remain preserved but hidden from this compact navigation section.


### Dictionary identity in the UI

The detail view distinguishes the compact dictionary/source identity from the full edition title. The compact line uses names such as `Aurélio`, `Michaelis` and `LDOCE`; an optional smaller secondary line carries the full edition title. This avoids redundant labels such as “dicionário Aurélio” while retaining edition provenance.

The Michaelis legacy catalog record includes metadata transcribed from the supplied DIC Michaelis Escolar 3.0 about screen: August 2008, Editora Melhoramentos Ltda., Amigo Mouse Software, lexicography coordinated by Clóvis Osvaldo Gregorim, citations selected by Francisco S. Borba and Sebastião Expedito Ignácio, and etymology credited to Mário Eduardo Viaro (USP).
