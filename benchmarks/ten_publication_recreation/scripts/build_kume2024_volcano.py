"""Build the Kume et al. 2024 (eLife) psoriasis volcano recreation entry.

Verified by VIEWING the published Figure 5A (a volcano plot: log2 fold-change vs
-log10 padj of psoriatic non-lesional vs control keratinocyte RNA-seq, with red
labelled genes). Source data = eLife Figure 5-source data 1, sheet "Figure 5A".
Article + figure + source data are CC BY 4.0 (eLife API copyright.license =
CC-BY-4.0 for article 97654), so the real panel is stored with attribution.

p-values are READ VERBATIM: the sheet ships -log10(padj); we store the exact
back-transform padj = 10**(-neglog10_padj) (a lossless inverse of the published
value, NOT a recomputation) and let the volcano renderer draw -log10(padj).
"""

from __future__ import annotations

import io
import json
import os
import sys
import urllib.request

import matplotlib
matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
BASE = os.path.abspath(os.path.join(HERE, ".."))

from make_my_figure_core.plots.registry import export_figure, make_spec, render  # noqa: E402

PUB_ID = "kume2024_psoriasis_semaphorin"
PUB = os.path.join(BASE, "publications", PUB_ID)
DATA_URL = "https://cdn.elifesciences.org/articles/97654/elife-97654-fig5-data1-v1.xlsx"
FIG_URL = ("https://iiif.elifesciences.org/lax/97654%2Felife-97654-fig5-v1.tif/"
           "full/900,/0/default.jpg")
DATE = "2026-07-15"

# Genes drawn/labelled in red in the published Figure 5A (read off the figure).
HIGHLIGHT = ["SPRR2F", "SERPINB4", "S100A7A", "CXCL8", "PI3", "DEFB4B", "SPRR2A",
             "S100A8", "S100A9", "S100A7", "KRT14", "DEFB4A", "KRT16", "SEMA4A",
             "KRT5", "KRT10"]


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def _write_json(path, obj):
    _write(path, json.dumps(obj, indent=2))


def main():
    # ---- data ---------------------------------------------------------
    raw = urllib.request.urlopen(DATA_URL, timeout=120).read()
    sheet = pd.read_excel(io.BytesIO(raw), sheet_name="Figure 5A", header=None)
    # row 0: [NaN, 'log2 FC', '-log10 padj']; rows 1.. : gene, log2FC, neglog10padj
    body = sheet.iloc[1:].copy()
    body.columns = ["gene", "log2FoldChange", "neglog10_padj"] + list(body.columns[3:])
    body = body[["gene", "log2FoldChange", "neglog10_padj"]].dropna(subset=["gene"])
    body["log2FoldChange"] = pd.to_numeric(body["log2FoldChange"], errors="coerce")
    body["neglog10_padj"] = pd.to_numeric(body["neglog10_padj"], errors="coerce")
    body = body.dropna(subset=["log2FoldChange", "neglog10_padj"]).reset_index(drop=True)
    # Exact lossless inverse of the published -log10(padj); clip to a positive floor.
    body["padj"] = np.power(10.0, -body["neglog10_padj"].clip(lower=0.0))
    body["padj"] = body["padj"].clip(upper=1.0)

    os.makedirs(os.path.join(PUB, "raw_data"), exist_ok=True)
    os.makedirs(os.path.join(PUB, "processed_data"), exist_ok=True)
    body[["gene", "log2FoldChange", "neglog10_padj"]].to_csv(
        os.path.join(PUB, "raw_data", "elife-97654-fig5A-source.csv"), index=False)
    proc = os.path.join(PUB, "processed_data", "psoriasis_nl_vs_ctl_de.csv")
    body.to_csv(proc, index=False)
    print(f"data: {len(body)} genes; "
          f"up>=1&padj<0.05: {int(((body.log2FoldChange>=1)&(body.padj<0.05)).sum())}, "
          f"down<=-1&padj<0.05: {int(((body.log2FoldChange<=-1)&(body.padj<0.05)).sum())}")

    # ---- render volcano through the app path --------------------------
    panel = os.path.join(PUB, "recreated_panels", "panel_A")
    os.makedirs(panel, exist_ok=True)
    body.to_csv(os.path.join(panel, "processed_data.csv"), index=False)

    spec = make_spec("volcano_plot", "psoriasis_nl_vs_ctl_de.csv", "publication")
    spec["mapping"] = {
        "x": "log2FoldChange", "p": "padj", "label": "gene",
        "use_fdr": True, "lfc_cutoff": 1.0, "p_cutoff": 0.05,
        "highlight_genes": HIGHLIGHT, "label_mode": "pasted",
        "show_arrows": True, "label_by": "symbol",
    }
    spec["output"] = {"formats": ["svg", "png", "pdf"],
                      "width_mm": 89.0, "height_mm": 90.0, "dpi": 300}
    spec["layout"] = {"title": "Psoriatic NL vs control",
                      "x_label": "log$_2$ fold-change",
                      "y_label": "-log$_{10}$ padj"}
    _write_json(os.path.join(panel, "plotspec.json"), spec)

    result = render(spec, body)
    export_figure(result.figure, os.path.join(panel, "recreated"),
                  ["png", "svg", "pdf"], 300)
    print("rendered:", result.metadata.get("n_up"), "up /",
          result.metadata.get("n_down"), "down /", result.metadata.get("n_labeled"), "labels")
    if result.warnings:
        print("warnings:", result.warnings)

    # ---- reference figure: crop panel A (volcano) from Figure 5 -------
    refdir = os.path.join(PUB, "reference_figures", PUB_ID)
    os.makedirs(refdir, exist_ok=True)
    img_bytes = urllib.request.urlopen(FIG_URL, timeout=120).read()
    full = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    W, H = full.size
    box = (0.0, 0.0, 0.44, 0.285)  # panel A = top-left quadrant (volcano)
    crop = full.crop((int(box[0] * W), int(box[1] * H),
                      int(box[2] * W), int(box[3] * H)))
    ref_png = os.path.join(refdir, "reference_panel.png")
    crop.save(ref_png)
    _write_json(os.path.join(refdir, "crop_metadata.json"), {
        "figure_id": "elife-97654-fig5",
        "crop": "panel A (top-left) cropped from the full 6-panel Figure 5 — the volcano plot",
        "crop_box_fractions": {"left": box[0], "top": box[1],
                               "right": box[2], "bottom": box[3]},
        "source_image": FIG_URL, "size": "width 900px",
    })
    _write(os.path.join(refdir, "license.txt"),
           "Kume M, Koguchi-Yoshioka H, Nakai S, Matsumura Y, Tanemura A, Yokoi K, "
           "... Watanabe R (2024). Downregulation of semaphorin 4A in keratinocytes "
           "reflects the features of non-lesional psoriasis. eLife 13:RP97654.\n"
           "DOI: 10.7554/eLife.97654\n"
           "Figure: Figure 5, panel A (volcano plot, psoriatic non-lesional vs control "
           "keratinocyte RNA-seq, GSE121212); figure id elife-97654-fig5\n"
           "Source: https://elifesciences.org/articles/97654 ; image "
           f"{FIG_URL}\n"
           "License: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/) -- "
           "(c) 2024 Kume et al.\n"
           f"Date accessed: {DATE}. Redistributed here (panel A cropped) with "
           "attribution under CC BY 4.0.\n")

    # ---- side-by-side -------------------------------------------------
    sbs_dir = os.path.join(PUB, "side_by_side")
    os.makedirs(sbs_dir, exist_ok=True)
    rec = mpimg.imread(os.path.join(panel, "recreated.png"))
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    axes[0].imshow(np.asarray(crop)); axes[0].set_title("Published: Kume 2024 Fig 5A (CC BY 4.0)")
    axes[1].imshow(rec); axes[1].set_title("Make My Figure recreation")
    for ax in axes:
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(os.path.join(sbs_dir, f"{PUB_ID}.png"), dpi=130, bbox_inches="tight")
    plt.close(fig)
    print("wrote side_by_side")


if __name__ == "__main__":
    main()
