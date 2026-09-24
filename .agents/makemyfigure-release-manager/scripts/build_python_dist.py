"""BUILD LEVEL 1: wheel + sdist from clean source with the project's own mechanism (python -m build).

    python .agents/makemyfigure-release-manager/scripts/build_python_dist.py [--version X.Y.Z] [--no-check]

Output goes to release_staging/<version>/python/ (never to a shared dist/ root, so old artefacts
cannot be confused with new ones). Runs `twine check` when twine is installed, records file
name, size, SHA-256 and the version read back from the wheel metadata, and runs the private-file
check on both archives. Exit 1 on any failure.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402


def wheel_version(path: str) -> str:
    with zipfile.ZipFile(path) as zf:
        meta = [n for n in zf.namelist() if n.endswith("METADATA")][0]
        text = zf.read(meta).decode("utf-8", "ignore")
    m = re.search(r"^Version: (.+)$", text, re.M)
    return m.group(1).strip() if m else ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", help="expected version (default: version.py)")
    ap.add_argument("--no-check", action="store_true", help="skip twine check")
    a = ap.parse_args()
    v = (a.version or C.version_py()).lstrip("v")
    if C.version_py() != v:
        print(f"FAIL: version.py says {C.version_py()} but {v} was requested"); return 1
    out_dir = C.staging_dir(v, "python")
    for old in glob.glob(os.path.join(out_dir, "*")):
        os.remove(old)
    tmp = tempfile.mkdtemp(prefix="mmf_dist_")
    r = C.run([sys.executable, "-m", "build", "--outdir", tmp], capture=True, timeout=1800)
    if r.returncode != 0:
        print(r.stdout[-2000:], r.stderr[-2000:]); print("FAIL: python -m build"); return 1
    files = sorted(glob.glob(os.path.join(tmp, "*")))
    rows = []
    for f in files:
        dest = os.path.join(out_dir, os.path.basename(f)); shutil.move(f, dest)
        row = {"file": os.path.basename(dest), "size": os.path.getsize(dest), "sha256": C.sha256(dest),
               "kind": "wheel" if dest.endswith(".whl") else "sdist"}
        if row["kind"] == "wheel":
            row["metadata_version"] = wheel_version(dest)
            row["version_ok"] = row["metadata_version"] == v
        rows.append(row)
    shutil.rmtree(tmp, ignore_errors=True)
    ok = bool(rows) and all(r.get("version_ok", True) for r in rows) and all(v in r["file"] for r in rows)
    twine = None
    if not a.no_check:
        r = C.run([sys.executable, "-m", "twine", "check", *[os.path.join(out_dir, x["file"]) for x in rows]])
        twine = {"returncode": r.returncode, "output": (r.stdout + r.stderr)[-800:]}
        ok = ok and r.returncode == 0
    pf = {}
    for x in rows:
        flag = "--wheel" if x["kind"] == "wheel" else "--sdist"
        r = C.run([sys.executable, os.path.join(os.path.dirname(__file__), "private_file_check.py"), flag, os.path.join(out_dir, x["file"]),
                   "--json", os.path.join(C.REPORTS_DIR, f"private_file_check_{x['kind']}.json")])
        pf[x["kind"]] = {"returncode": r.returncode, "summary": (r.stdout or "").splitlines()[0] if r.stdout else ""}
        ok = ok and r.returncode == 0
    rec = {"generated": C.now_iso(), "version": v, "commit": C.git("rev-parse", "HEAD"), "dirty": bool(C.git("status", "--porcelain")),
           "output_dir": os.path.relpath(out_dir, C.ROOT), "artifacts": rows, "twine_check": twine, "private_file_check": pf, "ok": ok}
    C.write_json(os.path.join(out_dir, "python_build_manifest.json"), rec)
    C.write_json(os.path.join(C.REPORTS_DIR, "python_dist.json"), rec)
    for x in rows:
        print(f"  {x['file']}  {x['size'] / 1e6:.2f} MB  sha256 {x['sha256'][:16]}...  {'version ok' if x.get('version_ok', True) else 'VERSION MISMATCH ' + str(x.get('metadata_version'))}")
    if twine:
        print(f"  twine check: {'ok' if twine['returncode'] == 0 else 'FAILED'}")
    for k, v2 in pf.items():
        print(f"  private-file check ({k}): {v2['summary']}")
    print("RESULT:", "PASS" if ok else "FAIL", "->", rec["output_dir"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
