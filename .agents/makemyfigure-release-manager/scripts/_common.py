"""Shared helpers for the MakeMyFigure Release Manager scripts.

Standard library only (plus the project's own code when a script needs it). Works from any
current directory: the repository root is found by walking up from this file to the directory
that holds pyproject.toml and make_my_figure_core/. Portable across Windows, macOS and Linux;
never needs the network unless a script says so (push, tag publication, GitHub release).
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional


def repo_root(start: Optional[str] = None) -> str:
    here = os.path.abspath(start or os.path.dirname(__file__))
    while True:
        if os.path.exists(os.path.join(here, "pyproject.toml")) and os.path.isdir(os.path.join(here, "make_my_figure_core")):
            return here
        parent = os.path.dirname(here)
        if parent == here:
            raise SystemExit("repository root not found above " + (start or __file__))
        here = parent


ROOT = repo_root()
AGENT_DIR = os.path.join(ROOT, ".agents", "makemyfigure-release-manager")
STAGING_ROOT = os.path.join(ROOT, "release_staging")   # release_staging/<version>/<platform>/ (outside dist/, which the project build scripts wipe with --clean)
REPORTS_DIR = os.path.join(AGENT_DIR, "reports")               # machine-readable outputs of the scripts
LEDGER_DIR = os.path.join(AGENT_DIR, "release_history")
VERSION_FILE = os.path.join(ROOT, "make_my_figure_core", "version.py")
APP_NAME = "MakeMyFigure"
REPO_SLUG = "surPoudel/make-my-figure"

# Public artefact naming used by v1.1.0 (scripts/build_*.{sh,ps1}); the checksum file and
# the manuals are added by hand. Kept here so every script agrees on the expected set.
EXPECTED_PUBLIC_ARTIFACTS = {
    "python": ["make_my_figure_core-{v}-py3-none-any.whl", "make_my_figure_core-{v}.tar.gz"],
    "windows": ["MakeMyFigure-{v}-Setup.exe", "MakeMyFigure-{v}-windows.zip"],
    "macos": ["MakeMyFigure-{v}.dmg"],
    "linux": ["MakeMyFigure-{v}-linux-x86_64.tar.gz", "MakeMyFigure-{v}.AppImage"],
    "manuals": ["MakeMyFigure_v{v}_Quick_Start.pdf", "MakeMyFigure_v{v}_User_Manual.pdf"],
    "checksums": ["SHA256SUMS.txt"],
}
OPTIONAL_PUBLIC_ARTIFACTS = {"MakeMyFigure-{v}.AppImage", "MakeMyFigure-{v}-windows.zip"}   # fallbacks / secondary

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:(rc|a|b)(\d+))?$")          # PEP 440 form used in version.py
TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)(?:-rc(\d+))?$")               # tag form used on GitHub


# ------------------------------------------------------------------ process helpers
def run(cmd: List[str], cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None,
        check: bool = False, capture: bool = True, timeout: Optional[int] = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd or ROOT, env=env, text=True, capture_output=capture, check=check, timeout=timeout)


def git(*args: str, check: bool = False) -> str:
    r = run(["git", *args], check=check)
    return (r.stdout or "").strip()


def git_ok() -> bool:
    return run(["git", "rev-parse", "--is-inside-work-tree"]).returncode == 0


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def write_json(path: str, obj: Any) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, default=str)
    return path


def read_json(path: str) -> Any:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def host() -> Dict[str, str]:
    sysname = platform.system()
    key = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(sysname, sysname.lower())
    info = {"os": sysname, "platform_key": key, "os_version": platform.version(), "release": platform.release(),
            "machine": platform.machine(), "python": platform.python_version(), "python_executable": sys.executable}
    if sysname == "Linux":
        try:
            out = run(["ldd", "--version"]).stdout.splitlines()[0]
            info["glibc"] = out.split()[-1]
        except Exception:  # noqa: BLE001
            pass
        if os.path.exists("/proc/version") and "microsoft" in open("/proc/version").read().lower():
            info["wsl"] = "true"
    return info


# ------------------------------------------------------------------ working-tree state (one definition for every script)
SHIPPED_PATHS = ("make_my_figure_core/", "apps/", "schemas/", "style_profiles/", "mock_data/", "examples/", "assets/", "packaging/",
                 "scripts/build_", "scripts/make_icons", "pyproject.toml", "setup.py", "MANIFEST.in", "LICENSE", "README.md", "CHANGELOG.md")


def tree_state() -> Dict[str, Any]:
    """Modified tracked files, or untracked files inside a path that the wheel / app bundles, make a
    build non-reproducible from its commit -> dirty. Untracked files elsewhere (benchmarks, docs,
    reports, scratch scripts) cannot enter an artefact -> recorded, not dirty."""
    lines = git("status", "--porcelain", "-uall").splitlines()
    modified = [l.strip() for l in lines if not l.startswith("??")]
    untracked = [l[3:] for l in lines if l.startswith("??")]
    untracked_shipped = [u for u in untracked if u.startswith(SHIPPED_PATHS)]
    return {"modified": modified, "untracked_shipped": untracked_shipped, "untracked_other": [u for u in untracked if u not in untracked_shipped],
            "dirty": bool(modified or untracked_shipped)}


# ------------------------------------------------------------------ version discovery
def version_py() -> str:
    text = open(VERSION_FILE, encoding="utf-8").read()
    m = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.M)
    return m.group(1) if m else ""


def pep440_to_tag(v: str) -> str:
    """1.1.0 -> v1.1.0 ; 1.0.0rc1 -> v1.0.0-rc1 (the project's convention)."""
    m = SEMVER_RE.match(v)
    if m and m.group(4):
        return f"v{m.group(1)}.{m.group(2)}.{m.group(3)}-{m.group(4)}{m.group(5)}"
    return "v" + v


def tag_to_pep440(tag: str) -> str:
    m = TAG_RE.match(tag)
    if not m:
        return tag.lstrip("v")
    base = f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
    return base + (f"rc{m.group(4)}" if m.group(4) else "")


def version_locations(v: Optional[str] = None) -> List[Dict[str, Any]]:
    """Every authoritative place the version appears, with what it currently says.
    Derived from the v1.1.0 / v1.1.1 release commits (f68a2f3, dc99f07)."""
    v = v or version_py()
    rows: List[Dict[str, Any]] = []

    def add(where, found, expected_note=""):
        rows.append({"location": where, "value": found, "matches": (found == v) if found is not None else None, "note": expected_note})

    add("make_my_figure_core/version.py", version_py(), "single source of truth; pyproject reads it dynamically")
    chg = _read(os.path.join(ROOT, "CHANGELOG.md"))
    m = re.search(r"^## \[(\d[^\]]*)\]", chg, re.M)
    add("CHANGELOG.md first released section", m.group(1) if m else None, "## [X.Y.Z] heading below Unreleased")
    readme = _read(os.path.join(ROOT, "README.md"))
    m = re.search(r"badge/version-([0-9][^-]*)-", readme)
    add("README.md version badge", m.group(1) if m else None)
    m = re.findall(r"MakeMyFigure-(\d+\.\d+\.\d+[^-.]*)[-.](?:Setup\.exe|dmg|windows\.zip|linux)", readme)
    add("README.md installer file names", sorted(set(m))[0] if m else None, "install table")
    for rel in ("docs/manuals/Quick_Start/MakeMyFigure_Quick_Start.md", "docs/manuals/User_Manual/MakeMyFigure_User_Manual.md"):
        t = _read(os.path.join(ROOT, rel))
        m = re.search(r"\*\*MakeMyFigure version:\*\*\s*(\S+)", t)
        add(rel + " banner", m.group(1) if m else None, "regenerated by scripts/build_manuals.py")
    notes = os.path.join(ROOT, "docs", f"RELEASE_NOTES_v{v}.md")
    add(f"docs/RELEASE_NOTES_v{v}.md", v if os.path.exists(notes) else None, "release notes file for the version")
    return rows


def _read(path: str) -> str:
    try:
        return open(path, encoding="utf-8", errors="ignore").read()
    except OSError:
        return ""


# ------------------------------------------------------------------ project facts (live)
def project_facts() -> Dict[str, Any]:
    """Plot and statistics counts from the code (never hard-coded)."""
    out: Dict[str, Any] = {}
    code = (
        "import os,sys; os.environ.setdefault('MPLBACKEND','Agg'); sys.path.insert(0, %r);"
        "from make_my_figure_core.plots.registry import available_plot_types;"
        "from make_my_figure_core.statistics.test_registry import TESTS;"
        "from make_my_figure_core.version import __version__;"
        "import json; print(json.dumps({'plot_types': len(available_plot_types()), 'statistical_procedures': len(TESTS), 'version': __version__}))"
    ) % ROOT
    r = run([sys.executable, "-c", code])
    if r.returncode == 0 and r.stdout.strip():
        try:
            out.update(json.loads(r.stdout.strip().splitlines()[-1]))
        except json.JSONDecodeError:
            out["error"] = r.stdout[-300:]
    else:
        out["error"] = (r.stderr or "")[-400:]
    return out


def staging_dir(version: str, platform_key: Optional[str] = None) -> str:
    d = os.path.join(STAGING_ROOT, version)
    if platform_key:
        d = os.path.join(d, platform_key)
    os.makedirs(d, exist_ok=True)
    return d


def print_table(rows: List[Dict[str, Any]], cols: List[str]) -> None:
    widths = {c: max(len(c), *(len(str(r.get(c, ""))) for r in rows)) for c in cols}
    print("  ".join(c.ljust(widths[c]) for c in cols))
    for r in rows:
        print("  ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols))
