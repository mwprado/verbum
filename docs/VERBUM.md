# Verbum 0.5.0

VLF v2 uses SQLite metadata, entries, FTS5 search_index and resources (sha256, mime, content). A media reference in an entry payload contains sha256 and optionally fullsize_sha256. The reader accesses resources only through SQLite. VLF v1 text is supported, but external media must be converted first.

## Local usage

```sh
python3 -m verbum list
python3 -m verbum search água
python3 -m verbum gui
python3 -m verbum install-desktop --default-bgl
```

Existing databases remain in ~/.local/share/verbum (or XDG_DATA_HOME/verbum). No reimport is required for a registered VLF v2. To rebuild Longman, use the separate GPL converter in the old repository. Do not remove original archives until conversion has been validated.

Optional BGL adapter uses separately licensed PyGlossary 5.x. Install in a virtual environment with system-site-packages for GTK. No proprietary dictionary data is distributed. RPM SPEC: package/verbum.spec; source tag verbum-0.5.0. The default MIME association is opt-in.
