"""Presentation renders for the v1.2.0 slides.

Builds into ``tutorial/showcase/6_whats_new/``. Everything here is rendered by the
released renderer from the bundled examples, at presentation size, so a slide
shows what the application actually draws rather than an illustration of it.

    python tutorial/showcase/build_whats_new.py
"""
from __future__ import annotations

import os
import pathlib
import sys
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import image as mpimg

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "6_whats_new"
sys.path.insert(0, str(ROOT))

from make_my_figure_core import examples                       # noqa: E402
from make_my_figure_core.plots import registry                 # noqa: E402

SPATIAL = ["spatial_categorical_map", "spatial_feature_map", "spatial_composition_map",
           "spatial_roi_map", "spatial_transcript_map", "neighborhood_enrichment_matrix"]


def render(plot_type, layout=None, style=None, mapping=None):
    table, aux, spec = examples.load_example(plot_type)
    if mapping:
        spec = {**spec, "mapping": {**(spec.get("mapping") or {}), **mapping}}
    if layout:
        spec = {**spec, "layout": {**(spec.get("layout") or {}), **layout}}
    if style:
        spec = {**spec, "style": {**(spec.get("style") or {}), **style}}
    return registry.render(spec, table.dataframe,
                           aux={k: v.dataframe for k, v in (aux or {}).items()})


def spatial_six():
    """The six plot types v1.2.0 adds, each from its bundled example."""
    # The key is switched off for the montage. At six panels on one slide each
    # legend was taller than the tissue map beside it, so the thing being shown
    # was the smallest object on the slide - and the deck's own rule is that the
    # plot occupies 50-80% of the area and that text must be readable. The plot
    # types are named by their panel titles; the keys are in the tutorials.
    # Point sizes chosen for a full-size figure disappear when that figure is
    # shrunk into one sixth of a slide. The transcript map draws 6,100 points at
    # the automatic size and came out blank in the montage, so these two are given
    # an explicit size - the same control a user would reach for.
    PRESENTATION = {
        "spatial_transcript_map": {"marker_size": 9, "alpha": 0.85},
        "spatial_categorical_map": {"marker_size": 9},
    }
    paths = []
    for pt in SPATIAL:
        mapping = dict(PRESENTATION.get(pt, {}))
        if pt != "neighborhood_enrichment_matrix":
            mapping["legend"] = False
        res = render(pt, mapping=mapping or None,
                     layout={"column_width": "double", "title": registry.display_name(pt)})
        p = OUT / f"_{pt}.png"
        res.figure.savefig(p, dpi=200, bbox_inches="tight", facecolor="white")
        plt.close(res.figure)
        paths.append(p)

    fig, axes = plt.subplots(2, 3, figsize=(16.0, 8.6), facecolor="white")
    for ax, p in zip(axes.ravel(), paths):
        ax.imshow(mpimg.imread(p))
        ax.axis("off")
    fig.suptitle("Spatial analysis: six plot types, one shared spatial core",
                 fontsize=25, fontweight="bold", color="#111111", y=0.985)
    fig.text(0.5, 0.012,
             "Neighbour graphs, local composition, cellular-neighbourhood clustering and "
             "enrichment. Example data built from published colorectal-carcinoma tissue.",
             ha="center", fontsize=15, color="#1F2937")
    fig.tight_layout(rect=(0, 0.035, 1, 0.955))
    target = OUT / "spatial_six.png"
    fig.savefig(target, dpi=150, facecolor="white")
    plt.close(fig)
    for p in paths:
        os.remove(p)
    return target


def width_is_final():
    """The same figure at three requested widths, drawn to true relative scale.

    Laid out by explicit axes rectangles rather than a gridspec: the panels have
    different physical heights as well as widths, so "to scale" means scaling both
    by one factor and top-aligning them. A gridspec with width_ratios scales the
    columns but leaves each title centred over a narrow column, which clipped the
    57 mm caption at both ends - a slide about text fitting is the worst place to
    clip text.
    """
    asks = [("57mm", 57.0), ("single", 110.0), ("double", 180.0)]
    panels = []
    for name, expected in asks:
        res = render("boxplot_or_violin_with_points", layout={"column_width": name})
        w_mm, h_mm = (v * 25.4 for v in res.figure.get_size_inches())
        p = OUT / f"_w_{name}.png"
        res.figure.savefig(p, dpi=200, facecolor="white")
        plt.close(res.figure)
        panels.append({"name": name, "asked": expected, "drew": w_mm, "h_mm": h_mm, "path": p})

    FW, FH = 16.0, 8.0                      # slide-shaped canvas, inches
    LEFT, RIGHT, TOP, BOT = 0.035, 0.035, 0.175, 0.175
    GAP = 0.022
    avail = 1.0 - LEFT - RIGHT - GAP * (len(panels) - 1)
    total_mm = sum(p["drew"] for p in panels)
    mm_per_frac = total_mm / avail          # one scale for every panel

    fig = plt.figure(figsize=(FW, FH), facecolor="white")
    x = LEFT
    top_y = 1.0 - TOP
    captions = []
    for p in panels:
        w_frac = p["drew"] / mm_per_frac
        # Same scale vertically, converted through the canvas aspect ratio.
        h_frac = (p["h_mm"] / mm_per_frac) * (FW / FH)
        h_frac = min(h_frac, top_y - BOT)
        ax = fig.add_axes((x, top_y - h_frac, w_frac, h_frac))
        ax.imshow(mpimg.imread(p["path"]))
        ax.axis("off")
        exact = "exact" if abs(p["drew"] - p["asked"]) < 0.5 else f"{p['drew'] - p['asked']:+.1f} mm off"
        caption = fig.text(x + w_frac / 2, top_y - h_frac - 0.028,
                           f"{p['name']}\nasked {p['asked']:.0f} mm · drew {p['drew']:.1f} mm ({exact})",
                           ha="center", va="top", fontsize=14, color="#1F2937", linespacing=1.45)
        captions.append(caption)
        x += w_frac + GAP

    fig.text(0.5, 0.955, "A requested width is final — these panels are to scale",
             ha="center", va="top", fontsize=26, fontweight="bold", color="#111111")
    fig.text(0.5, 0.075,
             "All 45 plot types honour all five width settings exactly: 225 of 225 combinations.\n"
             "Where the content cannot fit, the plot area gives up the room and the render says so.",
             ha="center", va="top", fontsize=15, color="#1F2937", linespacing=1.5)

    # A caption centred under the narrowest panel is wider than the panel, so it
    # ran off the left edge of the canvas. Measure it and slide it back inside
    # rather than guessing a character width.
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    margin = 8.0
    for caption in captions:
        box = caption.get_window_extent(renderer)
        shift = 0.0
        if box.x0 < margin:
            shift = (margin - box.x0) / fig.bbox.width
        elif box.x1 > fig.bbox.width - margin:
            shift = -((box.x1 - (fig.bbox.width - margin)) / fig.bbox.width)
        if shift:
            cx, cy = caption.get_position()
            caption.set_position((cx + shift, cy))

    target = OUT / "width_is_final.png"
    fig.savefig(target, dpi=150, facecolor="white")
    plt.close(fig)
    for p in panels:
        os.remove(p["path"])
    return target, [(p["name"], p["asked"], p["drew"], p["path"]) for p in panels]


def main():
    warnings.filterwarnings("ignore")
    OUT.mkdir(parents=True, exist_ok=True)
    a = spatial_six()
    print(f"  {a.relative_to(ROOT)}  {os.path.getsize(a) // 1024} KB")
    b, rendered = width_is_final()
    print(f"  {b.relative_to(ROOT)}  {os.path.getsize(b) // 1024} KB")
    for name, expected, drawn, _p in rendered:
        print(f"      {name:8s} asked {expected:6.1f} mm  drew {drawn:6.1f} mm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
