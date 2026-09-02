"""Tick-rotation words ("horizontal", "vertical") must apply, not be silently skipped.

``apply_publication_layout`` resolved the angle with ``{"horizontal": 0, ...}.get(word, int(word))``.
A dict default is evaluated before the lookup, so ``int("horizontal")`` raised ValueError inside a
try/except and the rotation was dropped without a word - the control appeared to do nothing for
exactly the two named values the option offers. The Manhattan renderer had the same line. Found by
the Figure Preset QC, which flips every visual option to a non-default value.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

from make_my_figure_core import examples as ex
from make_my_figure_core.plots.registry import render


def _rotations(fig):
    ax = fig.axes[0]
    return {t.get_rotation() for t in ax.get_xticklabels() if t.get_text()}


@pytest.mark.parametrize("word,angle", [("horizontal", 0.0), ("vertical", 90.0), ("45", 45.0)])
def test_layout_rotation_words_are_applied(word, angle):
    info, aux, spec = ex.load_example("barplot_with_error_bar")
    spec["layout"] = {**(spec.get("layout") or {}), "x_tick_rotation": word}
    res = render(spec, info.dataframe)
    try:
        assert _rotations(res.figure) == {angle}
    finally:
        plt.close(res.figure)


@pytest.mark.parametrize("word", ["horizontal", "vertical"])
def test_manhattan_accepts_rotation_words_as_an_option(word):
    info, aux, spec = ex.load_example("manhattan_plot")
    spec["mapping"]["x_tick_rotation"] = word
    res = render(spec, info.dataframe)          # used to raise ValueError
    try:
        expected = 0.0 if word == "horizontal" else 90.0
        assert _rotations(res.figure) == {expected}
    finally:
        plt.close(res.figure)


def test_unreadable_rotation_is_ignored_not_fatal():
    info, aux, spec = ex.load_example("barplot_with_error_bar")
    spec["layout"] = {**(spec.get("layout") or {}), "x_tick_rotation": "sideways"}
    res = render(spec, info.dataframe)
    plt.close(res.figure)
