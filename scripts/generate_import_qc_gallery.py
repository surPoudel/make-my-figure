"""Visual QC for imported external Figure Builder panels (v0.5).

Builds representative multi-panel figures mixing Make My Figure plots with
imported external files, and writes PNGs + a README index to
``outputs/publication_qc/figure_builder_imports/``.

    python scripts/generate_import_qc_gallery.py
"""

from __future__ import annotations

import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from make_my_figure_core import examples  # noqa: E402
from make_my_figure_core.panels import (  # noqa: E402
    FigureLayout, MultiPanelFigure, Panel, build_figure, import_external_panel, panel_warnings,
)
from make_my_figure_core.plots.registry import make_spec  # noqa: E402

OUT = os.path.join(_ROOT, "outputs", "publication_qc", "figure_builder_imports")
ASSETS = os.path.join(OUT, "figure_builder_assets")


def _synthetic_asset(path, size=(3.0, 2.2), dpi=150, kind="line"):
    fig = plt.figure(figsize=size, dpi=dpi)
    ax = fig.add_subplot(111)
    if kind == "micro":  # fake "microscopy" image with white margins
        import numpy as np
        ax.imshow(np.random.default_rng(0).random((40, 60)), cmap="magma")
    else:
        ax.plot([0, 1, 2, 3], [1, 3, 2, 4], marker="o")
        ax.set_title("external tool export")
    fig.savefig(path)
    plt.close(fig)
    return path


def _gen(pt, title):
    info, _a, _s = examples.load_example(pt)
    return Panel(plot_spec=make_spec(pt, "data.csv", "publication"), table=info.dataframe, title=title)


def main() -> int:
    os.makedirs(ASSETS, exist_ok=True)
    png = _synthetic_asset(os.path.join(ASSETS, "src_line.png"))
    micro = _synthetic_asset(os.path.join(ASSETS, "src_micro.png"), size=(2.4, 2.4), kind="micro")
    lowres = _synthetic_asset(os.path.join(ASSETS, "src_lowres.png"), size=(1.0, 1.0), dpi=70)

    def imp(src, **kw):
        p, _a = import_external_panel(src, ASSETS, **kw)
        return p

    cases = []
    # 1. generated-only
    cases.append(("generated_only", [ _gen("barplot_with_error_bar", "Bar"),
                                      _gen("scatterplot_with_regression", "Scatter") ], 2))
    # 2. one imported PNG
    cases.append(("one_imported_png", [ imp(png, title="Imported PNG", width_in=3.2) ], 1))
    # 3. mixed generated + imported (A/B/C/D labels)
    cases.append(("mixed_generated_and_imported", [
        _gen("volcano_plot", "Volcano"), imp(png, title="Imported", width_in=3.2),
        _gen("kaplan_meier_survival_curve", "Survival"), imp(micro, title="Microscopy", width_in=3.2,
                                                             border=True)], 2))
    # 4. imported with annotations
    cases.append(("imported_with_annotations", [ imp(png, title="Annotated", width_in=3.4, annotations=[
        {"kind": "region", "coords": "axes", "xy": [0.1, 0.1], "xy2": [0.45, 0.55], "text": "ROI", "color": "#0072B2"},
        {"kind": "callout", "coords": "axes", "xy": [0.7, 0.7], "xy2": [0.85, 0.35], "text": "peak", "arrow": True, "color": "#D55E00"}]) ], 1))
    # 5. cropped + auto-trim
    cases.append(("cropped_and_trimmed", [ imp(micro, title="Cropped", width_in=3.0,
                                              crop={"top": 0.1, "bottom": 0.1, "left": 0.1, "right": 0.1},
                                              auto_trim=True) ], 1))
    # 6. low-resolution (should warn)
    cases.append(("low_resolution_warning", [ imp(lowres, title="Low-res", width_in=6.0) ], 1))

    made, rows = [], []
    for name, panels, ncols in cases:
        mpf = MultiPanelFigure(name=name, layout=FigureLayout(ncols=ncols, panel_dpi=150))
        for p in panels:
            mpf.add_panel(p)
        fig = build_figure(mpf)
        out = os.path.join(OUT, f"{name}.png")
        fig.savefig(out, dpi=150, bbox_inches="tight")
        warns = panel_warnings(fig)
        rows.append((name, len(panels), "; ".join(warns) or "-"))
        made.append((name, out))
        plt.close(fig)
        print(f"  {name}: {os.path.relpath(out, _ROOT)}  warnings={warns}")

    with open(os.path.join(OUT, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("# Imported external-panel QC gallery (v0.5)\n\n")
        fh.write("Figures mixing Make My Figure plots with imported external files.\n\n")
        fh.write("| figure | panels | warnings |\n|---|---|---|\n")
        for name, n, w in rows:
            fh.write(f"| {name} | {n} | {w} |\n")
        fh.write("\nAssets in `figure_builder_assets/`. Regenerate: "
                 "`python scripts/generate_import_qc_gallery.py`.\n")
    print(f"\nWrote {len(made)} figures to {os.path.relpath(OUT, _ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
