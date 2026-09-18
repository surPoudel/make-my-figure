"""Pre-release checks. READ-ONLY: it never edits, commits, tags or pushes.

    python .agents/makemyfigure-developer/scripts/release_preflight.py --version 1.2.0

Verifies the conditions the release runbook (references/release-workflow.md) requires before step 17:
clean working tree, on an allowed branch, remote fetched and branch not behind, tag does not exist yet,
version string consistent in every authoritative location (make_my_figure_core/version.py, CHANGELOG
heading, release notes file, manuals' version banner), CHANGELOG has a section for the version with
no leftover "Unreleased" bullets, the release ledger has a draft entry, and the last recorded test run is
newer than the last code change. Prints a checklist; exit 1 when a blocking item fails.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", required=True, help="target version without the v prefix, e.g. 1.2.0")
    ap.add_argument("--branch", default="main", help="branch releases are cut from (project convention: main)")
    ap.add_argument("--no-fetch", action="store_true")
    a = ap.parse_args()
    v = a.version.lstrip("v"); tag = f"v{v}"
    rows = []

    def add(item, ok, note=""):
        rows.append({"item": item, "result": "PASS" if ok is True else ("INFO" if ok is None else "FAIL"), "note": str(note)[:140]})

    if not re.fullmatch(r"\d+\.\d+\.\d+(-[0-9A-Za-z.]+)?", v):
        add("semantic version format", False, v)
    else:
        add("semantic version format", True, tag)
    status = C.git("status", "--porcelain")
    add("clean working tree", status == "", status.splitlines()[0] if status else "clean")
    branch = C.git("rev-parse", "--abbrev-ref", "HEAD")
    add(f"on release branch ({a.branch})", branch == a.branch, branch)
    if not a.no_fetch:
        C.git("fetch", "--quiet", "origin")
    behind = C.git("rev-list", "--count", f"HEAD..origin/{a.branch}") if C.git("rev-parse", "--verify", "--quiet", f"origin/{a.branch}") else "?"
    add("not behind origin", behind == "0", f"{behind} commit(s) behind origin/{a.branch}")
    add("tag does not exist", tag not in C.git("tag", "--list").split(), tag)
    cur = C.version()
    add("make_my_figure_core/version.py == target", cur == v, f"version.py has {cur}")
    chg = open(os.path.join(C.ROOT, "CHANGELOG.md"), encoding="utf-8").read()
    add("CHANGELOG has section for version", bool(re.search(rf"^## \[{re.escape(v)}\]", chg, re.M)), f"## [{v}]")
    unreleased = re.search(r"^## Unreleased\s*\n(.*?)(?=^## )", chg, re.M | re.S)
    leftover = bool(unreleased and re.search(r"^\s*-\s+\S", unreleased.group(1), re.M))
    add("no leftover Unreleased bullets", not leftover, "move them under the version heading" if leftover else "clean")
    notes = os.path.join(C.ROOT, "docs", f"RELEASE_NOTES_v{v}.md")
    add("docs/RELEASE_NOTES_v<version>.md exists", os.path.exists(notes), os.path.relpath(notes, C.ROOT))
    manual_hits = C.grep_files(f"v{v}", ["docs/manuals"], exts=(".md",))
    stale = C.grep_files(f"v{cur}", ["docs/manuals"], exts=(".md",)) if cur != v else []
    add("manuals mention target version", bool(manual_hits), f"{len(manual_hits)} file(s); rebuild with scripts/build_manuals.py" if not manual_hits else f"{len(manual_hits)} file(s)")
    if stale:
        add("manuals still mention old version", False, ", ".join(stale[:3]))
    ledger = os.path.join(C.ROOT, "release_history", f"{tag}.md")
    add("release ledger draft exists", os.path.exists(ledger), os.path.relpath(ledger, C.ROOT))
    runs = sorted(glob.glob(os.path.join(C.ROOT, "reports", "agent_runs", "*_tests_*.md")), key=os.path.getmtime)
    last_code = int(C.git("log", "-1", "--format=%ct", "--", "make_my_figure_core", "apps", "scripts", "tests") or 0)
    if runs:
        newest = runs[-1]; ok = os.path.getmtime(newest) >= last_code
        add("recorded test run newer than last code change", ok, os.path.relpath(newest, C.ROOT))
    else:
        add("recorded test run", False, "run run_plot_tests.py --full first")
    wf = os.path.join(C.ROOT, ".github", "workflows", "build_desktop_releases.yml")
    add("release workflow present (builds on tag push)", os.path.exists(wf), "tag push v* builds Windows/macOS/Linux and uploads assets")
    add("requirements-lock.txt present", os.path.exists(os.path.join(C.ROOT, "requirements-lock.txt")), "exact versions the release was tested with")
    print(f"# Release preflight for {tag} (read-only)\n" + C.table(rows, ["item", "result", "note"]))
    failed = [r for r in rows if r["result"] == "FAIL"]
    print(f"\n{'BLOCKED: ' + str(len(failed)) + ' item(s) failing' if failed else 'All preflight items pass. Proceed with the runbook only under explicit RELEASE authorisation.'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
