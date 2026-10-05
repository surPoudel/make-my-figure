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
# Read the version from the repo root (no path embedded in the Python one-liner, so paths with
# quotes/apostrophes such as OneDrive "... Children's ..." folders work).
VER="$(cd "$ROOT" && python3 -c "from make_my_figure_core.version import __version__; print(__version__)")"
ARCH_TAG="$(uname -m)"

# Qt's xcb platform plugin is dlopen()ed at startup on every X11 desktop, and it
# links against a set of libxcb/libxkbcommon libraries that PyInstaller does not
# always bundle (it can only bundle what exists on the build machine). If any of
# them is absent the app aborts before drawing a window:
#   "Could not load the Qt platform plugin xcb ... even though it was found."
# That is exactly how v1.1.1 shipped an AppImage that could not start.
# Copy what the plugin needs into the bundle, then refuse to ship a build that is
# still missing one. This runs before the tarball is packed, so the tar.gz and the
# AppImage (assembled from this same folder) are both self-contained.
#
# HOST_LIBS are deliberately NOT bundled; they must come from the host:
#   * glibc and the dynamic loader — mixing a bundled glibc with the host's loader
#     is a well-known way to break an AppImage;
#   * the GL stack — it has to match the host's graphics driver;
#   * core X11/XCB client libs — present anywhere there is an X server at all.
# This mirrors the exclusion list AppImage tooling uses.
host_lib() {
  case "$1" in
    libc.so.*|libm.so.*|libdl.so.*|librt.so.*|libpthread.so.*|ld-linux*) return 0 ;;
    libGL.so.*|libEGL.so.*|libGLdispatch.so.*|libGLX.so.*|libglapi.so.*|libdrm.so.*) return 0 ;;
    libX11.so.*|libX11-xcb.so.*|libxcb.so.*) return 0 ;;
  esac
  return 1
}

QT_XCB="$APPDIR_SRC/_internal/PySide6/Qt/plugins/platforms/libqxcb.so"
if [ -f "$QT_XCB" ]; then
  LIBDIR="$APPDIR_SRC/_internal"
  echo "==> Bundling the Qt xcb platform plugin's libraries"
  { ldd "$QT_XCB" 2>/dev/null || true; } | awk '/=> \//{print $3}' | while read -r lib; do
    base="$(basename "$lib")"
    host_lib "$base" && continue
    [ -e "$LIBDIR/$base" ] || cp -Lv "$lib" "$LIBDIR/"
  done

  # Verify by PRESENCE IN THE BUNDLE, not by whether the build machine can resolve
  # it: the builder has these libraries installed, so an `ldd` check here would
  # pass against the host's copies and tell us nothing about the shipped artifact.
  echo "==> Verifying the xcb plugin's libraries are inside the bundle"
  missing=""
  for needed in $(readelf -d "$QT_XCB" 2>/dev/null | sed -n 's/.*NEEDED.*\[\(.*\)\]/\1/p'); do
    host_lib "$needed" && continue
    # Search the whole bundle: PyInstaller keeps Qt's own libraries under
    # _internal/PySide6/Qt/lib/ rather than at the top of _internal, so looking
    # only in $LIBDIR would report them missing and fail a perfectly good build.
    [ -n "$(find "$APPDIR_SRC" -name "$needed" -print -quit 2>/dev/null)" ] \
      || missing="$missing $needed"
  done
  if [ -n "$missing" ]; then
    echo "ERROR: the Qt xcb plugin needs libraries that are not in the bundle:" >&2
    for m in $missing; do echo "  - $m" >&2; done
    echo "Install them on the build machine (see the apt-get list in" >&2
    echo ".github/workflows/build_desktop_releases.yml) and rebuild." >&2
    exit 1
  fi
  echo "  all bundled"
else
  echo "==> WARNING: libqxcb.so not found in the build; skipping the xcb check" >&2
fi

# Portable tar.gz fallback (always produced).
echo "==> Creating portable tarball"
(cd "$ROOT/dist" && tar czf "MakeMyFigure-${VER}-linux-${ARCH_TAG}.tar.gz" MakeMyFigure)

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
# The Qt xcb plugin's libraries are bundled in _internal. PyInstaller's RPATH
# normally resolves them, but the plugin is dlopen()ed at startup, so state the
# search path explicitly instead of depending on that.
LD_LIBRARY_PATH="$HERE/usr/bin/_internal${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LD_LIBRARY_PATH
exec "$HERE/usr/bin/MakeMyFigure" "$@"
APPRUN
chmod +x "$APPDIR/AppRun"

if command -v appimagetool >/dev/null 2>&1; then
  echo "==> Building AppImage"
  # APPIMAGE_EXTRACT_AND_RUN: appimagetool is itself an AppImage, and the build
  # machine may have no FUSE. Extracting it avoids needing libfuse on the builder
  # (it does not affect the runtime embedded in the AppImage we produce).
  ( cd "$ROOT/dist" && ARCH="$(uname -m)" APPIMAGE_EXTRACT_AND_RUN=1 \
      appimagetool "MakeMyFigure.AppDir" "MakeMyFigure-${VER}.AppImage" ) \
    && echo "  wrote dist/MakeMyFigure-${VER}.AppImage" || echo "  appimagetool failed; tarball available"
else
  echo "==> appimagetool not found; skipping AppImage (tarball available)."
fi
echo "Done."
