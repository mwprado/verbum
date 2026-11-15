# Verbum Lexical Format (VLF) — Specification

Status: VLF version 2  
Container: SQLite 3  
Default extension: .vlf  
Character model: Unicode, JSON text encoded as UTF-8 by SQLite/Python  
Current SQLite user_version: 2

## 1. Purpose

VLF is the canonical local dictionary format used by Verbum. It is designed to:

- store lexical entries, metadata, search indexes and binary resources in one self-contained file;
- preserve source provenance without depending on the original source after import;
- support text-only dictionaries, image-bearing dictionaries, audio-bearing dictionaries, or any combination of those;
- keep media content-addressed by SHA-256 and deduplicated;
- preserve original media while allowing optional derived representations, including open playback formats;
- remain independent from source formats such as BGL, IDM/SKN, Pickle, JSON, TEI or Wiktionary dumps.

VLF is a data format. It does not embed executable Python objects, plugins, scripts or arbitrary code.

## 2. File structure

A VLF v2 file is a SQLite database with the following schema:

~~~sql
PRAGMA user_version=2;

CREATE TABLE metadata (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE entries (
    id         INTEGER PRIMARY KEY,
    lemma      TEXT NOT NULL,
    normalized TEXT NOT NULL,
    language   TEXT NOT NULL,
    payload    TEXT NOT NULL
);

CREATE TABLE resources (
    sha256  TEXT PRIMARY KEY,
    mime    TEXT NOT NULL,
    content BLOB NOT NULL
);

CREATE INDEX entries_normalized
    ON entries(normalized);

CREATE VIRTUAL TABLE search_index USING fts5(
    lemma,
    body,
    tokenize='unicode61 remove_diacritics 0'
);
~~~

The schema is intentionally small. Lexical structures and media references are extensible JSON objects inside entries.payload.

## 3. Metadata manifest

The metadata table MUST contain:

~~~text
key = "manifest"
~~~

Its value is a JSON object.

Required manifest fields:

- title: human-readable dictionary title;
- origin: stable source identifier;
- language: primary language identifier;
- function: principal lexical function;
- license: source/content license label.

The fields language, origin and function use lowercase identifier tokens matching:

~~~text
[a-z0-9]+(?:-[a-z0-9]+)*
~~~

Examples:

~~~text
pt-br
en
longman
wiktionary
general
learner
orthographic
~~~

The canonical dictionary slug is:

~~~text
language-origin-function[-edition]
~~~

The manifest also contains:

- id: UUID identifying the installed dictionary;
- slug: canonical dictionary slug;
- access: normally local for imported VLF files;
- distribution: source distribution/import metadata;
- format_version: integer 2.

Optional manifest fields include:

- edition;
- languages;
- functions;
- license_type;
- source_path;
- source_format;
- capabilities;
- source hashes or other provenance fields.

source_path is provenance only. A correctly built self-contained VLF MUST NOT require the original source path for resources that were successfully embedded.

## 4. Entries

Each entries.payload value is a JSON object.

Every entry MUST contain a non-empty lemma string.

language defaults to the manifest language when omitted by the importer.

Common lexical fields include:

- lemma;
- language;
- grammar;
- variants;
- senses;
- definition;
- definitions;
- examples;
- example_details;
- pronunciation_indices;
- media;
- source.

Importers MAY add additional JSON fields when needed to preserve source semantics.

The normalized column is generated from lemma using Unicode NFC, case folding and surrounding whitespace removal.

## 5. Search index

search_index is an FTS5 index.

The searchable body is produced from the lexical payload while excluding:

- source;
- media.

This keeps large provenance blobs and binary-resource references out of full-text search.

Exact and prefix lookup use entries.normalized.

## 6. Binary resources

All embedded binary resources are stored in the resources table.

A resource is identified by:

~~~text
SHA-256(content)
~~~

The SHA-256 hexadecimal digest is the primary key.

Current accepted resource MIME families are:

~~~text
audio/*
image/*
~~~

A single resource MUST NOT exceed 64 MiB.

Identical binary content is stored only once even when referenced by multiple entries.

## 7. Media is optional

VLF does not require audio, images or any other media.

These are all valid VLF dictionaries:

~~~text
text only
text + images
text + audio
text + images + audio
~~~

A source therefore MUST NOT be considered incomplete merely because it has no audio or no images.

This is important for future importers such as Wiktionary/Wiktionary-derived data, where available media can vary by entry and by source dump.

## 8. Media references

An entry may contain:

~~~json
{
  "media": [
    {
      "type": "audio",
      "archive": "source-specific-name",
      "name": "original-resource-name",
      "sha256": "preferred-resource-sha256",
      "mime": "audio/mpeg"
    }
  ]
}
~~~

archive and name preserve source-level identity. They are provenance fields and do not imply that the original archive is required after successful import.

sha256 identifies the preferred embedded representation.

mime records the MIME type associated with that preferred representation.

For images, a source may additionally provide:

~~~json
{
  "type": "image",
  "archive": "picture",
  "name": "thumbnail/example.jpg",
  "sha256": "...",
  "mime": "image/jpeg",
  "fullsize": "fullsize/example.jpg",
  "fullsize_sha256": "...",
  "fullsize_mime": "image/jpeg"
}
~~~

## 9. Missing source resources

A lexical source may reference media that is physically absent.

VLF preserves that fact explicitly rather than silently dropping the reference.

For a missing primary resource:

~~~json
{
  "missing": true
}
~~~

For a missing full-size image:

~~~json
{
  "fullsize_missing": true
}
~~~

A missing resource MUST NOT have a fabricated SHA-256.

A corrupt or structurally invalid resource is different from a missing resource and SHOULD remain an import error unless the importer can recover and validate the requested record deterministically.

## 10. Multiple representations

VLF v2 supports multiple representations of the same logical media resource without changing the SQLite schema.

A loader may preserve the original bytes and additionally embed derived forms.

Example:

~~~json
{
  "type": "audio",
  "archive": "exa_pron",
  "name": "example.mp3",

  "sha256": "sha256-of-preferred-ogg-opus",
  "mime": "audio/ogg",

  "original_sha256": "sha256-of-original-mp3",
  "original_mime": "audio/mpeg",

  "representations": [
    {
      "role": "original",
      "sha256": "sha256-of-original-mp3",
      "mime": "audio/mpeg"
    },
    {
      "role": "playback",
      "sha256": "sha256-of-preferred-ogg-opus",
      "mime": "audio/ogg",
      "codec": "opus",
      "container": "ogg",
      "lossy": true,
      "preferred": true
    }
  ]
}
~~~

Rules:

- the original representation SHOULD be preserved when a lossy source is transcoded;
- sha256 points to the preferred representation used by the normal reader;
- original_sha256 identifies the preserved source bytes when the preferred representation differs;
- every representation is stored independently in resources and deduplicated by SHA-256;
- at most one derived representation may be marked preferred;
- representations are optional;
- a dictionary containing only the original resource remains valid VLF v2.

The current recommended open audio derivative for speech is Ogg/Opus.

Automatic MP3-to-Opus transcoding is not required by VLF. Importers may provide it when appropriate. This avoids forcing lossy-to-lossy conversion or making large imports unnecessarily expensive.

## 11. Image representations

The same representation mechanism can be used for images.

For example, an importer may preserve a source JPEG or PNG and additionally provide a derived WebP or another supported representation.

The preferred representation MAY differ from the source original.

Full-size images may use the corresponding fields:

- fullsize_sha256;
- fullsize_mime;
- fullsize_original_sha256;
- fullsize_original_mime;
- fullsize_representations.

## 12. Resource validation

Before a binary resource is accepted, an importer SHOULD validate as much of the source format as is practical.

At minimum Verbum validates:

- resource is non-empty;
- resource size is within the VLF limit;
- MIME belongs to an accepted family;
- SHA-256 is computed from the exact bytes stored.

Source-specific importers can apply stricter checks.

For LDOCE5 audio, Verbum additionally validates MPEG Layer III structure after extraction.

If a damaged zlib wrapper contains a recoverable raw DEFLATE stream, Verbum may recover a requested record only when the complete record lies inside the recovered bytes. Missing bytes are never fabricated or padded.

## 13. Integrity

A VLF publisher MUST run:

~~~sql
PRAGMA integrity_check;
~~~

before publication.

A valid publication requires the result:

~~~text
ok
~~~

Verbum creates a temporary database, validates it, then publishes it into the dictionary registry. Rebuild operations publish a new generation rather than modifying the active VLF in place.

## 14. Provenance

VLF SHOULD preserve sufficient provenance to answer:

- which source produced the entry;
- which source resource produced an embedded binary;
- which conversion/importer produced a derived representation;
- which bytes were preserved.

Source-specific raw metadata may be retained inside entry.source.

For imported XML sources, preserving the original XML fragment or a source identifier is permitted when useful.

## 15. Licensing

The VLF container format does not grant rights over dictionary content.

The license of:

- Verbum software;
- source dictionary text;
- images;
- audio;
- derived resources;

must be considered separately.

Transcoding a proprietary audio resource into Ogg/Opus does not change the copyright or redistribution rights of the source content.

## 16. Security

VLF is intentionally data-only.

Importers MUST NOT require arbitrary executable objects to remain in the VLF.

Legacy Pickle input is migration-only and is read through the restricted Verbum importer. Pickle is not a VLF storage mechanism.

Binary resources are retrieved by SHA-256 from the local SQLite database.

## 17. Compatibility

PRAGMA user_version=2 identifies the current physical SQLite schema.

Adding optional JSON fields to entry payloads does not by itself require a user_version change.

A future incompatible change to table structure, required fields or resource addressing MUST increment the physical format version and provide an explicit migration path.

Readers SHOULD ignore unknown optional JSON fields.

## 18. Canonical import model

The intended architecture is:

~~~text
BGL / IDM-SKN / PKLZ / JSON / TEI / future Wiktionary importer
                         |
                         v
                    importers
                         |
                         v
                       VLF
                         |
                         v
                      Verbum
~~~

VLF is the canonical operational and preservation format. Source formats remain import formats, not runtime dependencies.


## 19. Operational recovery logs

Recovery logs are not part of the VLF container.

When a source resource is referenced but cannot be recovered safely, Verbum may preserve the corrupt reference in the VLF and additionally write a private JSON Lines recovery queue under:

~~~text
$XDG_DATA_HOME/verbum/logs/
~~~

or, when XDG_DATA_HOME is unset:

~~~text
~/.local/share/verbum/logs/
~~~

Current Longman logs use names such as:

~~~text
longman-unrecoverable-YYYYMMDDTHHMMSS.ffffffZ.jsonl
~~~

The first JSON object describes the import. Subsequent objects describe individual resources.

Example:

~~~json
{"record_type":"resource","archive":"exa_pron","name":"p008_000/example.mp3","media_type":"audio","extension":".mp3","reason":"unrecoverable media record","status":"pending"}
~~~

These logs are intentionally external to VLF because they are a maintenance and recovery work queue. They can later be consumed by diagnostic extractors, alternative decoders, transcoding experiments or repair tools without altering the published dictionary database.

The VLF itself remains authoritative about the lexical entry and records the unavailable resource with corrupt/corrupt_reason fields.


### Recovery status extension

Operational JSONL recovery records may transition from `pending` to `recovered` or `failed`. A recovered record may contain the official source URL, private recovered path, byte size, MIME type, SHA-256 and UTC recovery timestamp. These fields remain external operational metadata and do not change the VLF schema.
