"""Visual QA gallery for the RNA-seq + flexible-annotation milestone.

Renders: a p-only and a stars-only annotated bar plot, a volcano from the
example DE table, and a heatmap from the example voom matrix (with sample
annotation strips). Writes ``reports/rnaseq_qa_gallery.png`` for eyeballing
clipping / tiny text / legend overlap.

Usage:  python scripts/generate_rnaseq_qa_gallery.py
"""

from __future__ import annotations

import io
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from make_my_figure_core.plots.registry import figure_to_bytes, make_spec, render  # noqa: E402
from make_my_figure_core.rnaseq import (  # noqa: E402
    build_expression_matrix, classify_de, heatmap_spec_from_expression, load_rnaseq_table,
    parse_de_table, volcano_spec_from_de,
)
from make_my_figure_core.rnaseq.detect import split_expression_matrix  # noqa: E402

TM = os.path.join(_ROOT, "test_matrix")
OUT = os.path.join(_ROOT, "reports", "rnaseq_qa_gallery.png")


def _bar(annotation, title):
    rng = np.random.default_rng(1)
    df = pd.DataFrame([{"g": g, "y": float(rng.normal(m, 0.3))}
                       for g, m in [("Ctrl", 1.0), ("A", 1.9), ("B", 0.8)] for _ in range(9)])
    spec = make_spec("barplot_with_error_bar", "t", "publication")
    spec["mapping"] = {"x": "g", "y": "y"}
    spec["layout"] = {"title": title}
    spec["statistics"] = {"enabled": True, "test": "welch_t", "comparison_mode": "all_pairs",
                          "correction": "benjamini_hochberg", "annotation": annotation}
    return render(spec, df).figure


def _img(fig, dpi=115):
    return mpimg.imread(io.BytesIO(figure_to_bytes(fig, "png", dpi=dpi)))


def main() -> int:
    panels = []
    panels.append(("annotation: p-value only", _img(_bar({"content": "p"}, "p-value only"))))
    panels.append(("annotation: stars only", _img(_bar({"content": "stars"}, "stars only"))))

    if os.path.exists(os.path.join(TM, "Ctrl_vs_Treatment_DE.txt")):
        info = load_rnaseq_table(os.path.join(TM, "Ctrl_vs_Treatment_DE.txt"))
        de = classify_de(parse_de_table(info.dataframe), lfc_cutoff=1.0, alpha=0.05,
                         use_adjusted=False)
        spec = volcano_spec_from_de(de, top_n_labels=12)
        panels.append(("volcano from DE result", _img(render(spec, de.frame).figure)))

    if os.path.exists(os.path.join(TM, "voom_norm_annot.txt")):
        info = load_rnaseq_table(os.path.join(TM, "voom_norm_annot.txt"))
        mc, sc = split_expression_matrix(info.dataframe)
        em = build_expression_matrix(info.dataframe, metadata_columns=mc, sample_columns=sc)
        meta = None
        if os.path.exists(os.path.join(TM, "meta_info_detail.csv")):
            meta = pd.read_csv(os.path.join(TM, "meta_info_detail.csv"))
        hm = heatmap_spec_from_expression(em, transform="zscore", selection="top_variable",
                                          n_genes=40, metadata=meta, sample_id_col="SampleID",
                                          annotation_columns=["Group", "Sex"] if meta is not None else None)
        panels.append(("heatmap from voom matrix", _img(render(hm["spec"], hm["dataframe"]).figure)))

    n = len(panels)
    ncols = 2
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(ncols * 5.2, nrows * 4.6))
    axes = np.atleast_1d(axes).ravel()
    for ax, (title, img) in zip(axes, panels):
        ax.imshow(img); ax.set_title(title, fontsize=10); ax.axis("off")
    for ax in axes[n:]:
        ax.axis("off")
    fig.tight_layout()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=130)
    plt.close("all")
    print(f"Wrote {OUT} ({n} panels)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
