"""Cross-platform reconciliation: every staged build must come from the SAME source commit.

    python .agents/makemyfigure-release-manager/scripts/reconcile_platforms.py --version X.Y.Z [--require python,linux,windows,macos]

Reads release_staging/<version>/{python,linux,windows,macos}/*manifest.json and checks: identical
commit, identical version, clean tree at build time, self-test passed, expected artefacts present.
Writes release_staging/<version>/reconciliation.json. Exit 1 on any mismatch or missing required
platform. Builds made on other machines are brought in by copying their platform folder
(artefacts + platform_build_manifest.json) into release_staging/<version>/ on the coordinating machine.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", default=C.version_py())
    ap.add_argument("--require", default="python", help="comma list of platforms that must be present")
    a = ap.parse_args()
    v = a.version.lstrip("v")
    base = os.path.join(C.STAGING_ROOT, v)
    required = [p for p in a.require.split(",") if p]
    found = {}
    for plat in ("python", "linux", "windows", "macos"):
        mp = os.path.join(base, plat, "python_build_manifest.json" if plat == "python" else "platform_build_manifest.json")
        if os.path.exists(mp):
            found[plat] = C.read_json(mp)
    problems = []
    for p in required:
        if p not in found:
            problems.append(f"required platform missing: {p}")
    commits = {p: m.get("commit") for p, m in found.items()}
    if len(set(commits.values())) > 1:
        problems.append("builds come from different commits: " + ", ".join(f"{p}={c[:10]}" for p, c in commits.items()))
    for p, m in found.items():
        if m.get("version") != v:
            problems.append(f"{p}: version {m.get('version')} != {v}")
        if m.get("dirty"):
            problems.append(f"{p}: built from a dirty working tree")
        st = m.get("selftest", {}) if p != "python" else {"ok": m.get("ok")}
        if st.get("ok") is False:
            problems.append(f"{p}: self-test failed")
        if m.get("expected_missing"):
            problems.append(f"{p}: not produced -> {', '.join(m['expected_missing'])}")
    rows = [{"platform": p, "commit": (m.get("commit") or "")[:10], "version": m.get("version"), "tree": "dirty" if m.get("dirty") else "clean",
             "test": ("selftest " + ("OK" if (m.get("selftest") or {}).get("ok") else "FAIL")) if p != "python" else ("smoke " + ("OK" if m.get("ok") else "FAIL")),
             "artefacts": ", ".join(x["file"] for x in m.get("artifacts", []))} for p, m in found.items()]
    C.print_table(rows, ["platform", "commit", "version", "tree", "test", "artefacts"])
    ok = not problems
    for pr in problems:
        print("  !!", pr)
    rec = {"generated": C.now_iso(), "version": v, "required": required, "platforms": {p: {"commit": m.get("commit"), "version": m.get("version"), "dirty": m.get("dirty"),
           "artifacts": m.get("artifacts", []), "host": m.get("host")} for p, m in found.items()}, "problems": problems, "ok": ok,
           "same_commit": len(set(commits.values())) == 1 if commits else None}
    C.write_json(os.path.join(base, "reconciliation.json"), rec)
    C.write_json(os.path.join(C.REPORTS_DIR, "reconciliation.json"), rec)
    print("RESULT:", "PASS" if ok else "FAIL", f"({len(found)} platform build(s), same commit: {rec['same_commit']})")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
