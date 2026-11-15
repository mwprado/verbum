# Fedora is the supported packaging target for now; EPEL chroots should be disabled in COPR.
# Override upstream_repo if building before the GitHub repository is renamed.
%{!?upstream_repo:%global upstream_repo verbum}
# Source release tag must exist before building the SRPM.
%global appid io.github.mwprado.Verbum

Name:           verbum
Version:        0.5.0
Release:        25%{?dist}
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

desktop-file-install --dir=%{buildroot}%{_datadir}/applications data/%{appid}.desktop
install -Dm0644 data/%{appid}.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/%{appid}.svg
install -Dm0644 data/%{appid}.xml %{buildroot}%{_datadir}/mime/packages/%{appid}.xml
install -Dm0644 data/%{appid}.metainfo.xml %{buildroot}%{_datadir}/metainfo/%{appid}.metainfo.xml

%check
%{__python3} -m unittest discover -s tests -p 'test_verbum*.py' -v
%{__python3} -c 'from verbum.gtk import Application; from verbum import resources'
%{__python3} -c 'from verbum_ldoce5.export import validate_source; from verbum_ldoce5 import idmreader; from verbum_ldoce5.media import read_media'
desktop-file-validate %{buildroot}%{_datadir}/applications/%{appid}.desktop
appstream-util validate-relax --nonet %{buildroot}%{_datadir}/metainfo/%{appid}.metainfo.xml
# Test MIME compilation outside the buildroot.
mkdir -p mime-check/packages
cp data/%{appid}.xml mime-check/packages/
update-mime-database mime-check

%files
%license LICENSE LICENSES/GPL-3.0-or-later.txt
%doc docs/VERBUM.md
%{_bindir}/verbum
%{_bindir}/verbum-ldoce5-export
%{_bindir}/verbum-ldoce5-media
%{python3_sitelib}/verbum/
%{python3_sitelib}/verbum_ldoce5/
%{_datadir}/applications/%{appid}.desktop
%{_datadir}/icons/hicolor/scalable/apps/%{appid}.svg
%{_datadir}/mime/packages/%{appid}.xml
%{_datadir}/metainfo/%{appid}.metainfo.xml

%changelog
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
