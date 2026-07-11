"""Visual QA gallery for v0.5 features.

Renders the new plot types plus network / volcano-annotation / heatmap-highlight
/ clustering / manual-annotation variants from bundled example data, writes one
PNG each + a contact sheet + a README index under
``outputs/style_qa_gallery/v0_5/``.

    python scripts/generate_example_data.py
    python scripts/generate_v05_qa_gallery.py
"""

from __future__ import annotations

import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from make_my_figure_core import examples  # noqa: E402
from make_my_figure_core.plots.registry import make_spec, render  # noqa: E402

OUT_DIR = os.path.join(_ROOT, "outputs", "style_qa_gallery", "v0_5")

# (label, plot_type, mapping_overrides, annotations)
VARIANTS = [
    ("network_spring", "network_graph", {"layout": "spring", "color_by": "group"}, None),
    ("network_circular", "network_graph", {"layout": "circular", "color_by": "value"}, None),
    ("network_kamada", "network_graph", {"layout": "kamada_kawai", "min_weight": 0.5}, None),
    ("hierarchical_clustering_k3", "hierarchical_clustering", {"k": 3}, None),
    ("hierarchical_clustering_k4", "hierarchical_clustering", {"k": 4, "cluster": "columns"}, None),
    ("heatmap_cluster_k3", "heatmap_clustered_matrix", {"cluster_k_rows": 3, "scale": "row_zscore"}, None),
    ("volcano_labels_off", "volcano_plot", {"annotate": False}, None),
    ("volcano_top_up_down", "volcano_plot",
     {"label": "label", "label_mode": "top_up_down", "top_n_up": 6, "top_n_down": 6, "show_arrows": True}, None),
    ("volcano_top_fdr", "volcano_plot", {"label": "label", "label_mode": "top_fdr", "top_n": 12}, None),
    ("scatter_manual_annotations", "scatterplot_with_regression", None,
     [{"kind": "region", "coords": "axes", "xy": [0.08, 0.55], "xy2": [0.42, 0.92], "text": "cluster A", "color": "#0072B2"},
      {"kind": "callout", "coords": "axes", "xy": [0.7, 0.7], "xy2": [0.55, 0.35], "text": "outlier", "arrow": True, "color": "#D55E00"},
      {"kind": "text", "coords": "figure", "xy": [0.02, 0.96], "text": "A", "font_weight": "bold", "font_size": 16}]),
]


def _load_aux(pt):
    _info, aux, _ = examples.load_example(pt)
    return {k: v.dataframe for k, v in aux.items()} or None


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    made, problems, rows = [], [], []
    for label, pt, over, anns in VARIANTS:
        if not examples.has_example(pt):
            problems.append(f"{label}: no example for {pt}")
            continue
        info, aux, _ = examples.load_example(pt)
        aux_dfs = {k: v.dataframe for k, v in aux.items()} or None
        spec = make_spec(pt, "data.csv", "publication")
        if over:
            spec["mapping"] = dict(spec["mapping"], **over)
        if anns:
            spec["annotations"] = anns
        try:
            result = render(spec, info.dataframe, aux=aux_dfs)
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{label}: RENDER FAILED: {exc}")
            rows.append((label, pt, "FAILED", str(exc)[:80]))
            continue
        out = os.path.join(OUT_DIR, f"{label}.png")
        result.figure.savefig(out, dpi=150, bbox_inches="tight")
        chk = result.metadata.get("publication_check", {})
        warns = "; ".join(chk.get("warnings", [])) or "-"
        if not chk.get("passed", True):
            problems.append(f"{label}: publication check: {chk.get('warnings')}")
        rows.append((label, pt, "ok" if chk.get("passed", True) else "warn", warns))
        made.append((label, out))
        plt.close(result.figure)
        print(f"  {label}: {os.path.relpath(out, _ROOT)}")

    if made:
        ncols = 3
        nrows = (len(made) + ncols - 1) // ncols
        fig, axes = plt.subplots(nrows, ncols, figsize=(ncols * 4.4, nrows * 3.6))
        axes = axes.ravel() if hasattr(axes, "ravel") else [axes]
        for ax, (label, path) in zip(axes, made):
            ax.imshow(plt.imread(path))
            ax.set_title(label, fontsize=9)
            ax.axis("off")
        for ax in axes[len(made):]:
            ax.axis("off")
        fig.tight_layout()
        fig.savefig(os.path.join(OUT_DIR, "_contact_sheet.png"), dpi=130, bbox_inches="tight")
        plt.close(fig)

    with open(os.path.join(OUT_DIR, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("# v0.5 visual QA gallery\n\nRendered from bundled synthetic example data.\n\n")
        fh.write("| variant | plot type | render | warnings |\n|---|---|---|---|\n")
        for label, pt, status, warns in rows:
            fh.write(f"| {label} | `{pt}` | {status} | {warns} |\n")
        fh.write("\nContact sheet: `_contact_sheet.png`.\n")

    print(f"\nRendered {len(made)}/{len(VARIANTS)} variants to {os.path.relpath(OUT_DIR, _ROOT)}")
    if problems:
        print("\nISSUES:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("All v0.5 QA variants rendered and passed the publication check.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
