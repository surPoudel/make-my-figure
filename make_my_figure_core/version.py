"""Single source of truth for the application version.

`pyproject.toml` reads this via setuptools dynamic metadata, and the desktop
app's About dialog imports ``__version__`` from here, so the version is defined
in exactly one place.
"""

__version__ = "1.0.0rc1"


def build_info() -> dict:
    """Runtime build/environment info for the apps to display, so a user can confirm
    they are running the freshly-pulled code (not a stale installed package).

    Returns version, short git commit (or "unknown"), the module path actually
    imported, platform, and the active Matplotlib backend. Pure stdlib; never raises.
    """
    import os
    import platform as _plat

    info = {"version": __version__, "commit": "unknown",
            "module_path": os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "platform": "unknown", "python": _plat.python_version(), "backend": "unknown"}
    try:
        info["platform"] = _plat.platform()
    except Exception:  # noqa: BLE001
        pass
    try:
        import subprocess
        here = os.path.dirname(os.path.abspath(__file__))
        out = subprocess.run(["git", "-C", here, "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=5)
        if out.returncode == 0 and out.stdout.strip():
            info["commit"] = out.stdout.strip()
    except Exception:  # noqa: BLE001
        pass
    try:
        import matplotlib
        info["backend"] = matplotlib.get_backend()
    except Exception:  # noqa: BLE001
        pass
    return info


def build_banner() -> str:
    """One-line human banner, e.g. 'Make My Figure v0.6.1 · 4aaae44 · Linux · Agg'."""
    b = build_info()
    short_plat = str(b["platform"]).split("-")[0]
    return (f"Make My Figure v{b['version']} · {b['commit']} · {short_plat} · "
            f"{b['backend']}")
