"""Help text for the desktop app.

Plot descriptions and required columns are read from the bundled
``plot_schema_manifest.json`` so they stay factual and in sync with the data.
"""

from __future__ import annotations

from typing import Dict, List

from make_my_figure_core import data as mock_data
from make_my_figure_core.plots.registry import available_plot_types, display_name

DISCLAIMER = (
    "Make My Figure uses a single Publication style designed for manuscript-ready "
    "scientific figures. It does not provide official journal templates or claim "
    "compliance with any journal's formatting requirements. Always check your target "
    "journal's official author guidelines."
)

PRIVACY = (
    "Make My Figure runs entirely on your computer. Your data files, figures, and "
    "settings stay local. The app has no telemetry, no analytics, and never uploads "
    "your data to any server or cloud service."
)

FORMATTING = (
    "How to format your data:\n"
    "• Use the first row for column names (headers).\n"
    "• Keep one observation per row (e.g. one replicate, one sample, one gene).\n"
    "• Use numeric columns for measurements; keep IDs/labels as text.\n"
    "• Supported files: .xlsx, .csv, .tsv. Column order does not matter — you map "
    "columns to roles in the app.\n"
    "• You can start from any example: open it, click “Save template”, then "
    "replace the rows with your own data while keeping the column names."
)


def plot_help() -> List[Dict[str, object]]:
    """Return a help entry per supported plot type, from the manifest."""
    manifest = {d["plot_type"]: d for d in mock_data.load_manifest().get("datasets", [])}
    entries: List[Dict[str, object]] = []
    for pt in available_plot_types():
        m = manifest.get(pt, {})
        entries.append({
            "plot_type": pt,
            "title": display_name(pt),
            "description": m.get("description", ""),
            "required_columns": m.get("required_columns", []),
            "optional_columns": m.get("optional_columns", []),
            "replacement_note": m.get("user_replacement_note", ""),
            "example_file": mock_data.sample_filename(pt),
        })
    return entries
