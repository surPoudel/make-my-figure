"""PREFLIGHT: everything that must be true before a build is trusted or a release candidate is cut.
READ-ONLY apart from reports/release_preflight.json.

    python .agents/makemyfigure-release-manager/scripts/release_preflight.py [--version X.Y.Z]
           [--tests quick|full|skip] [--allow-dirty] [--for-release]

Checks (each is PASS / WARN / STOP):
  git      working tree clean; branch recorded (release tags are cut from main - WARN elsewhere,
           STOP with --for-release); HEAD present on origin (WARN if not pushed)
  version  version.py == requested; every documented location agrees (verify_version logic);
           CHANGELOG has a "## [X.Y.Z]" section; docs/RELEASE_NOTES_vX.Y.Z.md exists (WARN if not)
  tag      vX.Y.Z must not already exist locally or on origin
  files    packaging inputs present (spec, build scripts, Inno .iss, CI workflow, icons)
  private  private_file_check on the tree (STOP on any STOP finding)
  tests    --tests quick (release gates) | full (headless suite) | skip ; counts parsed live
  tools    build / twine / pyinstaller importable; gh authenticated (WARN only - never required
           for local builds)
Exit 1 when any STOP is present.
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
PACKAGING_FILES = ["packaging/make_my_figure.spec", "packaging/windows_installer.iss", "scripts/build_desktop.py",
                   "scripts/build_windows.ps1", "scripts/build_macos.sh", "scripts/build_linux.sh",
                   ".github/workflows/build_desktop_releases.yml", "assets/icons/icon.ico", "assets/icons/icon_256.png",
                   "pyproject.toml", "setup.py", "MANIFEST.in", "LICENSE", "CHANGELOG.md", "README.md"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version")
    ap.add_argument("--tests", choices=["quick", "full", "skip"], default="quick")
    ap.add_argument("--allow-dirty", action="store_true", help="downgrade a dirty tree to WARN (local test builds only)")
    ap.add_argument("--for-release", action="store_true", help="stricter: must be on main, HEAD pushed, notes present")
    ap.add_argument("--json", default=os.path.join(C.REPORTS_DIR, "release_preflight.json"))
    a = ap.parse_args()
    v = (a.version or C.version_py()).lstrip("v")
    tag = C.pep440_to_tag(v)
    rows = []

    def add(area, check, level, detail=""):
        rows.append({"area": area, "check": check, "level": level, "detail": detail})

    # --- git
    dirty = C.git("status", "--porcelain")
    add("git", "working tree clean", "PASS" if not dirty else ("WARN" if a.allow_dirty else "STOP"),
        "" if not dirty else f"{len(dirty.splitlines())} modified/untracked path(s): " + "; ".join(l.strip() for l in dirty.splitlines()[:5]))
    branch = C.git("rev-parse", "--abbrev-ref", "HEAD")
    add("git", "branch", "PASS" if branch == "main" else ("STOP" if a.for_release else "WARN"), f"{branch} (releases are tagged from main)")
    head = C.git("rev-parse", "HEAD")
    C.run(["git", "fetch", "origin", "--quiet"], timeout=120)
    on_remote = C.git("branch", "-r", "--contains", head)
    add("git", "HEAD present on origin", "PASS" if on_remote else ("STOP" if a.for_release else "WARN"),
        on_remote.replace("\n", ", ").strip() or "not pushed - a tag must point at a commit that exists on origin")
    # --- version
    add("version", "version.py", "PASS" if C.version_py() == v else "STOP", f"version.py={C.version_py()} requested={v}")
    add("version", "PEP 440 / semver form", "PASS" if C.SEMVER_RE.match(v) else "STOP", v)
    for loc in C.version_locations(v):
        if loc["value"] is None and "RELEASE_NOTES" in loc["location"]:
            add("version", loc["location"], "STOP" if a.for_release else "WARN", "missing - release_notes_draft.py can produce a draft")
        else:
            add("version", loc["location"], "PASS" if loc["matches"] else "STOP", f"says {loc['value']}")
    chg = open(os.path.join(C.ROOT, "CHANGELOG.md"), encoding="utf-8").read()
    add("version", f"CHANGELOG.md has '## [{v}]' section", "PASS" if re.search(rf"^## \[{re.escape(v)}\]", chg, re.M) else "STOP")
    # --- tag
    local_tag = C.git("rev-parse", "-q", "--verify", f"refs/tags/{tag}")
    remote_tag = C.git("ls-remote", "--tags", "origin", tag)
    add("tag", f"{tag} not yet created", "PASS" if not (local_tag or remote_tag) else "STOP",
        "" if not (local_tag or remote_tag) else "tag already exists - this version has been used; bump the version")
    last_tag = C.git("describe", "--tags", "--abbrev=0")
    add("tag", "previous tag", "PASS", f"{last_tag} ({C.git('rev-list', '--count', f'{last_tag}..HEAD')} commits since)" if last_tag else "none")
    # --- files
    missing = [f for f in PACKAGING_FILES if not os.path.exists(os.path.join(C.ROOT, f))]
    add("files", "packaging inputs present", "PASS" if not missing else "STOP", ", ".join(missing) if missing else f"{len(PACKAGING_FILES)} files")
    # --- private
    r = subprocess.run([sys.executable, os.path.join(HERE, "private_file_check.py"), "--tree"], text=True, capture_output=True, cwd=C.ROOT)
    first = (r.stdout or "").splitlines()[0] if r.stdout else r.stderr[-200:]
    add("private", "private-file check on the tree", "PASS" if r.returncode == 0 else "STOP", first)
    # --- live facts
    facts = C.project_facts()
    add("facts", "live counts", "PASS" if "error" not in facts else "WARN", f"{facts.get('plot_types')} plot types, {facts.get('statistical_procedures')} statistical procedures")
    # --- tests
    if a.tests != "skip":
        r = subprocess.run([sys.executable, os.path.join(HERE, "run_tests.py")] + (["--quick"] if a.tests == "quick" else []), text=True, capture_output=True, cwd=C.ROOT)
        summary = [l for l in (r.stdout or "").splitlines() if "passed" in l or "RESULT" in l]
        add("tests", f"pytest ({a.tests})", "PASS" if r.returncode == 0 else "STOP", " | ".join(summary)[:300] or r.stderr[-300:])
    else:
        add("tests", "pytest", "WARN", "skipped by request")
    # --- tools
    for mod in ("build", "twine", "PyInstaller"):
        r = subprocess.run([sys.executable, "-c", f"import {mod}, importlib.metadata as m; print(m.version('{mod.lower() if mod != 'PyInstaller' else 'pyinstaller'}'))"], text=True, capture_output=True)
        add("tools", mod, "PASS" if r.returncode == 0 else "WARN", r.stdout.strip() or "not importable in this interpreter")
    r = C.run(["gh", "auth", "status"])
    add("tools", "gh authenticated", "PASS" if r.returncode == 0 else "WARN", (r.stdout + r.stderr).strip().splitlines()[1].strip() if r.returncode == 0 and len((r.stdout + r.stderr).splitlines()) > 1 else "not available (only needed for publishing)")
    stops = [x for x in rows if x["level"] == "STOP"]
    warns = [x for x in rows if x["level"] == "WARN"]
    rec = {"generated": C.now_iso(), "version": v, "tag": tag, "branch": branch, "commit": head, "for_release": a.for_release,
           "checks": rows, "stop": len(stops), "warn": len(warns), "ok": not stops, "facts": facts}
    C.write_json(a.json, rec)
    for x in rows:
        print(f"  {x['level']:4s} [{x['area']}] {x['check']}{'  - ' + x['detail'] if x['detail'] else ''}")
    print(f"RESULT: {'PASS' if not stops else 'FAIL'}  ({len(stops)} STOP, {len(warns)} WARN) -> {os.path.relpath(a.json, C.ROOT)}")
    return 0 if not stops else 1


if __name__ == "__main__":
    raise SystemExit(main())
