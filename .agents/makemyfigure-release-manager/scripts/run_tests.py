"""Testing gate: run the project's authoritative test commands and record counts dynamically.

    python .agents/makemyfigure-release-manager/scripts/run_tests.py [--quick] [--gui] [--json out.json]

Commands come from README.md section 9 and docs/RELEASE_CHECKLIST.md:
  full headless suite:  python -m pytest -q -p no:pytest-qt --ignore=tests/test_desktop_gui.py   (MPLBACKEND=Agg)
  GUI module (--gui):   QT_QPA_PLATFORM=offscreen python -m pytest tests/test_desktop_gui.py -q   (needs PySide6 + Qt libs)
  --quick: the release gates only (r_validation_regressions, release_guardrails, packaging, package_data)
Counts (passed / failed / skipped / errors) are parsed from pytest's summary line - never hard-coded.
Exit 1 when any test failed or errored.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

GATES = ["tests/test_r_validation_regressions.py", "tests/test_release_guardrails.py",
         "tests/test_packaging.py", "tests/test_package_data.py"]


def parse_summary(text: str):
    counts = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0, "deselected": 0, "xfailed": 0}
    tail = "\n".join(text.strip().splitlines()[-5:])
    for k in counts:
        m = re.search(rf"(\d+) {k}", tail)
        if m:
            counts[k] = int(m.group(1))
    m = re.search(r"in ([0-9.]+)s", tail)
    counts["seconds"] = float(m.group(1)) if m else None
    return counts


def run_pytest(args, env_extra=None, label=""):
    env = dict(os.environ, MPLBACKEND="Agg", **(env_extra or {}))
    cmd = [sys.executable, "-m", "pytest", "-q", *args]
    t0 = time.time()
    r = C.run(cmd, env=env, timeout=7200)
    out = (r.stdout or "") + (r.stderr or "")
    counts = parse_summary(out)
    counts.update({"label": label, "command": " ".join(cmd), "returncode": r.returncode, "wall_seconds": round(time.time() - t0, 1),
                   "failures": re.findall(r"^(FAILED|ERROR) (.+)$", out, re.M)[:40]})
    return counts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="release gates only")
    ap.add_argument("--gui", action="store_true", help="also run tests/test_desktop_gui.py offscreen")
    ap.add_argument("--json", default=os.path.join(C.REPORTS_DIR, "test_results.json"))
    a = ap.parse_args()
    runs = []
    if a.quick:
        runs.append(run_pytest(["-p", "no:pytest-qt", *GATES], label="release gates"))
    else:
        runs.append(run_pytest(["-p", "no:pytest-qt", "--ignore=tests/test_desktop_gui.py", "tests"], label="full headless suite"))
    if a.gui:
        runs.append(run_pytest(["tests/test_desktop_gui.py"], env_extra={"QT_QPA_PLATFORM": "offscreen"}, label="desktop GUI module"))
    ok = all(r["returncode"] == 0 and r["failed"] == 0 and r["errors"] == 0 for r in runs)
    rec = {"generated": C.now_iso(), "commit": C.git("rev-parse", "--short", "HEAD"), "host": C.host(), "runs": runs, "ok": ok,
           "totals": {k: sum(r[k] for r in runs) for k in ("passed", "failed", "skipped", "errors")}}
    C.write_json(a.json, rec)
    for r in runs:
        print(f"{r['label']}: {r['passed']} passed, {r['failed']} failed, {r['skipped']} skipped, {r['errors']} errors  ({r['wall_seconds']}s)")
        for f in r["failures"][:10]:
            print("   ", " ".join(f))
    print("RESULT:", "PASS" if ok else "FAIL", "->", os.path.relpath(a.json, C.ROOT))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
