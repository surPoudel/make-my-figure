"""Validate every tutorial against the real application and write
tutorial/audit/validation_report.md.

    python tutorial/automation/validate_tutorials.py            # run all action scripts offscreen
    python tutorial/automation/validate_tutorials.py --report   # only rebuild the report from records

A tutorial is PASS when its action script ran to the end and every check passed (dataset exists,
plot type exists, each column role exists, the plot rendered, options exist, statistics ran,
exports were written). FAIL lists the first failing check or exception. BLOCKED means the script
could not start (missing dataset, missing library).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
TUT = os.path.join(ROOT, "tutorial")
sys.path.insert(0, HERE)


def build_report() -> str:
    recs = []
    for p in sorted(glob.glob(os.path.join(TUT, "audit", "validation", "*.json"))):
        recs.append(json.load(open(p, encoding="utf-8")))
    lines = ["# Tutorial validation report", "",
             f"Generated {time.strftime('%Y-%m-%d %H:%M')} by `tutorial/automation/validate_tutorials.py`. "
             "Each row is one action script run against the real desktop application (offscreen). "
             "Checks are recorded by the driver as the script performs the tutorial's own steps.", "",
             "| tutorial | status | checks | failed | captures | seconds | datasets | detail |", "|---|---|---|---|---|---|---|---|"]
    for r in recs:
        detail = r["error"] or "; ".join(c["check"] + (f" ({c['detail']})" if c.get("detail") else "") for c in r["failed_checks"]) or ""
        lines.append(f"| `{r['tutorial_id']}` | **{r['status']}** | {len(r['checks'])} | {len(r['failed_checks'])} | "
                     f"{len(r['captures'])} | {r['seconds']} | {', '.join(r['datasets'])} | {detail[:160]} |")
    lines += ["", "## Checks per tutorial", ""]
    for r in recs:
        lines.append(f"### `{r['tutorial_id']}` - {r['title']} ({r['status']})")
        lines.append("")
        for c in r["checks"]:
            lines.append(f"- {'PASS' if c['ok'] else 'FAIL'}: {c['check']}" + (f" - {c['detail']}" if c.get("detail") else ""))
        lines.append("")
    text = "\n".join(lines)
    with open(os.path.join(TUT, "audit", "validation_report.md"), "w", encoding="utf-8") as fh:
        fh.write(text)
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="only rebuild the report")
    ap.add_argument("tutorials", nargs="*")
    a = ap.parse_args()
    if not a.report:
        from run_tutorial import list_tutorials, run_one

        ids = a.tutorials or list_tutorials()
        for t in ids:
            run_one(t, mode="offscreen", pause=0.0, validate_only=False,
                    screenshots_root=os.path.join(TUT, "screenshots"),
                    outputs_root=os.path.join(TUT, "automation", "_outputs"))
    text = build_report()
    print(text.split("## Checks")[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
