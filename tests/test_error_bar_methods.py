"""The ``error`` control must draw the interval it names.

An author who picks "sd" and silently gets SEM-sized bars has published a wrong
figure, and nothing on the page says so. These tests therefore measure the
*drawn* geometry - the error-bar segments and the band polygon - against the
statistic computed by hand, rather than only checking that the figure changed.

The 95% interval here is the normal approximation ``1.96 * SEM`` that
``base.summarize_error`` has always used; the t-based interval lives in the
statistics module and is a different convention, not this one.
"""
import matplotlib
matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest

from make_my_figure_core import ui_hints
from make_my_figure_core.plots.registry import make_spec, render

# 1.96 is the multiplier base.summarize_error uses; the tests assert against the
# same convention rather than inventing a t critical value of their own.
Z95 = 1.96


def _stats(values):
    """``(mean, sd, sem)`` with the ddof=1 sd the renderers use."""
    arr = np.asarray(values, dtype=float)
    sd = float(np.std(arr, ddof=1))
    return float(np.mean(arr)), sd, sd / np.sqrt(arr.size)


def _bar_half_errors(ax):
    """Half-height of each drawn error bar, in data units, in bar order."""
    out = []
    for container in ax.containers:
        errorbar = getattr(container, "errorbar", None)
        if errorbar is None:
            continue
        segments = errorbar[2][0].get_segments()
        out.append([float(seg[1][1] - seg[0][1]) / 2.0 for seg in segments])
    return out


def _bar_frame():
    # Small integer replicates so the expected sd/sem are exact, not fitted.
    return pd.DataFrame({
        "condition": ["Control"] * 5 + ["Drug"] * 5,
        "measurement": [1.0, 2.0, 3.0, 4.0, 5.0, 10.0, 12.0, 14.0, 16.0, 18.0],
    })


def _bar_spec(method):
    return make_spec("barplot_with_error_bar", "t.csv", "publication",
                     mapping={"x": "condition", "y": "measurement", "error": method})


@pytest.mark.parametrize("method", ["sem", "sd", "ci95"])
def test_barplot_error_bars_match_the_named_statistic(method):
    df = _bar_frame()
    result = render(_bar_spec(method), df)
    ax = result.figure.axes[0]
    drawn = _bar_half_errors(ax)
    assert drawn, "the bar plot drew no error bars"
    drawn = drawn[0]

    expected = []
    for condition in ("Control", "Drug"):
        mean, sd, sem = _stats(df.loc[df.condition == condition, "measurement"])
        expected.append({"sem": sem, "sd": sd, "ci95": Z95 * sem}[method])

    assert drawn == pytest.approx(expected)
    assert result.metadata["error_method"] == method
    # The bar tops are the mean whichever interval was asked for.
    assert result.metadata["centers"] == pytest.approx([3.0, 14.0])


def test_barplot_error_choices_are_distinct_and_ordered():
    """SEM < 95% CI < SD for n=5, so the three choices cannot be confused."""
    drawn = {m: _bar_half_errors(render(_bar_spec(m), _bar_frame()).figure.axes[0])[0][0]
             for m in ("sem", "ci95", "sd")}
    assert drawn["sem"] < drawn["ci95"] < drawn["sd"]
    # ci95 is exactly the SEM scaled by the multiplier the codebase uses
    assert drawn["ci95"] == pytest.approx(Z95 * drawn["sem"])
    # and SEM is the SD divided by sqrt(n)
    assert drawn["sem"] == pytest.approx(drawn["sd"] / np.sqrt(5))


def test_barplot_error_none_draws_no_bars_and_leaves_the_label_clean():
    result = render(_bar_spec("none"), _bar_frame())
    ax = result.figure.axes[0]
    assert _bar_half_errors(ax) == []
    assert "mean" not in ax.get_ylabel()


def _grouped_frame():
    rows = []
    values = {("WT", "Vehicle"): [1.0, 2.0, 3.0, 4.0, 5.0],
              ("WT", "Drug"): [2.0, 4.0, 6.0, 8.0, 10.0],
              ("KO", "Vehicle"): [1.0, 1.5, 2.0, 2.5, 3.0],
              ("KO", "Drug"): [5.0, 10.0, 15.0, 20.0, 25.0]}
    for (genotype, treatment), vals in values.items():
        for value in vals:
            rows.append({"genotype": genotype, "treatment": treatment, "expression": value})
    return pd.DataFrame(rows), values


@pytest.mark.parametrize("method", ["sem", "sd", "ci95"])
def test_grouped_barplot_error_bars_match_the_named_statistic(method):
    df, values = _grouped_frame()
    spec = make_spec("grouped_barplot_with_error_bar", "t.csv", "publication",
                     mapping={"x": "genotype", "group": "treatment",
                              "y": "expression", "error": method})
    result = render(spec, df)
    drawn = _bar_half_errors(result.figure.axes[0])
    # One container per treatment group, each holding one bar per genotype.
    assert len(drawn) == 2

    for gi, treatment in enumerate(("Vehicle", "Drug")):
        for xi, genotype in enumerate(("WT", "KO")):
            mean, sd, sem = _stats(values[(genotype, treatment)])
            expected = {"sem": sem, "sd": sd, "ci95": Z95 * sem}[method]
            assert drawn[gi][xi] == pytest.approx(expected), f"{genotype}/{treatment}"
    assert result.metadata["error_method"] == method


def test_grouped_barplot_error_none_draws_no_bars():
    df, _ = _grouped_frame()
    spec = make_spec("grouped_barplot_with_error_bar", "t.csv", "publication",
                     mapping={"x": "genotype", "group": "treatment",
                              "y": "expression", "error": "none"})
    assert _bar_half_errors(render(spec, df).figure.axes[0]) == []


def _band_frame():
    rows = []
    # Two timepoints, five replicates, deliberately skewed at t=1 so the mean and
    # the median differ - that is what separates the symmetric methods from the
    # order statistics.
    values = {0: [1.0, 2.0, 3.0, 4.0, 5.0], 1: [10.0, 11.0, 12.0, 13.0, 40.0]}
    for time, vals in values.items():
        for value in vals:
            rows.append({"time": time, "signal": value})
    return pd.DataFrame(rows), values


def _band_spec(method):
    return make_spec("lineplot_timecourse_with_error_band", "t.csv", "publication",
                     mapping={"x": "time", "y": "signal", "error": method})


def _band_at(ax, xv):
    """``(low, high)`` of the drawn band at one x position."""
    fills = [c for c in ax.collections if c.get_paths()]
    assert len(fills) == 1, f"expected one band, found {len(fills)}"
    vertices = fills[0].get_paths()[0].vertices
    ys = vertices[np.isclose(vertices[:, 0], float(xv)), 1]
    return float(ys.min()), float(ys.max())


@pytest.mark.parametrize("method", ["sem", "sd", "ci95"])
def test_lineplot_band_matches_the_named_statistic(method):
    df, values = _band_frame()
    result = render(_band_spec(method), df)
    ax = result.figure.axes[0]
    for time in (0, 1):
        mean, sd, sem = _stats(values[time])
        half = {"sem": sem, "sd": sd, "ci95": Z95 * sem}[method]
        low, high = _band_at(ax, time)
        assert low == pytest.approx(mean - half), f"t={time} lower"
        assert high == pytest.approx(mean + half), f"t={time} upper"
    # Symmetric methods centre the line on the mean, not the median.
    line = ax.get_lines()[0]
    assert list(line.get_ydata()) == pytest.approx([np.mean(values[0]), np.mean(values[1])])
    assert result.metadata["error_method"] == method


def test_lineplot_band_order_statistics_are_median_centred():
    df, values = _band_frame()
    for method, expected in (("iqr", {0: (2.0, 4.0), 1: (11.0, 13.0)}),
                             ("range", {0: (1.0, 5.0), 1: (10.0, 40.0)})):
        result = render(_band_spec(method), df)
        ax = result.figure.axes[0]
        for time in (0, 1):
            assert _band_at(ax, time) == pytest.approx(expected[time]), f"{method} t={time}"
        line = ax.get_lines()[0]
        assert list(line.get_ydata()) == pytest.approx(
            [np.median(values[0]), np.median(values[1])])


def test_lineplot_error_none_draws_no_band():
    df, _ = _band_frame()
    ax = render(_band_spec("none"), df).figure.axes[0]
    assert [c for c in ax.collections if c.get_paths()] == []


@pytest.mark.parametrize("plot_type,expected", [
    ("barplot_with_error_bar", ["sem", "sd", "ci95", "none"]),
    ("grouped_barplot_with_error_bar", ["sem", "sd", "ci95", "none"]),
    ("lineplot_timecourse_with_error_band",
     ["sem", "sd", "ci95", "iqr", "range", "none"]),
])
def test_every_offered_error_choice_is_one_the_renderer_understands(plot_type, expected):
    """No choice may fall through to summarize_error's unknown-method default.

    That fallback silently returns SEM, so an offered-but-unrecognised choice is
    exactly the failure mode these tests exist to rule out.
    """
    option = next(o for o in ui_hints.options(plot_type) if o.key == "error")
    assert option.choices == expected
    assert option.default == "sem"


def test_audit_sends_plot_options_to_the_mapping_block(monkeypatch):
    """Regression guard for the harness, not the renderers.

    ``Option.scope`` says whether a setting is portable between figures - it is
    what decides whether a *style preset* carries it. It does not say where in
    the PlotSpec the value lives: every per-plot-type option lives in ``mapping``.
    An earlier option-efficacy run read scope as a location and wrote every
    scope="style" option into spec["style"], where with_overrides drops any key
    it does not recognise, and so reported ``error`` and 130 other live controls
    as dead.
    """
    from quality_audit import option_efficacy

    seen = {"mapping": set(), "style": set()}

    def fake_digest(plot_type, spec_patch=None, style_patch=None, layout_patch=None):
        seen["mapping"].update(spec_patch or {})
        seen["style"].update(style_patch or {})
        return np.zeros((2, 2, 4), dtype=np.float32)

    monkeypatch.setattr(option_efficacy, "_digest", fake_digest)
    monkeypatch.setattr(option_efficacy, "_elements_present", lambda pt: set())
    option_efficacy.audit_plot_type("barplot_with_error_bar")

    assert "error" in seen["mapping"]
    assert "error" not in seen["style"]


# --------------------------------------------------------------------------
# The statistic must not travel in a shared style
# --------------------------------------------------------------------------

ERROR_BAR_PLOTS = ["barplot_with_error_bar", "grouped_barplot_with_error_bar",
                   "lineplot_timecourse_with_error_band"]


@pytest.mark.parametrize("plot_type", ERROR_BAR_PLOTS)
def test_the_error_statistic_is_analysis_not_appearance(plot_type):
    """It was declared scope="style", so a style preset carried it.

    SEM, SD and CI95 bars are drawn identically - only the number differs - so a
    lab's shared "Default Barplot" style could turn a colleague's SD bars into
    SEM with nothing on the figure to show it had happened. Appearance travels
    between figures; what the error bar measures does not.
    """
    from make_my_figure_core import ui_hints

    option = next(o for o in ui_hints.options(plot_type) if o.key == "error")
    assert option.scope == "config", (
        f"{plot_type}: the error statistic is declared {option.scope!r}, so it "
        f"would be carried by a shareable style preset")


@pytest.mark.parametrize("plot_type", ERROR_BAR_PLOTS)
def test_a_style_preset_does_not_carry_the_error_statistic(plot_type):
    """The scope declaration is only worth anything if the splitter honours it."""
    from make_my_figure_core import presets

    split = presets.split_mapping(plot_type, {"error": "sd"})
    style_options = dict(getattr(split, "style_options", {}) or {})
    config_options = dict(getattr(split, "config_options", {}) or {})
    assert "error" not in style_options, (
        f"{plot_type}: a style preset would carry error={style_options['error']!r}")
    assert config_options.get("error") == "sd", (
        f"{plot_type}: the statistic must still travel in a full configuration")
