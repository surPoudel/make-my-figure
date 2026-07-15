"""Non-destructive PlotSpec auto-fixes for common publication-QC issues.

`suggest_fixes` maps a `PublicationScore`'s issues to available fix actions;
`apply_fixes` returns a NEW PlotSpec with the selected fixes applied. These are
pure dict transforms (no rendering) and never mutate the input spec.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List

from make_my_figure_core.qc.publication_score import PublicationScore

# fix_id -> (label, description). Also used to build the "Auto-fix" menu.
FIXES: Dict[str, Dict[str, str]] = {
    "enlarge_figure": {"label": "Enlarge figure",
                       "description": "Use double-column width for more room."},
    "legend_outside": {"label": "Move legend outside",
                       "description": "Place the legend outside the plotting area."},
    "hide_excess_labels": {"label": "Limit labels",
                           "description": "Show only the top labels to avoid overlap."},
    "increase_margins": {"label": "Increase margins",
                         "description": "Add padding so labels are not clipped."},
    "increase_font": {"label": "Increase font sizes",
                      "description": "Bump base and axis font sizes for legibility."},
    "increase_dpi": {"label": "Increase export DPI",
                     "description": "Raise export resolution to at least 300 DPI."},
}

# Which QC check ids each fix addresses.
_CHECK_TO_FIXES = {
    "export_dpi": ["increase_dpi"],
    "panel_resolution": ["increase_dpi"],
    "readability": ["increase_font", "enlarge_figure"],
    "missing_axis_labels": [],  # can't fabricate a label
    "legend_overlap": ["legend_outside"],
    "tick_density": ["hide_excess_labels", "enlarge_figure"],
    "heatmap_row_density": ["hide_excess_labels"],
    "label_crowding": ["hide_excess_labels"],
    "low_contrast": [],
    "missing_units": [],
    "missing_method_report": [],
}


def suggest_fixes(score: PublicationScore, spec: Dict[str, Any]) -> List[Dict[str, str]]:
    """Return the applicable fixes (deduped, in FIXES order) for a score."""
    wanted: List[str] = []
    for chk in score.issues():
        for fid in _CHECK_TO_FIXES.get(chk.id, []):
            if fid not in wanted:
                wanted.append(fid)
    return [{"id": fid, **FIXES[fid]} for fid in FIXES if fid in wanted]


def apply_fixes(spec: Dict[str, Any], fix_ids: List[str]) -> Dict[str, Any]:
    """Return a NEW spec with ``fix_ids`` applied. Never mutates ``spec``."""
    out = copy.deepcopy(spec) if spec else {}
    style = out.setdefault("style", {})
    layout = out.setdefault("layout", {})
    output = out.setdefault("output", {})
    mapping = out.setdefault("mapping", {})

    for fid in fix_ids:
        if fid == "enlarge_figure":
            layout["column_width"] = "double"
        elif fid == "legend_outside":
            style["legend_outside"] = True
        elif fid == "hide_excess_labels":
            # Generic knob renderers can honor; also cap common label options.
            mapping["max_labels"] = min(int(mapping.get("max_labels", 15) or 15), 15)
            if "top_n" in mapping:
                try:
                    mapping["top_n"] = min(int(mapping["top_n"]), 20)
                except (TypeError, ValueError):
                    mapping["top_n"] = 20
        elif fid == "increase_margins":
            layout["pad_inches"] = max(float(layout.get("pad_inches", 0.1) or 0.1), 0.25)
        elif fid == "increase_font":
            style["base_font_pt"] = max(float(style.get("base_font_pt", 11) or 11) + 1.0, 12.0)
            style["axis_font_pt"] = max(float(style.get("axis_font_pt", 12) or 12) + 1.0, 13.0)
            style["tick_label_pt"] = max(float(style.get("tick_label_pt", 10) or 10) + 1.0, 11.0)
        elif fid == "increase_dpi":
            try:
                current = int(output.get("dpi", 0) or 0)
            except (TypeError, ValueError):
                current = 0
            output["dpi"] = max(current, 300)

    # Drop empty containers we may have created but not used, to keep the spec tidy.
    for key in ("style", "layout", "output", "mapping"):
        if key in out and not out[key]:
            del out[key]
    return out
