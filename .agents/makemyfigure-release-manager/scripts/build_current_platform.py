"""BUILD LEVEL 2: native desktop build for the platform this script runs on, using the project's
own wrapper (scripts/build_linux.sh, scripts/build_macos.sh, scripts/build_windows.ps1).

    python .agents/makemyfigure-release-manager/scripts/build_current_platform.py [--version X.Y.Z]
           [--venv PATH | --system-python] [--fresh-venv] [--skip-selftest] [--app-only]

What it does, in order
  1. Confirms version.py == --version (never edits anything).
  2. Creates or reuses a CLEAN build virtual environment OUTSIDE the repository
     (default ~/.cache/makemyfigure-release/venv-<platform>-py<X.Y>; %LOCALAPPDATA% on Windows)
     and installs ".[desktop,build]" exactly as CI does. A polluted interpreter (conda base
     etc.) produces a bloated bundle - the WSL conda build was 929 MB against a 188 MB v1.1.0
     tarball - so --system-python is allowed only as an explicit, recorded choice.
  3. Runs the platform wrapper with that venv first on PATH. The wrappers call
     scripts/build_desktop.py --clean, which deletes build/ and dist/ (staging lives in
     release_staging/ for that reason).
  4. Runs the built executable with --selftest (renders all plot types, exports, package round
     trip, statistics) - offscreen when no display is present - and the private-file check on
     the app folder.
  5. Moves the public artefacts into release_staging/<version>/<platform>/ and writes
     platform_build_manifest.json (commit, dirty flag, tool versions, artefacts with SHA-256,
     self-test result, app-folder size). Exit 1 on any failure.
"""
from __future__ import annotations

import argparse
import glob
import os
import platform
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

PLAT = C.host()["platform_key"]


def default_venv() -> str:
    tag = f"venv-{PLAT}-py{sys.version_info.major}.{sys.version_info.minor}"
    base = os.environ.get("LOCALAPPDATA") if os.name == "nt" else os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base or os.path.expanduser("~"), "makemyfigure-release", tag)


def venv_python(venv: str) -> str:
    return os.path.join(venv, "Scripts", "python.exe") if os.name == "nt" else os.path.join(venv, "bin", "python")


def ensure_venv(venv: str, fresh: bool, log) -> str:
    if fresh and os.path.isdir(venv):
        shutil.rmtree(venv)
    py = venv_python(venv)
    if not os.path.exists(py):
        log(f"creating build venv {venv}")
        subprocess.run([sys.executable, "-m", "venv", venv], check=True)
        subprocess.run([py, "-m", "pip", "install", "-q", "--upgrade", "pip"], check=True)
    log("installing .[desktop,build] into the build venv (as CI does)")
    r = subprocess.run([py, "-m", "pip", "install", "-q", ".[desktop,build]"], cwd=C.ROOT, text=True, capture_output=True)
    if r.returncode != 0:
        raise SystemExit("pip install .[desktop,build] failed:\n" + r.stderr[-2000:])
    return py


def tool_versions(py: str) -> dict:
    code = ("import json,sys,importlib.metadata as m\n"
            "d={'python':sys.version.split()[0]}\n"
            "for p in ['pyinstaller','PySide6','matplotlib','numpy','pandas','scipy','statsmodels','lifelines','pillow']:\n"
            "    try: d[p]=m.version(p)\n"
            "    except Exception: d[p]=None\n"
            "print(json.dumps(d))")
    try:
        import json
        out = subprocess.run([py, "-c", code], text=True, capture_output=True, cwd=C.ROOT).stdout.strip()
        return json.loads(out)
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def wrapper_command():
    if PLAT == "linux":
        return ["bash", os.path.join(C.ROOT, "scripts", "build_linux.sh")]
    if PLAT == "macos":
        return ["bash", os.path.join(C.ROOT, "scripts", "build_macos.sh")]
    if PLAT == "windows":
        return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(C.ROOT, "scripts", "build_windows.ps1")]
    raise SystemExit(f"unsupported platform {PLAT}")


def app_executable():
    if PLAT == "macos":
        return os.path.join(C.ROOT, "dist", "MakeMyFigure.app", "Contents", "MacOS", "MakeMyFigure")
    return os.path.join(C.ROOT, "dist", "MakeMyFigure", "MakeMyFigure" + (".exe" if PLAT == "windows" else ""))


def app_folder():
    return os.path.join(C.ROOT, "dist", "MakeMyFigure.app" if PLAT == "macos" else "MakeMyFigure")


def public_artifacts(v: str):
    d = os.path.join(C.ROOT, "dist")
    pats = {"linux": [f"MakeMyFigure-{v}-linux-*.tar.gz", f"MakeMyFigure-{v}.AppImage"],
            "macos": [f"MakeMyFigure-{v}.dmg", f"MakeMyFigure-{v}-macos.zip"],
            "windows": [f"MakeMyFigure-{v}-Setup.exe", f"MakeMyFigure-{v}-windows.zip"]}[PLAT]
    out = []
    for p in pats:
        out += glob.glob(os.path.join(d, p))
    return sorted(out)


def folder_size(path: str):
    total = n = 0
    for dp, _, fns in os.walk(path):
        for fn in fns:
            try:
                total += os.path.getsize(os.path.join(dp, fn)); n += 1
            except OSError:
                pass
    return total, n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version")
    ap.add_argument("--venv", help="build venv path (default: outside the repo, see above)")
    ap.add_argument("--system-python", action="store_true", help="use the current interpreter (recorded; bundle may bloat)")
    ap.add_argument("--fresh-venv", action="store_true", help="recreate the build venv")
    ap.add_argument("--skip-selftest", action="store_true")
    ap.add_argument("--app-only", action="store_true", help="run scripts/build_desktop.py only (no tar/zip/dmg/installer)")
    ap.add_argument("--selftest-timeout", type=int, default=1800)
    a = ap.parse_args()
    v = (a.version or C.version_py()).lstrip("v")
    t_start = time.time()
    lines = []

    def log(msg):
        print(msg, flush=True); lines.append(msg)

    if C.version_py() != v:
        print(f"FAIL: version.py says {C.version_py()} but {v} requested"); return 1
    ts = C.tree_state()
    manifest = {"generated": C.now_iso(), "version": v, "platform": PLAT, "architecture": platform.machine(), "host": C.host(),
                "commit": C.git("rev-parse", "HEAD"), "commit_short": C.git("rev-parse", "--short", "HEAD"), "branch": C.git("rev-parse", "--abbrev-ref", "HEAD"),
                "dirty": ts["dirty"], "tree_state": ts, "ok": False}
    if a.system_python:
        py = sys.executable; manifest["interpreter"] = {"mode": "system-python (recorded: bundle may include unrelated packages)", "python": py}
    else:
        venv = a.venv or default_venv()
        py = ensure_venv(venv, a.fresh_venv, log)
        manifest["interpreter"] = {"mode": "clean build venv", "venv": venv, "python": py}
    manifest["tool_versions"] = tool_versions(py)
    log("tools: " + ", ".join(f"{k} {v2}" for k, v2 in manifest["tool_versions"].items()))
    for tool in ("appimagetool", "hdiutil", "iscc", "iscc.exe", "pandoc"):
        manifest.setdefault("tools_on_path", {})[tool] = bool(shutil.which(tool))
    env = dict(os.environ)
    bindir = os.path.dirname(py)
    env["PATH"] = bindir + os.pathsep + env.get("PATH", "")
    env.setdefault("PYTHONUTF8", "1")
    # scripts/build_desktop.py --clean removes dist/ entirely: make sure nothing of ours is there.
    for stale in glob.glob(os.path.join(C.ROOT, "dist", "*")):
        shutil.rmtree(stale) if os.path.isdir(stale) else os.remove(stale)
    cmd = [py, os.path.join(C.ROOT, "scripts", "build_desktop.py"), "--clean"] if a.app_only else wrapper_command()
    log("running: " + " ".join(cmd))
    t0 = time.time()
    r = subprocess.run(cmd, cwd=C.ROOT, env=env, text=True, capture_output=True)
    manifest["build"] = {"command": cmd, "returncode": r.returncode, "seconds": round(time.time() - t0, 1),
                         "stdout_tail": r.stdout[-3000:], "stderr_tail": r.stderr[-3000:]}
    if r.returncode != 0 or not os.path.exists(app_executable()):
        log("BUILD FAILED"); log(r.stderr[-1500:])
        C.write_json(os.path.join(C.REPORTS_DIR, f"platform_build_{PLAT}.json"), manifest); return 1
    size, n = folder_size(app_folder())
    manifest["app_folder"] = {"path": os.path.relpath(app_folder(), C.ROOT), "bytes": size, "files": n}
    log(f"app folder: {size / 1e6:.0f} MB, {n} files, built in {manifest['build']['seconds']} s")
    # Self-test of the actual executable.
    if not a.skip_selftest:
        senv = dict(os.environ)
        if PLAT == "linux" and not senv.get("DISPLAY") and not senv.get("WAYLAND_DISPLAY"):
            senv["QT_QPA_PLATFORM"] = "offscreen"
        t0 = time.time()
        try:
            sr = subprocess.run([app_executable(), "--selftest"], text=True, capture_output=True, env=senv, timeout=a.selftest_timeout, cwd=C.ROOT)
            out = (sr.stdout or "") + (sr.stderr or "")
            ok_line = [l for l in out.splitlines() if l.startswith("SELFTEST OK")]
            manifest["selftest"] = {"returncode": sr.returncode, "seconds": round(time.time() - t0, 1), "ok": bool(ok_line) and sr.returncode == 0,
                                    "summary": ok_line[0] if ok_line else out.strip().splitlines()[-1:] , "tail": out[-1500:]}
        except subprocess.TimeoutExpired:
            manifest["selftest"] = {"ok": False, "summary": f"timeout after {a.selftest_timeout}s"}
        log(f"selftest: {'OK' if manifest['selftest']['ok'] else 'FAILED'} - {manifest['selftest']['summary']}")
    else:
        manifest["selftest"] = {"ok": None, "summary": "skipped"}
    # Private-file check on the app folder (names/sizes).
    pr = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "private_file_check.py"), "--app", app_folder(),
                         "--json", os.path.join(C.REPORTS_DIR, f"private_file_check_app_{PLAT}.json")], text=True, capture_output=True, cwd=C.ROOT)
    manifest["private_file_check"] = {"returncode": pr.returncode, "summary": (pr.stdout or "").splitlines()[0] if pr.stdout else pr.stderr[-300:]}
    log(manifest["private_file_check"]["summary"])
    # Stage artefacts.
    out_dir = C.staging_dir(v, PLAT)
    for old in glob.glob(os.path.join(out_dir, "*")):
        os.remove(old)
    arts = []
    for p in public_artifacts(v):
        dest = os.path.join(out_dir, os.path.basename(p)); shutil.move(p, dest)
        arts.append({"file": os.path.basename(dest), "size": os.path.getsize(dest), "sha256": C.sha256(dest)})
        log(f"staged {os.path.basename(dest)}  {os.path.getsize(dest) / 1e6:.1f} MB")
    manifest["artifacts"] = arts
    expected = [n.format(v=v) for n in C.EXPECTED_PUBLIC_ARTIFACTS[PLAT]]
    manifest["expected_missing"] = [n for n in expected if n not in {x["file"] for x in arts}]
    if manifest["expected_missing"]:
        log("not produced on this host: " + ", ".join(manifest["expected_missing"]) + ("" if not a.app_only else " (--app-only)"))
    manifest["ok"] = (manifest["selftest"]["ok"] in (True, None)) and pr.returncode == 0 and (bool(arts) or a.app_only)
    manifest["total_seconds"] = round(time.time() - t_start, 1)
    manifest["log"] = lines
    C.write_json(os.path.join(out_dir, "platform_build_manifest.json"), manifest)
    C.write_json(os.path.join(C.REPORTS_DIR, f"platform_build_{PLAT}.json"), manifest)
    print("RESULT:", "PASS" if manifest["ok"] else "FAIL", "->", os.path.relpath(out_dir, C.ROOT))
    return 0 if manifest["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
