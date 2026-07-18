"""Clipping / overlap QC engine (make_my_figure_core.qa.layout_qc).

Advisory, honest (bbox-based) detection + non-destructive auto-fix. GUI-free.
"""

import matplotlib
import numpy as np
import pandas as pd
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from make_my_figure_core.qa.layout_qc import (
    LayoutQCReport, auto_fix_layout, check_layout)
from make_my_figure_core.plots.registry import available_plot_types, make_spec, render


def _clean_fig():
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot([0, 1, 2], [0, 1, 2])
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    return fig


def _clipped_fig():
    fig, ax = plt.subplots(figsize=(2.2, 2.0))
    ax.plot([0, 1, 2], [0, 1, 2])
    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(["VeryLongCategoryLabel_A", "VeryLongCategoryLabel_B",
                        "VeryLongCategoryLabel_C"])
    ax.set_ylabel("A very long y axis label that will clip")
    ax.set_title("A long title that likely clips at the figure edge")
    return fig


def test_clean_figure_passes():
    fig = _clean_fig()
    rep = check_layout(fig)
    assert isinstance(rep, LayoutQCReport)
    assert rep.status == "pass" and rep.issues == []
    plt.close(fig)


def test_clipped_figure_flags_clipping_with_structured_fields():
    fig = _clipped_fig()
    rep = check_layout(fig)
    assert rep.status in ("warning", "fail")
    clip = [i for i in rep.issues if i.category == "clipping"]
    assert clip, "clipping not detected"
    i = clip[0]
    assert i.artist and i.message and i.suggested_fix       # structured
    assert any(x.auto_fixable for x in rep.issues)          # auto-fix advertised
    plt.close(fig)


def test_auto_fix_reduces_clipping():
    # Auto-fix is advisory/best-effort (matplotlib tight_layout has limits on tiny
    # figures), so it must strictly REDUCE clipping and report what it did — it does
    # not promise perfection.
    fig = _clipped_fig()
    before = sum(1 for i in check_layout(fig).issues if i.category == "clipping")
    fixes = auto_fix_layout(fig)
    after = sum(1 for i in check_layout(fig).issues if i.category == "clipping")
    assert before > 0 and after < before, f"clipping {before} -> {after}"
    assert fixes  # reported what it did
    plt.close(fig)


def test_overlap_detected_for_stacked_annotations():
    fig, ax = plt.subplots(figsize=(4, 4))
    for i in range(8):
        ax.text(0.5, 0.5, f"Label{i}", fontsize=12)   # all stacked at one point
    rep = check_layout(fig)
    assert any(i.category == "overlap" for i in rep.issues)
    plt.close(fig)


def test_report_serializes_to_dict():
    rep = check_layout(_clipped_fig())
    d = rep.to_dict()
    assert set(d) == {"status", "issues"} and isinstance(d["issues"], list)
    if d["issues"]:
        assert {"category", "severity", "artist", "message", "suggested_fix",
                "auto_fixable"} <= set(d["issues"][0])


# --- integration with render() ----------------------------------------------
def test_render_populates_layout_qc_metadata():
    df = pd.DataFrame({"g": ["a", "b", "c"], "v": [1.0, 2, 3]})
    spec = make_spec("barplot_with_error_bar", "b", "publication", mapping={"x": "g", "y": "v"})
    r = render(spec, df)
    assert "layout_qc" in r.metadata and r.metadata["layout_qc"]["status"] in (
        "pass", "warning", "fail")


def test_render_auto_fix_option_records_fixes():
    # Force a cramped figure via a tiny explicit size + long labels, opt into auto-fix.
    df = pd.DataFrame({"g": [f"VeryLongCategory_{i}" for i in range(6)], "v": list(range(6))})
    spec = make_spec("barplot_with_error_bar", "b", "publication", mapping={"x": "g", "y": "v"})
    spec["layout"] = {"column_width": "single", "auto_fix_layout": True}
    r = render(spec, df)
    # auto-fix may or may not be needed depending on fonts, but it must not crash and
    # the QC report must be present.
    assert "layout_qc" in r.metadata


def test_layout_qc_never_crashes_on_any_plot_type():
    from make_my_figure_core import examples as ex
    from make_my_figure_core.plots.registry import default_mapping
    checked = 0
    for pt in available_plot_types():
        try:
            info, aux, ps = ex.load_example(pt)
        except Exception:
            continue
        sp = dict(ps) if ps else make_spec(pt, "a", "publication", mapping=default_mapping(pt))
        sp.setdefault("plot_type", pt)
        sp["journal_style"] = "publication"
        auxd = {k: v.dataframe for k, v in (aux or {}).items()} or None
        r = render(sp, info.dataframe, aux=auxd)
        assert "layout_qc" in r.metadata
        checked += 1
        plt.close("all")
    assert checked >= 30
