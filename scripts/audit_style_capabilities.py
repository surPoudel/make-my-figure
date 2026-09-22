"""Audit which style controls each renderer actually honours, and keep capabilities.py truthful.

A palette widget that changes nothing is a bug: the user moves a control, the figure does not
move, and the only honest thing the app can do is say so. ``styles/capabilities.py`` is where
that honesty lives - it declares, per plot type, which Publication controls apply - but a
declaration drifts from the code unless something checks it. This script is that check.

It reads every registered renderer's source and records what it consumes:

* ``style.color_for(...)`` or ``style.palette``      -> the categorical palette applies
* ``style.sequential_cmap`` / ``style.diverging_cmap`` -> a continuous colormap applies (the
  palette control also switches these, so the palette applies to colormap-driven plots too)
* ``.colorbar(``                                       -> a colorbar is drawn
* ``style.marker_size``                                -> the marker-size control applies
* ``style.line_width_pt`` / ``regression_line_width``  -> the line-width control applies
* ``legend(`` / ``place_legend(``                      -> a legend can be placed
* ``get_mapping(spec, "<...color|cmap...>")``         -> plot-specific colour options
* literal colour strings                               -> colours the user cannot change (listed
                                                          so each one is a known decision)

Usage::

    python scripts/audit_style_capabilities.py            # write the audit CSV, report drift
    python scripts/audit_style_capabilities.py --write    # also regenerate _CAPS in capabilities.py

The generated ``_CAPS`` keeps the hand-written reasons and axis flags (those cannot be inferred
from source) and replaces only the flags the scan can prove.
"""

from __future__ import annotations

import argparse
import csv
import importlib
import os
import pathlib
import re
import sys
from typing import Dict, List

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from make_my_figure_core.plots import registry as R  # noqa: E402
from make_my_figure_core.styles import capabilities as C  # noqa: E402
from make_my_figure_core import ui_hints  # noqa: E402

OUT_DIR = ROOT / "reports" / "figure_preset_qc"
CSV_PATH = OUT_DIR / "color_controls_audit.csv"

_HEX = re.compile(r'"(#[0-9A-Fa-f]{6})"')
_NAMED = re.compile(r'\b(?:color|c|edgecolor|facecolor)=\s*"(black|white|red|blue|grey|gray|'
                    r'crimson|firebrick|steelblue|darkgrey|lightgrey|0\.\d+)"')


def scan_renderer(plot_type: str) -> Dict[str, object]:
    fn = R._RENDERERS[plot_type]
    src = pathlib.Path(importlib.import_module(fn.__module__).__file__).read_text(encoding="utf-8")
    tokens = set(re.findall(r"\bstyle\.([a-z_]+)\b", src))
    mapping_colors = sorted(set(re.findall(
        r'get_mapping\(spec,\s*"([a-z_]*(?:color|cmap|colormap|palette)[a-z_]*)"', src)))
    # colour option keys the registry exposes for this plot (the user-facing colour controls)
    option_colors = sorted(o.key for o in ui_hints.options(plot_type)
                           if re.search(r"color|cmap|colormap|palette", o.key))
    literal = sorted(set(_HEX.findall(src)) | set(_NAMED.findall(src)))
    uses_palette = ("color_for(" in src) or ("palette" in tokens)
    uses_cmap = bool({"sequential_cmap", "diverging_cmap"} & tokens)
    return {
        "plot_type": plot_type,
        "categorical_palette": uses_palette,
        "continuous_colormap": uses_cmap,
        # the palette control switches the colormaps too, so it has an effect on cmap plots
        "palette_control_has_effect": uses_palette or uses_cmap,
        "colorbar": ".colorbar(" in src,
        "legend": ("legend(" in src) or ("place_legend(" in src),
        "marker_size": "marker_size" in tokens,
        "line_width": bool({"line_width_pt", "regression_line_width"} & tokens),
        "mapping_color_keys": ";".join(mapping_colors),
        "color_options_exposed": ";".join(option_colors),
        "literal_colors": ";".join(literal),
        "style_tokens_read": ";".join(sorted(tokens - {"apply", "with_overrides",
                                                        "figure_size_inches", "color_for",
                                                        "rc_params"})),
    }


def color_model(row: Dict[str, object]) -> str:
    """Which colour model a renderer needs - the question the spec asks per plot."""
    parts = []
    if row["categorical_palette"]:
        parts.append("categorical palette")
    if row["continuous_colormap"]:
        parts.append("continuous colormap")
    keys = str(row["mapping_color_keys"])
    if "node_color" in keys or "edge_color" in keys:
        parts.append("node/edge mapping")
    if "color_up" in keys or "color_down" in keys or "color_ns" in keys:
        parts.append("significance classes")
    if "cutoff_line_color" in keys:
        parts.append("threshold-line colour")
    if "label_color" in keys:
        parts.append("annotation colour")
    if not parts:
        parts.append("fixed colours only")
    return " + ".join(parts)


def declared(plot_type: str) -> Dict[str, bool]:
    caps = C.get_style_capabilities(plot_type)
    return {
        "palette_control_has_effect": caps.supports_palette,
        "continuous_colormap": caps.supports_continuous_colormap,
        "colorbar": caps.supports_colorbar,
        "legend": caps.supports_legend,
        "marker_size": caps.supports_marker_size,
        "line_width": caps.supports_line_width,
    }


def drift(rows: List[Dict[str, object]]) -> List[str]:
    out = []
    for row in rows:
        dec = declared(str(row["plot_type"]))
        for key, val in dec.items():
            if bool(row[key]) != bool(val):
                out.append(f"{row['plot_type']}: {key} is declared {val} but the renderer "
                           f"{'does' if row[key] else 'does not'} use it")
    return out


# Reasons that cannot be inferred from source - kept when regenerating.
_REASONS = {
    "network_graph": "does not apply to network plots (they have no axes; use node/edge colors, "
                     "node size and edge width instead)",
    "heatmap_clustered_matrix": "heatmaps use a continuous colormap, not per-point markers",
    "oncoprint_mutation_heatmap": "oncoprints use categorical mutation colors, not markers",
    "volcano_plot": "a volcano colours points by significance class (up / down / not significant) "
                    "- set those three colours in the plot options; the palette does not apply",
    "barplot_with_error_bar": "bars have no markers or data lines; error-bar and edge widths come "
                              "from the profile",
    "grouped_barplot_with_error_bar": "bars have no markers or data lines; error-bar and edge "
                                      "widths come from the profile",
    "stacked_bar_composition": "stacked bars have no markers or data lines",
    "sankey_plot": "flows have no axes, markers or lines in the plot sense",
    "hierarchical_dendrogram": "a dendrogram has no markers; branch width follows the profile",
}
_NO_AXES = {"network_graph", "sankey_plot", "chord_diagram"}


def render_caps_block(rows: List[Dict[str, object]]) -> str:
    """Python source for ``_CAPS`` - only plots that differ from the axes-based default."""
    default = C.PlotStyleCapabilities(plot_type="_default")
    lines = ["_CAPS: Dict[str, PlotStyleCapabilities] = {"]
    for row in rows:
        pt = str(row["plot_type"])
        flags = {
            "supports_palette": bool(row["palette_control_has_effect"]),
            "supports_group_colors": bool(row["categorical_palette"]),
            "supports_continuous_colormap": bool(row["continuous_colormap"]),
            "supports_colorbar": bool(row["colorbar"]),
            "supports_legend": bool(row["legend"]),
            "supports_marker_size": bool(row["marker_size"]),
            "supports_line_width": bool(row["line_width"]),
        }
        if pt in _NO_AXES:
            flags.update(supports_axes=False, supports_x_tick_rotation=False,
                         supports_y_tick_rotation=False, supports_axis_label_padding=False)
        if pt == "network_graph":
            flags.update(supports_node_colors=True, supports_edge_colors=True)
        diffs = {k: v for k, v in flags.items() if getattr(default, k) != v}
        if not diffs:
            continue
        reason = _REASONS.get(pt)
        parts = [f'plot_type="{pt}"'] + [f"{k}={v}" for k, v in diffs.items()]
        # wrap at ~92 columns, continuation lines indented under the first argument
        wrapped, cur = [], "        "
        for part in parts:
            piece = part + ", "
            if len(cur) + len(piece) > 92 and cur.strip():
                wrapped.append(cur.rstrip())
                cur = "        "
            cur += piece
        wrapped.append(cur.rstrip().rstrip(","))
        entry = f'    "{pt}": PlotStyleCapabilities(\n' + "\n".join(wrapped)
        if reason:
            import textwrap
            reason_lines = textwrap.wrap(reason, width=78)
            entry += ',\n        unsupported_controls_reason=(\n'
            entry += "\n".join(f'            "{ln}{" " if i < len(reason_lines) - 1 else ""}"'
                                for i, ln in enumerate(reason_lines))
            entry += ")"
        entry += "),"
        lines.append(entry)
    lines.append("}")
    return "\n".join(lines)


def write_caps(block: str) -> None:
    path = ROOT / "make_my_figure_core" / "styles" / "capabilities.py"
    src = path.read_text(encoding="utf-8")
    start = src.index("_CAPS: Dict[str, PlotStyleCapabilities] = {")
    end = src.index("\n}\n", start) + 2
    header = ("# Per-plot capabilities. GENERATED by scripts/audit_style_capabilities.py --write from\n"
              "# what each renderer's source actually reads; hand-written reasons are kept in that\n"
              "# script's _REASONS table. Do not edit the flags by hand - fix the renderer or the\n"
              "# script, then regenerate, so a control is never declared to work when it does not.\n")
    # drop an older generated header if present
    prev = src.rfind("\n\n", 0, start)
    lead = src[prev + 2:start]
    if lead.startswith("# Per-plot"):
        start = prev + 2
    path.write_text(src[:start] + header + block + src[end:], encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="regenerate _CAPS in capabilities.py")
    args = ap.parse_args()

    rows = [scan_renderer(pt) for pt in R.available_plot_types()]
    for row in rows:
        row["color_model"] = color_model(row)
        dec = declared(str(row["plot_type"]))
        row["declared_palette"] = dec["palette_control_has_effect"]
        row["declared_marker_size"] = dec["marker_size"]
        row["declared_line_width"] = dec["line_width"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fields = ["plot_type", "color_model", "categorical_palette", "continuous_colormap",
              "palette_control_has_effect", "declared_palette", "colorbar", "legend",
              "marker_size", "declared_marker_size", "line_width", "declared_line_width",
              "mapping_color_keys", "color_options_exposed", "literal_colors", "style_tokens_read"]
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})
    shown = os.path.relpath(CSV_PATH, ROOT) if str(CSV_PATH).startswith(str(ROOT)) else str(CSV_PATH)
    print(f"wrote {shown} ({len(rows)} renderers)")

    problems = drift(rows)
    if args.write:
        write_caps(render_caps_block(rows))
        importlib.reload(C)
        problems = drift(rows)
        print("regenerated _CAPS in styles/capabilities.py")
    if problems:
        print(f"\n{len(problems)} declaration(s) disagree with renderer source:")
        for p in problems:
            print("  -", p)
        return 1
    print("capabilities agree with renderer source for every plot type")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
