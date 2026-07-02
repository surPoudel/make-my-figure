"""Capture library versions for reproducibility metadata."""

from __future__ import annotations

from functools import lru_cache
from typing import Dict


@lru_cache(maxsize=1)
def software_versions() -> Dict[str, str]:
    """Return version strings for the libraries used by the statistics engine."""
    out: Dict[str, str] = {}
    try:
        import sys

        out["python"] = sys.version.split()[0]
    except Exception:
        pass
    for mod in ("numpy", "scipy", "pandas", "statsmodels"):
        try:
            m = __import__(mod)
            out[mod] = getattr(m, "__version__", "unknown")
        except Exception:
            out[mod] = "not installed"
    try:
        from make_my_figure_core.version import __version__

        out["make_my_figure_core"] = __version__
    except Exception:
        pass
    return dict(out)
