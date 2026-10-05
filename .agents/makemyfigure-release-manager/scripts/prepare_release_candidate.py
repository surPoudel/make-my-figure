"""PREPARE RELEASE CANDIDATE. Default is a DRY RUN that changes nothing.

    python .agents/makemyfigure-release-manager/scripts/prepare_release_candidate.py --version X.Y.Z [--execute] [--tests quick|full|skip]

Dry run (default): prints, for the target version, (1) the version-edit plan - every file the
version lives in and what it currently says, (2) the preflight result for the current tree,
(3) the tag pre-check for vX.Y.Z, (4) the exact build/verify commands the BUILD LOCAL mode runs,
(5) the exact publication commands that are NOT run here. Writes release_staging/<v>/rc_plan.json.
Nothing is edited, committed, tagged or pushed.

--execute: applies only the mechanical text edits (version.py, README badge + installer names)
and creates a release-notes draft; the CHANGELOG heading and the manual banners
(scripts/build_manuals.py) remain human steps and are listed. Still no commit, tag or push:
those belong to release_manager.py commit-push / release, which require explicit authorization.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def sh(args):
    r = subprocess.run(args, text=True, capture_output=True, cwd=C.ROOT)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", required=True, help="target release version, e.g. 1.2.0")
    ap.add_argument("--execute", action="store_true", help="apply the mechanical version edits (no commit/tag/push)")
    ap.add_argument("--tests", choices=["quick", "full", "skip"], default="quick")
    a = ap.parse_args()
    target = a.version.lstrip("v")
    current = C.version_py()
    tag = f"v{target}" if not C.SEMVER_RE.match(target) else C.pep440_to_tag(target)
    plan = {"generated": C.now_iso(), "mode": "execute" if a.execute else "dry-run", "target_version": target, "current_version": current,
            "tag": tag, "branch": C.git("rev-parse", "--abbrev-ref", "HEAD"), "commit": C.git("rev-parse", "HEAD"), "findings": [], "steps": []}
    print(f"== prepare release candidate {tag}  [{plan['mode']}]  current version.py = {current}, branch {plan['branch']} @ {plan['commit'][:10]}")
    if not C.SEMVER_RE.match(target):
        plan["findings"].append({"level": "STOP", "text": f"'{target}' is not a valid release version (expected MAJOR.MINOR.PATCH or MAJOR.MINOR.PATCHrcN); nothing beyond the dry run may proceed"})
    if plan["branch"] != "main":
        plan["findings"].append({"level": "WARN", "text": f"on branch {plan['branch']}: release candidates are cut from main"})
    # 1. version-edit plan
    print("\n-- 1. version-edit plan")
    edits = []
    for loc in C.version_locations(current):
        needs = loc["value"] != target
        edits.append({"location": loc["location"], "current": loc["value"], "target": target, "needs_edit": needs, "how": loc["note"]})
        print(f"   {'EDIT ' if needs else 'ok   '}{loc['location']}: {loc['value']} -> {target}  {loc['note']}")
    plan["version_edits"] = edits
    if a.execute and current != target and C.SEMVER_RE.match(target):
        vp = os.path.join(C.ROOT, "make_my_figure_core", "version.py"); s = open(vp, encoding="utf-8").read()
        open(vp, "w", encoding="utf-8").write(re.sub(r"(__version__\s*=\s*['\"])[^'\"]+(['\"])", rf"\g<1>{target}\g<2>", s))
        rp = os.path.join(C.ROOT, "README.md"); s = open(rp, encoding="utf-8").read()
        s = s.replace(f"badge/version-{current}-", f"badge/version-{target}-").replace(f"MakeMyFigure-{current}", f"MakeMyFigure-{target}").replace(f"make_my_figure_core-{current}", f"make_my_figure_core-{target}")
        open(rp, "w", encoding="utf-8").write(s)
        plan["steps"].append("edited make_my_figure_core/version.py and README.md version strings")
        print(f"   applied: version.py and README.md now say {target}")
        print("   HUMAN: add the '## [%s]' CHANGELOG section; run scripts/build_manuals.py to refresh the manual banners; write docs/RELEASE_NOTES_v%s.md" % (target, target))
    # 2. preflight on the tree as it is now
    print("\n-- 2. preflight (current tree)")
    rc, out = sh([PY, os.path.join(HERE, "release_preflight.py"), "--version", C.version_py(), "--tests", a.tests, "--allow-dirty"])
    print("\n".join("   " + l for l in out.strip().splitlines()[-25:]))
    plan["preflight"] = {"returncode": rc, "for_version": C.version_py()}
    # 3. tag pre-check
    print(f"\n-- 3. tag pre-check for {tag}")
    rc, out = sh([PY, os.path.join(HERE, "verify_tag.py"), "--tag", tag, "--pre-check"])
    print("\n".join("   " + l for l in out.strip().splitlines()))
    plan["tag_precheck"] = {"returncode": rc}
    if current != target:
        print(f"   (expected until version.py is bumped to {target}: the tag must equal 'v' + version.py)")
    # 4. build plan
    A = ".agents/makemyfigure-release-manager/scripts"
    build_cmds = [f"python {A}/build_python_dist.py --version {target}", f"python {A}/smoke_test_install.py --version {target}",
                  f"python {A}/build_current_platform.py --version {target}   # once per OS: Windows, macOS, Linux (same commit)",
                  f"python {A}/reconcile_platforms.py --version {target} --require python,windows,macos,linux",
                  f"python {A}/generate_checksums.py --version {target}", f"python {A}/validate_artifacts.py --version {target} --compare-release <previous tag>",
                  f"python {A}/release_notes_draft.py --version {target}", f"python {A}/release_report.py --version {target}"]
    print("\n-- 4. build and verification commands (BUILD LOCAL mode; run, not published)")
    for c in build_cmds: print("   " + c)
    plan["build_commands"] = build_cmds
    # 5. publication - not run
    pub_cmds = [f"git commit -am 'Prepare {tag}'      # via release_manager.py commit-push (authorization required)",
                "git push origin main",
                f"git tag -a {tag} -m 'MakeMyFigure {tag}' && git push origin {tag}      # via release_manager.py release",
                f"gh release create {tag} --title 'MakeMyFigure {tag}' --notes-file release_staging/{target}/RELEASE_NOTES_DRAFT.md release_staging/{target}/*/<artefacts> SHA256SUMS.txt"]
    print("\n-- 5. publication commands: NOT RUN (require explicit author authorization through release_manager.py)")
    for c in pub_cmds: print("   " + c)
    plan["publication_commands_not_run"] = pub_cmds
    plan["stopped_before"] = ["git commit", "git push", "git tag", "gh release create"]
    for f in plan["findings"]:
        print(f"\n   {f['level']}: {f['text']}")
    out_dir = C.staging_dir(target)
    C.write_json(os.path.join(out_dir, "rc_plan.json"), plan)
    C.write_json(os.path.join(C.REPORTS_DIR, "prepare_rc.json"), plan)
    stop = any(f["level"] == "STOP" for f in plan["findings"])
    plan["ok"] = not stop
    C.write_json(os.path.join(out_dir, "rc_plan.json"), plan)
    C.write_json(os.path.join(C.REPORTS_DIR, "prepare_rc.json"), plan)
    print(f"\nRESULT: {'DRY RUN COMPLETE' if not a.execute else 'EDITS APPLIED'} - stopped before {', '.join(plan['stopped_before'])}"
          + ("  [STOP findings present]" if stop else "") + f" -> {os.path.relpath(out_dir, C.ROOT)}/rc_plan.json")
    return 1 if stop else 0


if __name__ == "__main__":
    raise SystemExit(main())
