"""Checksums: SHA256SUMS.txt (sha256sum format, as published for v1.1.0) and release_artifacts.json.

    python .agents/makemyfigure-release-manager/scripts/generate_checksums.py --version X.Y.Z [--verify]

Walks release_staging/<version>/{python,windows,macos,linux,manuals}/ and lists every public
artefact (the manifests and reports in those folders are skipped). --verify re-hashes and compares
against an existing SHA256SUMS.txt instead of writing it; exit 1 on any mismatch or missing file.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

PUBLIC_EXT = (".whl", ".tar.gz", ".exe", ".zip", ".dmg", ".AppImage", ".pdf")
PLATFORM_DIRS = ("python", "windows", "macos", "linux", "manuals")


def artifact_type(name: str) -> str:
    n = name.lower()
    if n.endswith(".whl"): return "wheel"
    if n.endswith(".tar.gz") and n.startswith("make_my_figure_core"): return "sdist"
    if n.endswith("-setup.exe"): return "windows-installer"
    if n.endswith("-windows.zip"): return "windows-portable-zip"
    if n.endswith(".dmg"): return "macos-dmg"
    if n.endswith("-macos.zip"): return "macos-zip-fallback"
    if n.endswith(".appimage"): return "linux-appimage"
    if n.endswith(".tar.gz"): return "linux-portable-tarball"
    if n.endswith(".pdf"): return "manual-pdf"
    return "other"


def collect(version: str):
    rows = []
    base = os.path.join(C.STAGING_ROOT, version)
    for plat in PLATFORM_DIRS:
        d = os.path.join(base, plat)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            p = os.path.join(d, fn)
            if os.path.isfile(p) and fn.endswith(PUBLIC_EXT):
                arch = "x86_64" if "x86_64" in fn else ("arm64" if "arm64" in fn else ("any" if fn.endswith((".whl", ".tar.gz", ".pdf")) and plat == "python" or plat == "manuals" else "see platform manifest"))
                rows.append({"filename": fn, "size": os.path.getsize(p), "sha256": C.sha256(p), "platform": plat,
                             "architecture": arch, "artifact_type": artifact_type(fn), "path": os.path.relpath(p, C.ROOT)})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", default=C.version_py())
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    v = a.version.lstrip("v")
    out_dir = C.staging_dir(v, "checksums")
    sums_path = os.path.join(out_dir, "SHA256SUMS.txt")
    rows = collect(v)
    if not rows:
        print(f"no public artefacts under release_staging/{v}/"); return 1
    if a.verify:
        if not os.path.exists(sums_path):
            print("SHA256SUMS.txt missing"); return 1
        recorded = dict(reversed(l.split("  ", 1)) for l in open(sums_path, encoding="utf-8").read().splitlines() if "  " in l)
        bad = [r["filename"] for r in rows if recorded.get(r["filename"]) != r["sha256"]]
        missing = [f for f in recorded if f not in {r["filename"] for r in rows}]
        print(f"verify: {len(rows)} artefacts, {len(bad)} mismatched, {len(missing)} recorded but absent")
        for b in bad: print("  MISMATCH", b)
        for m in missing: print("  ABSENT  ", m)
        return 0 if not bad and not missing else 1
    with open(sums_path, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(f"{r['sha256']}  {r['filename']}\n")
    expected = {n.format(v=v) for names in C.EXPECTED_PUBLIC_ARTIFACTS.values() for n in names} - {"SHA256SUMS.txt"}
    present = {r["filename"] for r in rows}
    rec = {"generated": C.now_iso(), "version": v, "commit": C.git("rev-parse", "HEAD"), "artifacts": rows,
           "expected_missing": sorted(expected - present), "unexpected_present": sorted(present - expected),
           "optional_missing": sorted((expected - present) & {n.format(v=v) for n in C.OPTIONAL_PUBLIC_ARTIFACTS})}
    C.write_json(os.path.join(out_dir, "release_artifacts.json"), rec)
    print(f"SHA256SUMS.txt: {len(rows)} artefact(s) -> {os.path.relpath(sums_path, C.ROOT)}")
    for r in rows:
        print(f"  {r['sha256'][:16]}...  {r['filename']}  ({r['size'] / 1e6:.1f} MB, {r['platform']}, {r['artifact_type']})")
    if rec["expected_missing"]:
        print("  not yet present (expected for a full public release):", ", ".join(rec["expected_missing"]))
    if rec["unexpected_present"]:
        print("  present but not in the expected set:", ", ".join(rec["unexpected_present"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
