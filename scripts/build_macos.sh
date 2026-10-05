#!/usr/bin/env bash
# Build the macOS .app bundle and a .dmg (or zipped .app fallback).
# Run from the repo root:  ./scripts/build_macos.sh
# Requires: python3 with build deps:  python -m pip install -e ".[desktop,build]"
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Generating .icns from PNGs (if iconutil available)"
ICONSET="$ROOT/build/icon.iconset"
ICNS="$ROOT/assets/icons/icon.icns"
if command -v iconutil >/dev/null 2>&1; then
  rm -rf "$ICONSET"; mkdir -p "$ICONSET"
  for s in 16 32 128 256 512; do
    cp "$ROOT/assets/icons/icon_${s}.png" "$ICONSET/icon_${s}x${s}.png" 2>/dev/null || true
  done
  cp "$ROOT/assets/icons/icon_512.png" "$ICONSET/icon_512x512.png" 2>/dev/null || true
  iconutil -c icns "$ICONSET" -o "$ICNS" 2>/dev/null && echo "  wrote $ICNS" || echo "  icns generation skipped"
fi

echo "==> Building .app with PyInstaller"
python3 "$ROOT/scripts/build_desktop.py" --clean

APP="$ROOT/dist/MakeMyFigure.app"
[ -d "$APP" ] || { echo "Build failed: $APP not found"; exit 1; }
# Read the version from the repo root (no path embedded in the Python one-liner, so paths with
# quotes/apostrophes such as OneDrive "... Children's ..." folders work).
VER="$(cd "$ROOT" && python3 -c "from make_my_figure_core.version import __version__; print(__version__)")"

# Optional codesign/notarization only if Apple secrets are present.
if [ -n "${APPLE_DEVELOPER_ID:-}" ]; then
  echo "==> Apple signing configured (APPLE_DEVELOPER_ID set); see docs/CODE_SIGNING.md"
  # codesign --deep --force --options runtime --sign "$APPLE_DEVELOPER_ID" "$APP" || true
else
  echo "==> No Apple developer secrets; producing UNSIGNED .app (expected)."
fi

# Produce a .dmg if create-dmg or hdiutil is available; else zip the .app.
DMG="$ROOT/dist/MakeMyFigure-${VER}.dmg"
if command -v hdiutil >/dev/null 2>&1; then
  echo "==> Creating $DMG"
  rm -f "$DMG"
  hdiutil create -volname "Make My Figure" -srcfolder "$APP" -ov -format UDZO "$DMG" || {
    echo "  hdiutil failed; falling back to zip"; }
fi
if [ ! -f "$DMG" ]; then
  echo "==> Zipping .app as fallback"
  (cd "$ROOT/dist" && zip -r -q "MakeMyFigure-${VER}-macos.zip" "MakeMyFigure.app")
fi
echo "Done."
