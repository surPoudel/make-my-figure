"""Renderers must draw the same figure on every supported pandas version.

pandas' default ``sort_values`` kind is quicksort, which is not stable: rows that tie on the sort key
come out in an arbitrary order that differs between pandas 2 (object dtype) and pandas 3 (default
``str`` dtype). On 2026-09-22 the whole-library fingerprint showed the stacked composition bars drawn
in the order S01, S14, S13, ... on pandas 2.2.3 and S01, S02, S03, ... on pandas 3.0.6 for the same
data. Every ``sort_values`` in the renderers now asks for a stable sort, so ties keep the input
order on every version.
"""
import glob
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from make_my_figure_core.plots.registry import make_spec, render

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_every_renderer_sort_is_stable():
    unstable = []
    for path in sorted(glob.glob(os.path.join(ROOT, "make_my_figure_core", "plots", "*.py"))):
        with open(path, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                if ".sort_values(" in line and 'kind="stable"' not in line and "kind='stable'" not in line:
                    unstable.append(f"{os.path.basename(path)}:{lineno}: {line.strip()}")
    assert not unstable, "sort_values without kind='stable':\n" + "\n".join(unstable)


def _stacked_frame():
    rows = []
    # Samples arrive in a deliberately scrambled order so a stable sort has something to preserve;
    # the group column ties within each group, which is where quicksort scrambles.
    order = ["S03", "S01", "S02", "S06", "S04", "S05"]
    groups = {"S01": "Control", "S02": "Control", "S03": "Control",
              "S04": "Treated", "S05": "Treated", "S06": "Treated"}
    for s in order:
        for comp, frac in (("A", 0.5), ("B", 0.3), ("C", 0.2)):
            rows.append({"sample_id": s, "group": groups[s], "cell_type": comp, "fraction": frac})
    return pd.DataFrame(rows)


def test_stacked_bar_sort_by_group_keeps_input_order_within_ties():
    df = _stacked_frame()
    spec = make_spec("stacked_bar_composition", "synthetic.csv", "publication",
                     mapping={"x": "sample_id", "stack": "cell_type", "y": "fraction",
                              "facet_or_sort_by": "group"})
    result = render(spec, df)
    try:
        labels = [t.get_text() for t in result.figure.axes[0].get_xticklabels()]
    finally:
        plt.close(result.figure)
    # Control group first (alphabetical on the key), and within each group the order the samples
    # first appeared in the table - never the arbitrary quicksort order.
    assert labels == ["S03", "S01", "S02", "S06", "S04", "S05"]


def test_stacked_bar_sort_by_group_is_identical_for_object_and_string_dtypes():
    df = _stacked_frame()
    spec = make_spec("stacked_bar_composition", "synthetic.csv", "publication",
                     mapping={"x": "sample_id", "stack": "cell_type", "y": "fraction",
                              "facet_or_sort_by": "group"})
    seen = []
    for dtype in ("object", "string"):
        work = df.copy()
        for c in ("sample_id", "group", "cell_type"):
            work[c] = work[c].astype(dtype)
        result = render(spec, work)
        try:
            seen.append([t.get_text() for t in result.figure.axes[0].get_xticklabels()])
        finally:
            plt.close(result.figure)
    assert seen[0] == seen[1] == ["S03", "S01", "S02", "S06", "S04", "S05"]
