"""Survival-curve input forms, event-indicator validation and percentage scaling.

Regression cover for collaborator concern C1. The reported symptom was a survival plot that came
out as a nearly flat line with no warning: the supplied workbook held an already-computed survival
curve (one column of S(t) per group) while the renderer expected one row per subject with a 0/1
event indicator, so exactly one "event" was counted out of 28 rows.

All fixtures here are synthetic and constructed in-test. The shape that triggered the bug - a time
column plus repeated columns of a monotonically non-increasing survival function - is reproduced
from first principles, not copied from the collaborator's file.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from make_my_figure_core.plots.base import RenderError
from make_my_figure_core.plots.registry import make_spec, render

PLOT = "kaplan_meier_survival_curve"


def _precomputed_curves() -> pd.DataFrame:
    """A digitised lifespan figure: time plus three S(t) columns that all share one header.

    The repeated header is deliberate. A spreadsheet exported from another tool often labels every
    group identically, and pandas disambiguates to ``event``, ``event.1``, ``event.2``; all three
    must survive as three separate curves.
    """
    t = np.array([0, 2, 5, 10, 15, 20, 25, 30, 35, 40], dtype=float)
    a = np.array([1.00, 0.99, 0.97, 0.95, 0.92, 0.85, 0.60, 0.30, 0.08, 0.00])
    b = np.array([1.00, 0.99, 0.96, 0.94, 0.90, 0.78, 0.42, 0.15, 0.03, 0.00])
    c = np.array([1.00, 1.00, 0.96, 0.94, 0.93, 0.87, 0.55, 0.25, 0.05, 0.00])
    df = pd.DataFrame({"time_months": t})
    df["event"] = a
    df["event.1"] = b
    df["event.2"] = c
    return df


def _subject_level(seed: int = 11, n: int = 40) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for group, scale in (("Control", 26.0), ("Treated", 15.0)):
        event_t = rng.exponential(scale, n)
        censor_t = rng.exponential(50.0, n)
        for obs, ev in zip(np.minimum(event_t, censor_t), (event_t <= censor_t).astype(int)):
            rows.append({"t": float(obs), "ev": int(ev), "arm": group})
    return pd.DataFrame(rows)


def _render(mapping, df, **kw):
    spec = make_spec(PLOT, "synthetic", "publication", mapping=mapping, **kw)
    return render(spec, df)


# --------------------------------------------------------------------------------------
# The reported failure: a precomputed curve fed to the subject-level form
# --------------------------------------------------------------------------------------

def test_survival_probabilities_as_event_column_are_refused_not_drawn():
    """The exact reported case must raise, and say what to do instead.

    Before the fix this produced a step at S = 1 - 1/n with no warning, because only the single row
    whose value was exactly 1.0 matched ``events == 1``.
    """
    df = _precomputed_curves()
    with pytest.raises(RenderError) as excinfo:
        _render({"time": "time_months", "event": "event"}, df)
    message = str(excinfo.value)
    assert "already-computed survival curve" in message
    assert "precomputed" in message
    assert "survival_columns" in message


def test_non_binary_event_column_with_many_levels_is_refused():
    """A many-valued column outside 0-1 is not an indicator either."""
    df = pd.DataFrame({"t": [1.0, 2.0, 3.0, 4.0, 5.0], "ev": [3.0, 7.0, 11.0, 2.0, 9.0]})
    with pytest.raises(RenderError, match="not an event indicator"):
        _render({"time": "t", "event": "ev"}, df)


# --------------------------------------------------------------------------------------
# The precomputed form
# --------------------------------------------------------------------------------------

def test_precomputed_form_draws_one_curve_per_column():
    df = _precomputed_curves()
    res = _render({"input_form": "precomputed", "time": "time_months",
                   "survival_columns": ["event", "event.1", "event.2"]}, df)
    try:
        assert res.metadata["n_curves"] == 3
        assert res.metadata["survival_input_form"] == "precomputed"
        # every source column is recorded, so a curve can be traced back to its column
        assert {g["source_column"] for g in res.metadata["groups"].values()} == {
            "event", "event.1", "event.2"}
        # the supplied values are plotted as given, not re-estimated
        ax = res.figure.axes[0]
        drawn = [ln for ln in ax.lines if len(ln.get_ydata()) == len(df)]
        assert len(drawn) == 3
        for line in drawn:
            ys = np.asarray(line.get_ydata(), dtype=float)
            assert ys[0] == pytest.approx(1.0)
            assert ys[-1] == pytest.approx(0.0)
            assert np.all(np.diff(ys) <= 1e-12)   # never increases
    finally:
        plt.close(res.figure)


def test_precomputed_form_repeated_headers_stay_separate_curves():
    """Feature identity: three same-named columns must not collapse into one."""
    df = _precomputed_curves()
    res = _render({"input_form": "precomputed", "time": "time_months",
                   "survival_columns": ["event", "event.1", "event.2"]}, df)
    try:
        ys = [tuple(np.round(ln.get_ydata(), 6)) for ln in res.figure.axes[0].lines
              if len(ln.get_ydata()) == len(df)]
        assert len(ys) == 3
        assert len(set(ys)) == 3, "curves were deduplicated by label"
    finally:
        plt.close(res.figure)


def test_precomputed_form_needs_a_survival_column():
    df = _precomputed_curves()
    with pytest.raises(RenderError, match="survival"):
        _render({"input_form": "precomputed", "time": "time_months"}, df)


def test_precomputed_form_warns_when_a_curve_increases():
    df = pd.DataFrame({"time": [0.0, 1.0, 2.0, 3.0], "s": [1.0, 0.6, 0.8, 0.4]})
    res = _render({"input_form": "precomputed", "time": "time", "survival": "s"}, df)
    try:
        assert any("never rise" in w for w in res.warnings)
    finally:
        plt.close(res.figure)


def test_precomputed_form_refuses_to_invent_a_logrank_test():
    """A log-rank test cannot come from a curve; the refusal must be explicit."""
    df = _precomputed_curves()
    res = _render({"input_form": "precomputed", "time": "time_months",
                   "survival_columns": ["event", "event.1"]}, df,
                  statistics={"enabled": True, "test": "logrank"})
    try:
        assert res.stats_report is None
        assert any("cannot be computed from a precomputed survival curve" in w
                   for w in res.warnings)
    finally:
        plt.close(res.figure)


# --------------------------------------------------------------------------------------
# Percentage scale, labels and reference line
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("scale,top,label", [
    ("fraction", 1.0, "Survival probability"),
    ("percent", 100.0, "% survival"),
])
def test_y_scale_sets_limits_and_default_label(scale, top, label):
    df = _precomputed_curves()
    res = _render({"input_form": "precomputed", "time": "time_months",
                   "survival": "event", "y_scale": scale}, df)
    try:
        ax = res.figure.axes[0]
        assert ax.get_ylim()[1] == pytest.approx(top * 1.02)
        assert ax.get_ylabel() == label
        assert np.asarray(ax.lines[0].get_ydata(), dtype=float)[0] == pytest.approx(top)
    finally:
        plt.close(res.figure)


def test_percent_scale_applies_to_estimated_curves_too():
    res = _render({"time": "t", "event": "ev", "group": "arm", "y_scale": "percent"},
                  _subject_level())
    try:
        ax = res.figure.axes[0]
        assert ax.get_ylim()[1] == pytest.approx(102.0)
        assert np.asarray(ax.lines[0].get_ydata(), dtype=float)[0] == pytest.approx(100.0)
    finally:
        plt.close(res.figure)


def test_reference_line_is_drawn_in_axis_units():
    df = _precomputed_curves()
    res = _render({"input_form": "precomputed", "time": "time_months", "survival": "event",
                   "y_scale": "percent", "reference_line": 50}, df)
    try:
        ys = [ln.get_ydata()[0] for ln in res.figure.axes[0].lines
              if len(set(np.round(ln.get_ydata(), 9))) == 1]
        assert any(y == pytest.approx(50.0) for y in ys)
    finally:
        plt.close(res.figure)


def test_group_labels_rename_curves_without_touching_the_data():
    df = _precomputed_curves()
    before = df.copy(deep=True)
    res = _render({"input_form": "precomputed", "time": "time_months",
                   "survival_columns": ["event", "event.1"],
                   "group_labels": ["Wild type", "Mutant"]}, df)
    try:
        labels = [ln.get_label() for ln in res.figure.axes[0].lines
                  if not str(ln.get_label()).startswith("_")]
        assert "Wild type" in labels and "Mutant" in labels
        assert df.equals(before)          # renderer must not mutate the caller's frame
    finally:
        plt.close(res.figure)


# --------------------------------------------------------------------------------------
# Event-indicator recoding must reach the statistics, not just the drawing
# --------------------------------------------------------------------------------------

def test_two_level_event_coding_is_reported_and_counted_correctly():
    df = _subject_level()
    shifted = df.assign(ev=df["ev"] + 1)          # 1/2 coding, as R often produces
    res = _render({"time": "t", "event": "ev", "group": "arm"}, shifted)
    try:
        assert any("coded 1/2" in w for w in res.warnings)
        counted = {k: v["events"] for k, v in res.metadata["groups"].items()}
        truth = df.groupby("arm")["ev"].sum().to_dict()
        assert counted == truth
    finally:
        plt.close(res.figure)


def test_recoded_events_give_the_same_logrank_as_zero_one():
    """The drawn curve and the reported test must read the same indicator."""
    df = _subject_level()
    stats = {"enabled": True, "test": "logrank", "mode": "omnibus"}

    def chi2_for(frame):
        res = _render({"time": "t", "event": "ev", "group": "arm"}, frame, statistics=stats)
        try:
            return res.metadata["statistics_report"]["results"][0]["statistic"]
        finally:
            plt.close(res.figure)

    assert chi2_for(df) == pytest.approx(chi2_for(df.assign(ev=df["ev"] + 1)), abs=1e-12)


def test_logrank_matches_statsmodels_survdiff():
    """Independent oracle for the test reported on the figure."""
    survdiff = pytest.importorskip(
        "statsmodels.duration.survfunc", reason="statsmodels needed as the log-rank oracle"
    ).survdiff
    df = _subject_level()
    res = _render({"time": "t", "event": "ev", "group": "arm"}, df,
                  statistics={"enabled": True, "test": "logrank", "mode": "omnibus"})
    try:
        mine = res.metadata["statistics_report"]["results"][0]
    finally:
        plt.close(res.figure)
    chi2, p = survdiff(df["t"].to_numpy(), df["ev"].to_numpy(), df["arm"].to_numpy())
    assert mine["statistic"] == pytest.approx(chi2, abs=1e-10)
    assert mine["p_value"] == pytest.approx(p, abs=1e-10)


# --------------------------------------------------------------------------------------
# Curve style guard
# --------------------------------------------------------------------------------------

def test_line_style_is_refused_for_estimated_curves():
    res = _render({"time": "t", "event": "ev", "group": "arm", "curve_style": "line"},
                  _subject_level())
    try:
        assert any("misrepresents an estimated" in w for w in res.warnings)
    finally:
        plt.close(res.figure)


def test_line_style_is_allowed_for_precomputed_curves():
    df = _precomputed_curves()
    res = _render({"input_form": "precomputed", "time": "time_months", "survival": "event",
                   "curve_style": "line"}, df)
    try:
        assert not any("misrepresents" in w for w in res.warnings)
    finally:
        plt.close(res.figure)


def test_unknown_input_form_and_scale_are_rejected():
    df = _precomputed_curves()
    with pytest.raises(RenderError, match="input_form"):
        _render({"input_form": "nonsense", "time": "time_months", "event": "event"}, df)
    with pytest.raises(RenderError, match="y_scale"):
        _render({"input_form": "precomputed", "time": "time_months", "survival": "event",
                 "y_scale": "nonsense"}, df)


def test_survival_options_are_exposed_to_the_frontends():
    """The plot exposed no options at all, which is what made the axis look fixed."""
    from make_my_figure_core.ui_hints import column_fields, options
    keys = {o.key for o in options(PLOT)}
    assert {"input_form", "y_scale", "reference_line"} <= keys
    assert "survival_columns" in column_fields(PLOT)


def test_precomputed_spec_round_trips_through_the_sidecar(tmp_path):
    """The new mapping must survive export -> sidecar -> re-render unchanged."""
    import json

    from make_my_figure_core.plots.registry import export_figure, figure_to_bytes, write_sidecar

    df = _precomputed_curves()
    mapping = {"input_form": "precomputed", "time": "time_months",
               "survival_columns": ["event", "event.1"], "y_scale": "percent",
               "reference_line": 50, "group_labels": ["Wild type", "Mutant"]}
    spec = make_spec(PLOT, "synthetic", "publication", mapping=mapping)
    first = render(spec, df)
    stem = str(tmp_path / "curve")
    export_figure(first.figure, stem, ["png"])
    write_sidecar(spec, first.metadata, stem)
    reference = figure_to_bytes(render(spec, df).figure, "svg")
    plt.close(first.figure)

    recovered = json.load(open(stem + ".plot_spec.json", encoding="utf-8"))["plot_spec"]
    assert recovered["mapping"]["survival_columns"] == ["event", "event.1"]
    assert recovered["mapping"]["y_scale"] == "percent"

    again = render(recovered, df)
    try:
        assert again.metadata["n_curves"] == 2
        assert again.metadata["y_scale"] == "percent"
        # same drawing commands, ignoring the ids/timestamp matplotlib stamps per export
        import re
        norm = lambda b: re.sub(rb"[0-9a-f]{10,}", b"H",
                                re.sub(rb"<dc:date>[^<]*</dc:date>", b"", b))
        assert norm(figure_to_bytes(again.figure, "svg")) == norm(reference)
    finally:
        plt.close(again.figure)


def test_survival_columns_is_declared_a_multi_column_role():
    """A single-value picker would quietly plot one curve out of several.

    `survival_columns` takes one column per group. If a frontend renders it as a single-value
    selector the figure still draws - with one curve - and looks finished, which is the failure mode
    this whole concern was about.
    """
    from make_my_figure_core import ui_hints

    assert ui_hints.is_multi_column("survival_columns")
    assert "survival_columns" in ui_hints.MULTI_COLUMN_FIELDS
    assert not ui_hints.is_multi_column("time")
    assert not ui_hints.is_multi_column("event")


def test_streamlit_offers_a_multiselect_for_multi_column_roles():
    """Static check: the browser app must not render a list-valued role as a single picker."""
    import ast
    import pathlib

    source = pathlib.Path("apps/streamlit_app/streamlit_app.py").read_text(encoding="utf-8")
    assert "is_multi_column" in source, (
        "the column-mapping loop must consult ui_hints.is_multi_column")
    tree = ast.parse(source)
    assert any(isinstance(n, ast.Attribute) and n.attr == "multiselect"
               for n in ast.walk(tree)), "no multiselect widget in the app"


def test_desktop_gives_multi_column_roles_a_list_widget():
    """Static check: the desktop cannot be exercised here (Qt has no display), so the
    widget-selection logic is asserted from source instead of by clicking it."""
    import ast
    import pathlib

    source = pathlib.Path("apps/desktop_app/main.py").read_text(encoding="utf-8")
    assert "from make_my_figure_core import ui_hints" in source
    assert "ui_hints.is_multi_column(field)" in source, (
        "the column-role loop must give multi-column roles a multi-select widget")
    assert "_multi_col_widgets" in source, "collected values must reach the mapping"
    ast.parse(source)   # the module must at least be syntactically valid
