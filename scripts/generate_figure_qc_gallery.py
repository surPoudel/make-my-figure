#!/usr/bin/env python
"""Figure QC gallery for the layout/annotation release-candidate pass.

Renders each affected plot type with a DEFAULT and an ADJUSTED layout (exercising
the new controls), exports PNG/PDF/SVG, writes qc_summary.csv + qc_report.md, and a
contact_sheet.png/pdf overview. Deterministic synthetic data; no private data.

    python scripts/generate_figure_qc_gallery.py --output reports/figure_qc_release_candidate
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from make_my_figure_core import examples as ex  # noqa: E402
from make_my_figure_core.plots.registry import export_figure, make_spec, render  # noqa: E402


def _rng(seed=0):
    return np.random.default_rng(seed)


def _cases():
    """Yield (name, plot_type, df, mapping, aux, layout_adjust)."""
    rng = _rng()
    # stacked composition
    sdf = pd.DataFrame({"sample": [f"Sample_{i:02d}" for i in range(8) for _ in range(3)],
                        "comp": ["A", "B", "C"] * 8,
                        "frac": rng.uniform(0.1, 1, 24)})
    yield ("stacked", "stacked_bar_composition", sdf,
           {"x": "sample", "stack": "comp", "y": "frac"},
           None, {"x_tick_rotation": 90, "legend_location": "outside right"})

    # PCA marker size
    pdf = pd.DataFrame({"gene": [f"g{i}" for i in range(60)]})
    for s in [f"S{i}" for i in range(10)]:
        pdf[s] = rng.normal(size=60)
    yield ("pca_small_markers", "pca_scatter_from_matrix", pdf,
           {"matrix_row_id": "gene", "value_columns": [f"S{i}" for i in range(10)]}, None, None)
    yield ("pca_large_markers", "pca_scatter_from_matrix", pdf,
           {"matrix_row_id": "gene", "value_columns": [f"S{i}" for i in range(10)],
            "marker_size": 160}, None, None)

    # manhattan with custom cutoff + rotation
    n = 600
    mdf = pd.DataFrame({"chrom": np.repeat([str(i) for i in range(1, 7)], n // 6),
                        "pos": np.tile(np.arange(n // 6), 6), "p": rng.uniform(1e-9, 1, n)})
    yield ("manhattan", "manhattan_plot", mdf, {"chrom": "chrom", "pos": "pos", "p": "p"},
           None, None)
    yield ("manhattan_custom", "manhattan_plot", mdf,
           {"chrom": "chrom", "pos": "pos", "p": "p", "genome_wide_threshold": 1e-6,
            "cutoff_line_color": "#1B7837", "cutoff_line_width": 2.5, "x_tick_rotation": 45,
            "show_suggestive_line": False}, None, None)

    # paired dot independent colors
    subs = [f"p{i}" for i in range(12)]
    pdf2 = pd.DataFrame({"subject": np.repeat(subs, 2), "cond": ["pre", "post"] * 12,
                         "value": rng.normal(5, 2, 24)})
    yield ("paired_independent_colors", "paired_slopegraph", pdf2,
           {"subject": "subject", "condition": "cond", "value": "value",
            "line_color": "#CCCCCC", "point_color": "#B2182B"}, None, None)

    # MA + volcano with labels
    de = pd.DataFrame({"feature_label": [f"G{i}" for i in range(120)],
                       "log2_fold_change": rng.normal(0, 2, 120),
                       "p_value": rng.uniform(0, 1, 120),
                       "adjusted_p_value": rng.uniform(0, 1, 120),
                       "AveExpr": rng.uniform(0, 12, 120)})
    yield ("ma_labeled", "ma_plot", de,
           {"x": "AveExpr", "y": "log2_fold_change", "p": "adjusted_p_value",
            "label": "feature_label", "selected_labels": ["G1", "G5", "G9"],
            "label_offsets": json.dumps({"G1": [30, 20]})}, None, None)
    yield ("volcano_labeled", "volcano_plot", de,
           {"x": "log2_fold_change", "p": "adjusted_p_value", "label": "feature_label",
            "annotate": True, "label_mode": "top_fdr", "top_n": 12}, None, None)

    # clustered heatmap + hierarchical clustering with long row names
    hrows = [f"LongGeneName_{i:03d}" for i in range(20)]
    hcols = [f"Sample_{c}" for c in range(9)]
    hdf = pd.DataFrame({"gene": hrows})
    for c in hcols:
        hdf[c] = rng.normal(size=20)
    yield ("clustered_heatmap", "heatmap_clustered_matrix", hdf,
           {"row_id": "gene", "value_columns": hcols, "scale": "row_zscore",
            "cluster_rows": True, "cluster_columns": True, "cluster_k_rows": 3,
            "show_row_labels": True}, None, None)
    yield ("hierarchical_clustering", "hierarchical_clustering", hdf,
           {"row_id": "gene", "value_columns": hcols, "cluster": "rows", "k": 3,
            "scale": "row_zscore", "y_label_pad": 14}, None, None)

    # lollipop with aligned labels
    ldf = pd.DataFrame({"pos": sorted(rng.integers(1, 500, 14)), "count": rng.integers(3, 10, 14),
                        "mut": [f"p.M{i}V" for i in range(14)],
                        "type": rng.choice(["missense", "nonsense"], 14)})
    yield ("lollipop", "lollipop_mutation_plot", ldf,
           {"x": "pos", "y": "count", "label": "mut", "color": "type", "label_top_n": 6},
           None, None)

    # bundled examples (upset, swimmer) — real fixtures
    for pt, name in (("upset_plot", "upset"), ("swimmer_plot", "swimmer")):
        try:
            info, aux, ps = ex.load_example(pt)
            auxd = {k: v.dataframe for k, v in (aux or {}).items()} or None
            yield (name, pt, info.dataframe, dict(ps.get("mapping") or {}), auxd, None)
        except Exception:  # noqa: BLE001
            pass


def run(output_dir: str) -> dict:
    os.makedirs(output_dir, exist_ok=True)
    rows, thumbs = [], []
    for name, pt, df, mapping, aux, layout_adj in _cases():
        row = {"name": name, "plot_type": pt, "status": "", "png": "", "pdf": "",
               "svg": "", "n_warnings": 0}
        try:
            spec = make_spec(pt, name, "publication", mapping=mapping)
            if layout_adj:
                spec["layout"] = {**spec.get("layout", {}), **layout_adj}
            result = render(spec, df, aux=aux)
            row["status"] = "ok"
            row["n_warnings"] = len(result.warnings or [])
            base = os.path.join(output_dir, name)
            export_figure(result.figure, base, ["png", "pdf", "svg"], dpi=300)
            for fmt in ("png", "pdf", "svg"):
                p = f"{base}.{fmt}"
                row[fmt] = "ok" if os.path.exists(p) and os.path.getsize(p) > 200 else "empty"
            thumbs.append((name, f"{base}.png"))
            with open(base + ".plot_spec.json", "w", encoding="utf-8") as fh:
                json.dump(spec, fh, indent=2, default=str)
            plt.close(result.figure)
        except Exception as exc:  # noqa: BLE001
            row["status"] = f"error: {exc}"
        rows.append(row)

    # contact sheet
    import matplotlib.image as mpimg
    ok = [(n, p) for n, p in thumbs if os.path.exists(p)]
    if ok:
        cols = 3
        rowsn = (len(ok) + cols - 1) // cols
        fig, axes = plt.subplots(rowsn, cols, figsize=(cols * 4.2, rowsn * 3.4),
                                 constrained_layout=True)
        axes = np.atleast_1d(axes).ravel()
        for ax in axes:
            ax.axis("off")
        for i, (n, p) in enumerate(ok):
            axes[i].imshow(mpimg.imread(p))
            axes[i].set_title(n, fontsize=10, fontweight="bold")
        fig.suptitle("Figure QC gallery (layout/annotation pass)", fontsize=14, fontweight="bold")
        fig.savefig(os.path.join(output_dir, "contact_sheet.png"), dpi=140)
        fig.savefig(os.path.join(output_dir, "contact_sheet.pdf"), dpi=200)
        plt.close(fig)

    fields = ["name", "plot_type", "status", "png", "pdf", "svg", "n_warnings"]
    with open(os.path.join(output_dir, "qc_summary.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    n_ok = sum(1 for r in rows if r["status"] == "ok")
    lines = ["# Figure QC gallery — layout/annotation pass", "",
             f"- Cases: {len(rows)} · rendered OK: {n_ok} · errors: {len(rows) - n_ok}", "",
             "| case | plot_type | status | png | pdf | svg | warns |",
             "|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['name']} | {r['plot_type']} | {r['status']} | {r['png']} | "
                     f"{r['pdf']} | {r['svg']} | {r['n_warnings']} |")
    with open(os.path.join(output_dir, "qc_report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return {"cases": len(rows), "ok": n_ok, "errors": len(rows) - n_ok, "output": output_dir}


def main() -> int:
    ap = argparse.ArgumentParser(description="Figure QC gallery for the layout pass.")
    ap.add_argument("--output", default="reports/figure_qc_release_candidate")
    args = ap.parse_args()
    print(json.dumps(run(args.output), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
