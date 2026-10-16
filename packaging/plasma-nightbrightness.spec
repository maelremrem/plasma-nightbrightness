Name:           plasma-nightbrightness
Version:        0.2.2
Release:        1%{?dist}
Summary:        KDE Plasma 6 scheduled display brightness configuration
License:        MIT
URL:            https://github.com/maelremrem/plasma-nightbrightness
Source0:        %{name}-%{version}.tar.gz

BuildRequires:  cmake
BuildRequires:  ninja-build
BuildRequires:  gcc-c++
BuildRequires:  extra-cmake-modules
BuildRequires:  qt6-qtbase-devel
BuildRequires:  qt6-qtdeclarative-devel
BuildRequires:  qt6-qtpositioning-devel
BuildRequires:  kf6-kcmutils-devel
BuildRequires:  kf6-kcoreaddons-devel
BuildRequires:  kf6-ki18n-devel
BuildRequires:  python3
BuildRequires:  systemd-rpm-macros

Requires:       python3
Requires:       qt6-qttools
Requires:       qt6-qtpositioning
Requires:       qt6-qtlocation
Requires:       geoclue2
Requires:       powerdevil
Requires:       kf6-kirigami
Requires:       kf6-kcmutils

%description
An optional KDE Plasma 6 KCM and user service that follow a
configurable day/night brightness schedule using PowerDevil D-Bus.
The scheduler is disabled by default and never changes brightness
until explicitly enabled through the KDE settings module.

%prep
%autosetup

%build
%cmake -G Ninja
%cmake_build

%install
%cmake_install
install -Dpm 0755 daemon/nightbrightness.py %{buildroot}%{_libexecdir}/nightbrightness-daemon
install -Dpm 0644 systemd/nightbrightness.service %{buildroot}%{_userunitdir}/nightbrightness.service

%check
python3 -m unittest discover -s tests -v
python3 -m py_compile daemon/nightbrightness.py

%files
%license LICENSE
%doc README.md
%{_libdir}/qt6/plugins/plasma/kcms/systemsettings/kcm_nightbrightness.so
%{_datadir}/applications/*nightbrightness*.desktop
%{_libexecdir}/nightbrightness-daemon
%{_libexecdir}/nightbrightness-geolocation
%{_userunitdir}/nightbrightness.service

%changelog
* Fri Oct 16 2026 KDE Night Brightness Contributors - 0.2.2-1
- Fix automatic location parsing when GeoClue2 returns repeated updates
* Thu Oct 15 2026 KDE Night Brightness Contributors - 0.2.1-1
- Add map selector, solar time preview and optional automatic location updates

* Thu Oct 15 2026 KDE Night Brightness Contributors - 0.2.0-1
- Initial RPM candidate for Fedora KDE Plasma 6
