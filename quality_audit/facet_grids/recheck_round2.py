import sys, warnings as W; sys.path.insert(0, ".")
import numpy as np, pandas as pd
from matplotlib.colors import to_rgb
from apps.desktop_app.controller import DesktopController
from make_my_figure_core.plots.facets import facet_axes, facet_host
C = DesktopController(); DF = pd.read_csv("new_task_ravi/mock_plant_growth.csv"); D = C.loaded_from_dataframe(DF, "p.csv")
BOX = {"x":"Month","y":"Growth_cm","hue":"Nitrogen_Concentration","facet_row":"Age","facet_col":"Species"}
LINE = {"x":"Month","y":"Growth_cm","color":"Nitrogen_Concentration","facet_row":"Age","facet_col":"Species"}
BIG = {"axis_font_pt":16,"tick_label_pt":14,"title_font_pt":18,"legend_pt":13}
T80 = "A very long title about the distribution of plant growth across species, ages and N"
def R(pt, m, lay=None, style=None, data=D):
    s = C.build_spec(pt, "publication", data.table_name, m, width="default"); s.setdefault("layout",{}).update(lay or {})
    if style: s["style"] = style
    r = C.render(s, data); f = r.figure; f.canvas.draw(); r._rd = f.canvas.get_renderer(); return r
def panel_w(r): return round(min(p.get_window_extent(r._rd).width for p in facet_axes(r.figure)) / r.figure.dpi, 2)
def overlap(a, b): return not (a.x1 < b.x0 or a.x0 > b.x1 or a.y1 < b.y0 or a.y0 > b.y1)
out = []
# A
for pt, m, lay, sty in (("boxplot_or_violin_with_points", BOX, {"title": T80, "legend_location": "outside bottom"}, BIG),
                        ("boxplot_or_violin_with_points", BOX, {"title": T80}, {"title_font_pt": 18}),
                        ("lineplot_timecourse_with_error_band", LINE, {"title": T80, "legend_location": "outside top"}, BIG)):
    r = R(pt, m, lay, sty); out.append(("A panel width in", pt[:4], panel_w(r), "fig", r.figure.get_size_inches().round(2).tolist(), [w[:50] for w in r.warnings]))
# B
for pt, m in (("boxplot_or_violin_with_points", BOX), ("lineplot_timecourse_with_error_band", LINE)):
    r = R(pt, m, {"legend_location": "inside upper left"}); lb = facet_host(r.figure).get_legend().get_window_extent(r._rd)
    strips = [a.get_window_extent(r._rd) for a in r.figure.axes if a.get_label() == "<facet-strip>"]
    out.append(("B inside legend overlaps a strip", pt[:4], any(overlap(lb, sb) for sb in strips)))
# C/D
for disp in ("band", "bars"):
    for pt_m in ((LINE, True), ({"x":"Month","y":"Growth_cm","color":"Nitrogen_Concentration"}, False)):
        m, faceted = pt_m
        r = R("lineplot_timecourse_with_error_band", {**m, "error_display": disp}, style={"color_overrides": {"High N": "#d62728"}})
        ax = facet_axes(r.figure)[0] if faceted else r.figure.axes[0]
        cols = set()
        for a in list(ax.collections) + list(ax.lines):
            if getattr(a, "_mmf_group", None) == "High N" or a.get_label() == "High N":
                c = a.get_edgecolor() if type(a).__name__ == "LineCollection" else (a.get_facecolor() if hasattr(a, "get_facecolor") else a.get_color())
                c = c[0] if hasattr(c, "ndim") and getattr(c, "ndim", 1) == 2 else c
                cols.add(tuple(np.round(to_rgb(c), 2)))
        leg = (facet_host(r.figure) if faceted else ax).get_legend()
        hcol = None
        for h, t in zip(leg.legend_handles, leg.get_texts()):
            if t.get_text() == "High N": hcol = tuple(np.round(to_rgb(h.get_color()), 2))
        out.append((f"C/D {disp} {'facet' if faceted else 'plain'} artist colours", cols, "legend", hcol))
# E
r = R("boxplot_or_violin_with_points", BOX, {"width_mm": 120}); out.append(("E 120mm panel", panel_w(r), [w[:60] for w in r.warnings if "panels is about" in w]))
DF3 = DF.copy(); DF3["eight"] = np.tile(np.arange(8), 30)
r = R("boxplot_or_violin_with_points", {**BOX, "facet_col": "eight", "facet_row": None}, data=C.loaded_from_dataframe(DF3, "p3.csv")); out.append(("E 8 cols panel", panel_w(r), [w[:60] for w in r.warnings if "panels is about" in w]))
# F
for pt, m in (("boxplot_or_violin_with_points", {**BOX, "facet_row": None}), ("lineplot_timecourse_with_error_band", {**LINE, "facet_row": None})):
    r = R(pt, m, {"legend_location": "outside bottom"}); lb = facet_host(r.figure).get_legend().get_window_extent(r._rd)
    out.append(("F single row bottom legend below canvas pt", pt[:4], round(-min(0, lb.y0) * 72 / r.figure.dpi, 1), [w[:40] for w in r.warnings]))
# minor: wrap at words
DF2 = DF.copy(); DF2["Species"] = DF2.Species.map({"Species_A": "Arabidopsis thaliana ecotype Columbia-0 greenhouse line", "Species_B": "Brassica napus winter cultivar long-day treatment line"})
r = R("boxplot_or_violin_with_points", BOX, {"width_mm": 120}, data=C.loaded_from_dataframe(DF2, "p2.csv"))
out.append(("wrap strips", [a.texts[0].get_text() for a in r.figure.axes if a.get_label() == "<facet-strip>"][:2]))
for o in out: print(*o)
