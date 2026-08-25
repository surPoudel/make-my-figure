"""Resource-path resolution across a checkout, an installed wheel, and a frozen bundle.

Bundled resources (``schemas/``, ``style_profiles/``, ``mock_data/``, ``examples/``) are reached
only through :func:`resource_path`, so this module is the single place that has to know where they
live. That differs by how the code was obtained:

* **checkout** - at the project root, one level above this package;
* **installed wheel** - inside the package, under ``_bundled/``, put there at build time by
  ``setup.py`` (a wheel contains only the package directory, so root-level folders would be lost);
* **PyInstaller bundle** - extracted under ``sys._MEIPASS``.

The install case was previously unhandled: every published wheel shipped without these folders, so
``render()`` raised ``FileNotFoundError`` on the plot-spec schema before drawing anything. The
checkout path is tried after the package one, so an editable install keeps using the root copies and
a checkout never depends on a stale staged copy.
"""

from __future__ import annotations

import os
import sys

# Folders staged into the package by the build. Keep in step with setup.py::BUNDLED_DIRS.
BUNDLED_DIRS = ("schemas", "style_profiles", "mock_data", "examples")

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
_STAGED_BASE = os.path.join(_PKG_DIR, "_bundled")
_DEV_BASE = os.path.abspath(os.path.join(_PKG_DIR, ".."))


def project_base() -> str:
    """Return the base directory that contains the bundled resource folders."""
    # PyInstaller sets sys.frozen and sys._MEIPASS.
    meipass = getattr(sys, "_MEIPASS", None)
    if getattr(sys, "frozen", False) and meipass:
        return meipass
    # Allow an explicit override (useful for tests / alternative layouts).
    override = os.environ.get("MAKE_MY_FIGURE_RESOURCES")
    if override and os.path.isdir(override):
        return override
    # Installed wheel: the folders were staged inside the package at build time.
    if os.path.isdir(_STAGED_BASE):
        return _STAGED_BASE
    return _DEV_BASE


def resource_path(*parts: str) -> str:
    """Join ``parts`` onto the resolved resource base directory."""
    return os.path.join(project_base(), *parts)


def missing_bundled_dirs() -> list:
    """Bundled folders that are not present under the resolved base.

    Lets a caller give a useful message instead of a bare ``FileNotFoundError`` on a file deep
    inside a folder that was never shipped.
    """
    base = project_base()
    return [name for name in BUNDLED_DIRS if not os.path.isdir(os.path.join(base, name))]
