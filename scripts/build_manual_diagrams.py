"""Schematic diagrams for the manuals - plain boxes and arrows, matplotlib only."""
import matplotlib; matplotlib.use("Agg")
import os
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "manuals", "assets", "diagrams")
FONT = dict(family="DejaVu Sans")

def box(ax, x, y, w, h, text, fc="#F2F5F9", ec="#3B5B7A", fs=9.5, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=1.3))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else "normal", **FONT)

def arrow(ax, x0, y0, x1, y1, text=""):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=14, lw=1.2, color="#3B5B7A"))
    if text:
        ax.text((x0 + x1) / 2, (y0 + y1) / 2 + 0.18, text, ha="center", va="bottom", fontsize=8, color="#3B5B7A", **FONT)

def canvas(w=11, h=3.4):
    fig, ax = plt.subplots(figsize=(w, h)); ax.set_xlim(0, w); ax.set_ylim(0, h); ax.axis("off"); return fig, ax

def save(fig, name):
    fig.savefig(os.path.join(OUT, name + ".png"), dpi=200, bbox_inches="tight")
    fig.savefig(os.path.join(OUT, name + ".svg"), bbox_inches="tight"); plt.close(fig)

fig, ax = canvas(12, 3.2)
steps = ["Load data\n(CSV / TSV / TXT /\nExcel workbook)", "Map columns\n(you confirm roles)", "Choose a plot\n(38 types) or take a\nrecommendation", "Statistics\n(optional)", "Publication\nstyle, annotations", "Export\n(SVG / PDF / PNG /\nTIFF / EPS + PlotSpec)"]
x = 0.3
for i, s in enumerate(steps):
    box(ax, x, 1.0, 1.7, 1.4, s)
    if i < len(steps) - 1: arrow(ax, x + 1.72, 1.7, x + 1.98, 1.7)
    x += 2.0
ax.text(6, 0.35, "Multi-panel assembly (Figure Builder) and Figure presets sit alongside every step.", ha="center", fontsize=9, color="#444", **FONT)
save(fig, "workflow_overview")

fig, ax = canvas(11, 4.6)
box(ax, 0.4, 2.6, 4.4, 1.7, "PlotSpec  (*.plot_spec.json)\nexact record of ONE figure:\ntable name · column roles · options ·\nthresholds · labels · style · statistics ·\nannotations · worksheet provenance", fc="#FFF7E6", ec="#9A6B00", fs=9)
box(ax, 6.2, 3.35, 4.4, 1.0, "Figure STYLE preset  (*.mmfpreset.json)\nfonts · palette · geometry · legend/colorbar ·\nexport defaults · visual plot options", fc="#EAF6EC", ec="#2E7D32", fs=9)
box(ax, 6.2, 2.05, 4.4, 1.0, "Figure FULL configuration preset\nstyle preset + column roles · thresholds ·\naxis labels · statistics test · annotations", fc="#EAF6EC", ec="#2E7D32", fs=9)
arrow(ax, 4.85, 3.7, 6.15, 3.85, "Save preset (style)"); arrow(ax, 4.85, 3.2, 6.15, 2.55, "Save preset (full)")
box(ax, 0.4, 0.4, 4.4, 1.3, "Never in a preset:\nthe data table · table name · worksheet\nprovenance · row values · click-selected points", fc="#FDECEC", ec="#B71C1C", fs=9)
box(ax, 6.2, 0.4, 4.4, 1.3, "Apply preset onto NEW data\n→ settings return · new table stays the new table\n→ missing columns are listed for you to map,\n   never substituted", fc="#F2F5F9", fs=9)
arrow(ax, 8.4, 2.0, 8.4, 1.75)
save(fig, "plotspec_vs_preset")

fig, ax = canvas(12, 3.4)
steps = ["① Map columns\nfeature ID · value\n(sample) columns ·\nvalue scale confirmed", "② Define groups\nmetadata file, workbook\nsheet, or typed per\nsample column", "③ Preprocess\n(raw-like data only)\ndiagnostics · QC plots ·\nrecommended recipes", "④ Validation\nreport of mapping,\ngroups, missing values,\nduplicate ids", "⑤ Recommend &\ngenerate\ndifferential summary ·\nheatmap · PCA · box", "Plot editor\nfull controls · presets ·\nexport with MatrixSpec +\nPreprocessingSpec"]
x = 0.3
for i, s in enumerate(steps):
    box(ax, x, 1.0, 1.75, 1.6, s, fs=8.6)
    if i < len(steps) - 1: arrow(ax, x + 1.77, 1.8, x + 1.98, 1.8)
    x += 2.0
ax.text(6, 0.35, "The original matrix is never modified; every derived matrix is a new table with its steps recorded.", ha="center", fontsize=9, color="#444", **FONT)
save(fig, "matrix_workflow")

fig, ax = canvas(11, 4.0)
box(ax, 0.4, 2.4, 3.0, 1.2, "Generated panel\nPlotSpec + data table\n(re-rendered on demand)", fc="#F2F5F9")
box(ax, 0.4, 0.6, 3.0, 1.2, "Imported panel\nPNG / JPG / TIFF / WEBP / BMP\nPDF / SVG / EPS (rasterised)", fc="#FFF7E6", ec="#9A6B00")
box(ax, 4.2, 1.5, 2.8, 1.4, "Figure Builder\ngrid · panel sizes ·\ngutters · labels · fonts", bold=True)
box(ax, 7.9, 2.4, 2.8, 1.2, "Composite figure\nPNG / SVG / PDF\n(panel content raster,\nlabels vector text)", fc="#EAF6EC", ec="#2E7D32")
box(ax, 7.9, 0.6, 2.8, 1.2, "FigureSpec (*.figure_spec.json)\n+ Layout preset (*.mmflayout.json)\n+ figure_builder_assets/", fc="#EAF6EC", ec="#2E7D32", fs=8.8)
arrow(ax, 3.45, 3.0, 4.15, 2.5); arrow(ax, 3.45, 1.2, 4.15, 1.9); arrow(ax, 7.05, 2.5, 7.85, 3.0); arrow(ax, 7.05, 1.9, 7.85, 1.2)
save(fig, "figure_builder_provenance")
print("diagrams regenerated")
