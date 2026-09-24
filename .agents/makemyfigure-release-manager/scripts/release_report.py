"""Consolidated RELEASE_REPORT.md for a version from the JSON produced by the other scripts.

    python .agents/makemyfigure-release-manager/scripts/release_report.py --version X.Y.Z

Reads reports/*.json and release_staging/<v>/**/*manifest.json, never re-runs anything. States
explicitly which publication steps have NOT been performed (tag, GitHub release, push).
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402


def load(path):
    return C.read_json(path) if os.path.exists(path) else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", default=C.version_py())
    a = ap.parse_args()
    v = a.version.lstrip("v"); tag = C.pep440_to_tag(v)
    R = C.REPORTS_DIR; base = os.path.join(C.STAGING_ROOT, v)
    state = load(os.path.join(R, "release_state.json")); pre = load(os.path.join(R, "release_preflight.json"))
    tests = load(os.path.join(R, "test_results.json")); py = load(os.path.join(base, "python", "python_build_manifest.json"))
    smoke = load(os.path.join(R, "wheel_smoke_test.json")); rec = load(os.path.join(base, "reconciliation.json"))
    sums = load(os.path.join(base, "checksums", "release_artifacts.json")); val = load(os.path.join(R, "artifact_validation.json"))
    plats = {p: load(os.path.join(base, p, "platform_build_manifest.json")) for p in ("windows", "macos", "linux")}
    tagv = load(os.path.join(R, "tag_verification.json"))
    L = [f"# MakeMyFigure {tag} - build and release report", "", f"Generated {C.now_iso()} by the Build and Release Manager agent on "
         f"{C.host()['os']} {C.host().get('release', '')}{' (WSL)' if C.host().get('wsl') else ''}.", "",
         f"Source: branch `{C.git('rev-parse', '--abbrev-ref', 'HEAD')}` commit `{C.git('rev-parse', '--short', 'HEAD')}`; "
         f"working tree {'clean' if not C.git('status', '--porcelain') else 'DIRTY'}; version.py `{C.version_py()}`.", ""]
    L += ["## 1. Repository state", ""]
    if state:
        L += [f"- Latest public tag: `{state.get('latest_tag', {}).get('name', '?')}` at `{str(state.get('latest_tag', {}).get('commit', ''))[:10]}`; "
              f"commits since: {state.get('latest_tag', {}).get('commits_since', '?')}",
              f"- Live facts: {state.get('facts', {}).get('plot_types')} plot types, {state.get('facts', {}).get('statistical_procedures')} statistical procedures",
              f"- GitHub latest release: {state.get('github', {}).get('latest_release', {}).get('tagName', 'n/a')} "
              f"({len(state.get('github', {}).get('latest_release', {}).get('assets', []) or [])} assets); repository visibility {state.get('github', {}).get('visibility', '?')}"]
    else:
        L.append("- inspect_release_state.py has not been run")
    L += ["", "## 2. Preflight", ""]
    if pre:
        L.append(f"- {pre['stop']} STOP, {pre['warn']} WARN -> {'PASS' if pre['ok'] else 'FAIL'}")
        L += [f"  - {x['level']} [{x['area']}] {x['check']}{': ' + x['detail'] if x['detail'] else ''}" for x in pre["checks"] if x["level"] != "PASS"]
    else:
        L.append("- not run")
    L += ["", "## 3. Tests", ""]
    if tests:
        L += [f"- {r['label']}: {r['passed']} passed, {r['failed']} failed, {r['skipped']} skipped, {r['errors']} errors ({r['wall_seconds']} s)" for r in tests["runs"]]
    else:
        L.append("- not run by the agent in this session")
    L += ["", "## 4. Python distributions", ""]
    if py:
        L += [f"- `{x['file']}` {x['size'] / 1e6:.2f} MB sha256 `{x['sha256']}`" for x in py["artifacts"]]
        L.append(f"- twine check: {'ok' if (py.get('twine_check') or {}).get('returncode') == 0 else 'not run / failed'}; private-file check: "
                 + ", ".join(f"{k} {'clean' if v2['returncode'] == 0 else 'FINDINGS'}" for k, v2 in py.get("private_file_check", {}).items()))
    if smoke:
        L.append(f"- fresh-venv smoke test: {'PASS' if smoke['ok'] else 'FAIL'} - " + "; ".join(f"{k}={c.get('value') if c['ok'] else 'ERROR ' + c.get('error', '')}" for k, c in smoke.get("checks", {}).items()))
    L += ["", "## 5. Native desktop builds", "", "| platform | commit | interpreter | app folder | self-test | artefacts |", "|---|---|---|---|---|---|"]
    for p, m in plats.items():
        if not m:
            L.append(f"| {p} | - | - | - | not built on this host | - |"); continue
        L.append(f"| {p} | `{m['commit_short']}`{' (dirty)' if m['dirty'] else ''} | {m['interpreter']['mode']}; PyInstaller {m['tool_versions'].get('pyinstaller')}, PySide6 {m['tool_versions'].get('PySide6')} | "
                 f"{m.get('app_folder', {}).get('bytes', 0) / 1e6:.0f} MB / {m.get('app_folder', {}).get('files', 0)} files | "
                 f"{'OK' if m['selftest']['ok'] else m['selftest'].get('summary')} ({m['selftest'].get('seconds', '?')} s) | "
                 + ", ".join(f"`{x['file']}` {x['size'] / 1e6:.0f} MB" for x in m["artifacts"]) + "|")
    L += ["", "## 6. Reconciliation and checksums", ""]
    L.append(f"- reconciliation: {'PASS' if rec['ok'] else 'FAIL'}; same commit across builds: {rec['same_commit']}; platforms: {', '.join(rec['platforms'])}" if rec else "- reconciliation not run")
    if sums:
        L.append(f"- SHA256SUMS.txt covers {len(sums['artifacts'])} artefact(s); expected but not staged: {', '.join(sums['expected_missing']) or 'none'}")
    if val:
        L.append(f"- artefact validation: {'PASS' if val['ok'] else 'FAIL'}" + (f" (sizes compared with {val['compare_release']})" if val.get("compare_release") else ""))
        L += [f"  - {'ok' if x['ok'] else '!!'} `{x['filename']}` {x['archive_detail']} {x['size_vs_reference']}" for x in val["artifacts"]]
    L += ["", "## 7. Publication status", ""]
    if tagv:
        L.append(f"- tag {tagv['tag']} {'pre-check' if tagv['pre_check'] else 'verification'}: {'PASS' if tagv['ok'] else 'FAIL'}")
    exists = C.git("rev-parse", "-q", "--verify", f"refs/tags/{tag}")
    L += [f"- git tag `{tag}`: {'EXISTS at ' + exists[:10] if exists else 'NOT created'}",
          f"- GitHub release `{tag}`: " + ("published" if C.run(["gh", "release", "view", tag]).returncode == 0 else "NOT created"),
          "- Nothing in this report was pushed, tagged or published by the agent unless the two lines above say so."]
    out = os.path.join(C.staging_dir(v), "RELEASE_REPORT.md")
    open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
    open(os.path.join(C.REPORTS_DIR, "RELEASE_REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L)); print(f"\n-> {os.path.relpath(out, C.ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
