"""Shared helpers for the MakeMyFigure Developer scripts.

Portable: standard library plus the project's own dependencies. Works from any current
directory (the repository root is found by walking up to ``pyproject.toml``), on Windows,
macOS and Linux, headless (matplotlib Agg), and without network access.

Every script feature-detects optional components (Figure Package, experimental presets,
publication scoring...) instead of assuming a branch or a version.
"""
from __future__ import annotations

import importlib
import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, Iterable, List, Optional

os.environ.setdefault("MPLBACKEND", "Agg")


def repo_root(start: Optional[str] = None) -> str:
    """Walk up from ``start`` (default: this file) until a directory holding pyproject.toml
    and make_my_figure_core/ is found."""
    here = os.path.abspath(start or os.path.dirname(__file__))
    while True:
        if os.path.exists(os.path.join(here, "pyproject.toml")) and \
                os.path.isdir(os.path.join(here, "make_my_figure_core")):
            return here
        parent = os.path.dirname(here)
        if parent == here:
            raise SystemExit("repository root not found (no pyproject.toml + make_my_figure_core/ above "
                             f"{start or __file__})")
        here = parent


ROOT = repo_root()
AGENT_DIR = os.path.join(ROOT, ".agents", "makemyfigure-developer")
for _p in (ROOT, os.path.join(ROOT, "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _purge_editable_finders() -> None:
    """An editable ``pip install -e`` of make_my_figure_core from ANOTHER checkout installs a
    meta-path finder that can serve submodules missing from this checkout (a mixed import of two
    branches). Remove such finders so THIS checkout is the only source of the core package."""
    keep = []
    for f in sys.meta_path:
        name = (type(f).__name__ + " " + repr(f) + " " + getattr(f, "__module__", "")).lower()
        if "editable" in name and "make_my_figure_core" in name.replace("-", "_"):
            continue
        if "__editable___make_my_figure_core" in getattr(f, "__module__", "") .lower():
            continue
        keep.append(f)
    sys.meta_path[:] = keep
    for mod in [m for m in list(sys.modules) if m == "make_my_figure_core" or m.startswith("make_my_figure_core.")]:
        f = getattr(sys.modules[mod], "__file__", "") or ""
        if not os.path.abspath(f).startswith(ROOT):
            del sys.modules[mod]


_purge_editable_finders()


def assert_core_from_root(module) -> None:
    f = os.path.abspath(getattr(module, "__file__", "") or "")
    if not f.startswith(ROOT):
        raise SystemExit(f"{module.__name__} was imported from {f}, not from this checkout ({ROOT}). "
                         "Another checkout is installed editable; run with this checkout first on sys.path "
                         "or `pip uninstall make_my_figure_core`.")


def optional_import(name: str):
    """Import a module or return None (feature detection, never raises). A project module that
    resolves outside this checkout (another branch installed editable) counts as ABSENT."""
    try:
        mod = importlib.import_module(name)
    except Exception:  # noqa: BLE001 - absence of a feature is information, not an error
        return None
    if name.startswith("make_my_figure_core"):
        f = os.path.abspath(getattr(mod, "__file__", "") or "")
        if not f.startswith(ROOT):
            return None
    return mod


def features() -> Dict[str, bool]:
    """Which optional components exist in THIS checkout. Scripts branch on these flags."""
    return {
        "figure_package": optional_import("make_my_figure_core.package.writer") is not None,
        "experimental_presets": optional_import("make_my_figure_core.experimental_presets") is not None,
        "preset_preview": optional_import("make_my_figure_core.preset_preview") is not None,
        "publication_score": optional_import("make_my_figure_core.qc.publication_score") is not None,
        "text_layout_qc": optional_import("make_my_figure_core.qc.text_layout_qc") is not None,
        "recommendations": optional_import("make_my_figure_core.recommendations.recommendation_runner") is not None,
        "panels": optional_import("make_my_figure_core.panels.builder") is not None,
        "presets": optional_import("make_my_figure_core.presets") is not None,
        "ui_hints": optional_import("make_my_figure_core.ui_hints") is not None,
        "style_capabilities": optional_import("make_my_figure_core.styles.capabilities") is not None,
        "pyside6": optional_import("PySide6.QtWidgets") is not None,
        "pyinstaller": optional_import("PyInstaller") is not None,
        "streamlit": optional_import("streamlit") is not None,
    }


def registry():
    reg = importlib.import_module("make_my_figure_core.plots.registry")
    assert_core_from_root(reg)
    return reg


def plot_types() -> List[str]:
    return list(registry().available_plot_types())


def version() -> str:
    return importlib.import_module("make_my_figure_core.version").__version__


def git(*args: str, cwd: Optional[str] = None, check: bool = False) -> str:
    out = subprocess.run(["git", *args], cwd=cwd or ROOT, capture_output=True, text=True)
    if check and out.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {out.stderr.strip()}")
    return out.stdout.strip()


def grep_files(pattern: str, paths: Iterable[str], *, exts: Iterable[str] = (".py", ".md", ".json", ".txt")) -> List[str]:
    """Files under ``paths`` (relative to ROOT) containing ``pattern`` (literal). Pure Python, portable."""
    rx = re.compile(re.escape(pattern))
    hits: List[str] = []
    for base in paths:
        absbase = os.path.join(ROOT, base)
        if os.path.isfile(absbase):
            candidates = [absbase]
        else:
            candidates = []
            for dp, dn, fn in os.walk(absbase):
                dn[:] = [d for d in dn if d not in ("__pycache__", ".git", "node_modules")]
                candidates += [os.path.join(dp, f) for f in fn if f.endswith(tuple(exts))]
        for f in candidates:
            try:
                with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                    if rx.search(fh.read()):
                        hits.append(os.path.relpath(f, ROOT).replace(os.sep, "/"))
            except OSError:
                continue
    return sorted(hits)


def renderer_module_for(plot_type: str) -> Optional[str]:
    """Module name of the renderer registered for ``plot_type`` (from the registry's function)."""
    reg = registry()
    fn = getattr(reg, "_RENDERERS", {}).get(plot_type)
    return getattr(fn, "__module__", None) if fn else None


def renderer_path_for(plot_type: str) -> Optional[str]:
    mod = renderer_module_for(plot_type)
    if not mod:
        return None
    m = importlib.import_module(mod)
    return os.path.relpath(m.__file__, ROOT).replace(os.sep, "/")


def dump_json(obj: Any, path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, default=str, sort_keys=False)
    return path


def table(rows: List[Dict[str, Any]], columns: List[str]) -> str:
    """Small markdown table for console/report output."""
    out = ["| " + " | ".join(columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(r.get(c, "")) for c in columns) + " |")
    return "\n".join(out)


def headless_pytest_args() -> List[str]:
    """pytest flags that make the suite run without a display / Qt."""
    args = ["-p", "no:cacheprovider"]
    if optional_import("PySide6.QtWidgets") is None:     # top-level PySide6 imports even when Qt libs are missing
        args += ["-p", "no:pytest-qt"]                    # GUI test modules skip themselves at module level
        if os.path.exists(os.path.join(ROOT, "tests", "test_qt_gui.py")):
            args.append("--ignore=tests/test_qt_gui.py")
    return args
