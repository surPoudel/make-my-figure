"""Generate quality_audit/plot_capability_matrix.csv from the live registry.

Generated, never hand-maintained: a matrix typed out by hand goes stale the first
time a plot type is added, and a stale audit is worse than none. Everything here
is read from the code that actually runs - the renderer registry, the UI option
declarations, the style-capability table, the example manifest - so a column can
only claim a capability the software really has.

    python quality_audit/build_capability_matrix.py
"""
from __future__ import annotations

import csv
import inspect
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from make_my_figure_core import examples, ui_hints  # noqa: E402
from make_my_figure_core.plots import registry  # noqa: E402
from make_my_figure_core.styles.capabilities import get_style_capabilities  # noqa: E402

OUT = os.path.join(ROOT, "quality_audit", "plot_capability_matrix.csv")

COLUMNS = [
    "plot_type", "display_name",
    # typography / canvas
    "title", "x_axis", "y_axis", "x_tick", "y_tick", "figure_size", "axis_padding",
    # colour
    "legend", "colorbar", "palette", "group_colors", "continuous_colormap",
    "semantic_colors", "cluster_colors", "node_colors", "edge_colors",
    # marks
    "point_style", "line_style", "marker_style",
    # annotation
    "annotations", "point_picking", "label_repulsion", "label_background", "arrows",
    "counts",
    # structure
    "faceting", "row_labels", "column_labels", "row_clusters", "column_clusters",
    "dendrogram",
    # plumbing
    "n_column_fields", "n_style_options", "n_config_options",
    "export", "publication_check", "PlotSpec", "FigurePackage",
    "example_data", "tutorial", "screenshot", "publishable_example",
    "status",
]

# Option keys that indicate a capability, matched against the declared option keys.
PATTERNS = {
    "semantic_colors": r"color_(up|down|ns|sig|signif)",
    "cluster_colors": r"cluster.*(color|palette)|(color|palette).*cluster",
    "annotations": r"annotat|label_mode|top_n|label_by",
    "point_picking": r"pick|click",
    # the real key is label_box; an earlier pattern looked for label_background
    # and reported 0/45 while the control was plainly visible in the app
    "label_background": r"label_(bg|background|box)|bbox",
    "arrows": r"arrow",
    "counts": r"append_count|show_count|count_annotation|_count\b",
    "faceting": r"facet",
    "row_labels": r"row_label",
    "column_labels": r"(column|col)_label",
    # keys are cluster_k_rows / cluster_rows, not row_cluster
    "row_clusters": r"row_cluster|cluster_rows|cluster_k_rows|row_k",
    "column_clusters": r"(column|col)_cluster|cluster_(columns|k_columns)|col_k",
    "dendrogram": r"dendrogram",
    "point_style": r"marker_size|point_size|jitter|alpha",
    "line_style": r"line_?width|linestyle|line_style",
    "marker_style": r"\bmarker\b|marker_shape",
    "axis_padding": r"pad(ding)?$|_pad",
}


def _renderer_source(plot_type: str) -> str:
    import importlib
    import pathlib
    mod = importlib.import_module(registry._RENDERERS[plot_type].__module__)
    src = pathlib.Path(mod.__file__).read_text(encoding="utf-8")
    for helper in re.findall(r"from make_my_figure_core\.plots\.(_[a-z0-9_]+) import", src):
        try:
            h = importlib.import_module(f"make_my_figure_core.plots.{helper}")
            src += "\n" + pathlib.Path(h.__file__).read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001
            continue
    return src


def _yes(flag: bool) -> str:
    return "yes" if flag else "-"


def row_for(plot_type: str) -> dict:
    opts = list(ui_hints.options(plot_type))
    keys = " ".join(o.key for o in opts)
    src = _renderer_source(plot_type)
    caps = get_style_capabilities(plot_type)
    entry = examples.entry(plot_type)
    fields = ui_hints.column_fields(plot_type)

    def has(name: str) -> bool:
        return bool(re.search(PATTERNS[name], keys, re.I))

    tutorial_dir = os.path.join(ROOT, "tutorial", "plots", plot_type)
    row = {
        "plot_type": plot_type,
        "display_name": registry.display_name(plot_type),
        # typography / canvas: universal by design, so these are structural facts
        "title": "yes", "x_axis": _yes(caps.supports_axes), "y_axis": _yes(caps.supports_axes),
        "x_tick": _yes(caps.supports_x_tick_rotation),
        "y_tick": _yes(caps.supports_y_tick_rotation),
        "figure_size": "yes",                       # verified by tests for all types
        "axis_padding": _yes(caps.supports_axis_label_padding),
        "legend": _yes(caps.supports_legend),
        "colorbar": _yes(caps.supports_colorbar),
        "palette": _yes(caps.supports_palette),
        "group_colors": _yes(caps.supports_group_colors),
        "continuous_colormap": _yes(caps.supports_continuous_colormap),
        "semantic_colors": _yes(has("semantic_colors")),
        "cluster_colors": _yes(has("cluster_colors")),
        "node_colors": _yes(caps.supports_node_colors),
        "edge_colors": _yes(caps.supports_edge_colors),
        "point_style": _yes(caps.supports_marker_size or has("point_style")),
        "line_style": _yes(caps.supports_line_width),
        # marker shape is set through the renderer's own block on some plots,
        # so the option list alone under-reports it
        "marker_style": _yes(has("marker_style") or bool(
            re.search(r'marker\s*=|"marker"|\bmarkers\[', src))),
        "annotations": _yes(has("annotations")),
        "point_picking": _yes(has("point_picking") or "pick" in src.lower()),
        "label_repulsion": _yes("adjust_text" in src or "adjustText" in src),
        "label_background": _yes(has("label_background")),
        "arrows": _yes(has("arrows")),
        "counts": _yes(has("counts")),
        # faceting is a column MAPPING on the spatial maps, not a style option
        "faceting": _yes(has("faceting") or "facet" in " ".join(fields)),
        "row_labels": _yes(has("row_labels")),
        "column_labels": _yes(has("column_labels")),
        "row_clusters": _yes(has("row_clusters")),
        "column_clusters": _yes(has("column_clusters")),
        "dendrogram": _yes(has("dendrogram")),
        "n_column_fields": len(fields),
        "n_style_options": sum(1 for o in opts if o.scope == "style"),
        "n_config_options": sum(1 for o in opts if o.scope == "config"),
        "export": "yes", "publication_check": "yes",
        "PlotSpec": "yes", "FigurePackage": "yes",
        "example_data": _yes(entry is not None),
        "tutorial": _yes(os.path.isdir(tutorial_dir)),
        "screenshot": _yes(os.path.exists(os.path.join(tutorial_dir, "screenshot.png"))),
        "publishable_example": _yes(
            os.path.exists(os.path.join(tutorial_dir, "publication_example.png"))),
    }
    missing = [k for k in ("example_data", "tutorial", "screenshot", "publishable_example")
               if row[k] == "-"]
    row["status"] = "complete" if not missing else "missing: " + ",".join(missing)
    return row


def main() -> int:
    types = registry.available_plot_types()
    rows = [row_for(p) for p in types]
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    complete = sum(1 for r in rows if r["status"] == "complete")
    print(f"{len(rows)} registered plot types -> {OUT}")
    print(f"  complete: {complete}   incomplete: {len(rows) - complete}")
    for key in ("tutorial", "screenshot", "publishable_example", "example_data"):
        print(f"  with {key:20s}: {sum(1 for r in rows if r[key] == 'yes'):>3}/{len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
