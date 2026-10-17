import sys, warnings as W; sys.path.insert(0, ".")
import numpy as np, pandas as pd
from matplotlib.collections import PathCollection
from apps.desktop_app.controller import DesktopController
from make_my_figure_core.plots.facets import facet_axes, facet_host
C = DesktopController(); DF = pd.read_csv("new_task_ravi/mock_plant_growth.csv")
D = C.loaded_from_dataframe(DF, "p.csv")
BOX = {"x":"Month","y":"Growth_cm","hue":"Nitrogen_Concentration","facet_row":"Age","facet_col":"Species"}
LINE = {"x":"Month","y":"Growth_cm","color":"Nitrogen_Concentration","facet_row":"Age","facet_col":"Species"}
def R(pt, m, lay=None, style=None, data=D):
    s = C.build_spec(pt, "publication", data.table_name, m, width="default"); s.setdefault("layout",{}).update(lay or {})
    if style: s["style"] = style
    with W.catch_warnings(record=True) as caught:
        W.simplefilter("always"); r = C.render(s, data)
    r._py_warnings = [str(w.message)[:60] for w in caught if "tight_layout" in str(w.message)]
    f = r.figure; f.canvas.draw(); r._rd = f.canvas.get_renderer(); return r
def legend_box(r): return facet_host(r.figure).get_legend().get_window_extent(r._rd)
def overlap(a, b): return not (a.x1 < b.x0 or a.x0 > b.x1 or a.y1 < b.y0 or a.y0 > b.y1)
out = []
# 1 inside legend visible: host above panels
r = R("lineplot_timecourse_with_error_band", LINE, {"legend_location":"inside upper left"})
h = facet_host(r.figure); out.append(("1 host above panels", h.get_zorder() > max(a.get_zorder() for a in facet_axes(r.figure)), h.get_legend() is not None))
r = R("lineplot_timecourse_with_error_band", LINE); lb = legend_box(r); out.append(("1b line default legend outside right", lb.x0 > max(a.get_window_extent(r._rd).x1 for a in facet_axes(r.figure))))
# 2 horizontal + free value axis: no point outside its panel's xlim
r = R("boxplot_or_violin_with_points", {**BOX, "orientation":"horizontal", "facet_share_y": False})
bad = 0
for ax in facet_axes(r.figure):
    lo, hi = sorted(ax.get_xlim()); pts = np.concatenate([c.get_offsets()[:,0] for c in ax.collections if isinstance(c, PathCollection) and len(c.get_offsets())])
    bad += int(((pts < lo) | (pts > hi)).sum())
out.append(("2 horizontal free: points outside", bad))
# 3 free y: every panel shows y tick labels, limits differ
r = R("boxplot_or_violin_with_points", {**BOX, "facet_share_y": False})
shown = [any(t.get_visible() and t.get_text() for t in ax.get_yticklabels()) for ax in facet_axes(r.figure)]
out.append(("3 free y labels on all panels", shown, len({tuple(np.round(a.get_ylim(),4)) for a in facet_axes(r.figure)})))
# 4/5 outside left/bottom clear of shared labels (pt)
for pt, m in (("boxplot_or_violin_with_points", BOX), ("lineplot_timecourse_with_error_band", LINE)):
    for loc, sty, lay in (("outside left", None, {}), ("outside bottom", None, {}),
                          ("outside bottom", {"axis_font_pt":16,"tick_label_pt":14,"title_font_pt":18,"legend_pt":13}, {}),
                          ("outside bottom", None, {"title": "A very long title about the distribution of plant growth across species, ages and nitrogen"})):
        r = R(pt, m, {"legend_location": loc, **lay}, sty); h = facet_host(r.figure); lb = legend_box(r)
        if loc == "outside left":
            edge = h.yaxis.label.get_window_extent(r._rd).x0; gap = (edge - lb.x1) * 72 / r.figure.dpi
        else:
            edge = h.xaxis.label.get_window_extent(r._rd).y0; gap = (edge - lb.y1) * 72 / r.figure.dpi
        out.append((f"4/5 {pt[:4]} {loc} {'bigfont' if sty else ''}{'longtitle' if lay else ''} gap pt", round(gap,1)))
# 6 strips: text inside strip
def strip_ok(r):
    res = []
    for a in r.figure.axes:
        if a.get_label() == "<facet-strip>" and a.texts:
            sb = a.get_window_extent(r._rd); tb = a.texts[0].get_window_extent(r._rd)
            res.append(tb.x0 >= sb.x0 - 1 and tb.x1 <= sb.x1 + 1 and tb.y0 >= sb.y0 - 1 and tb.y1 <= sb.y1 + 1)
    return all(res), len(res)
r = R("boxplot_or_violin_with_points", BOX, {"width_mm": 120}); out.append(("6 strips fit at 120mm", strip_ok(r), [w[:70] for w in r.warnings if "panels" in w]))
DF2 = DF.copy(); DF2["LongSpecies"] = DF2.Species.map({"Species_A":"Arabidopsis thaliana ecotype Columbia-0 greenhouse line","Species_B":"Brassica napus winter cultivar long-day treatment line"})
r = R("boxplot_or_violin_with_points", {**BOX, "facet_col":"LongSpecies"}, data=C.loaded_from_dataframe(DF2,"p2.csv")); out.append(("6b long names strips fit", strip_ok(r), [w[:60] for w in r.warnings if "facet label" in w]))
# 7/8 width cap
DF3 = DF.copy(); DF3["eight"] = np.tile(np.arange(8), 30)
r = R("boxplot_or_violin_with_points", {**BOX, "facet_col":"eight", "facet_row":None}, data=C.loaded_from_dataframe(DF3,"p3.csv"))
out.append(("8 eight columns size in", r.figure.get_size_inches().round(2).tolist(), [w[:80] for w in r.warnings if "panels is about" in w]))
# 9 line override recolours bars and band
for disp in ("bars","band"):
    r = R("lineplot_timecourse_with_error_band", {**LINE, "error_display": disp}, style={"color_overrides": {"High N": "#d62728"}})
    ax = facet_axes(r.figure)[0]; tagged = [a for a in list(ax.collections)+list(ax.lines) if getattr(a,"_mmf_group",None)=="High N"]
    from matplotlib.colors import to_rgb
    cols = {tuple(np.round(to_rgb((a.get_edgecolor() if type(a).__name__=="LineCollection" else (a.get_facecolor() if hasattr(a,"get_facecolor") else [a.get_color()]))[0]),2)) for a in tagged}
    out.append((f"9 override reaches {disp}", len(tagged), cols))
# 10 default box grid warnings
r = R("boxplot_or_violin_with_points", BOX); out.append(("10 default box warnings", [w[:50] for w in r.warnings], "tight_layout warnings:", len(r._py_warnings)))
# 11 line facet == x warns
r = R("lineplot_timecourse_with_error_band", {**LINE, "facet_col":"Month", "facet_row":None}); out.append(("11 line facet==x warns", any("both" in w for w in r.warnings)))
# 12 hue == facet var: box centred on tick
X = pd.read_excel("new_task_ravi/makemyfigure_demo_data.xlsx")
r = R("boxplot_or_violin_with_points", {"x":"time_point","y":"value","hue":"treatment_A","facet_row":"treatment _B","facet_col":"treatment_A"}, data=C.loaded_from_dataframe(X,"x.csv"))
ax = [a for a in facet_axes(r.figure) if a.patches][0]; centres = sorted({round((lambda b: (b.x0+b.x1)/2)(p.get_path().get_extents()),3) for p in ax.patches}); out.append(("12 hue==facet box centres", centres[:4], "ticks", list(ax.get_xticks())[:4]))
# 13 sampled ticks
r = R("lineplot_timecourse_with_error_band", LINE); out.append(("13 line x ticks", list(facet_axes(r.figure)[3].get_xticks())))
for o in out: print(*o)
