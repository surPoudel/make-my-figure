"""Run the tests that matter for one plot type: its own tests, tests of related renderers, and
the registry-wide suites that enumerate every plot type. Then optionally the full suite.

    python .agents/makemyfigure-developer/scripts/run_plot_tests.py dumbbell_plot
    python .agents/makemyfigure-developer/scripts/run_plot_tests.py dumbbell_plot --related box_violin,dot_strip --full

Headless by default (MPLBACKEND=Agg; Qt tests skipped when PySide6 cannot load). Writes a
summary to reports/agent_runs/<plot_type>_tests_<timestamp>.md so the acceptance report can
cite it. Baseline for comparison: the most recent reports/*/baseline_test_results.md or the
previous agent run.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402


def registry_wide_tests() -> list:
    """Test modules that call available_plot_types(): a new plot enters them automatically."""
    return sorted(C.grep_files("available_plot_types()", ["tests"], exts=(".py",)))


def tests_mentioning(token: str) -> list:
    return sorted(C.grep_files(token, ["tests"], exts=(".py",)))


def run_pytest(paths: list, label: str, extra: list) -> dict:
    cmd = [sys.executable, "-m", "pytest", "-q", "--no-header", *C.headless_pytest_args(), *extra, *paths]
    env = {**os.environ, "MPLBACKEND": "Agg"}
    t0 = dt.datetime.now()
    out = subprocess.run(cmd, cwd=C.ROOT, capture_output=True, text=True, env=env)
    tail = (out.stdout.strip().splitlines() or [""])[-1]
    m = re.search(r"(\d+) passed", tail); f = re.search(r"(\d+) failed", tail); s = re.search(r"(\d+) skipped", tail)
    e = re.search(r"(\d+) error", tail)
    failed_names = [ln for ln in out.stdout.splitlines() if ln.startswith("FAILED") or ln.startswith("ERROR")]
    return {"label": label, "cmd": " ".join(cmd), "passed": int(m.group(1)) if m else 0,
            "failed": int(f.group(1)) if f else 0, "skipped": int(s.group(1)) if s else 0,
            "errors": int(e.group(1)) if e else 0, "seconds": (dt.datetime.now() - t0).total_seconds(),
            "summary": tail, "failed_names": failed_names, "returncode": out.returncode,
            "stderr_tail": out.stderr[-1500:] if out.returncode not in (0, 1) else ""}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plot_type")
    ap.add_argument("--related", default="", help="comma-separated renderer module names or plot types to include")
    ap.add_argument("--full", action="store_true", help="also run the complete headless suite")
    ap.add_argument("--extra", default="", help="extra pytest args, quoted")
    a = ap.parse_args()
    pt = a.plot_type
    mod = C.renderer_module_for(pt)
    modname = mod.split(".")[-1] if mod else pt
    focused = sorted(set(tests_mentioning(pt) + tests_mentioning(modname)))
    related = []
    for r in [x.strip() for x in a.related.split(",") if x.strip()]:
        related += tests_mentioning(r)
    related = sorted(set(related) - set(focused))
    wide = sorted(set(registry_wide_tests()) - set(focused) - set(related))
    extra = a.extra.split() if a.extra else []
    results = []
    for label, paths in (("focused", focused), ("related", related), ("registry-wide", wide)):
        if paths:
            print(f"[{label}] {len(paths)} module(s)"); results.append(run_pytest(paths, label, extra))
            print("   ", results[-1]["summary"])
        else:
            print(f"[{label}] no test modules found")
    if a.full:
        print("[full suite]"); results.append(run_pytest(["tests"], "full", extra)); print("   ", results[-1]["summary"])
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    rep_dir = os.path.join(C.ROOT, "reports", "agent_runs"); os.makedirs(rep_dir, exist_ok=True)
    rep = os.path.join(rep_dir, f"{pt}_tests_{stamp}.md")
    lines = [f"# Test run for `{pt}` - {stamp}", "", f"checkout: {C.git('rev-parse', '--abbrev-ref', 'HEAD')} {C.git('rev-parse', '--short', 'HEAD')}",
             f"python: {sys.version.split()[0]}; features: {', '.join(k for k, v in C.features().items() if v)}", "",
             "| stage | passed | failed | errors | skipped | seconds |", "|---|---|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r['label']} | {r['passed']} | {r['failed']} | {r['errors']} | {r['skipped']} | {r['seconds']:.0f} |")
    lines += ["", "## commands", *[f"- `{r['cmd']}`" for r in results]]
    for r in results:
        if r["failed_names"]:
            lines += ["", f"## {r['label']} failures", *[f"- {n}" for n in r["failed_names"]]]
        if r["stderr_tail"]:
            lines += ["", f"## {r['label']} stderr", "```", r["stderr_tail"], "```"]
    lines += ["", "## focused modules", *[f"- {p}" for p in focused], "", "## related modules", *[f"- {p}" for p in related],
              "", "## registry-wide modules", *[f"- {p}" for p in wide]]
    open(rep, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"\nreport: {os.path.relpath(rep, C.ROOT)}")
    bad = any(r["failed"] or r["errors"] or r["returncode"] not in (0, 5) for r in results)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
