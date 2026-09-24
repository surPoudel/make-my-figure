"""Clean BUILD staging only. Never touches archived releases or anything outside build/ and dist/.

    python .agents/makemyfigure-release-manager/scripts/clean_build_outputs.py [--version X.Y.Z] [--all-staging] [--dry-run]

Removes: build/ (PyInstaller work dir), dist/MakeMyFigure*, dist/*.AppDir and, for the given
version, release_staging/<version>/. Historical files that sit loose in dist/ (older wheels, zips)
are listed but left alone unless --all-staging is combined with --purge-loose (asks nothing, so
use deliberately).
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", default=C.version_py())
    ap.add_argument("--all-staging", action="store_true", help="remove release_staging entirely")
    ap.add_argument("--purge-loose", action="store_true", help="also delete loose historical files in dist/ (deliberate)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    dist = os.path.join(C.ROOT, "dist")
    targets = [os.path.join(C.ROOT, "build")]
    targets += glob.glob(os.path.join(dist, "MakeMyFigure*"))
    targets += glob.glob(os.path.join(dist, "*.AppDir"))
    targets.append(os.path.join(C.STAGING_ROOT) if a.all_staging else os.path.join(C.STAGING_ROOT, a.version.lstrip("v")))
    loose = [p for p in glob.glob(os.path.join(dist, "*")) if os.path.isfile(p)]
    for t in targets:
        if not os.path.exists(t):
            continue
        print(("would remove " if a.dry_run else "removing ") + os.path.relpath(t, C.ROOT))
        if not a.dry_run:
            shutil.rmtree(t) if os.path.isdir(t) else os.remove(t)
    if loose:
        print(f"{len(loose)} loose historical file(s) in dist/ " + ("removed" if a.purge_loose and not a.dry_run else "left alone") + ":")
        for p in loose[:20]:
            print("   ", os.path.basename(p))
            if a.purge_loose and not a.dry_run:
                os.remove(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
