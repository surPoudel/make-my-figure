"""On-demand, self-contained R environment for RNA-seq DE.

Rather than bundling a ~1 GB R + Bioconductor stack into the installer, the app
installs a private R environment on first use with **micromamba**, pulling
**prebuilt** conda-forge/bioconda binaries (no compiler needed on the user's
machine). The environment lives in the per-user app-data directory and the app
points itself at its ``Rscript`` via the resolver here.

Everything is opt-in and streamed with progress. Nothing is downloaded unless
the user clicks "Set up R for RNA-seq". Subprocess calls use argument lists (no
shell) so spaces / OneDrive paths are safe.
"""

from __future__ import annotations

import os
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import urllib.request
from typing import Callable, Dict, List, Optional

# Packages installed into the managed environment (prebuilt binaries).
R_CONDA_PACKAGES = [
    "r-base>=4.2",
    "bioconductor-edger",
    "bioconductor-limma",
    "bioconductor-deseq2",
    "r-statmod",
    "r-jsonlite",
]
CONDA_CHANNELS = ["conda-forge", "bioconda"]

ProgressFn = Callable[[str], None]


def app_data_dir() -> str:
    """Per-user application data directory for Make My Figure."""
    override = os.environ.get("MAKE_MY_FIGURE_DATA_DIR")
    if override:
        return override
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    elif sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~\\AppData\\Local")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(base, "MakeMyFigure")


def r_env_prefix() -> str:
    """Path to the managed R conda environment."""
    return os.path.join(app_data_dir(), "r_env")


def managed_rscript_path() -> Optional[str]:
    """Return the managed env's Rscript path if it exists, else None."""
    prefix = r_env_prefix()
    candidates = [os.path.join(prefix, "bin", "Rscript"),
                  os.path.join(prefix, "Scripts", "Rscript.exe"),
                  os.path.join(prefix, "bin", "Rscript.exe"),
                  os.path.join(prefix, "Rscript.exe")]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def _platform_key() -> str:
    machine = platform.machine().lower()
    if sys.platform == "darwin":
        return "osx-arm64" if machine in ("arm64", "aarch64") else "osx-64"
    if sys.platform.startswith("win"):
        return "win-64"
    if machine in ("aarch64", "arm64"):
        return "linux-aarch64"
    return "linux-64"


def _micromamba_dir() -> str:
    return os.path.join(app_data_dir(), "micromamba")


def micromamba_path() -> Optional[str]:
    """Return an existing micromamba executable (managed copy or on PATH)."""
    exe = "micromamba.exe" if sys.platform.startswith("win") else "micromamba"
    managed = os.path.join(_micromamba_dir(), exe)
    if os.path.exists(managed):
        return managed
    found = shutil.which("micromamba")
    return found


def download_micromamba(progress: Optional[ProgressFn] = None) -> str:
    """Download the micromamba binary for this platform into the app-data dir.

    Uses the official ``micro.mamba.pm`` tarball endpoint (contains
    ``bin/micromamba`` on unix, ``Library/bin/micromamba.exe`` on Windows).
    Returns the path to the extracted executable.
    """
    def log(msg: str) -> None:
        if progress:
            progress(msg)

    existing = micromamba_path()
    if existing:
        log(f"Using micromamba at {existing}")
        return existing

    key = _platform_key()
    url = f"https://micro.mamba.pm/api/micromamba/{key}/latest"
    dest_dir = _micromamba_dir()
    os.makedirs(dest_dir, exist_ok=True)
    tar_path = os.path.join(dest_dir, "micromamba.tar.bz2")
    log(f"Downloading micromamba ({key})…")
    urllib.request.urlretrieve(url, tar_path)
    log("Extracting micromamba…")
    exe_out = os.path.join(dest_dir, "micromamba.exe" if sys.platform.startswith("win")
                           else "micromamba")
    with tarfile.open(tar_path, "r:bz2") as tf:
        member = None
        for m in tf.getmembers():
            if m.name.endswith("micromamba") or m.name.endswith("micromamba.exe"):
                member = m
                break
        if member is None:
            raise RuntimeError("micromamba binary not found in the downloaded archive.")
        with tf.extractfile(member) as src, open(exe_out, "wb") as out:
            shutil.copyfileobj(src, out)
    os.chmod(exe_out, os.stat(exe_out).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    try:
        os.remove(tar_path)
    except OSError:
        pass
    log(f"micromamba ready at {exe_out}")
    return exe_out


def install_command(mamba: str, prefix: str) -> List[str]:
    """Build the micromamba create argument list (no shell)."""
    cmd = [mamba, "create", "-y", "-p", prefix]
    for ch in CONDA_CHANNELS:
        cmd += ["-c", ch]
    cmd += R_CONDA_PACKAGES
    return cmd


def install_r_environment(progress: Optional[ProgressFn] = None,
                          timeout: int = 3600) -> Dict[str, object]:
    """Install the managed R + Bioconductor environment.

    Streams output lines to ``progress``. Returns a dict with ``ok``,
    ``rscript`` (path or None), ``prefix``, and ``log``. Requires network access
    the first time; uses prebuilt binaries (no compiler needed).
    """
    log_lines: List[str] = []

    def log(msg: str) -> None:
        log_lines.append(msg)
        if progress:
            progress(msg)

    try:
        mamba = download_micromamba(progress)
    except Exception as exc:
        log(f"ERROR: could not obtain micromamba: {exc}")
        return {"ok": False, "rscript": None, "prefix": r_env_prefix(),
                "log": "\n".join(log_lines), "error": str(exc)}

    prefix = r_env_prefix()
    os.makedirs(os.path.dirname(prefix), exist_ok=True)
    env = dict(os.environ)
    env["MAMBA_ROOT_PREFIX"] = os.path.join(app_data_dir(), "mamba_root")
    cmd = install_command(mamba, prefix)
    log("Installing R + edgeR/limma/DESeq2 (prebuilt binaries; this can take a few minutes)…")
    log("$ " + " ".join(cmd))
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, env=env)
        for line in iter(proc.stdout.readline, ""):
            if line:
                log(line.rstrip())
        proc.wait(timeout=timeout)
        rc = proc.returncode
    except Exception as exc:
        log(f"ERROR: install failed: {exc}")
        return {"ok": False, "rscript": None, "prefix": prefix,
                "log": "\n".join(log_lines), "error": str(exc)}

    rscript = managed_rscript_path()
    ok = rc == 0 and rscript is not None
    log("Done." if ok else f"Install finished with code {rc}; Rscript found: {rscript is not None}")
    return {"ok": ok, "rscript": rscript, "prefix": prefix, "log": "\n".join(log_lines),
            "returncode": rc}
