"""Loader for the per-plot example/template datasets under ``examples/``.

Reads ``examples/example_data_manifest.json`` (produced by
``scripts/generate_example_data.py``) and exposes the example table, any
auxiliary table (PCA metadata), and the bundled PlotSpec for each plot type.
Resource paths resolve via :mod:`make_my_figure_core.resources` so this works
in a dev checkout and inside a packaged app.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from make_my_figure_core.io.loaders import TableInfo, load_table
from make_my_figure_core.resources import project_base, resource_path

MANIFEST_REL = os.path.join("examples", "example_data_manifest.json")


def manifest_path() -> str:
    return resource_path("examples", "example_data_manifest.json")


def has_manifest() -> bool:
    return os.path.exists(manifest_path())


@lru_cache(maxsize=1)
def load_manifest() -> Dict[str, Any]:
    with open(manifest_path(), "r", encoding="utf-8") as fh:
        return json.load(fh)


def _entries() -> List[Dict[str, Any]]:
    return load_manifest().get("plot_types", [])


def entry(plot_type: str) -> Optional[Dict[str, Any]]:
    for e in _entries():
        if e["plot_type"] == plot_type:
            return e
    return None


def plot_types_with_examples() -> List[str]:
    return [e["plot_type"] for e in _entries()]


def has_example(plot_type: str) -> bool:
    return entry(plot_type) is not None


def _abs(rel_path: str) -> str:
    """Resolve a manifest (repo-relative) path against the resource base."""
    return os.path.join(project_base(), rel_path)


def template_path(plot_type: str, ext: str = "csv") -> Optional[str]:
    e = entry(plot_type)
    if not e:
        return None
    rel = e["files"].get(ext)
    return _abs(rel) if rel else None


def example_readme(plot_type: str) -> Optional[str]:
    return template_path(plot_type, "readme")


def load_example(plot_type: str) -> Tuple[TableInfo, Dict[str, TableInfo], Dict[str, Any]]:
    """Return ``(table_info, aux, plotspec)`` for ``plot_type``'s example.

    ``aux`` maps auxiliary-table names (e.g. ``"metadata"``) to loaded tables.
    Raises ``KeyError`` if there is no example for the plot type.
    """
    e = entry(plot_type)
    if not e:
        raise KeyError(f"No example dataset for plot type '{plot_type}'.")
    info = load_table(_abs(e["files"]["csv"]))
    aux: Dict[str, TableInfo] = {}
    for name, rel in (e.get("aux_tables") or {}).items():
        aux[name] = load_table(_abs(rel))
    plotspec: Dict[str, Any] = {}
    spec_rel = e["files"].get("plotspec")
    if spec_rel and os.path.exists(_abs(spec_rel)):
        with open(_abs(spec_rel), "r", encoding="utf-8") as fh:
            plotspec = json.load(fh)
    return info, aux, plotspec
