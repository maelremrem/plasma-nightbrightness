#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAME=plasma-nightbrightness
VERSION=0.2.2
TOPDIR="$ROOT/.rpmbuild"
if ! command -v dnf >/dev/null 2>&1; then
  echo 'Run this builder on Fedora Linux.' >&2
  exit 1
fi
if [[ "${1:-}" == '--install-deps' ]]; then
  sudo dnf install -y rpm-build cmake ninja-build gcc-c++ extra-cmake-modules \
    qt6-qtbase-devel qt6-qtdeclarative-devel qt6-qtpositioning-devel kf6-kcmutils-devel \
    kf6-kcoreaddons-devel kf6-ki18n-devel python3 systemd-rpm-macros
elif ! command -v rpmbuild >/dev/null 2>&1; then
  echo 'rpmbuild missing. Run: ./build-rpm.sh --install-deps' >&2
  exit 1
fi
mkdir -p "$TOPDIR"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
cp "$ROOT/packaging/${NAME}.spec" "$TOPDIR/SPECS/"
tar --exclude="__pycache__" --exclude="*.pyc" -czf "$TOPDIR/SOURCES/${NAME}-${VERSION}.tar.gz" \
  --transform "s,^,${NAME}-${VERSION}/," \
  -C "$ROOT" CMakeLists.txt LICENSE README.md kcm_nightbrightness.json \
  src ui daemon systemd tests tools
rpmbuild -ba --define "_topdir $TOPDIR" "$TOPDIR/SPECS/${NAME}.spec"
echo
find "$TOPDIR/RPMS" -name "${NAME}-*.rpm" -print
find "$TOPDIR/SRPMS" -name "${NAME}-*.src.rpm" -print
