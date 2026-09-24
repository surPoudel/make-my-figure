"""MakeMyFigure Build and Release Manager - command line control plane.

    python .agents/makemyfigure-release-manager/scripts/release_manager.py <mode> [options]

Modes (see AGENT.md):
  audit                 read-only: repository / version / tag / GitHub / private-file state
  build-local           preflight -> wheel+sdist -> venv smoke -> native app for THIS OS -> checksums
                        -> validation -> reconciliation -> report. Publishes nothing.
  prepare-rc            dry-run plan for a target version (--execute applies version text edits only)
  commit-push           GATED. Commits the release-preparation files and pushes the branch.
  release               GATED. Annotated tag + push tag + GitHub release with staged artefacts, then verifies.
  finalize              GATED. After the CI workflow attached its installers: re-upload preferred local builds,
                        regenerate + upload SHA256SUMS.txt, verify, ledger (finalize_release.py).

Gates for commit-push and release (all three are required, none is stored anywhere):
  1. --authorize "I authorize <mode> for vX.Y.Z"   (typed by the author, version must match)
  2. environment variable MMF_RELEASE_AUTHORIZED=yes   (set in the shell for that command only)
  3. an interactive "yes" at the final prompt (skipped only with --yes, for scripted use by the author)
Credentials are never read or written by this tool: git uses the author's existing remote
configuration and gh its existing login.
"""
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def step(title, args, env=None, allow_fail=False):
    print(f"\n### {title}\n$ {' '.join(shlex.quote(x) for x in args)}", flush=True)
    r = subprocess.run(args, cwd=C.ROOT, env=env)
    if r.returncode != 0 and not allow_fail:
        print(f"\nSTOPPED: '{title}' failed (exit {r.returncode}). Nothing further was run.")
        raise SystemExit(r.returncode)
    return r.returncode


def script(name):
    return os.path.join(HERE, name)


def gate(mode: str, version: str, a) -> None:
    tag = C.pep440_to_tag(version)
    expected = f"I authorize {mode} for {tag}"
    if a.authorize != expected:
        raise SystemExit(f"GATE: pass --authorize \"{expected}\" exactly (got {a.authorize!r}).")
    if os.environ.get("MMF_RELEASE_AUTHORIZED") != "yes":
        raise SystemExit("GATE: set MMF_RELEASE_AUTHORIZED=yes in the environment for this command.")
    if not a.yes:
        ans = input(f"Final confirmation - {mode} {tag} from {C.git('rev-parse', '--short', 'HEAD')} on {C.git('rev-parse', '--abbrev-ref', 'HEAD')}? type yes: ")
        if ans.strip().lower() != "yes":
            raise SystemExit("GATE: not confirmed.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["audit", "build-local", "prepare-rc", "commit-push", "release", "finalize"])
    ap.add_argument("--prefer-local", default="linux", help="finalize: platforms whose local builds replace CI's")
    ap.add_argument("--version", help="version (default version.py; required for prepare-rc)")
    ap.add_argument("--tests", choices=["quick", "full", "skip"], default="quick")
    ap.add_argument("--skip-platform", action="store_true", help="build-local: wheel/sdist only")
    ap.add_argument("--allow-dirty", action="store_true", help="build-local on an uncommitted tree (recorded in manifests)")
    ap.add_argument("--compare-release", help="previous tag for size comparison (default: latest tag)")
    ap.add_argument("--execute", action="store_true", help="prepare-rc: apply version text edits")
    ap.add_argument("--platforms", default="python,linux,windows,macos", help="release: platforms that must be staged")
    ap.add_argument("--authorize", default="", help="gated modes: the exact authorization sentence")
    ap.add_argument("--yes", action="store_true", help="gated modes: skip the interactive confirmation")
    ap.add_argument("--dry-run", action="store_true", help="gated modes: print the commands and stop")
    ap.add_argument("--message", help="commit-push: commit message")
    a = ap.parse_args()
    v = (a.version or C.version_py()).lstrip("v"); tag = C.pep440_to_tag(v) if C.SEMVER_RE.match(v) else f"v{v}"
    latest = C.git("describe", "--tags", "--abbrev=0")

    if a.mode == "audit":
        step("repository state", [PY, script("inspect_release_state.py")])
        step("version consistency", [PY, script("verify_version.py"), "--allow-missing-notes"], allow_fail=True)
        step("private-file check", [PY, script("private_file_check.py"), "--tree"], allow_fail=True)
        return 0

    if a.mode == "build-local":
        pre = [PY, script("release_preflight.py"), "--version", v, "--tests", a.tests] + (["--allow-dirty"] if a.allow_dirty else [])
        step("preflight", pre)
        step("wheel + sdist", [PY, script("build_python_dist.py"), "--version", v])
        step("fresh-venv smoke test", [PY, script("smoke_test_install.py"), "--version", v])
        plats = "python"
        if not a.skip_platform:
            step(f"native build for {C.host()['platform_key']}", [PY, script("build_current_platform.py"), "--version", v])
            plats += "," + C.host()["platform_key"]
        step("checksums", [PY, script("generate_checksums.py"), "--version", v])
        step("artefact validation", [PY, script("validate_artifacts.py"), "--version", v] + (["--compare-release", a.compare_release or latest] if (a.compare_release or latest) else []))
        step("reconciliation", [PY, script("reconcile_platforms.py"), "--version", v, "--require", plats])
        step("release notes draft", [PY, script("release_notes_draft.py"), "--version", v], allow_fail=True)
        step("report", [PY, script("release_report.py"), "--version", v])
        print("\nBUILD LOCAL complete. Nothing was committed, tagged, pushed or published.")
        return 0

    if a.mode == "prepare-rc":
        if not a.version:
            raise SystemExit("prepare-rc needs --version X.Y.Z")
        return step("prepare release candidate", [PY, script("prepare_release_candidate.py"), "--version", v, "--tests", a.tests] + (["--execute"] if a.execute else []), allow_fail=True)

    if a.mode == "commit-push":
        files = ["make_my_figure_core/version.py", "CHANGELOG.md", "README.md", f"docs/RELEASE_NOTES_v{v}.md",
                 "docs/manuals/Quick_Start/MakeMyFigure_Quick_Start.md", "docs/manuals/User_Manual/MakeMyFigure_User_Manual.md"]
        files = [f for f in files if os.path.exists(os.path.join(C.ROOT, f))]
        msg = a.message or f"Prepare {tag}: version bump, changelog, release notes"
        cmds = [["git", "add", *files], ["git", "commit", "-m", msg], ["git", "push", "origin", C.git("rev-parse", "--abbrev-ref", "HEAD")]]
        print("commit-push would run:"); [print("  $ " + " ".join(shlex.quote(x) for x in c)) for c in cmds]
        if a.dry_run:
            print("dry run - stopped."); return 0
        step("preflight (release strictness, dirty allowed because we are committing the release files)",
             [PY, script("release_preflight.py"), "--version", v, "--tests", a.tests, "--allow-dirty"])
        gate("commit-push", v, a)
        for c in cmds:
            step(" ".join(c[:2]), c)
        print(f"\ncommit-push done: {C.git('rev-parse', '--short', 'HEAD')} pushed."); return 0

    if a.mode == "finalize":
        cmd = [PY, script("finalize_release.py"), "--tag", tag, "--prefer-local", a.prefer_local] + (["--dry-run"] if a.dry_run else []) \
            + (["--authorize", a.authorize] if a.authorize else []) + (["--yes"] if a.yes else [])
        return step("finalize release after CI", cmd, allow_fail=True)

    if a.mode == "release":
        base = os.path.join(C.STAGING_ROOT, v)
        assets = []
        for plat in ("python", "windows", "macos", "linux", "manuals"):
            d = os.path.join(base, plat)
            if os.path.isdir(d):
                assets += [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith((".whl", ".tar.gz", ".exe", ".zip", ".dmg", ".AppImage", ".pdf"))]
        sums = os.path.join(base, "checksums", "SHA256SUMS.txt"); notes = os.path.join(base, "RELEASE_NOTES_DRAFT.md")
        if os.path.exists(sums):
            assets.append(sums)
        cmds = [["git", "tag", "-a", tag, "-m", f"MakeMyFigure {tag}"], ["git", "push", "origin", tag],
                ["gh", "release", "create", tag, "--title", f"MakeMyFigure {tag}", "--notes-file", notes, "--verify-tag", *assets]]
        print(f"release would run ({len(assets)} assets):"); [print("  $ " + " ".join(shlex.quote(x) for x in c)) for c in cmds]
        if a.dry_run:
            print("dry run - stopped."); return 0
        step("preflight (release strictness)", [PY, script("release_preflight.py"), "--version", v, "--tests", a.tests, "--for-release"])
        step("tag pre-check", [PY, script("verify_tag.py"), "--tag", tag, "--pre-check"])
        step("reconciliation", [PY, script("reconcile_platforms.py"), "--version", v, "--require", a.platforms])
        step("checksums verify", [PY, script("generate_checksums.py"), "--version", v, "--verify"])
        step("artefact validation", [PY, script("validate_artifacts.py"), "--version", v] + (["--compare-release", a.compare_release or latest] if latest else []))
        if not os.path.exists(notes):
            raise SystemExit(f"release notes draft missing: {notes} (run release_notes_draft.py and have the author approve it)")
        gate("release", v, a)
        for c in cmds:
            step(" ".join(c[:3]), c)
        step("post-release tag verification", [PY, script("verify_tag.py"), "--tag", tag])
        step("ledger record", [PY, script("record_release.py"), "--tag", tag], allow_fail=True)
        print(f"\nrelease {tag} published. Post-release: download one asset per OS and smoke-test; confirm SHA256SUMS.txt; update the ledger notes.")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
