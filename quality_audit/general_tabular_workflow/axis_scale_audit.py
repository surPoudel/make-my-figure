"""Audit axis display scaling across every registered plot type.

Writes, next to this file:
  plot_capability_audit.csv   one row per plot type x axis: supported?, reason, what the audit saw
  axis_scaling_validation.csv one row per applicable plot x axis x scale x tick format
  visual_review/axis_scale_<plot>.png  contact sheets (linear | log10 plain | log10 power | log2 | ln)

Checks per applicable combination: the log scale is applied (or refused with a
reported reason when the bundled example has values <= 0); the plotted values are
identical to the linear render; the limits contain every value; at least two
labelled ticks; tick/axis-label/title font sizes unchanged; PNG, PDF and SVG
export; PlotSpec JSON round trip and Figure Package round trip render
byte-identical PNGs at one dpi.
"""
import copy
import hashlib
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)

from apps.desktop_app.controller import DesktopController  # noqa: E402
from make_my_figure_core.plots.axis_scale import plotted_values  # noqa: E402
from make_my_figure_core.plots.registry import available_plot_types, figure_to_bytes  # noqa: E402
from make_my_figure_core.styles.capabilities import axis_scale_support  # noqa: E402

C = DesktopController()
VIS = os.path.join(HERE, "visual_review")
SCALES = ("log10", "log2", "ln")
FORMATS = ("auto", "plain", "power")


def _digest(fig):
    return hashlib.sha256(figure_to_bytes(fig, "png", dpi=100)).hexdigest()


def _fonts(ax):
    ax.figure.canvas.draw()
    ticks = [t.get_fontsize() for t in ax.get_yticklabels() + ax.get_xticklabels() if t.get_text()]
    return (round(max(ticks), 3) if ticks else None, round(ax.yaxis.label.get_fontsize(), 3),
            round(ax.xaxis.label.get_fontsize(), 3), round(ax.title.get_fontsize(), 3))


def _labelled(ax, axis):
    lo, hi = sorted(ax.get_ylim() if axis == "y" else ax.get_xlim())
    ticks = ax.get_yticklabels() if axis == "y" else ax.get_xticklabels()
    idx = 1 if axis == "y" else 0
    return [t.get_text() for t in ticks if t.get_text() and lo <= t.get_position()[idx] <= hi]


def _render(pt, data, layout):
    spec = C.build_spec(pt, "publication", data.table_name, C.default_mapping(pt))
    spec.setdefault("layout", {}).update(layout)
    return spec, C.render(spec, data)


def main():
    os.makedirs(VIS, exist_ok=True)
    cap_rows, val_rows = [], []
    for pt in available_plot_types():
        data = C.load_example(pt)
        _, base = _render(pt, data, {})
        ax0 = base.figure.axes[0] if base.figure.axes else None
        for axis in "xy":
            ok, reason = axis_scale_support(pt, axis)
            row = {"plot_type": pt, "axis": axis, "supported": ok, "reason": reason}
            if not ok:
                _, res = _render(pt, data, {f"{axis}_scale": "log10"})
                a1 = res.figure.axes[0] if res.figure.axes else None
                unchanged = ax0 is None or (a1.get_xscale(), a1.get_yscale()) == (ax0.get_xscale(), ax0.get_yscale())
                reported = any("not available for this plot" in w for w in res.warnings)
                row.update({"audit": "request reported, axis untouched" if unchanged and reported else "FAIL",
                            "pass": unchanged and reported})
                cap_rows.append(row)
                continue
            fails = 0
            v0 = np.sort(plotted_values(ax0, axis))
            fonts0 = _fonts(ax0)
            sheet = [("linear", base.figure)]
            for scale in SCALES:
                for fmt in FORMATS:
                    spec, res = _render(pt, data, {f"{axis}_scale": scale, f"{axis}_tick_format": fmt})
                    ax = res.figure.axes[0]
                    refused = any("not applied" in w for w in res.warnings)
                    applied = (ax.get_yscale() if axis == "y" else ax.get_xscale()) == "log"
                    v1 = np.sort(plotted_values(ax, axis))
                    same = np.array_equal(v0, v1)
                    lo, hi = sorted(ax.get_ylim() if axis == "y" else ax.get_xlim())
                    contains = (not applied) or (v1.size and lo <= v1.min() and hi >= v1.max())
                    labels = _labelled(ax, axis)
                    fonts_same = _fonts(ax) == fonts0
                    exports = all(len(figure_to_bytes(res.figure, f, dpi=100)) > 300 for f in ("png", "pdf", "svg"))
                    again = C.render(json.loads(json.dumps(spec)), data)
                    spec_rt = _digest(again.figure) == _digest(res.figure)
                    pkg = C.open_package(C.package_bytes(C.package_content(data, spec, res, name=pt)))
                    d2, s2 = C.loaded_from_package(pkg)
                    pkg_rt = _digest(C.render(s2, d2).figure) == _digest(res.figure)
                    ok_row = same and (applied or refused) and contains and (len(labels) >= 2 or not applied) \
                        and fonts_same and exports and spec_rt and pkg_rt
                    fails += 0 if ok_row else 1
                    val_rows.append({"plot_type": pt, "axis": axis, "scale": scale, "tick_format": fmt,
                                     "applied": applied, "refused_with_reason": refused,
                                     "values_identical": same, "limits_contain_data": bool(contains),
                                     "labelled_ticks": len(labels), "tick_labels": " | ".join(labels[:8]),
                                     "fonts_unchanged": fonts_same, "png_pdf_svg": exports,
                                     "plotspec_roundtrip_identical": spec_rt,
                                     "package_roundtrip_identical": pkg_rt, "pass": ok_row,
                                     "notes": " | ".join(w for w in res.warnings if "axis" in w.lower())[:300]})
                    if fmt in ("plain", "power") and scale == "log10" or (fmt == "auto" and scale != "log10"):
                        sheet.append((f"{scale} {fmt}", res.figure))
                    else:
                        plt.close(res.figure)
                    plt.close(again.figure)
            n = len(SCALES) * len(FORMATS)
            row.update({"audit": f"{n - fails}/{n} scale x format combinations pass", "pass": fails == 0})
            cap_rows.append(row)
            fig, axs = plt.subplots(1, len(sheet), figsize=(4.2 * len(sheet), 3.6))
            for a, (title, f) in zip(np.atleast_1d(axs), sheet):
                path = os.path.join(VIS, "_tmp.png")
                f.savefig(path, dpi=70)
                a.imshow(mpimg.imread(path))
                a.set_title(title, fontsize=9)
                a.axis("off")
            fig.suptitle(f"{pt} — {axis} axis", fontsize=11)
            fig.tight_layout()
            fig.savefig(os.path.join(VIS, f"axis_scale_{pt}_{axis}.png"), dpi=80)
            plt.close("all")
        plt.close("all")
    tmp = os.path.join(VIS, "_tmp.png")
    if os.path.exists(tmp):
        os.remove(tmp)
    pd.DataFrame(cap_rows).to_csv(os.path.join(HERE, "plot_capability_audit.csv"), index=False)
    pd.DataFrame(val_rows).to_csv(os.path.join(HERE, "axis_scaling_validation.csv"), index=False)
    cap, val = pd.DataFrame(cap_rows), pd.DataFrame(val_rows)
    print(f"plot types: {len(available_plot_types())}; capability rows {len(cap)}, pass {int(cap['pass'].sum())}; "
          f"validation rows {len(val)}, pass {int(val['pass'].sum())}")
    if (~val["pass"]).any():
        print(val[~val["pass"]][["plot_type", "axis", "scale", "tick_format", "applied", "values_identical",
                                 "labelled_ticks", "fonts_unchanged", "plotspec_roundtrip_identical",
                                 "package_roundtrip_identical"]].to_string())
    if (~cap["pass"]).any():
        print(cap[~cap["pass"]].to_string())


if __name__ == "__main__":
    main()
