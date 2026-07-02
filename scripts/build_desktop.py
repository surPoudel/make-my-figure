"""Build the Make My Figure desktop app with PyInstaller (all platforms).

Usage:
    python scripts/build_desktop.py [--clean]

Produces:
    dist/MakeMyFigure/            (Windows/Linux one-folder app)
    dist/MakeMyFigure.app         (macOS application bundle)

This only builds the raw app folder/bundle. Wrapping it into a platform
installer (.exe setup, .dmg, .AppImage, .deb) is done by the per-OS scripts and
the GitHub Actions workflow.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from make_my_figure_core.version import __version__

SPEC = os.path.join(_ROOT, "packaging", "make_my_figure.spec")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean", action="store_true", help="remove build/ and dist/ first")
    args = ap.parse_args()

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller is not installed. Install build deps:\n"
              "  pip install -e \".[desktop,build]\"", file=sys.stderr)
        return 2

    if args.clean:
        for d in ("build", "dist"):
            p = os.path.join(_ROOT, d)
            if os.path.isdir(p):
                shutil.rmtree(p)

    env = dict(os.environ, MMF_VERSION=__version__)
    cmd = [
        sys.executable, "-m", "PyInstaller",
        SPEC,
        "--noconfirm",
        "--distpath", os.path.join(_ROOT, "dist"),
        "--workpath", os.path.join(_ROOT, "build", "pyinstaller"),
    ]
    print("Building Make My Figure", __version__)
    print(" ", " ".join(cmd))
    result = subprocess.run(cmd, cwd=_ROOT, env=env)
    if result.returncode != 0:
        return result.returncode
    print("\nBuild complete. See the dist/ folder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
