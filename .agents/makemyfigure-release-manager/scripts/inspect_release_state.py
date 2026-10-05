"""AUDIT: report the release-relevant state of this checkout. READ-ONLY.

    python .agents/makemyfigure-release-manager/scripts/inspect_release_state.py [--json out.json] [--no-fetch]

Prints and (optionally) writes: repository, remote, branch, HEAD, dirty/untracked state, tags
(latest, on HEAD), version.py and every other version location, live plot / statistics counts,
packaging mechanism detected from the tree, build tooling available on this machine, previous
GitHub release (via gh, if installed and online), and existing dist/ contents.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402


def tool(name: str) -> str:
    return shutil.which(name) or ""


def python_module(mod: str) -> str:
    r = C.run([sys.executable, "-c", f"import {mod}; print(getattr({mod}, '__version__', 'present'))"])
    return r.stdout.strip() if r.returncode == 0 else ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", default=os.path.join(C.REPORTS_DIR, "release_state.json"))
    ap.add_argument("--no-fetch", action="store_true", help="do not contact the remote")
    a = ap.parse_args()

    st = {"generated": C.now_iso(), "root": C.ROOT, "host": C.host()}
    if not C.git_ok():
        st["git"] = {"error": "not a git repository"}
    else:
        if not a.no_fetch:
            C.run(["git", "fetch", "--quiet", "--tags", "origin"])
        head = C.git("rev-parse", "HEAD")
        branch = C.git("rev-parse", "--abbrev-ref", "HEAD")
        porcelain = C.git("status", "--porcelain")
        modified = [l for l in porcelain.splitlines() if not l.startswith("??")]
        untracked = [l[3:] for l in porcelain.splitlines() if l.startswith("??")]
        tags_on_head = C.git("tag", "--points-at", "HEAD").split()
        latest_tag = C.git("describe", "--tags", "--abbrev=0", "--match", "v*") or ""
        all_tags = [t for t in C.git("tag", "--list", "v*", "--sort=-creatordate").split() if C.TAG_RE.match(t)]
        upstream = C.git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
        ahead_behind = C.git("rev-list", "--left-right", "--count", f"HEAD...{upstream}") if upstream else ""
        st["git"] = {
            "remote": C.git("remote", "get-url", "origin"), "branch": branch, "head": head, "head_short": head[:7],
            "head_subject": C.git("log", "-1", "--format=%s"), "head_date": C.git("log", "-1", "--format=%cs"),
            "dirty": bool(modified), "modified_files": modified[:50], "untracked_files": untracked[:50],
            "tags_on_head": tags_on_head, "latest_release_tag": latest_tag,
            "latest_release_tag_commit": C.git("rev-parse", f"{latest_tag}^{{commit}}")[:7] if latest_tag else "",
            "release_tags_newest_first": all_tags[:12], "upstream": upstream,
            "ahead_behind_upstream": ahead_behind.replace("\t", " ahead / ") + " behind" if ahead_behind else "no upstream",
            "commits_since_latest_tag": C.git("rev-list", "--count", f"{latest_tag}..HEAD") if latest_tag else "",
        }
    st["version"] = {"version_py": C.version_py(), "tag_form": C.pep440_to_tag(C.version_py()),
                     "locations": C.version_locations()}
    st["version"]["all_locations_agree"] = all(r["matches"] for r in st["version"]["locations"] if r["matches"] is not None)
    st["project_facts"] = C.project_facts()
    st["packaging"] = {
        "python_dist": "setuptools (pyproject.toml, dynamic version) + setup.py resource staging into make_my_figure_core/_bundled; built with `python -m build`",
        "desktop": "PyInstaller one-folder app from packaging/make_my_figure.spec via scripts/build_desktop.py; per-OS wrappers scripts/build_windows.ps1 (zip + Inno Setup exe), build_macos.sh (.app -> .dmg, zip fallback), build_linux.sh (tar.gz + AppImage)",
        "ci": ".github/workflows/build_desktop_releases.yml (tag push v* or manual dispatch; installers uploaded to the GitHub release; wheel/sdist, manuals and SHA256SUMS.txt are manual)",
        "files_present": {p: os.path.exists(os.path.join(C.ROOT, p)) for p in (
            "pyproject.toml", "setup.py", "MANIFEST.in", "packaging/make_my_figure.spec", "packaging/windows_installer.iss",
            "scripts/build_desktop.py", "scripts/build_windows.ps1", "scripts/build_macos.sh", "scripts/build_linux.sh",
            ".github/workflows/build_desktop_releases.yml", "assets/icons/icon.ico", "assets/icons/icon_256.png", "docs/RELEASE_CHECKLIST.md")},
    }
    st["tooling"] = {
        "python": sys.version.split()[0], "pyinstaller": python_module("PyInstaller"), "build": python_module("build"),
        "twine": python_module("twine"), "PySide6": python_module("PySide6"), "pytest": python_module("pytest"),
        "git": tool("git"), "gh": tool("gh"), "appimagetool": tool("appimagetool"), "iscc": tool("iscc") or tool("ISCC"),
        "hdiutil": tool("hdiutil"), "iconutil": tool("iconutil"), "pwsh": tool("pwsh") or tool("powershell"),
    }
    dist = os.path.join(C.ROOT, "dist")
    st["dist"] = {"exists": os.path.isdir(dist),
                  "top_level": sorted(os.listdir(dist))[:40] if os.path.isdir(dist) else [],
                  "staging_versions": sorted(os.listdir(C.STAGING_ROOT)) if os.path.isdir(C.STAGING_ROOT) else []}
    if tool("gh") and not a.no_fetch:
        r = C.run(["gh", "release", "view", "--repo", C.REPO_SLUG, "--json", "tagName,publishedAt,isDraft,isPrerelease,assets,url"])
        if r.returncode == 0:
            try:
                rel = json.loads(r.stdout)
                st["github_latest_release"] = {"tag": rel["tagName"], "published": rel["publishedAt"], "url": rel["url"],
                                               "assets": [x["name"] for x in rel.get("assets", [])]}
            except json.JSONDecodeError:
                pass
        r = C.run(["gh", "repo", "view", C.REPO_SLUG, "--json", "visibility", "-q", ".visibility"])
        st["github_visibility"] = r.stdout.strip() if r.returncode == 0 else "unknown"

    C.write_json(a.json, st)
    g = st.get("git", {})
    print(f"MakeMyFigure release state  ({st['generated']})")
    print(f"  root            {C.ROOT}")
    print(f"  host            {st['host']['os']} {st['host'].get('release','')} {st['host']['machine']}  python {st['host']['python']}" + ("  (WSL)" if st['host'].get('wsl') else ""))
    print(f"  branch / HEAD   {g.get('branch')} @ {g.get('head_short')}  {g.get('head_subject','')[:70]}")
    print(f"  upstream        {g.get('upstream') or '-'}  {g.get('ahead_behind_upstream','')}")
    print(f"  working tree    {'DIRTY (' + str(len(g.get('modified_files', []))) + ' modified)' if g.get('dirty') else 'clean'}; untracked {len(g.get('untracked_files', []))}")
    print(f"  latest tag      {g.get('latest_release_tag')} -> {g.get('latest_release_tag_commit')}  ({g.get('commits_since_latest_tag')} commits since)")
    print(f"  tags on HEAD    {g.get('tags_on_head') or '-'}")
    print(f"  version.py      {st['version']['version_py']}  (tag form {st['version']['tag_form']}); all locations agree: {st['version']['all_locations_agree']}")
    for row in st["version"]["locations"]:
        flag = "ok " if row["matches"] else ("-- " if row["matches"] is None else "!! ")
        print(f"     {flag}{row['location']}: {row['value']}")
    pf = st["project_facts"]
    print(f"  live facts      {pf.get('plot_types')} plot types, {pf.get('statistical_procedures')} statistical procedures" + (f"  ERROR {pf['error']}" if pf.get('error') else ""))
    print(f"  packaging       {st['packaging']['python_dist']}")
    print(f"                  {st['packaging']['desktop']}")
    missing = [p for p, ok in st["packaging"]["files_present"].items() if not ok]
    print(f"  packaging files {'all present' if not missing else 'MISSING: ' + ', '.join(missing)}")
    print("  tooling         " + ", ".join(f"{k}={'yes' if v else 'no'}" if k not in ('pyinstaller', 'build', 'PySide6', 'pytest', 'twine', 'python') else f"{k}={v or 'no'}" for k, v in st["tooling"].items()))
    if "github_latest_release" in st:
        gl = st["github_latest_release"]
        print(f"  GitHub latest   {gl['tag']} ({gl['published'][:10]}) {len(gl['assets'])} assets; repo visibility {st.get('github_visibility')}")
    print(f"  dist/           {len(st['dist']['top_level'])} entries; staged versions {st['dist']['staging_versions'] or '-'}")
    print(f"  written         {os.path.relpath(a.json, C.ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
