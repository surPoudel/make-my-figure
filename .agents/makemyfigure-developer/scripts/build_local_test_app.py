"""Build (or explain how to launch) a LOCAL test application for the host operating system.

    python .agents/makemyfigure-developer/scripts/build_local_test_app.py            # build with PyInstaller for this OS
    python .agents/makemyfigure-developer/scripts/build_local_test_app.py --source   # no build: print the from-source launch commands
    python .agents/makemyfigure-developer/scripts/build_local_test_app.py --dry-run  # show what would run

Uses the project's own build entry points (scripts/build_desktop.py, which drives
packaging/make_my_figure.spec; the per-platform wrappers scripts/build_windows.ps1,
build_macos.sh, build_linux.sh add installers/bundles). Only the HOST platform is built; other
platforms are produced by the GitHub workflow at release time (see references/release-workflow.md).
Never fabricates an artifact: if PyInstaller or PySide6 is missing it says so and falls back to
the from-source launch instructions.
"""
from __future__ import annotations

import argparse
import glob
import os
import platform
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402


def source_instructions() -> str:
    py = "python" if platform.system() == "Windows" else "python3"
    return f"""Launch from source (no build needed for day-to-day author testing):

  cd "{C.ROOT}"
  {py} -m pip install -e ".[desktop]"          # once; PySide6 + core deps
  {py} -m apps.desktop_app.main                 # desktop application
  {py} -m streamlit run apps/streamlit_app/streamlit_app.py   # browser application

The About dialog / banner shows version, commit and module path (make_my_figure_core.version.build_info),
so the author can confirm the app runs the freshly edited checkout, not an installed copy."""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", action="store_true", help="print from-source launch instructions only")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--clean", action="store_true", help="pass --clean to build_desktop.py")
    a = ap.parse_args()
    host = platform.system()
    feats = C.features()
    print(f"host: {host} {platform.machine()}; python {sys.version.split()[0]}; checkout {C.git('rev-parse', '--short', 'HEAD')} "
          f"v{C.version()}; PySide6={'yes' if feats['pyside6'] else 'no'}; PyInstaller={'yes' if feats['pyinstaller'] else 'no'}")
    if a.source:
        print(source_instructions()); return 0
    if not feats["pyside6"] or not feats["pyinstaller"]:
        print("Cannot build a binary here: " + ("PySide6 is missing or cannot load (headless/WSL without Qt libraries). " if not feats["pyside6"] else "")
              + ("PyInstaller is not installed (pip install -e '.[desktop,build]'). " if not feats["pyinstaller"] else ""))
        print(source_instructions()); return 2
    wrappers = {"Windows": ["powershell", "-ExecutionPolicy", "Bypass", "-File", os.path.join(C.ROOT, "scripts", "build_windows.ps1")],
                "Darwin": ["bash", os.path.join(C.ROOT, "scripts", "build_macos.sh")],
                "Linux": ["bash", os.path.join(C.ROOT, "scripts", "build_linux.sh")]}
    cmd = wrappers.get(host) or [sys.executable, os.path.join(C.ROOT, "scripts", "build_desktop.py")]
    if a.clean and cmd[-1].endswith("build_desktop.py"):
        cmd.append("--clean")
    print("build command:", " ".join(cmd))
    if a.dry_run:
        return 0
    t0 = time.time()
    rc = subprocess.run(cmd, cwd=C.ROOT).returncode
    arts = sorted(glob.glob(os.path.join(C.ROOT, "dist", "**", "*"), recursive=True), key=os.path.getmtime)[-8:]
    print(f"\nexit code {rc} after {time.time() - t0:.0f}s; newest dist/ entries:")
    for p in arts:
        print("  ", os.path.relpath(p, C.ROOT), f"{os.path.getsize(p) // 1024} KB" if os.path.isfile(p) else "")
    print("\nSmoke test: launch the artifact, open the About dialog, confirm version + commit, load the new plot's example.")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
