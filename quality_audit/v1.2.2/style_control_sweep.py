"""Every style control the panel can show, on every plot type: does it act?

The reported defect was a "Diverging map" chooser beside a dot plot that ramps a
single magnitude - visible, and unable to do anything. That is a class of bug,
not one bug, so this asks the same question of every control on every plot:

    change it, re-render, and see whether the figure actually changed.

A control that changes nothing is only acceptable when the plot type DECLARES it
unsupported (the panel then hides it). Anything else is a promise the figure
breaks. Writes style_control_sweep.csv beside this file.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import pathlib
import sys
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from make_my_figure_core import examples                      # noqa: E402
from make_my_figure_core.plots import registry                # noqa: E402
from make_my_figure_core.styles.capabilities import (          # noqa: E402
    STYLE_CONTROL_CAPABILITY, get_style_capabilities)

DPI = 70

# Every control the desktop style panel writes into spec["style"], with a value
# far enough from the default that a change cannot be missed.
CONTROLS = {
    "title_font_pt": 22.0,
    "axis_font_pt": 20.0,
    "tick_label_pt": 18.0,
    "legend_pt": 18.0,
    "annotation_pt": 18.0,
    "marker_size": 180.0,
    "line_width_pt": 4.5,
    "spine_width_pt": 3.5,
    "legend_outside": True,
    "grid": True,
    "font_family": "DejaVu Serif",
    "palette_name": "grayscale",
    "sequential_cmap": "Greys",
    "diverging_cmap": "PuOr",
    "color_overrides": {"0": "#FF00FF"},
}

# Controls whose effect depends on the example having the thing they style, not
# on the plot type being able to honour them at all.
NEEDS = {
    "legend_pt": "legend",
    "legend_outside": "legend",
    "annotation_pt": "text",
    "marker_size": "markers",
    "line_width_pt": "lines",
    "title_font_pt": "title",
    "grid": "axes",
    "spine_width_pt": "axes",
    "axis_font_pt": "axis labels",
    "tick_label_pt": "tick labels",
}


def digest(fig) -> str:
    fig.savefig(io.BytesIO(), format="png", dpi=DPI)      # settle at this dpi
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI)
    return hashlib.sha256(buf.getvalue()).hexdigest()[:16]


def render(plot_type, style=None):
    table, aux, spec = examples.load_example(plot_type)
    spec = json.loads(json.dumps(spec))
    if style:
        spec["style"] = {**(spec.get("style") or {}), **style}
    return registry.render(spec, table.dataframe,
                           aux={k: v.dataframe for k, v in (aux or {}).items()})


def figure_has(fig, what) -> bool:
    if what == "legend":
        return any(ax.get_legend() is not None for ax in fig.axes) or bool(fig.legends)
    if what == "text":
        return any(ax.texts for ax in fig.axes)
    if what == "markers":
        return any(ax.collections for ax in fig.axes) or any(
            line.get_marker() not in ("", "None", None) for ax in fig.axes for line in ax.lines)
    if what == "lines":
        return any(ax.lines for ax in fig.axes)
    if what == "title":
        return any(ax.get_title().strip() for ax in fig.axes) or (
            getattr(fig, "_suptitle", None) is not None)
    if what == "axes":
        return any(ax.axison and ax.get_frame_on() for ax in fig.axes)
    if what == "axis labels":
        return any(ax.get_xlabel().strip() or ax.get_ylabel().strip() for ax in fig.axes)
    if what == "tick labels":
        return any(t.get_text().strip() for ax in fig.axes
                   for t in list(ax.get_xticklabels()) + list(ax.get_yticklabels()))
    return True


def main():
    warnings.filterwarnings("ignore")
    plot_types = [p for p in sorted(registry.available_plot_types()) if examples.entry(p)]
    rows, problems = [], []
    for i, pt in enumerate(plot_types, 1):
        caps = get_style_capabilities(pt)
        baseline = render(pt)
        base_digest = digest(baseline.figure)
        # Which colormap chooser the PANEL shows for this figure. Capabilities
        # can only say the plot type uses colormaps at all; which of the two is
        # live depends on the data, so the render reports it and the panel - and
        # therefore this sweep - follows that.
        role = (baseline.metadata or {}).get("colormap_role")
        row = {"plot_type": pt}
        for key, value in CONTROLS.items():
            flag = STYLE_CONTROL_CAPABILITY.get(key)
            declared = getattr(caps, flag, True) if flag else True
            if not declared:
                row[key] = "hidden"          # the panel does not offer it
                continue
            if key in ("sequential_cmap", "diverging_cmap") \
                    and role != key.split("_")[0]:
                row[key] = "hidden"          # the other map governs this figure
                continue
            need = NEEDS.get(key)
            if need and not figure_has(baseline.figure, need):
                row[key] = "no " + need      # nothing of that kind in this example
                continue
            result = render(pt, {key: value})
            changed = digest(result.figure) != base_digest
            plt.close(result.figure)
            row[key] = "acts" if changed else "DEAD"
            if not changed:
                problems.append((pt, key))
        plt.close(baseline.figure)
        rows.append(row)
        print(f"  [{i:2d}/{len(plot_types)}] {pt}")
        sys.stdout.flush()

    cols = ["plot_type"] + list(CONTROLS)
    with open(OUT / "style_control_sweep.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    tally = {}
    for row in rows:
        for key in CONTROLS:
            tally.setdefault(key, {}).setdefault(row[key], 0)
            tally[key][row[key]] += 1
    print(f"\n  {len(plot_types)} plot types x {len(CONTROLS)} controls")
    for key, counts in tally.items():
        print(f"    {key:18} {counts}")
    print(f"\n  visible controls that do nothing: {len(problems)}")
    by_control = {}
    for pt, key in problems:
        by_control.setdefault(key, []).append(pt)
    for key, pts in sorted(by_control.items()):
        print(f"    {key:18} {len(pts)}: {', '.join(pts)}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
