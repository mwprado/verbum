# Fedora is the supported packaging target for now; EPEL chroots should be disabled in COPR.
# Override upstream_repo if building before the GitHub repository is renamed.
%{!?upstream_repo:%global upstream_repo verbum}
# Source release tag must exist before building the SRPM.
%global appid io.github.mwprado.Verbum

Name:           verbum
Version:        0.5.0
Release:        57%{?dist}
Summary:        Multilingual dictionary and lexical service for GNOME

License:        MIT AND GPL-3.0-or-later
URL:            https://github.com/mwprado/%{upstream_repo}
Source0:        %{url}/archive/refs/tags/verbum-%{version}.tar.gz#/%{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-gobject
BuildRequires:  gobject-introspection
BuildRequires:  python3-cairo
BuildRequires:  python3-lxml
BuildRequires:  gtk4
BuildRequires:  libadwaita
BuildRequires:  desktop-file-utils
BuildRequires:  libappstream-glib
BuildRequires:  shared-mime-info

%if 0%{?fedora}
Requires:       python3 >= 3.12
%else
Requires:       python3 >= 3.9
%endif
Requires:       python3-gobject
Requires:       gobject-introspection
Requires:       python3-cairo
Requires:       python3-lxml
Requires:       gtk4
Requires:       libadwaita
Requires:       gstreamer1
Requires:       gstreamer1-plugins-base
Requires:       gstreamer1-plugins-good
Requires:       hicolor-icon-theme
Requires:       shared-mime-info
Requires:       desktop-file-utils
Requires:       xdg-utils
# BGL import is part of the supported Fedora GUI functionality.
# EPEL packaging is temporarily out of scope and should be disabled in COPR.
%if 0%{?fedora}
Requires:       (python3dist(pyglossary) >= 5 with python3dist(pyglossary) < 6)
%endif

%description
Verbum is a multilingual lexical service and native GNOME dictionary
application. It imports local dictionaries into Verbum Lexical Format
(VLF), a SQLite-based storage format, and supports ranked lexical
search, spelling suggestions, and contextual Longman audio.

Babylon BGL import requires PyGlossary 5.x on the supported Fedora builds.
Dictionary contents are not distributed with this package.

%prep
%autosetup -n %{upstream_repo}-verbum-%{version}

%build
# Pure Python application; no Qt build or network access needed.

%install
install -d %{buildroot}%{python3_sitelib}/verbum
install -pm0644 verbum/*.py verbum/catalog.toml %{buildroot}%{python3_sitelib}/verbum/

install -d %{buildroot}%{python3_sitelib}/verbum_ldoce5
install -pm0644 verbum_ldoce5/*.py %{buildroot}%{python3_sitelib}/verbum_ldoce5/

install -d %{buildroot}%{_bindir}
cat > %{buildroot}%{_bindir}/verbum <<'EOF'
#!%{__python3}
from verbum.__main__ import main
raise SystemExit(main())
EOF
chmod 0755 %{buildroot}%{_bindir}/verbum

cat > %{buildroot}%{_bindir}/verbum-ldoce5-export <<'EOF'
#!%{__python3}
from verbum_ldoce5.export import main
raise SystemExit(main())
EOF
chmod 0755 %{buildroot}%{_bindir}/verbum-ldoce5-export

cat > %{buildroot}%{_bindir}/verbum-ldoce5-media <<'EOF'
#!%{__python3}
from verbum_ldoce5.media import main
raise SystemExit(main())
EOF
chmod 0755 %{buildroot}%{_bindir}/verbum-ldoce5-media

cat > %{buildroot}%{_bindir}/verbum-ldoce5-recover <<'EOF'
#!%{__python3}
from verbum_ldoce5.recover import main
raise SystemExit(main())
EOF
chmod 0755 %{buildroot}%{_bindir}/verbum-ldoce5-recover

desktop-file-install --dir=%{buildroot}%{_datadir}/applications data/%{appid}.desktop
install -Dm0644 data/%{appid}.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/%{appid}.svg
install -Dm0644 data/%{appid}.xml %{buildroot}%{_datadir}/mime/packages/%{appid}.xml
install -Dm0644 data/%{appid}.metainfo.xml %{buildroot}%{_datadir}/metainfo/%{appid}.metainfo.xml

%check
%{__python3} -m unittest discover -s tests -p 'test_verbum*.py' -v
%{__python3} -c 'from verbum.gtk import Application; from verbum import resources'
%{__python3} -c 'from verbum_ldoce5.export import validate_source; from verbum_ldoce5 import idmreader; from verbum_ldoce5.media import read_media; from verbum_ldoce5.recover import recover_log'
desktop-file-validate %{buildroot}%{_datadir}/applications/%{appid}.desktop
appstream-util validate-relax --nonet %{buildroot}%{_datadir}/metainfo/%{appid}.metainfo.xml
# Test MIME compilation outside the buildroot.
mkdir -p mime-check/packages
cp data/%{appid}.xml mime-check/packages/
update-mime-database mime-check

%files
%license LICENSE LICENSES/GPL-3.0-or-later.txt
%doc docs/VERBUM.md docs/VLF.md
%{_bindir}/verbum
%{_bindir}/verbum-ldoce5-export
%{_bindir}/verbum-ldoce5-media
%{_bindir}/verbum-ldoce5-recover
%{python3_sitelib}/verbum/
%{python3_sitelib}/verbum_ldoce5/
%{_datadir}/applications/%{appid}.desktop
%{_datadir}/icons/hicolor/scalable/apps/%{appid}.svg
%{_datadir}/mime/packages/%{appid}.xml
%{_datadir}/metainfo/%{appid}.metainfo.xml

%changelog
* Sun Nov 15 2026 Moacyr Prado - 0.5.0-57
- Make the persistent # plus A-Z dictionary index substantially more compact
- Override GNOME button minimum width and horizontal padding only for index tabs
- Let all 27 index tabs share the available width evenly
- Keep horizontal scrolling only as a fallback for genuinely narrow windows
- Preserve the two-row dictionary navigation and full verbete panel

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-56
- Keep the dictionary index visible whenever a specific dictionary is selected
- Fit the compact # plus A-Z index across the available width before scrolling
- Add # as the jump index for numeric and symbolic headwords
- Keep non-Latin alphabetic entries outside # and reachable by sequential arrows
- Add << and >> controls for the first and last headword of the current index
- Keep single left/right arrows for one-headword-at-a-time navigation
- Preserve the full scrollable entry panel above the navigation controls
- Add regression tests for hash and index-boundary navigation

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-55
- Preserve dictionary entries that sort before A or after Z in lexical navigation
- Keep A-Z as jump indices only, not as dictionary boundaries
- Open the true first entry when a dictionary is selected
- Allow previous/next word navigation to cross both A and Z boundaries
- Add regression coverage for numeric and non-Latin headwords

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-54
- Remove Ir para and visual page navigation from dictionary browsing
- Restore the full scrollable entry panel as the primary dictionary view
- Add a bottom dictionary-style index with word arrows above A-Z tabs
- Make left/right arrows move exactly one headword at a time
- Make each A-Z tab open the first headword of that letter
- Treat accented initials such as Á/À/Â/Ã as part of A navigation
- Fetch only the target entry from the VLF for each navigation action
- Keep the normal search permanently in the top header

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-53
- Keep the primary search permanently in the top header
- Replace separate dictionary navigation controls with one compact bottom bar
- Put A-Z, Ir para, previous/next page and page number in the same web-like bar
- Make Ir para open the page containing the exact headword and highlight it
- Keep nearest-page positioning when an exact headword is not present
- Reduce visible dictionary provenance to one muted source line

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-52
- Skip fully empty legacy sequence records before tuple/list entry conversion
- Prevent blank tuple/list records from becoming empty-lemma entries
- Keep non-empty malformed legacy records as hard errors
- Fix the only failing regression test from release 51

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-51
- Allow selecting multiple BGL files in one import operation
- Allow selecting multiple Pickle/PKLZ files in one import operation
- Import selected files sequentially into independent VLF dictionaries
- Continue the batch when one file fails or is already installed
- Show per-file progress and a final imported/skipped/failed summary
- Keep rebuild operations single-source for dictionary identity safety

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-50
- Add alphabet navigation (0-9 and A-Z) to dictionary browsing
- Add an Ir para field for direct lexical repositioning by headword or prefix
- Implement indexed seek-to-page using the existing normalized VLF index
- Keep jumps as repositioning operations rather than search filters
- Preserve Previous/Next pagination after alphabet or direct jumps
- Add regression coverage for lexical seek navigation

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-49
- Browse all headwords when an installed dictionary is selected with an empty search
- Add SQLite LIMIT/OFFSET pagination without loading the full dictionary into memory
- Show 100 headwords per page with total count and Previous/Next navigation
- Keep typed searches unchanged when switching dictionaries
- Add regression coverage for ordered paginated VLF browsing

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-48
- Treat the outer key as authoritative for keyed legacy dictionaries such as VOLP
- Skip blank keyed records that have no embedded lexical lemma instead of aborting import
- Preserve strict errors for non-empty unkeyed malformed records
- Recognize dicionario-abl-volp.pklz as VOLP, pt-BR, orthographic, origin ABL
- Add regression coverage for VOLP-style blank keys and metadata

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-47
- Skip genuinely empty auxiliary records in legacy Pickle/PKLZ containers
- Prevent blank VOLP index records from aborting an otherwise valid import
- Keep non-empty malformed lexical records as hard errors instead of hiding corruption
- Add regression coverage for empty legacy records

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-46
- Use compact source names such as Aurélio, Michaelis and LDOCE in the GTK UI
- Show the full dictionary edition title as a smaller secondary line
- Add supplied Michaelis Escolar 3.0 publication and editorial metadata to the catalog
- Keep full edition titles available in tooltips and provenance metadata

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-45
- Improve Outras entradas e locuções as a compact navigable grid
- Show only related headword titles, with count and a short interaction hint
- Make each related entry directly searchable with one click
- Keep embedded definitions preserved in VLF but hidden from the compact section

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-44
- Show only headword/locution titles under Outras entradas e locuções
- Preserve full embedded definitions in legacy_tail/raw_definition without rendering them
- Extract deduplicated legacy_entries during import for compact presentation
- Add regression coverage for related-entry title extraction

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-43
- Fix double escaping in legacy lexical-structure regular expressions
- Restore grammar detection for forms such as 'Substantivo feminino.'
- Restore numbered-sense detection for sequences beginning with '1.'
- Restore embedded-entry title detection after a numbering reset

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-42
- Fix exact offset when separating embedded legacy headwords after sense numbering resets
- Preserve the complete next headword text without dropping its first character
- Strengthen regression coverage for legacy-tail preservation

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-41
- Organize flattened legacy dictionary entries into conservative lexical structure
- Preserve raw_definition while extracting etymology, grammar and sequential senses
- Stop structural parsing on numbering resets or jumps instead of guessing
- Render homograph index beside the headword and senses as compact numbered rows
- Keep unclassified embedded entries/locutions visible in a separate section
- Present etymology as a dedicated section

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-40
- Preserve Aurélio homograph metadata after legacy lemma normalization
- Align regression tests with the canonical homograph payload field
- Keep numbered senses distinct from numbered homograph/headword blocks

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-39
- Correct Aurélio legacy $N$ semantics: marker identifies numbered homograph/entry
- Keep sense numbering distinct from homograph numbering
- Preserve the marker as homograph and the original marked key as source_lemma
- Recover homograph index from matching marked fields even with unmarked lema_original
- Supersede the temporary sense_index interpretation from release 38

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-38
- Interpret legacy Aurélio $N$ suffixes as acepção indices instead of homographs
- Preserve the numeric marker as sense_index and the marked key as source_lemma
- Recover sense_index from matching marked fields even when lema_original is unmarked
- Remove incorrect homograph metadata from normalized legacy records
- Extend regression coverage for legacy sense-index preservation

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-37
- Fix legacy homograph regex escaping introduced in the Aurélio normalization
- Restore stripping of trailing markers such as $1$ and $3$
- Keep the existing regression tests as the packaging gate

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-36
- Fix RPM install section accidentally executing verbum-ldoce5-recover
- Install the recovery helper only under buildroot during package assembly
- Include verbum-ldoce5-recover in the RPM file manifest

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-35
- Add verbum-ldoce5-recover for official LDOCE Online example-audio recovery
- Read pending/failed exa_pron items from Verbum JSONL recovery logs
- Allow additional MP3 names for batch recovery of a damaged TDZ block
- Validate downloaded MPEG Layer III audio before accepting it
- Store recovered media privately without modifying the original LDOCE5 or VLF
- Record source URL, SHA-256, size, local path and recovery status in JSONL

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-34
- Prefer lema_original when importing recovered legacy dictionary records
- Remove trailing legacy homograph markers such as $1$ and $2$ from searchable lemmas
- Preserve the original marked lemma as source_lemma and numeric homograph metadata
- Keep legitimate punctuation in dictionary headwords unchanged
- Add regression coverage for Aurélio-style marked lemmas

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-33
- Write unrecoverable Longman media to a private JSONL recovery queue
- Record archive, logical name, media type, extension, failure reason and pending status
- Return and report the recovery-log path after import
- Keep recovery logs outside VLF for later extraction and decoder experiments
- Document the recovery-log format and location

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-32
- Advance IDM media catalog scans across any number of skipped compression blocks
- Distinguish unrecoverable source media from genuinely missing resources
- Preserve corrupt media references and diagnostic reason in VLF
- Continue Longman import when an individual source media record is irrecoverable
- Report separate missing_resources and corrupt_resources counts

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-31
- Publish the formal VLF v2 specification
- Support original plus preferred derived media representations in VLF
- Keep original resource bytes addressable by SHA-256 when a derivative is preferred
- Make GTK media rendering depend on media type and MIME instead of Longman archive names
- Support Ogg/Opus and other audio MIME suffixes during playback
- Document text-only, image-only and mixed-media dictionary models

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-30
- Recover complete LDOCE5 records from blocks with a bad zlib trailer
- Never pad or accept records that extend beyond the recovered DEFLATE bytes
- Validate extracted MP3 resources using consecutive MPEG Layer III frames
- Preserve SHA-256 content addressing when media is embedded into VLF

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-29
- Keep error dialogs visually clean with a short user-facing message
- Move technical diagnostics into an expandable Mais informações section
- Show full errors in a selectable scrollable text box
- Keep one-click Copy error inside the expanded details

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-28
- Make GUI error details selectable
- Add one-click Copy error action to clipboard
- Use copyable error dialogs for import, removal and open failures

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-27
- Fix legacy PKLZ top-level lemma-map detection
- Do not collapse dictionaries containing lemmas named palavra, verbete or termo
- Recognize scalar headword fields only when detecting a single legacy entry
- Prefer lema_original metadata when present
- Add regression coverage for Aurélio-style PKLZ records and casa lookup

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-26
- Continue LDOCE5 import when a referenced media file is absent from the source archive
- Preserve missing media references explicitly in VLF instead of silently dropping them
- Embed every media resource that is actually present
- Report the number of missing source resources after import
- Keep corrupt or invalid media as hard import errors

* Sun Nov 15 2026 Moacyr Prado - 0.5.0-25
- Fix Python 3 syntax in PKLZ regression tests
- Encode non-ASCII byte fixtures explicitly as UTF-8
- Keep protocol-0 pickle fixtures ASCII-safe with Unicode escapes

* Sat Nov 14 2026 Moacyr Prado - 0.5.0-24
- Recognize recovered class-state dictionaries as single legacy entries
- Accept definicao/definição legacy Portuguese definition fields
- Correct protocol-0 regression fixtures for non-ASCII text

* Sat Nov 14 2026 Moacyr Prado - 0.5.0-23
- Recover protocol 0/1 class-based legacy Pickle files through inert proxy objects
- Handle copyreg/copy_reg _reconstructor without importing original classes
- Convert recovered instance state directly to JSON-safe VLF data
- Recognize verbete and palavra as legacy Portuguese lemma fields

* Sat Nov 14 2026 Moacyr Prado - 0.5.0-22
- Normalize legacy Pickle/PKLZ records to JSON-safe VLF primitives
- Decode bytes and convert tuples recursively before indexing
- Generate ASCII-safe legacy dictionary identifiers from accented filenames
- Add coverage for accented PKLZ filenames and byte-based records

* Sat Nov 14 2026 Moacyr Prado - 0.5.0-21
- Reproduce original CDB first-inserted precedence for unresolved duplicate media keys
- Prefer XML path disambiguation and identical-content deduplication first
- Avoid false ambiguous-media failures while preserving original LDOCE5 behavior

* Sat Nov 14 2026 Moacyr Prado - 0.5.0-20
- Rebuild LDOCE5 media indexing from first principles
- Preserve every physical SKN occurrence instead of collapsing duplicates
- Follow original archive-specific logical keys for pictures and audio
- Disambiguate XML paths by exact path and suffix
- Treat duplicate physical records with identical content as one resource
- Reject only genuinely conflicting ambiguous media

* Sat Nov 14 2026 Moacyr Prado - 0.5.0-19
- Preserve logical XML paths for LDOCE5 audio resources
- Disambiguate repeated audio basenames using unique path suffixes
- Fall back to basename only when it maps to exactly one SKN record
- Include the failing resource path in media import diagnostics

* Sat Nov 14 2026 Moacyr Prado - 0.5.0-18
- Match original LDOCE5 audio file-map semantics
- Resolve GB/US/example/SFX audio by basename from XML topic
- Keep picture resolution on dirs[0]/filename semantics

* Sat Nov 14 2026 Moacyr Prado - 0.5.0-17
- Match original LDOCE5 picture file-map semantics
- Resolve picture resources as dirs[0]/filename
- Fix thumbnail/fullsize imports such as thumbnail/abacus.jpg

* Sat Nov 14 2026 Moacyr Prado - 0.5.0-16
- Render embedded dictionary illustrations automatically in entry details
- Show LDOCE5 thumbnails in an illustration gallery
- Keep full-size image access available from each illustration

* Sat Nov 14 2026 Moacyr Prado - 0.5.0-15
- Resolve LDOCE5 picture resources by unique logical-path suffix
- Support SKN catalogs with additional internal picture directories
- Keep ambiguous media references rejected instead of selecting arbitrarily

* Sat Nov 14 2026 Moacyr Prado - 0.5.0-14
- Add restricted legacy Pickle/PKLZ importer
- Reject arbitrary Python globals, classes and functions during unpickling
- Normalize common dictionary structures directly into VLF
- Expose Pickle/PKLZ import in GTK and CLI

* Sat Nov 14 2026 Moacyr Prado - 0.5.0-13
- Preserve full LDOCE5 audio paths from XML metadata
- Resolve media by full internal path with safe unique-basename fallback
- Fix ambiguous exa_pron resources during complete imports

* Sat Nov 14 2026 Moacyr Prado - 0.5.0-12
- Restore complete LDOCE5 media extraction
- Embed pronunciation audio, example audio and images in VLF during import
- Add persistent verbum-ldoce5-media helper for efficient resource streaming

* Sat Nov 14 2026 Moacyr Prado - 0.5.0-11
- Fix bundled LDOCE5 converter installation paths
- Package verbum-ldoce5-export and verbum_ldoce5 modules
- Add python3-lxml as a build dependency for converter smoke tests

* Sat Nov 14 2026 Moacyr Prado - 0.5.0-10
- Bundle the GPL LDOCE5 IDM/SKN converter inside the Verbum source and RPM
- Keep the converter as a separate subprocess component from the MIT application
- Add python3-lxml runtime dependency for Longman XML parsing
- Enable GUI-only Longman import with no external package required

* Sat Nov 14 2026 Moacyr Prado - 0.5.0-9
- Add Longman LDOCE5 import through the external GPL converter
- Expose Longman in the GTK import dialog and CLI
- Keep proprietary dictionary data local and unmodified

* Sat Nov 14 2026 Moacyr Prado - 0.5.0-8
- Remove hard spec error for EPEL chroots
- Require PyGlossary 5.x on Fedora builds only
- Keep EPEL temporarily disabled through COPR project settings

* Sat Nov 14 2026 Moacyr Prado - 0.5.0-7
- Temporarily disable EPEL 9 and EPEL 10 builds
- Make PyGlossary 5.x a mandatory runtime dependency
- Target Fedora with Python 3.12 or newer

* Sat Nov 14 2026 Moacyr Prado - 0.5.0-6
- Keep PyGlossary as a weak dependency until a provider exists in Cangaceiro
- Preserve Verbum installation on Fedora and EPEL without PyGlossary
- Let DNF install PyGlossary automatically when the repository provides it

* Sat Nov 14 2026 Moacyr Prado - 0.5.0-5
- Make PyGlossary a required runtime dependency for Babylon BGL import
- Use the Python 3.9-compatible PyGlossary 4.x line on EPEL 9
- Use PyGlossary 5.x on EPEL 10 and Fedora

* Sat Nov 14 2026 Moacyr Prado - 0.5.0-4
- Support EPEL 9 system Python 3.9 with the tomli backport
- Retain Cairo introspection dependencies and all build tests

* Sat Nov 14 2026 Moacyr Prado - 0.5.0-3
- Require GObject introspection typelibs and Python Cairo in build and runtime environments
- Fix GTK import smoke test in minimal Fedora 45 Mock chroots

* Sat Nov 14 2026 Moacyr Prado - 0.5.0-2
- Add reproducible SCM source build for COPR

* Sat Nov 14 2026 Moacyr Prado - 0.5.0-1
- Initial independent Verbum RPM packaging
- Include GNOME launcher, SVG icon, AppStream metadata and BGL MIME integration
- Read embedded VLF resources without the legacy archive reader
