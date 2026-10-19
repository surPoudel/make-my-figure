import sys; sys.path.insert(0, ".")
import io, numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.image as mpimg
from apps.desktop_app.controller import DesktopController
from make_my_figure_core.plots.registry import figure_to_bytes
C = DesktopController(); DF = pd.read_csv("new_task_ravi/mock_plant_growth.csv"); D = C.loaded_from_dataframe(DF, "p.csv")
DF2 = DF.copy(); DF2["Species"] = DF2.Species.map({"Species_A": "Arabidopsis thaliana ecotype Columbia-0 greenhouse line", "Species_B": "Brassica napus winter cultivar long-day treatment line"}); D2 = C.loaded_from_dataframe(DF2, "p2.csv")
BOX = {"x":"Month","y":"Growth_cm","hue":"Nitrogen_Concentration","facet_row":"Age","facet_col":"Species"}
LINE = {"x":"Month","y":"Growth_cm","color":"Nitrogen_Concentration","facet_row":"Age","facet_col":"Species"}
BIG = {"axis_font_pt":16,"tick_label_pt":14,"title_font_pt":18,"legend_pt":13}
cases = [
 ("box inside upper left", "boxplot_or_violin_with_points", BOX, {"legend_location": "inside upper left"}, None, D),
 ("box long title bigfont bottom", "boxplot_or_violin_with_points", BOX, {"title": "A very long title about the distribution of plant growth across species, ages and N", "legend_location": "outside bottom"}, BIG, D),
 ("box 120mm long names", "boxplot_or_violin_with_points", BOX, {"width_mm": 120}, None, D2),
 ("line cols-only bottom", "lineplot_timecourse_with_error_band", {**LINE, "facet_row": None}, {"legend_location": "outside bottom"}, None, D),
 ("line override bars", "lineplot_timecourse_with_error_band", {**LINE, "error_display": "bars"}, {}, {"color_overrides": {"High N": "#d62728"}}, D),
 ("box horizontal free", "boxplot_or_violin_with_points", {**BOX, "orientation": "horizontal", "facet_share_y": False}, {}, None, D),
]
fig, axs = plt.subplots(2, 3, figsize=(21, 11))
for ax, (name, pt, m, lay, sty, data) in zip(axs.ravel(), cases):
    s = C.build_spec(pt, "publication", data.table_name, m, width="default"); s.setdefault("layout", {}).update(lay)
    if sty: s["style"] = sty
    r = C.render(s, data)
    ax.imshow(mpimg.imread(io.BytesIO(figure_to_bytes(r.figure, "png", dpi=80)))); ax.axis("off"); ax.set_title(name, fontsize=10)
    plt.close(r.figure)
fig.tight_layout(); fig.savefig("/tmp/mmf/facet/sheet_final.png", dpi=60)
