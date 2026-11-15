# Fedora-only for now. Requires Python >= 3.12 and GTK 4/libadwaita.
# Override upstream_repo if building before the GitHub repository is renamed.
%{!?upstream_repo:%global upstream_repo verbum}
# Source release tag must exist before building the SRPM.
%global appid io.github.mwprado.Verbum

Name:           verbum
Version:        0.5.0
Release:        7%{?dist}
Summary:        Multilingual dictionary and lexical service for GNOME

License:        MIT
URL:            https://github.com/mwprado/%{upstream_repo}
Source0:        %{url}/archive/refs/tags/verbum-%{version}.tar.gz#/%{name}-%{version}.tar.gz

BuildArch:      noarch
%if 0%{?rhel}
%{error:Verbum packaging is temporarily disabled on EPEL 9/10; build on Fedora only}
%endif

BuildRequires:  python3-devel
BuildRequires:  python3-gobject
BuildRequires:  gobject-introspection
BuildRequires:  python3-cairo
BuildRequires:  gtk4
BuildRequires:  libadwaita
BuildRequires:  desktop-file-utils
BuildRequires:  libappstream-glib
BuildRequires:  shared-mime-info

Requires:       python3 >= 3.12
Requires:       python3-gobject
Requires:       gobject-introspection
Requires:       python3-cairo
Requires:       gtk4
Requires:       libadwaita
Requires:       gstreamer1
Requires:       gstreamer1-plugins-base
Requires:       gstreamer1-plugins-good
Requires:       hicolor-icon-theme
Requires:       shared-mime-info
Requires:       desktop-file-utils
Requires:       xdg-utils
# BGL import is part of the supported GUI functionality.
Requires:       (python3dist(pyglossary) >= 5 with python3dist(pyglossary) < 6)

%description
Verbum is a multilingual lexical service and native GNOME dictionary
application. It imports local dictionaries into Verbum Lexical Format
(VLF), a SQLite-based storage format, and supports ranked lexical
search, spelling suggestions, and contextual Longman audio.

Babylon BGL import requires PyGlossary 5.x at runtime.
Dictionary contents are not distributed with this package.

%prep
%autosetup -n %{upstream_repo}-verbum-%{version}

%build
# Pure Python application; no Qt build or network access needed.

%install
install -d %{buildroot}%{python3_sitelib}/verbum
install -pm0644 verbum/*.py verbum/catalog.toml %{buildroot}%{python3_sitelib}/verbum/

install -d %{buildroot}%{_bindir}
cat > %{buildroot}%{_bindir}/verbum <<'EOF'
#!%{__python3}
from verbum.__main__ import main
raise SystemExit(main())
EOF
chmod 0755 %{buildroot}%{_bindir}/verbum

desktop-file-install --dir=%{buildroot}%{_datadir}/applications data/%{appid}.desktop
install -Dm0644 data/%{appid}.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/%{appid}.svg
install -Dm0644 data/%{appid}.xml %{buildroot}%{_datadir}/mime/packages/%{appid}.xml
install -Dm0644 data/%{appid}.metainfo.xml %{buildroot}%{_datadir}/metainfo/%{appid}.metainfo.xml

%check
%{__python3} -m unittest discover -s tests -p 'test_verbum*.py' -v
%{__python3} -c 'from verbum.gtk import Application; from verbum import resources'
desktop-file-validate %{buildroot}%{_datadir}/applications/%{appid}.desktop
appstream-util validate-relax --nonet %{buildroot}%{_datadir}/metainfo/%{appid}.metainfo.xml
# Test MIME compilation outside the buildroot.
mkdir -p mime-check/packages
cp data/%{appid}.xml mime-check/packages/
update-mime-database mime-check

%files
%license LICENSE
%doc docs/VERBUM.md
%{_bindir}/verbum
%{python3_sitelib}/verbum/
%{_datadir}/applications/%{appid}.desktop
%{_datadir}/icons/hicolor/scalable/apps/%{appid}.svg
%{_datadir}/mime/packages/%{appid}.xml
%{_datadir}/metainfo/%{appid}.metainfo.xml

%changelog
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
