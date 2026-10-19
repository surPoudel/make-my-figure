"""PNG digests of every plot type's default example render (and a few variants)."""
import hashlib, json, sys
sys.path.insert(0, ".")
from apps.desktop_app.controller import DesktopController
from make_my_figure_core.plots.registry import available_plot_types, figure_to_bytes
C = DesktopController(); out = {}
for pt in available_plot_types():
    d = C.load_example(pt)
    s = C.build_spec(pt, "publication", d.table_name, C.default_mapping(pt))
    r = C.render(s, d)
    out[pt] = hashlib.sha256(figure_to_bytes(r.figure, "png", dpi=100)).hexdigest()[:20]
for pt, extra in (("boxplot_or_violin_with_points", {"kind": "violin"}), ("boxplot_or_violin_with_points", {"hue": "batch"}),
                  ("lineplot_timecourse_with_error_band", {"error": "sd"})):
    d = C.load_example(pt); s = C.build_spec(pt, "publication", d.table_name, {**C.default_mapping(pt), **extra})
    try:
        out[f"{pt}|{extra}"] = hashlib.sha256(figure_to_bytes(C.render(s, d).figure, "png", dpi=100)).hexdigest()[:20]
    except Exception as e:
        out[f"{pt}|{extra}"] = f"ERR {e}"
json.dump(out, open(sys.argv[1], "w"), indent=1); print(len(out), "digests")
