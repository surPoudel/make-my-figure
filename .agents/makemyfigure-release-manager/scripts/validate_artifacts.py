"""Artefact validation for everything staged under release_staging/<version>/.

    python .agents/makemyfigure-release-manager/scripts/validate_artifacts.py --version X.Y.Z [--compare-release vA.B.C]

Per artefact: expected file name for the version, archive integrity (zip test / tar listing /
wheel METADATA version / sdist contains version.py with the same version), minimum plausible size,
and the app executable present inside portable archives. With --compare-release the sizes are
compared with the published GitHub release assets and a >2x or <0.5x change is flagged (a bloated
or truncated bundle). Writes reports/artifact_validation.json. Exit 1 on any failure.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tarfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

MIN_MB = {"wheel": 0.5, "sdist": 0.5, "windows-installer": 40, "windows-portable-zip": 60, "macos-dmg": 60, "macos-zip-fallback": 60,
          "linux-appimage": 80, "linux-portable-tarball": 80, "manual-pdf": 0.2}
sys.path.insert(0, os.path.dirname(__file__))
from generate_checksums import artifact_type, collect  # noqa: E402


def check_archive(path: str, kind: str, v: str):
    try:
        if kind == "wheel":
            with zipfile.ZipFile(path) as zf:
                if zf.testzip():
                    return False, "corrupt member"
                meta = [n for n in zf.namelist() if n.endswith("METADATA")][0]
                mv = re.search(r"^Version: (.+)$", zf.read(meta).decode(), re.M).group(1)
                has = any(n.endswith("make_my_figure_core/_bundled/schemas/plot_spec.schema.json") or "_bundled/schemas" in n for n in zf.namelist())
                return mv == v and has, f"metadata {mv}; bundled schemas {'present' if has else 'MISSING'}"
        if kind == "sdist":
            with tarfile.open(path) as tf:
                names = tf.getnames()
                vp = [n for n in names if n.endswith("make_my_figure_core/version.py")]
                if not vp:
                    return False, "version.py missing"
                txt = tf.extractfile(vp[0]).read().decode()
                sv = re.search(r"__version__\s*=\s*['\"]([^'\"]+)", txt).group(1)
                return sv == v and any(n.endswith("pyproject.toml") for n in names), f"version.py {sv}, {len(names)} members"
        if kind in ("windows-portable-zip", "macos-zip-fallback"):
            with zipfile.ZipFile(path) as zf:
                bad = zf.testzip()
                names = zf.namelist()
                exe = any(n.endswith("MakeMyFigure.exe") or n.endswith("Contents/MacOS/MakeMyFigure") for n in names)
                return bad is None and exe, f"{len(names)} members, executable {'present' if exe else 'MISSING'}"
        if kind == "linux-portable-tarball":
            with tarfile.open(path) as tf:
                names = tf.getnames()
                exe = "MakeMyFigure/MakeMyFigure" in names
                return exe, f"{len(names)} members, executable {'present' if exe else 'MISSING'}"
        if kind == "linux-appimage":
            with open(path, "rb") as fh:
                head = fh.read(16)
            return head[:4] == b"\x7fELF" and head[8:11] == b"AI\x02", "ELF with AppImage type-2 magic" if head[8:11] == b"AI\x02" else "not an AppImage type-2 file"
        if kind == "windows-installer":
            with open(path, "rb") as fh:
                return fh.read(2) == b"MZ", "PE executable"
        if kind == "macos-dmg":
            return os.path.getsize(path) > 0, "dmg (verify with hdiutil verify on macOS)"
        if kind == "manual-pdf":
            with open(path, "rb") as fh:
                return fh.read(5) == b"%PDF-", "PDF header"
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"
    return True, ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", default=C.version_py())
    ap.add_argument("--compare-release", help="published tag to compare asset sizes against, e.g. v1.1.0")
    ap.add_argument("--json", default=os.path.join(C.REPORTS_DIR, "artifact_validation.json"))
    a = ap.parse_args()
    v = a.version.lstrip("v")
    rows = collect(v)
    if not rows:
        print("nothing staged"); return 1
    ref = {}
    if a.compare_release:
        r = C.run(["gh", "release", "view", a.compare_release, "--json", "assets"])
        if r.returncode == 0:
            rv = a.compare_release.lstrip("v")
            for asset in json.loads(r.stdout)["assets"]:
                ref[asset["name"].replace(rv, v)] = asset["size"]
    expected_names = {n.format(v=v) for names in C.EXPECTED_PUBLIC_ARTIFACTS.values() for n in names}
    results = []
    for row in rows:
        kind = artifact_type(row["filename"]); p = os.path.join(C.ROOT, row["path"])
        ok_name = row["filename"] in expected_names
        ok_size = row["size"] >= MIN_MB.get(kind, 0) * 1e6
        ok_arch, detail = check_archive(p, kind, v)
        cmp = ""
        ok_cmp = True
        if ref.get(row["filename"]):
            ratio = row["size"] / ref[row["filename"]]
            cmp = f"{ratio:.2f}x of {a.compare_release}"
            ok_cmp = 0.5 <= ratio <= 2.0
        ok = ok_name and ok_size and ok_arch and ok_cmp
        results.append({**row, "kind": kind, "name_ok": ok_name, "size_ok": ok_size, "archive_ok": ok_arch, "archive_detail": detail,
                        "size_vs_reference": cmp, "size_ratio_ok": ok_cmp, "ok": ok})
        print(f"  {'ok ' if ok else '!! '}{row['filename']}  {row['size'] / 1e6:.1f} MB  {detail}{'  ' + cmp if cmp else ''}"
              + ("" if ok_name else "  [unexpected name]") + ("" if ok_size else "  [too small]") + ("" if ok_cmp else "  [size differs >2x from reference]"))
    ok = all(r["ok"] for r in results)
    C.write_json(a.json, {"generated": C.now_iso(), "version": v, "compare_release": a.compare_release, "artifacts": results, "ok": ok})
    print("RESULT:", "PASS" if ok else "FAIL", f"({len(results)} artefact(s))")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
