"""Resource-path resolution that works both in development and when frozen.

In a normal checkout, bundled resources (``schemas/``, ``style_profiles/``,
``mock_data/``) live at the project root, one level above this package. When the
app is packaged with PyInstaller, those folders are added to the bundle and
extracted under ``sys._MEIPASS``. ``resource_path`` resolves either case so the
core never hard-codes a development-only path.
"""

from __future__ import annotations

import os
import sys

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
_DEV_BASE = os.path.abspath(os.path.join(_PKG_DIR, ".."))


def project_base() -> str:
    """Return the base directory that contains bundled resource folders."""
    # PyInstaller sets sys.frozen and sys._MEIPASS.
    meipass = getattr(sys, "_MEIPASS", None)
    if getattr(sys, "frozen", False) and meipass:
        return meipass
    # Allow an explicit override (useful for tests / alternative layouts).
    override = os.environ.get("MAKE_MY_FIGURE_RESOURCES")
    if override and os.path.isdir(override):
        return override
    return _DEV_BASE


def resource_path(*parts: str) -> str:
    """Join ``parts`` onto the resolved resource base directory."""
    return os.path.join(project_base(), *parts)
