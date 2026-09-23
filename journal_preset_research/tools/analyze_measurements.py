"""Aggregate the corpus measurements into evidence tables (research tool).

Usage: python analyze_measurements.py AUTO.csv VISUAL_GLOB OUT_DIR

Inputs
* AUTO.csv - figure-level automated measurements (run_auto_measurements.py).
* VISUAL_GLOB - panel-level visual review CSVs (visual_review_*.csv).

Outputs (OUT_DIR)
* style_measurements.csv - the merged panel-level table (visual rows joined to the figure-level
  automated numbers of the same paper/figure), with evidence classes.
* style_summary_by_family.csv - per journal family (and per family x plot group) medians, IQR and
  n for numeric fields; modal value and share for categorical fields.
* family_differences.md - which fields differ between families (Kruskal-Wallis for numeric,
  chi-square for categorical, with effect sizes), and which do not.
* outliers.md - panels outside 1.5 x IQR of their family group for numeric fields.

Only aggregate numbers appear in the outputs; no image content is copied.
"""

from __future__ import annotations

import argparse
import collections
import csv
import glob
import json
import math
import os
from typing import Any, Dict, List

import numpy as np

NUMERIC_AUTO = ["typeset_width_mm", "smallest_cluster_pt", "dominant_cluster_pt", "largest_cluster_pt",
                "stroke_pt_inferred", "coloured_fraction", "n_hue_clusters", "mean_saturation",
                "figure_aspect", "n_panels_detected"]
CATEGORICAL_VISUAL = ["spines", "tick_direction", "grid", "background", "error_bar_style",
                      "points_overlaid", "marker_fill", "marker_size_class", "line_weight_class",
                      "axis_line_weight_class", "legend_position", "legend_frame", "palette_class",
                      "sequential_cmap_class", "colourbar_position", "panel_label_case",
                      "panel_label_weight", "panel_label_size_class", "font_class",
                      "axis_label_weight", "title_present", "significance_style", "brackets",
                      "n_stated_in_panel", "tick_label_density", "x_tick_rotation",
                      "panel_aspect_class"]
NUMERIC_VISUAL = ["legend_entries", "n_categorical_colours"]

PLOT_GROUPS = {
    "bar": "bars", "grouped_bar": "bars", "stacked_bar": "bars",
    "box": "distributions", "violin": "distributions", "dot_strip": "distributions",
    "histogram_density": "distributions",
    "scatter": "scatter", "scatter_regression": "scatter", "pca_umap": "scatter", "volcano": "scatter",
    "ma": "scatter", "dot_bubble": "scatter",
    "line": "lines", "line_band": "lines", "survival": "lines", "roc_pr": "lines",
    "heatmap": "heatmaps", "heatmap_clustered": "heatmaps", "oncoprint": "heatmaps",
    "forest": "other", "network": "other", "sankey": "other", "pie_donut": "other", "other_quant": "other",
}


def norm_family(name: str) -> str:
    n = (name or "").strip().lower()
    if n.startswith("nature"):
        return "Nature"
    if n.startswith("science"):
        return "Science"
    if n.startswith("cell"):
        return "Cell"
    return name or "unknown"


# Absolute typography/stroke sizes are trusted only from the typeset-PDF route (observed scale).
# Web-JPEG estimates (~700 px images, assumed width) are kept in the merged table but excluded
# from central estimates and difference tests.
TYPESET_ONLY_FIELDS = {"smallest_cluster_pt", "dominant_cluster_pt", "largest_cluster_pt",
                       "stroke_pt_inferred", "typeset_width_mm"}


def _f(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _kruskal(groups: List[List[float]]):
    try:
        from scipy.stats import kruskal
        groups = [g for g in groups if len(g) >= 5]
        if len(groups) < 2:
            return None, None
        h, p = kruskal(*groups)
        n = sum(len(g) for g in groups)
        eps2 = (h - len(groups) + 1) / (n - len(groups)) if n > len(groups) else None   # epsilon-squared
        return float(p), (float(eps2) if eps2 is not None else None)
    except Exception:  # noqa: BLE001
        return None, None


def _chi2(table: Dict[str, Dict[str, int]]):
    try:
        from scipy.stats import chi2_contingency
        fams = sorted(table)
        cats = sorted({c for f in fams for c in table[f]})
        m = np.array([[table[f].get(c, 0) for c in cats] for f in fams], dtype=float)
        m = m[:, m.sum(axis=0) > 0]
        if m.shape[0] < 2 or m.shape[1] < 2 or m.sum() < 20:
            return None, None
        chi2, p, dof, _ = chi2_contingency(m)
        n = m.sum()
        k = min(m.shape) - 1
        v = math.sqrt(chi2 / (n * k)) if k > 0 else None   # Cramer's V
        return float(p), (float(v) if v is not None else None)
    except Exception:  # noqa: BLE001
        return None, None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("auto_csv")
    ap.add_argument("visual_glob")
    ap.add_argument("out_dir")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)

    auto = {}
    for r in csv.DictReader(open(a.auto_csv, encoding="utf-8")):
        auto[(r["paper_id"], str(r["figure_number"]))] = r
    visual: List[Dict[str, Any]] = []
    for path in sorted(glob.glob(a.visual_glob)):
        for r in csv.DictReader(open(path, encoding="utf-8")):
            visual.append(r)

    merged: List[Dict[str, Any]] = []
    for v in visual:
        key = (v["paper_id"], str(v["figure_number"]))
        au = auto.get(key, {})
        row = dict(v)
        row["journal_family"] = norm_family(v.get("journal_family", ""))
        for c in NUMERIC_AUTO + ["route", "width_evidence", "width_assumption", "text_evidence",
                                 "line_widths_pt_observed", "text_size_clusters_pt"]:
            row[f"fig_{c}"] = au.get(c, "")
        row["plot_group"] = PLOT_GROUPS.get(v.get("plot_family", ""), "non-quantitative"
                                            if v.get("plot_family") == "non-quantitative" else "other")
        merged.append(row)
    if merged:
        cols = list(merged[0].keys())
        with open(os.path.join(a.out_dir, "style_measurements.csv"), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(merged)

    quant = [m for m in merged if m["plot_group"] != "non-quantitative"]
    fams = sorted({m["journal_family"] for m in quant})

    # --- summaries -------------------------------------------------------------------------
    summary_rows = []
    diffs = []

    def summarise(subset, label):
        for field in NUMERIC_AUTO + NUMERIC_VISUAL:
            src = (lambda m: m.get(f"fig_{field}")) if field in NUMERIC_AUTO else (lambda m: m.get(field))
            keep = (lambda m: m.get("fig_route") == "typeset_pdf") if field in TYPESET_ONLY_FIELDS else (lambda m: True)
            per_fam = {f: [x for x in (_f(src(m)) for m in subset if m["journal_family"] == f and keep(m)) if x is not None]
                       for f in fams}
            for f, vals in per_fam.items():
                if vals:
                    summary_rows.append({"group": label, "journal_family": f, "field": field, "kind": "numeric",
                                         "n": len(vals), "median": round(float(np.median(vals)), 3),
                                         "q1": round(float(np.percentile(vals, 25)), 3),
                                         "q3": round(float(np.percentile(vals, 75)), 3),
                                         "mode_or_min": round(float(np.min(vals)), 3),
                                         "share_or_max": round(float(np.max(vals)), 3)})
            p, eff = _kruskal(list(per_fam.values()))
            diffs.append({"group": label, "field": field, "kind": "numeric", "p": p, "effect": eff,
                          "n": sum(len(v) for v in per_fam.values()),
                          "medians": {f: (round(float(np.median(v)), 2) if v else None) for f, v in per_fam.items()}})
        for field in CATEGORICAL_VISUAL:
            table = {f: collections.Counter(m.get(field, "") for m in subset
                                            if m["journal_family"] == f and m.get(field) not in ("", "UNKNOWN", "na"))
                     for f in fams}
            for f, cnt in table.items():
                n = sum(cnt.values())
                if n:
                    mode, k = cnt.most_common(1)[0]
                    summary_rows.append({"group": label, "journal_family": f, "field": field, "kind": "categorical",
                                         "n": n, "median": "", "q1": "", "q3": "", "mode_or_min": mode,
                                         "share_or_max": round(k / n, 3)})
            p, eff = _chi2(table)
            diffs.append({"group": label, "field": field, "kind": "categorical", "p": p, "effect": eff,
                          "n": sum(sum(c.values()) for c in table.values()),
                          "medians": {f: (c.most_common(1)[0][0] if c else None) for f, c in table.items()}})

    summarise(quant, "all_quantitative")
    for grp in sorted({m["plot_group"] for m in quant}):
        summarise([m for m in quant if m["plot_group"] == grp], grp)

    with open(os.path.join(a.out_dir, "style_summary_by_family.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["group", "journal_family", "field", "kind", "n", "median", "q1", "q3",
                                           "mode_or_min", "share_or_max"])
        w.writeheader()
        w.writerows(summary_rows)

    # --- differences report ----------------------------------------------------------------
    lines = ["# Journal-family differences in measured style", "",
             "Numeric fields: Kruskal-Wallis across families, effect = epsilon-squared (0.01 small, 0.06 medium, 0.14 large). ",
             "Categorical fields: chi-square, effect = Cramer's V (0.1 small, 0.3 medium, 0.5 large). ",
             "Absolute text and stroke sizes use only figures measured from typeset PDFs (observed scale); web-JPEG estimates are excluded. ",
             "A field counts as *meaningfully different* only when p < 0.01 AND the effect is at least medium; ",
             "everything else is treated as shared practice and the presets must NOT manufacture a difference there.", ""]
    for label in ["all_quantitative"] + sorted({d["group"] for d in diffs} - {"all_quantitative"}):
        lines.append(f"## {label}")
        lines.append("")
        lines.append("| field | kind | n | p | effect | meaningful | per-family value |")
        lines.append("|---|---|---|---|---|---|---|")
        for d in [d for d in diffs if d["group"] == label]:
            p, e = d["p"], d["effect"]
            meaningful = (p is not None and e is not None and p < 0.01 and
                          e >= (0.06 if d["kind"] == "numeric" else 0.3))
            lines.append(f"| {d['field']} | {d['kind']} | {d['n']} | "
                         f"{'' if p is None else f'{p:.3g}'} | {'' if e is None else f'{e:.2f}'} | "
                         f"{'YES' if meaningful else 'no'} | {json.dumps(d['medians'])} |")
        lines.append("")
    with open(os.path.join(a.out_dir, "family_differences.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    # --- outliers --------------------------------------------------------------------------
    out = ["# Outlier panels (outside 1.5 x IQR of their journal-family group)", ""]
    for field in ["fig_smallest_cluster_pt", "fig_dominant_cluster_pt", "fig_stroke_pt_inferred", "n_categorical_colours", "legend_entries"]:
        for f in fams:
            vals = [(m, _f(m.get(field))) for m in quant if m["journal_family"] == f
                    and (m.get("fig_route") == "typeset_pdf" or field[4:] not in TYPESET_ONLY_FIELDS)]
            xs = [v for _, v in vals if v is not None]
            if len(xs) < 8:
                continue
            q1, q3 = np.percentile(xs, 25), np.percentile(xs, 75)
            lo, hi = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
            for m, v in vals:
                if v is not None and (v < lo or v > hi):
                    out.append(f"- {field} = {v} ({f}, {m['paper_id']} Fig {m['figure_number']}{m.get('panel', '')}, "
                               f"{m.get('plot_family', '')}); group IQR {q1:.2f}-{q3:.2f}; excluded from central estimates; "
                               f"reason to check: {m.get('notes', '')[:80]}")
    with open(os.path.join(a.out_dir, "outliers.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print(f"{len(merged)} merged rows ({len(quant)} quantitative); {len(summary_rows)} summary rows; "
          f"{len(diffs)} difference tests; {len(out) - 2} outlier lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
