"""Help text for the desktop app.

Plot descriptions, required/optional columns and the example file are read from the
bundled ``examples/example_data_manifest.json`` (one entry per plot type, kept complete by
``tests/test_examples.py``), falling back to the older ``plot_schema_manifest.json`` for any
plot type without an example. Before v1.1.2 only the legacy manifest was consulted, so the
Help page showed no columns for the 21 plot types added after v0.3.
"""

from __future__ import annotations

from typing import Dict, List

from make_my_figure_core import data as mock_data
from make_my_figure_core import examples
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

ARTIFACTS = (
    "Three kinds of files, three purposes:\n"
    "• PlotSpec (name.plot_spec.json) — the recipe for ONE plot: plot type, column roles, "
    "options, style, statistics configuration. It does NOT contain the data; the source "
    "table is required to reopen it.\n"
    "• Figure preset (name.mmfpreset.json) — reusable appearance/configuration to apply to "
    "NEW data. Never contains data or table names.\n"
    "• Figure package (name.mmfpackage) — ONE portable file with the PlotSpec (or FigureSpec "
    "for a composite), a frozen copy of the exact tables used, the original source file when "
    "available, StatsSpec results, Matrix/SampleMetadata/Preprocessing records where they "
    "apply, imported images, preview PNG/SVG/PDF and a manifest with a SHA-256 for every "
    "file. Open it anywhere with 'Open Figure Package'; the application verifies every "
    "checksum first and refuses to open a package whose contents were changed.\n"
    "Because a package contains data, share it only with people who may see those data."
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
    """Return a help entry per supported plot type, from the examples manifest (legacy fallback)."""
    legacy = {d["plot_type"]: d for d in mock_data.load_manifest().get("datasets", [])}
    entries: List[Dict[str, object]] = []
    for pt in available_plot_types():
        ex = examples.entry(pt) or {} if examples.has_manifest() else {}
        m = legacy.get(pt, {})
        files = ex.get("files") or {}
        example_file = files.get("csv") or mock_data.sample_filename(pt)
        if isinstance(example_file, str) and example_file.startswith("examples/"):
            example_file = example_file[len("examples/"):]
        entries.append({
            "plot_type": pt,
            "title": display_name(pt),
            "description": ex.get("description") or m.get("description", ""),
            "required_columns": ex.get("required_columns") or m.get("required_columns", []),
            "optional_columns": ex.get("optional_columns") or m.get("optional_columns", []),
            "replacement_note": ex.get("user_replacement_note") or m.get("user_replacement_note", ""),
            "example_file": example_file,
        })
    return entries
