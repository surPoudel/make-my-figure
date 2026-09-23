"""Build the author review PDFs.

    python tutorial/review/build_review_pdfs.py

* tutorial/review/TUTORIAL_VISUAL_REVIEW.pdf - representative screenshots, the before / after
  showcase pairs, the observation-control grid and the publication-preset sequence, each page
  captioned with the file it came from.
* presentation/review/PRESENTATION_VISUAL_REVIEW.pdf - every slide of the deck at review size,
  from the PNG renders in tutorial/slides/_render (produced by PowerPoint through
  tutorial/slides/render_pptx_windows.py), two slides per page with the slide number and the
  review classification.

Pure matplotlib (PdfPages); no extra dependencies.
"""
from __future__ import annotations

import csv
import glob
import os
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
TUT = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(TUT, ".."))
SHOTS = os.path.join(TUT, "screenshots")
SHOW = os.path.join(TUT, "showcase")
PRES_REVIEW = os.path.join(ROOT, "presentation", "review")
plt.rcParams["font.family"] = "DejaVu Sans"


def _page(pdf, title, items, ncols=2, note=""):
    """items: list of (path, caption). Landscape letter page."""
    nrows = max(1, (len(items) + ncols - 1) // ncols)
    fig = plt.figure(figsize=(11, 8.5))
    fig.text(0.04, 0.955, title, fontsize=15, weight="bold", color="#1F2937")
    if note:
        fig.text(0.04, 0.925, note, fontsize=9.5, color="#555")
    top, bottom = 0.90, 0.05
    cell_h = (top - bottom) / nrows
    for i, (path, cap) in enumerate(items):
        r, c = divmod(i, ncols)
        ax = fig.add_axes([0.04 + c * (0.92 / ncols), top - (r + 1) * cell_h + 0.055, 0.92 / ncols - 0.02, cell_h - 0.075])
        ax.axis("off")
        if path and os.path.exists(path):
            ax.imshow(Image.open(path))
        else:
            ax.text(0.5, 0.5, "missing: " + os.path.basename(str(path)), ha="center", va="center", color="red")
        ax.set_title("\n".join(textwrap.wrap(cap, 70)), fontsize=8.5, loc="left", color="#333")
    pdf.savefig(fig)
    plt.close(fig)


def tutorial_review():
    out = os.path.join(HERE, "TUTORIAL_VISUAL_REVIEW.pdf")
    with PdfPages(out) as pdf:
        fig = plt.figure(figsize=(11, 8.5)); fig.text(0.06, 0.8, "Make My Figure desktop tutorial", fontsize=22, weight="bold", color="#1F2937")
        fig.text(0.06, 0.73, "Visual review sheet for the author - representative screenshots and same-data showcases", fontsize=13, color="#333")
        fig.text(0.06, 0.62, "Every image is either a capture of the real desktop application (automation/run_tutorial.py, offscreen, 1680 x 1000)\n"
                 "or a figure rendered by the application's own renderer from the tutorial datasets (showcase/build_showcase.py).\n"
                 "Presets are loaded from their files and applied with the application's own apply function.\n"
                 "All datasets are simulated. Data integrity per showcase pair: audit/showcase_data_integrity.csv.", fontsize=10.5, color="#333")
        pdf.savefig(fig); plt.close(fig)

        _page(pdf, "Getting started - navigation captures (full window is appropriate here)",
              [(os.path.join(SHOTS, "getting_started", "01_start_screen.png"), "start screen"),
               (os.path.join(SHOTS, "getting_started", "04_workspace.png"), "workspace with the bundled box / violin example")])
        _page(pdf, "Column mapping - the ambiguous table",
              [(os.path.join(SHOTS, "mapping_ambiguous", "01b_data_preview.png"), "Data preview: col_A, measurement_2, condition_code, thing, score_final, id_value"),
               (os.path.join(SHOTS, "mapping_ambiguous", "02_mapping_proposed.png"), "2. Map columns as proposed for the box plot"),
               (os.path.join(SHOTS, "mapping_ambiguous", "04_scatter_mapping.png"), "the same table mapped for a scatter (x, y, color, label)"),
               (os.path.join(SHOTS, "mapping_ambiguous", "06_final.png"), "figure crop: scatter with per-group regression")])
        _page(pdf, "Showcase 1 - one dataset, publication presets (manuscript typography)",
              [(os.path.join(SHOW, "1_group_comparison", "A_default_box.png"), "A default rendering"),
               (os.path.join(SHOW, "1_group_comparison", "B_box_points_outline_preset.png"), "B preset Box + observations (outline) + statistics"),
               (os.path.join(SHOW, "1_group_comparison", "C_violin_points_preset.png"), "C preset Violin + observations"),
               (os.path.join(SHOW, "1_group_comparison", "D_bar_points_jittered_preset.png"), "D preset Bar + observations (jittered)")],
              note="same 40 observations (7 / 9 / 11 / 13 per group); presets are experimental evidence-derived presets, not journal-approved")
        _page(pdf, "Showcase 1 - the same observations, six point treatments (presentation typography)",
              [(os.path.join(SHOW, "1_group_comparison", f"{n}_pres.png"), n.replace("_", " ")) for n in
               ("J1_small_narrow_jitter", "J2_large_moderate_jitter", "J3_open_circles", "J4_black_edged_filled", "J5_beeswarm", "J6_centered_no_jitter")],
              ncols=3, note="point_size, point_jitter_width, point_fill, point_edge, point_edge_width, point_arrangement, point_alpha - the data never change")
        _page(pdf, "Showcase 2 - volcano, default versus refined (presentation typography)",
              [(os.path.join(SHOW, "2_volcano", "A_default_pres.png"), "A default: raw P axis, 10 labels, profile marker size"),
               (os.path.join(SHOW, "2_volcano", "B_refined_pres.png"), "B refined: adjusted P (FDR) axis, labelled boxes, larger markers")])
        _page(pdf, "Showcase 3 - heatmap, basic versus refined (30 most variable features in both)",
              [(os.path.join(SHOW, "3_heatmap", "A_basic_pres.png"), "A basic: unscaled values, auto colormap, clustered columns"),
               (os.path.join(SHOW, "3_heatmap", "B_refined_pres.png"), "B refined: row z-score, RdBu_r, columns in file order, labelled"),
               (os.path.join(SHOW, "3_heatmap", "C_heatmap_with_dendrogram_pres.png"), "C the Hierarchical clustering plot type draws the tree")], ncols=3)
        _page(pdf, "Showcase 4 and 5 - scatter and survival, basic versus refined",
              [(os.path.join(SHOW, "4_scatter", "A_basic_pres.png"), "scatter A basic"),
               (os.path.join(SHOW, "4_scatter", "B_refined_pres.png"), "scatter B refined: colour by cell line, r / R2 / P / n"),
               (os.path.join(SHOW, "5_survival", "A_default_pres.png"), "Kaplan-Meier A default"),
               (os.path.join(SHOW, "5_survival", "B_refined_pres.png"), "Kaplan-Meier B refined: percent, 50 % line, log-rank P")])
        obs = os.path.join(SHOTS, "observations_jitter")
        if os.path.isdir(obs):
            _page(pdf, "Tutorial chapter - showing individual observations and controlling jitter (real UI captures)",
                  [(os.path.join(obs, n), n) for n in ("01_defaults_options.png", "03_jitter_narrow.png", "04_point_size_60.png",
                                                       "05_open_circles.png", "07_box_outline_n_labels.png", "08_statistics_brackets.png")], ncols=3)
            _page(pdf, "Tutorial chapter - preview, apply, keep adjusting",
                  [(os.path.join(obs, n), n) for n in ("09_preview_dialog.png", "10_after_preset.png", "11_adjusted_after_preset.png")], ncols=3)
        pres = os.path.join(SHOTS, "publication_presets")
        if os.path.isdir(pres):
            _page(pdf, "Tutorial chapter - publication presets (real UI captures)",
                  [(os.path.join(pres, n), n) for n in ("02_preset_panel_default.png", "03_preset_panel_experimental.png", "04_preview_dialog_violin.png",
                                                        "01_before_preset.png", "05_after_violin_preset.png", "07_after_89mm_preset.png")], ncols=3)
    print("wrote", out)


def presentation_review():
    os.makedirs(PRES_REVIEW, exist_ok=True)
    renders = sorted(glob.glob(os.path.join(TUT, "slides", "_render", "slide_*.png")))
    review = {}
    csv_path = os.path.join(ROOT, "presentation", "audit", "slide_review.csv")
    if os.path.exists(csv_path):
        for r in csv.DictReader(open(csv_path, encoding="utf-8")):
            review[int(r["slide"])] = r
    out = os.path.join(PRES_REVIEW, "PRESENTATION_VISUAL_REVIEW.pdf")
    with PdfPages(out) as pdf:
        for i in range(0, len(renders), 2):
            items = []
            for p in renders[i:i + 2]:
                n = int(os.path.basename(p).split("_")[1].split(".")[0])
                r = review.get(n, {})
                cap = f"slide {n}" + (f"  [{r.get('classification', '')}] {r.get('purpose', '')}" if r else "")
                items.append((p, cap))
            _page(pdf, "Presentation review - rendered by PowerPoint at 1600 x 1200", items, ncols=2 if len(items) == 2 else 1)
    print("wrote", out, f"({len(renders)} slides)")


if __name__ == "__main__":
    tutorial_review()
    presentation_review()
