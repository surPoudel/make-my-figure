#!/usr/bin/env bash
# Build the Linux desktop app and package it as an AppImage (and a tar.gz fallback).
# Run from the repo root:  ./scripts/build_linux.sh
# Requires: python3 with build deps:  python -m pip install -e ".[desktop,build]"
# Optional AppImage: appimagetool on PATH (downloaded in CI).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Building app folder with PyInstaller"
python3 "$ROOT/scripts/build_desktop.py" --clean

APPDIR_SRC="$ROOT/dist/MakeMyFigure"
[ -d "$APPDIR_SRC" ] || { echo "Build failed: $APPDIR_SRC not found"; exit 1; }

# Portable tar.gz fallback (always produced).
echo "==> Creating portable tarball"
(cd "$ROOT/dist" && tar czf MakeMyFigure-linux.tar.gz MakeMyFigure)

# Assemble an AppDir for AppImage.
APPDIR="$ROOT/dist/MakeMyFigure.AppDir"
rm -rf "$APPDIR"; mkdir -p "$APPDIR/usr/bin"
cp -r "$APPDIR_SRC/." "$APPDIR/usr/bin/"
cp "$ROOT/assets/icons/icon_256.png" "$APPDIR/makemyfigure.png" 2>/dev/null || true

cat > "$APPDIR/MakeMyFigure.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Make My Figure
Exec=MakeMyFigure
Icon=makemyfigure
Categories=Science;Education;Graphics;
DESKTOP

cat > "$APPDIR/AppRun" <<'APPRUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/MakeMyFigure" "$@"
APPRUN
chmod +x "$APPDIR/AppRun"

if command -v appimagetool >/dev/null 2>&1; then
  echo "==> Building AppImage"
  ( cd "$ROOT/dist" && ARCH="$(uname -m)" appimagetool "MakeMyFigure.AppDir" "MakeMyFigure.AppImage" ) \
    && echo "  wrote dist/MakeMyFigure.AppImage" || echo "  appimagetool failed; tarball available"
else
  echo "==> appimagetool not found; skipping AppImage (tarball available)."
fi
echo "Done."
