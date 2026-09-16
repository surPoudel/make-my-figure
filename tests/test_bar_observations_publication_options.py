"""Publication "bar + individual observations" mode for the two bar renderers.

Covers: unchanged default render; explicit summary/error recording (mean/median, sem/sd/ci95/
ci95_t/iqr); every observation drawn for equal and unequal designs; outline fill; horizontal
orientation; n labels; brackets clearing points and whiskers; and the style/config split of the
new options through a Figure Preset round-trip.
"""

from __future__ import annotations

import io
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from matplotlib.collections import PathCollection
from matplotlib.container import ErrorbarContainer

from make_my_figure_core import presets as P
from make_my_figure_core.plots.base import RenderError
from make_my_figure_core.plots.registry import make_spec, render

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "examples" / "group_comparison_test_data"
BAR = "barplot_with_error_bar"
GROUPED = "grouped_barplot_with_error_bar"


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


def _df(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / f"{name}.csv")


def _bar_spec(name: str, mapping=None, **kw):
    m = {"x": "group", "y": "value"}
    m.update(mapping or {})
    return make_spec(BAR, f"{name}.csv", "publication", mapping=m, **kw)


def _grouped_spec(mapping=None, **kw):
    m = {"x": "subgroup", "group": "group", "y": "value"}
    m.update(mapping or {})
    return make_spec(GROUPED, "two_by_three.csv", "publication", mapping=m, **kw)


def _scatters(ax):
    return [c for c in ax.collections if isinstance(c, PathCollection)]


def _brackets(ax):
    """Bracket polylines drawn by the stats overlay (four vertices each)."""
    return [ln for ln in ax.lines if len(ln.get_xdata()) == 4]


def _errorbars(ax) -> ErrorbarContainer:
    return next(c for c in ax.containers if isinstance(c, ErrorbarContainer))


def _tick_texts(ax, axis: str = "x"):
    """Tick label text with the auto-rotation's line wrapping normalised to single spaces."""
    labels = ax.get_xticklabels() if axis == "x" else ax.get_yticklabels()
    return [" ".join(t.get_text().split()) for t in labels]


def _png(fig) -> np.ndarray:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=80)
    buf.seek(0)
    return plt.imread(buf)


# --------------------------------------------------------------------------------------
# defaults are unchanged
# --------------------------------------------------------------------------------------

def test_default_render_is_the_historical_bar_chart():
    res = render(_bar_spec("unequal_4_9_13"), _df("unequal_4_9_13"))
    ax = res.figure.axes[0]
    assert _scatters(ax) == []                                   # no points by default
    assert all(abs(p.get_width() - 0.68) < 1e-9 for p in ax.patches)
    assert ax.get_ylabel() == "value (mean ± SEM)"
    assert ax.get_ylim()[0] == 0.0
    assert ax.get_legend() is None
    meta = res.metadata
    assert meta["summary"] == "mean" and meta["error"] == "sem"
    assert meta["error_method"] == "sem"                         # historical key kept
    assert meta["group_n"] == {"Control": 4, "Low": 9, "High": 13}
    assert meta["baseline_zero"] is True and meta["points"] is False
    assert meta["orientation"] == "vertical"
    assert res.warnings == []


def test_explicit_defaults_render_identically_to_no_options():
    df = _df("unequal_4_9_13")
    plain = _png(render(_bar_spec("unequal_4_9_13"), df).figure)
    explicit = _png(render(_bar_spec("unequal_4_9_13", {
        "summary": "mean", "error": "sem", "points": False, "bar_width": 0.68, "bar_fill": "filled",
        "bar_edge_width": 0, "bar_alpha": 1.0, "error_cap": True, "show_n": "none",
        "orientation": "vertical"}), df).figure)
    assert plain.shape == explicit.shape and np.array_equal(plain, explicit)


def test_grouped_default_metadata_records_summary_and_cell_n():
    res = render(_grouped_spec(), _df("two_by_three"))
    meta = res.metadata
    assert meta["summary"] == "mean" and meta["error"] == "sem" and meta["error_method"] == "sem"
    assert set(meta["group_n"]) == {f"{a}|{g}" for a in ("Young", "Adult", "Old")
                                    for g in ("Control", "Treatment")}
    assert all(n == 6 for n in meta["group_n"].values())
    assert _scatters(res.figure.axes[0]) == []


# --------------------------------------------------------------------------------------
# explicit summary / error
# --------------------------------------------------------------------------------------

def test_median_bars_differ_from_mean_bars_and_are_recorded():
    df = _df("unequal_4_9_13")
    mean = render(_bar_spec("unequal_4_9_13"), df)
    median = render(_bar_spec("unequal_4_9_13", {"summary": "median", "error": "iqr"}), df)
    assert median.metadata["summary"] == "median" and median.metadata["error"] == "iqr"
    assert median.metadata["centers"] != mean.metadata["centers"]
    for cat, c in zip(median.metadata["categories"], median.metadata["centers"]):
        assert c == pytest.approx(float(df.loc[df.group == cat, "value"].median()), abs=1e-6)
    heights_mean = [p.get_height() for p in mean.figure.axes[0].patches]
    heights_median = [p.get_height() for p in median.figure.axes[0].patches]
    assert heights_mean != heights_median
    assert median.figure.axes[0].get_ylabel() == "value (median, IQR)"
    assert "interquartile" in median.metadata["error_definition"]


def test_median_with_sem_is_corrected_to_iqr_and_reported():
    res = render(_bar_spec("unequal_4_9_13", {"summary": "median", "error": "sem"}), _df("unequal_4_9_13"))
    assert res.metadata["error"] == "iqr"
    assert res.metadata["error_requested"] == "sem"
    assert any("summary=median" in w and "iqr" in w for w in res.warnings)


@pytest.mark.parametrize("error,definition", [
    ("sem", "standard error"), ("sd", "standard deviation"),
    ("ci95", "normal approximation"), ("ci95_t", "t-based"), ("none", "no error bars"),
])
def test_error_choice_is_recorded_with_its_definition(error, definition):
    res = render(_bar_spec("n6", {"error": error}), _df("n6"))
    assert res.metadata["error"] == error and res.metadata["error_method"] == error
    assert definition in res.metadata["error_definition"]
    assert "error_requested" not in res.metadata


def test_ci95_keeps_normal_approximation_and_ci95_t_is_wider_for_small_n():
    """Changing ``ci95`` would alter existing figures, so the t interval is the new ``ci95_t``."""
    from scipy import stats as st

    df = _df("n3")
    vals = df.loc[df.group == "Control", "value"].to_numpy(float)
    sem = vals.std(ddof=1) / np.sqrt(len(vals))
    r_norm = render(_bar_spec("n3", {"error": "ci95"}), df)
    r_t = render(_bar_spec("n3", {"error": "ci95_t"}), df)

    def whisker_top(res):
        segs = _errorbars(res.figure.axes[0]).lines[2][0].get_segments()
        return float(segs[0][:, 1].max())

    assert whisker_top(r_norm) == pytest.approx(vals.mean() + 1.96 * sem, rel=1e-6)
    assert whisker_top(r_t) == pytest.approx(vals.mean() + st.t.ppf(0.975, 2) * sem, rel=1e-6)
    assert whisker_top(r_t) > whisker_top(r_norm)
    assert r_t.figure.axes[0].get_ylabel() == "value (mean ± 95% CI, t)"
    assert r_norm.figure.axes[0].get_ylabel() == "value (mean ± CI95)"    # historical label


# --------------------------------------------------------------------------------------
# observations
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["n3", "n4", "n6", "n10", "n20", "n50",
                                  "unequal_4_9_13", "unequal_6_vs_17", "unequal_5_vs_8"])
def test_every_observation_is_drawn_per_group(name):
    df = _df(name)
    res = render(_bar_spec(name, {"points": True}), df)
    ax = res.figure.axes[0]
    scatters = _scatters(ax)
    categories = res.metadata["categories"]
    assert len(scatters) == len(categories)
    for i, (cat, coll) in enumerate(zip(categories, scatters)):
        offsets = coll.get_offsets()
        expected = df.loc[df.group == cat, "value"].to_numpy(float)
        assert len(offsets) == len(expected) == res.metadata["group_n"][cat]
        assert np.allclose(np.sort(offsets[:, 1]), np.sort(expected))      # values, untouched
        assert np.all(np.abs(offsets[:, 0] - i) <= 0.34 + 1e-9)            # inside the bar
        assert coll.get_zorder() > max(p.get_zorder() for p in ax.patches)   # above the bars
    assert res.metadata["n_observations_drawn"] == len(df)
    assert res.metadata["points"] is True
    # the value axis reaches every point
    assert ax.get_ylim()[1] >= df.value.max()
    assert ax.get_ylim()[0] <= min(0.0, df.value.min())


def test_dense_group_suggestion_is_surfaced_as_a_warning_and_nothing_is_dropped():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"group": ["A"] * 80 + ["B"] * 6,
                       "value": np.r_[rng.normal(1, 0.2, 80), rng.normal(2, 0.2, 6)]})
    res = render(_bar_spec("dense", {"points": True}), df)
    assert any("80 observations" in w for w in res.warnings)
    assert [len(c.get_offsets()) for c in _scatters(res.figure.axes[0])] == [80, 6]


def test_grouped_points_sit_on_the_dodged_bars():
    df = _df("two_by_three")
    res = render(_grouped_spec({"points": True}), df)
    ax = res.figure.axes[0]
    scatters = _scatters(ax)
    assert len(scatters) == 6 and all(len(c.get_offsets()) == 6 for c in scatters)
    bar_centres = sorted(p.get_x() + p.get_width() / 2 for p in ax.patches)
    point_centres = sorted(float(c.get_offsets()[:, 0].mean()) for c in scatters)
    assert np.allclose(bar_centres, point_centres, atol=0.12)
    assert res.metadata["n_observations_drawn"] == 36


# --------------------------------------------------------------------------------------
# bar appearance
# --------------------------------------------------------------------------------------

def test_outline_fill_draws_white_bars_with_coloured_edges():
    res = render(_bar_spec("two_groups_n6", {"bar_fill": "outline", "bar_edge_width": 1.4}), _df("two_groups_n6"))
    ax = res.figure.axes[0]
    faces = [tuple(p.get_facecolor()[:3]) for p in ax.patches]
    edges = [tuple(p.get_edgecolor()[:3]) for p in ax.patches]
    assert all(f == (1.0, 1.0, 1.0) for f in faces)
    assert len(set(edges)) == 2 and (1.0, 1.0, 1.0) not in edges
    assert all(abs(p.get_linewidth() - 1.4) < 1e-9 for p in ax.patches)
    assert res.metadata["bar_fill"] == "outline"


def test_bar_width_alpha_and_cap_options_reach_the_artists():
    df = _df("two_groups_n6")
    res = render(_bar_spec("two_groups_n6", {"bar_width": 0.4, "bar_alpha": 0.5, "error_cap": False}), df)
    ax = res.figure.axes[0]
    assert all(abs(p.get_width() - 0.4) < 1e-9 for p in ax.patches)
    assert all(abs(p.get_alpha() - 0.5) < 1e-9 for p in ax.patches)
    assert len(_errorbars(ax).lines[1]) == 0                        # no caplines
    res_cap = render(_bar_spec("two_groups_n6"), df)
    assert len(_errorbars(res_cap.figure.axes[0]).lines[1]) == 2    # top + bottom caps


def test_color_role_colours_bars_by_a_second_column_with_a_legend():
    df = _df("unequal_4_9_13")
    df["arm"] = np.where(df["group"] == "Control", "vehicle", "drug")
    res = render(_bar_spec("unequal_4_9_13", {"color": "arm"}), df)
    ax = res.figure.axes[0]
    faces = [tuple(np.round(p.get_facecolor()[:3], 4)) for p in ax.patches]
    assert faces[1] == faces[2] != faces[0]
    assert [t.get_text() for t in ax.get_legend().get_texts()] == ["vehicle", "drug"]
    assert res.metadata["color_by"] == "arm"
    missing = render(_bar_spec("unequal_4_9_13", {"color": "not_a_column"}), df)
    assert any("not in the table" in w for w in missing.warnings)
    assert missing.metadata["color_by"] == "group"


# --------------------------------------------------------------------------------------
# orientation
# --------------------------------------------------------------------------------------

def test_horizontal_bars_with_points_and_statistics():
    df = _df("two_groups_n6")
    res = render(_bar_spec("two_groups_n6", {"orientation": "horizontal", "points": True}),
                 df)
    ax = res.figure.axes[0]
    assert [t.get_text() for t in ax.get_yticklabels()] == ["Control", "Treatment"]
    assert all(abs(p.get_height() - 0.68) < 1e-9 for p in ax.patches)
    widths = sorted(p.get_width() for p in ax.patches)
    assert widths == pytest.approx(sorted(df.groupby("group")["value"].mean()), rel=1e-6)
    for i, coll in enumerate(_scatters(ax)):
        offsets = coll.get_offsets()
        assert np.all(np.abs(offsets[:, 1] - i) <= 0.34 + 1e-9)          # category axis is y
    assert ax.get_xlim()[0] == 0.0 and ax.get_xlim()[1] >= df.value.max()
    assert "(mean ± SEM)" in ax.get_xlabel()
    assert res.metadata["orientation"] == "horizontal"

    with_stats = render(_bar_spec("two_groups_n6", {"orientation": "horizontal", "points": True},
                                  statistics={"enabled": True, "test": "welch_t"}), df)
    assert with_stats.stats_report is not None and len(with_stats.stats_report.results) == 1
    ax2 = with_stats.figure.axes[0]
    brackets = _brackets(ax2)
    if brackets:
        # horizontal bracket: to the right of every drawn point
        assert min(min(ln.get_xdata()) for ln in brackets) >= df.value.max()
    else:
        assert any("corner text panel" in w for w in with_stats.warnings)


def test_grouped_horizontal_median_outline_renders():
    res = render(_grouped_spec({"orientation": "horizontal", "points": True, "bar_fill": "outline",
                                "summary": "median", "error": "iqr"}), _df("two_by_three"))
    ax = res.figure.axes[0]
    assert [t.get_text() for t in ax.get_yticklabels()] == ["Young", "Adult", "Old"]
    assert len(_scatters(ax)) == 6
    assert res.metadata["summary"] == "median" and res.metadata["error"] == "iqr"


# --------------------------------------------------------------------------------------
# n labels
# --------------------------------------------------------------------------------------

def test_show_n_below_above_and_legend():
    df = _df("unequal_4_9_13")
    below = render(_bar_spec("unequal_4_9_13", {"show_n": "below"}), df)
    assert _tick_texts(below.figure.axes[0]) == ["Control (n = 4)", "Low (n = 9)", "High (n = 13)"]
    assert len(below.figure.axes[0].texts) == 0                 # nothing drawn over the tick labels
    below_h = render(_bar_spec("unequal_4_9_13", {"show_n": "below", "orientation": "horizontal"}), df)
    assert _tick_texts(below_h.figure.axes[0], "y") == ["Control (n = 4)", "Low (n = 9)", "High (n = 13)"]

    above = render(_bar_spec("unequal_4_9_13", {"show_n": "above", "points": True}), df)
    ax = above.figure.axes[0]
    texts = {t.get_text(): t for t in ax.texts}
    assert set(texts) == {"n = 4", "n = 9", "n = 13"}
    # each label sits above the highest drawn value of its category
    for cat, n in above.metadata["group_n"].items():
        t = texts[f"n = {n}"]
        assert t.xy[1] >= df.loc[df.group == cat, "value"].max() - 1e-9

    legend = render(_bar_spec("unequal_4_9_13", {"show_n": "legend"}), df)
    leg = legend.figure.axes[0].get_legend()
    assert [t.get_text() for t in leg.get_texts()] == ["Control (n = 4)", "Low (n = 9)", "High (n = 13)"]
    assert legend.metadata["show_n"] == "legend"


def test_grouped_show_n_in_legend_and_tick_labels():
    df = _df("two_by_three")
    res = render(_grouped_spec({"show_n": "legend"}), df)
    leg = res.figure.axes[0].get_legend()
    assert [t.get_text() for t in leg.get_texts()] == ["Control (n = 6, 6, 6)", "Treatment (n = 6, 6, 6)"]
    below = render(_grouped_spec({"show_n": "below"}), df)
    assert _tick_texts(below.figure.axes[0]) == ["Young (n = 6)", "Adult (n = 6)", "Old (n = 6)"]


# --------------------------------------------------------------------------------------
# statistics brackets clear points and whiskers
# --------------------------------------------------------------------------------------

def _assert_brackets_clear_data(ax, df, categories):
    brackets = _brackets(ax)
    assert brackets, "no bracket drawn"
    tops = {}
    for i, cat in enumerate(categories):
        vals = df.loc[df.group == cat, "value"].to_numpy(float)
        whisker = vals.mean() + vals.std(ddof=1) / np.sqrt(len(vals))
        tops[i] = max(vals.max(), whisker)
    for ln in brackets:
        x1, x2 = sorted((min(ln.get_xdata()), max(ln.get_xdata())))
        spanned = [tops[i] for i in tops if x1 - 1e-6 <= i <= x2 + 1e-6]
        assert min(ln.get_ydata()) > max(spanned)
    assert ax.get_ylim()[1] > max(max(ln.get_ydata()) for ln in brackets)


def test_two_group_bracket_clears_points_and_error_bars():
    df = _df("two_groups_n6")
    res = render(_bar_spec("two_groups_n6", {"points": True}, statistics={"enabled": True, "test": "welch_t"}), df)
    _assert_brackets_clear_data(res.figure.axes[0], df, res.metadata["categories"])
    assert len(_brackets(res.figure.axes[0])) == 1
    info = res.stats_report.config["_annotation_info"]
    assert info["n_brackets"] == 1


def test_three_group_posthoc_brackets_clear_points_and_error_bars():
    df = _df("unequal_4_9_13")
    res = render(_bar_spec("unequal_4_9_13", {"points": True},
                           statistics={"enabled": True, "test": "auto", "posthoc": True,
                                       "annotation": {"show_nonsignificant": True}}), df)
    ax = res.figure.axes[0]
    _assert_brackets_clear_data(ax, df, res.metadata["categories"])
    assert len(_brackets(ax)) == 3
    assert any(r.comparison_type != "two_group" for r in res.stats_report.results)   # omnibus panel


def test_brackets_start_higher_when_points_are_shown():
    df = _df("two_groups_n6")
    stats = {"enabled": True, "test": "welch_t"}
    without = render(_bar_spec("two_groups_n6", statistics=stats), df)
    with_pts = render(_bar_spec("two_groups_n6", {"points": True}, statistics=stats), df)
    y_without = min(_brackets(without.figure.axes[0])[0].get_ydata())
    y_with = min(_brackets(with_pts.figure.axes[0])[0].get_ydata())
    assert y_with > y_without
    assert y_with > df.value.max()


def test_grouped_within_x_brackets_clear_points():
    df = _df("two_by_three")
    res = render(_grouped_spec({"points": True}, statistics={"enabled": True, "test": "welch_t",
                                                              "annotation": {"show_nonsignificant": True}}),
                 df)
    ax = res.figure.axes[0]
    brackets = _brackets(ax)
    assert len(brackets) == 3
    for ln, level in zip(sorted(brackets, key=lambda l: min(l.get_xdata())), ["Young", "Adult", "Old"]):
        assert min(ln.get_ydata()) > df.loc[df.subgroup == level, "value"].max()


# --------------------------------------------------------------------------------------
# axis policy
# --------------------------------------------------------------------------------------

def test_user_range_that_would_crop_points_is_refused_and_negative_data_drops_the_baseline():
    df = _df("two_groups_n6")
    with pytest.raises(RenderError, match="would hide data"):
        render(_bar_spec("two_groups_n6", {"points": True, "y_max": 0.5}), df)
    ok = render(_bar_spec("two_groups_n6", {"points": True, "y_max": 5}), df)
    assert ok.metadata["axis_overrides"]["y_limits"] == [0.0, 5.0]
    shifted = df.assign(value=df.value - 1.5)
    neg = render(_bar_spec("two_groups_n6", {"points": True}), shifted)
    assert neg.metadata["baseline_zero"] is False
    assert neg.figure.axes[0].get_ylim()[0] <= shifted.value.min()


# --------------------------------------------------------------------------------------
# presets: appearance travels, summary/error do not
# --------------------------------------------------------------------------------------

STYLE_OPTS = {"points": True, "point_arrangement": "beeswarm", "point_fill": "open", "bar_width": 0.5,
              "bar_fill": "outline", "bar_edge_width": 1.2, "bar_alpha": 0.9, "error_cap": False,
              "show_n": "below", "orientation": "horizontal"}


@pytest.mark.parametrize("plot_type", [BAR, GROUPED])
def test_style_preset_round_trips_appearance_but_not_summary_or_error(plot_type):
    roles = {"x": "group", "y": "value"} if plot_type == BAR else {"x": "subgroup", "group": "group", "y": "value"}
    spec = make_spec(plot_type, "a.csv", "publication",
                     mapping={**roles, **STYLE_OPTS, "summary": "median", "error": "iqr"})
    style = P.extract_preset(spec, mode="style", name="bars with dots")
    for k, v in STYLE_OPTS.items():
        assert style["options"][k] == v, k
    assert "summary" not in style["options"] and "error" not in style["options"]
    scopes = P.option_scopes(plot_type)
    assert scopes["summary"] == "config" and scopes["error"] == "config"
    assert all(scopes[k] == "style" for k in STYLE_OPTS)

    fresh = make_spec(plot_type, "b.csv", "publication", mapping=roles)
    res = P.apply_preset(style, fresh, columns=list(roles.values()))
    for k, v in STYLE_OPTS.items():
        assert res.spec["mapping"][k] == v, k
    assert "summary" not in res.spec["mapping"] and "error" not in res.spec["mapping"]
    assert res.skipped == []

    full = P.extract_preset(spec, mode="full")
    assert full["config_options"]["summary"] == "median" and full["config_options"]["error"] == "iqr"

    # and the applied style preset renders
    df = _df("two_groups_n6") if plot_type == BAR else _df("two_by_three")
    out = render(res.spec, df)
    assert out.metadata["summary"] == "mean" and out.metadata["error"] == "sem"   # not carried
    assert out.metadata["orientation"] == "horizontal" and out.metadata["bar_fill"] == "outline"
    assert _scatters(out.figure.axes[0])
