"""Comparison sheets: the same synthetic figure under Publication defaults and each experimental preset.

Usage: python scripts/experimental_preset_comparison_sheets.py [--out reports/journal_presets/comparison_sheets]
                                                                [--plot-types a,b,c]

One PNG per plot type. Each column is a preset (first column = Publication defaults at the app's
default width), rendered at the preset's target width and shown at a common physical scale, so
that text and line weights can be compared by eye exactly as they would print. A caption under
each column names the preset, its target width and the smallest effective font. Synthetic example
data only.
"""

from __future__ import annotations

import argparse
import io
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402

from make_my_figure_core import experimental_presets as xp  # noqa: E402
from make_my_figure_core import preset_preview as pv  # noqa: E402
from make_my_figure_core.plots import registry  # noqa: E402
from make_my_figure_core.plots.registry import display_name  # noqa: E402
from make_my_figure_core.qc.text_layout_qc import check_text_layout  # noqa: E402

DEFAULT_TYPES = ["boxplot_or_violin_with_points", "grouped_barplot_with_error_bar", "scatterplot_with_regression",
                 "lineplot_timecourse_with_error_band", "kaplan_meier_survival_curve", "volcano_plot",
                 "heatmap_clustered_matrix", "pca_scatter_from_matrix", "forest_plot", "enrichment_dotplot"]
SHEET_DPI = 150   # pixels per inch of *paper*; every column is drawn at true physical size at this dpi


def render_at_scale(spec, df, aux, target_mm):
    result = registry.render(spec, df, aux=aux)
    qc = check_text_layout(result.figure, target_width_mm=target_mm)
    png = registry.figure_to_bytes(result.figure, "png", dpi=SHEET_DPI)
    plt.close(result.figure)
    return Image.open(io.BytesIO(png)).convert("RGB"), qc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "reports" / "journal_presets" / "comparison_sheets"))
    ap.add_argument("--plot-types", default="")
    a = ap.parse_args()
    entries = xp.list_experimental_presets()
    if not entries:
        print("no experimental presets found", file=sys.stderr)
        return 1
    os.makedirs(a.out, exist_ok=True)
    pts = [p for p in a.plot_types.split(",") if p] or DEFAULT_TYPES
    index = ["# Comparison sheets", "", "Columns: Publication defaults, then each experimental preset at its "
             "target width; all columns share one physical scale (150 px per inch of paper). Synthetic data.", ""]
    for pt in pts:
        columns = []
        spec, df, aux = pv.synthetic_spec(pt)
        img, qc = render_at_scale(spec, df, aux, None)
        columns.append((img, f"Publication defaults\n{qc.tight_width_mm} mm wide, smallest text {qc.min_font_pt} pt"))
        for e in entries:
            if not e.universal and e.plot_type != pt:
                continue
            p = xp.load_experimental_preset(e.path)
            s2, df2, aux2 = pv.synthetic_spec(pt)
            res = pv.apply_with_guard(p, s2, columns=list(df2.columns))
            img2, qc2 = render_at_scale(res.spec, df2, aux2, e.target_width_mm)
            tgt = f"target {e.target_width_mm:g} mm -> " if e.target_width_mm else "no width target; "
            columns.append((img2, f"{e.name}\n{tgt}{qc2.tight_width_mm} mm wide, "
                                  f"smallest text {qc2.effective_min_font_pt} pt"))
        # compose: same pixel scale, columns side by side, captions below
        pad = 30
        cap_h = 70
        total_w = sum(im.width for im, _ in columns) + pad * (len(columns) + 1)
        max_h = max(im.height for im, _ in columns)
        sheet = Image.new("RGB", (total_w, max_h + cap_h + pad * 2), "white")
        x = pad
        from PIL import ImageDraw
        draw = ImageDraw.Draw(sheet)
        for im, cap in columns:
            sheet.paste(im, (x, pad))
            draw.multiline_text((x, pad + max_h + 8), cap, fill=(40, 40, 40))
            x += im.width + pad
        draw.text((pad, sheet.height - 18), f"{display_name(pt)} - synthetic example data - {len(columns)} columns at one physical scale",
                  fill=(90, 90, 90))
        out = os.path.join(a.out, f"{pt}.png")
        sheet.save(out)
        index.append(f"- [{display_name(pt)}]({pt}.png)")
        print(pt, "->", out, flush=True)
    with open(os.path.join(a.out, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(index) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
