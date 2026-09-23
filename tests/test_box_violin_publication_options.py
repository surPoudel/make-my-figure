"""Publication options of ``boxplot_or_violin_with_points``.

Covers: the default render is the historical one; every new option renders; unequal and arbitrary n
are drawn in full (one marker per observation); horizontal orientation; a ``hue`` column dodges
with a legend and within-x statistics; category order; n labels; statistics brackets clear the
highest drawn point; and the new style options travel in a Figure style preset.
"""

from __future__ import annotations

import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from matplotlib.collections import PathCollection

from make_my_figure_core import presets as P
from make_my_figure_core import ui_hints
from make_my_figure_core.plots.base import RenderError
from make_my_figure_core.plots.registry import make_spec, render
from make_my_figure_core.styles.capabilities import get_style_capabilities

PT = "boxplot_or_violin_with_points"
DATA = pathlib.Path(__file__).resolve().parent.parent / "examples" / "group_comparison_test_data"


@pytest.fixture(autouse=True)
def _close():
    yield
    plt.close("all")


def _df(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / f"{name}.csv")


def _spec(mapping=None, statistics=None):
    spec = make_spec(PT, "t.csv", "publication", mapping={"x": "group", "y": "value", **(mapping or {})})
    if statistics:
        spec["statistics"] = statistics
    return spec


def _render(mapping=None, data="three_groups_unequal", statistics=None):
    return render(_spec(mapping, statistics), _df(data))


def _point_collections(ax):
    """The scatter collections drawn by the observation helper, in drawing order."""
    return [c for c in ax.collections if isinstance(c, PathCollection) and len(c.get_offsets())]


def _brackets(ax):
    """Bracket polylines drawn by the statistics overlay: 4 vertices, vertical ticks at both ends."""
    out = []
    for ln in ax.lines:
        xs, ys = np.asarray(ln.get_xdata(), float), np.asarray(ln.get_ydata(), float)
        if len(xs) == 4 and xs[0] == xs[1] and xs[2] == xs[3] and xs[0] != xs[2] and ys[1] == ys[2]:
            out.append((xs, ys))
    return out


def _max_point_value(ax) -> float:
    return max(float(c.get_offsets()[:, 1].max()) for c in _point_collections(ax))


# --- default render ---------------------------------------------------------------------------

def test_default_render_is_the_historical_box_plot():
    df = _df("three_groups_unequal")
    res = render(_spec(), df)
    ax = res.figure.axes[0]
    groups = list(dict.fromkeys(df["group"]))
    assert res.metadata["kind"] == "box"
    assert res.metadata["orientation"] == "vertical"
    assert res.metadata["groups"] == groups
    assert res.metadata["group_n"] == {g: int((df["group"] == g).sum()) for g in groups}
    # positions 1..n, managed-box-plot limits, category names as tick labels, no legend
    assert list(ax.get_xticks()) == [1.0, 2.0, 3.0]
    assert [t.get_text() for t in ax.get_xticklabels()] == groups
    assert ax.get_xlim() == (0.5, 3.5)
    assert ax.get_legend() is None
    assert ax.get_xlabel() == "group" and ax.get_ylabel() == "value"
    # boxes 0.5 wide, palette fill at 0.5 alpha with black edges (legacy look)
    boxes = ax.patches
    assert len(boxes) == 3
    for box in boxes:
        ext = box.get_path().get_extents()
        assert abs((ext.x1 - ext.x0) - 0.5) < 1e-9
        assert box.get_alpha() == 0.5
        assert matplotlib.colors.to_hex(box.get_edgecolor()) == "#000000"
    # one marker per observation, in group order
    assert [len(c.get_offsets()) for c in _point_collections(ax)] == [5, 8, 11]
    # no forced zero baseline
    assert ax.get_ylim()[0] > 0.0
    assert res.warnings == []


def test_legacy_point_size_is_honoured_exactly():
    for size in (4.0, 40.0):
        ax = _render({"points": True, "point_size": size}).figure.axes[0]
        sizes = {float(s) for c in _point_collections(ax) for s in c.get_sizes()}
        assert sizes == {size}


def test_default_point_size_is_adaptive_and_bounded():
    small = _render({}, data="n3").figure.axes[0]
    large = _render({}, data="n50").figure.axes[0]
    s_small = float(_point_collections(small)[0].get_sizes()[0])
    s_large = float(_point_collections(large)[0].get_sizes()[0])
    assert s_small > s_large >= 3.0


def test_legacy_outlier_coupling_and_independent_toggle():
    df = _df("one_extreme_observation")
    # points shown -> no fliers (historical coupling)
    ax = render(_spec(), df).figure.axes[0]
    fliers = [ln for ln in ax.lines if ln.get_linestyle() == "None" and len(ln.get_xdata())]
    assert fliers == []
    # points hidden -> fliers (historical coupling)
    ax = render(_spec({"points": False}), df).figure.axes[0]
    assert any(ln.get_linestyle() == "None" and len(ln.get_xdata()) for ln in ax.lines)
    # explicit: points shown AND outliers marked
    res = render(_spec({"show_outliers": True}), df)
    ax = res.figure.axes[0]
    assert any(ln.get_linestyle() == "None" and len(ln.get_xdata()) for ln in ax.lines)
    assert res.metadata["style"]["show_outliers"] is True
    # explicit: neither
    ax = render(_spec({"points": False, "show_outliers": False}), df).figure.axes[0]
    assert not any(ln.get_linestyle() == "None" and len(ln.get_xdata()) for ln in ax.lines)


# --- every option renders -----------------------------------------------------------------------

_OPTION_CASES = [
    {"kind": "violin"}, {"kind": "box+violin"}, {"kind": "summary"},
    {"point_arrangement": "centered"}, {"point_arrangement": "beeswarm"}, {"point_jitter_width": 0.7},
    {"point_marker": "D"}, {"point_fill": "open"}, {"point_edge": "same"}, {"point_edge": "none"},
    {"point_edge_width": 1.2}, {"point_alpha": 0.4},
    {"box_width": 0.2}, {"box_width": 0.9}, {"box_fill": "filled"}, {"box_fill": "outline"},
    {"box_line_width": 2.5}, {"median_line_width": 3.0}, {"whisker_cap_width": 0.0},
    {"whisker_cap_width": 1.0}, {"show_outliers": True}, {"violin_alpha": 0.9, "kind": "violin"},
    {"orientation": "horizontal"}, {"group_spacing": 1.8}, {"group_spacing": 0.5},
    {"category_order": "alphabetical"}, {"category_order": "median_descending"},
    {"show_n": "below"}, {"show_n": "above"}, {"show_n": "legend"},
    {"kind": "summary", "orientation": "horizontal", "box_fill": "outline", "show_n": "above"},
]


@pytest.mark.parametrize("mapping", _OPTION_CASES, ids=[str(m) for m in _OPTION_CASES])
def test_every_new_option_renders(mapping):
    res = _render(mapping)
    assert res.figure.axes
    assert sorted(len(c.get_offsets()) for c in _point_collections(res.figure.axes[0])) == [5, 8, 11]


def test_every_declared_option_is_read_by_the_renderer():
    """Each ui_hints option flipped away from its default changes the metadata or the drawing."""
    base = _render({})
    base_ax = base.figure.axes[0]
    for opt in ui_hints.options(PT):
        if opt.kind == "choice":
            value = [c for c in opt.choices if c != opt.default][0]
        elif opt.kind == "bool":
            value = not bool(opt.default)
        else:
            value = float(opt.maximum)
        res = _render({opt.key: value})
        # renders and either records the option or changes what is drawn
        ax = res.figure.axes[0]
        changed = (res.metadata != base.metadata
                   or len(ax.collections) != len(base_ax.collections)
                   or len(ax.lines) != len(base_ax.lines)
                   or ax.get_legend() is not None)
        assert changed, opt.key


def test_option_scopes_are_declared_as_specified():
    scopes = {o.key: o.scope for o in ui_hints.options(PT)}
    for key in ("kind", "points", "point_arrangement", "point_jitter_width", "point_size", "point_marker",
                "point_fill", "point_edge", "point_edge_width", "point_alpha", "box_width", "box_fill",
                "box_line_width", "median_line_width", "whisker_cap_width", "show_outliers",
                "violin_alpha", "orientation", "group_spacing", "show_n", "x_tick_rotation"):
        assert scopes[key] == "style", key
    assert scopes["category_order"] == "config"
    assert "hue" in ui_hints.column_fields(PT)
    caps = get_style_capabilities(PT)
    assert caps.supports_legend and caps.supports_marker_size


# --- n comes from the data ----------------------------------------------------------------------

@pytest.mark.parametrize("name", ["three_groups_unequal", "unequal_6_vs_17", "unequal_4_9_13", "n3", "n50",
                                  "two_groups_n30"])
@pytest.mark.parametrize("kind", ["box", "violin", "box+violin", "summary"])
def test_unequal_and_arbitrary_n_are_drawn_in_full(name, kind):
    df = _df(name)
    res = render(_spec({"kind": kind}), df)
    ax = res.figure.axes[0]
    counts = df.groupby("group", sort=False)["value"].count()
    drawn = _point_collections(ax)
    assert [len(c.get_offsets()) for c in drawn] == [int(counts[g]) for g in res.metadata["groups"]]
    # every drawn value is a data value; nothing is thinned or invented
    for g, coll in zip(res.metadata["groups"], drawn):
        assert np.allclose(np.sort(coll.get_offsets()[:, 1]), np.sort(df.loc[df["group"] == g, "value"]))
    assert res.metadata["group_n"] == {g: int(counts[g]) for g in res.metadata["groups"]}


def test_dense_group_gets_a_suggestion_not_thinning():
    df = pd.DataFrame({"group": ["a"] * 120 + ["b"] * 120, "value": np.random.default_rng(1).normal(size=240)})
    res = render(_spec(), df)
    assert [len(c.get_offsets()) for c in _point_collections(res.figure.axes[0])] == [120, 120]
    assert any("observations" in w for w in res.warnings)


# --- orientation ------------------------------------------------------------------------------

def test_horizontal_orientation_swaps_axes_consistently():
    df = _df("three_groups_unequal")
    res = render(_spec({"orientation": "horizontal"}), df)
    ax = res.figure.axes[0]
    groups = res.metadata["groups"]
    assert res.metadata["orientation"] == "horizontal"
    assert [t.get_text() for t in ax.get_yticklabels()] == groups
    assert list(ax.get_yticks()) == [1.0, 2.0, 3.0]
    assert ax.get_xlabel() == "value" and ax.get_ylabel() == "group"
    # observations lie along x at the value, around the category position on y
    for pos, g, coll in zip((1, 2, 3), groups, _point_collections(ax)):
        off = coll.get_offsets()
        assert np.allclose(np.sort(off[:, 0]), np.sort(df.loc[df["group"] == g, "value"]))
        assert np.all(np.abs(off[:, 1] - pos) < 0.5)
    # boxes are horizontal: their vertical extent is the box width
    for box in ax.patches:
        ext = box.get_path().get_extents()
        assert abs((ext.y1 - ext.y0) - 0.5) < 1e-9
    # first category reads at the top
    lo, hi = ax.get_ylim()
    assert lo > hi


def test_horizontal_statistics_fall_back_to_a_text_panel_with_a_warning():
    res = render(_spec({"orientation": "horizontal"}, {"enabled": True, "test": "welch_t"}), _df("unequal_6_vs_17"))
    ax = res.figure.axes[0]
    assert _brackets(ax) == []
    assert any("vertical orientation only" in w for w in res.warnings)
    assert res.metadata["statistics_annotation"] == "corner"
    panel = [t.get_text() for t in ax.texts if "vs" in t.get_text()]
    assert panel and panel[0].startswith("Control vs Treatment: ") and len(panel[0].split(": ", 1)[1]) > 0
    # with p-values requested, the panel carries them
    res_p = render(_spec({"orientation": "horizontal"},
                         {"enabled": True, "test": "welch_t", "annotation": {"content": "p"}}), _df("unequal_6_vs_17"))
    panel_p = [t.get_text() for t in res_p.figure.axes[0].texts if "vs" in t.get_text()]
    assert panel_p and "p" in panel_p[0].split(": ", 1)[1].lower()
    assert res.metadata["statistics_report"]["results"]


# --- hue ---------------------------------------------------------------------------------------

def test_hue_dodges_within_each_category_with_a_legend():
    df = _df("two_by_three")
    res = render(_spec({"hue": "subgroup"}), df)
    ax = res.figure.axes[0]
    assert res.metadata["hue"] == "subgroup"
    assert res.metadata["hue_levels"] == ["Young", "Adult", "Old"]
    assert res.metadata["groups"] == ["Control", "Treatment"]
    assert res.metadata["group_n"] == {"Control": 18, "Treatment": 18}
    assert res.metadata["group_n_by_hue"]["Control|Young"] == 6
    # 6 dodged boxes: three around x = 1, three around x = 2, none overlapping
    centres = sorted(0.5 * (b.get_path().get_extents().x0 + b.get_path().get_extents().x1) for b in ax.patches)
    assert len(centres) == 6
    assert all(abs(c - 1.0) < 0.4 for c in centres[:3]) and all(abs(c - 2.0) < 0.4 for c in centres[3:])
    assert min(np.diff(centres[:3])) > 0.2
    # one point collection per (x, hue) with the right n
    assert [len(c.get_offsets()) for c in _point_collections(ax)] == [6] * 6
    leg = ax.get_legend()
    assert leg is not None
    assert [t.get_text() for t in leg.get_texts()] == ["Young", "Adult", "Old"]
    assert leg.get_title().get_text() == "subgroup"
    assert [t.get_text() for t in ax.get_xticklabels()] == ["Control", "Treatment"]


def test_hue_legend_carries_n_when_requested():
    res = render(_spec({"hue": "subgroup", "show_n": "legend"}), _df("two_by_three"))
    leg = res.figure.axes[0].get_legend()
    assert [t.get_text() for t in leg.get_texts()] == ["Young (n = 12)", "Adult (n = 12)", "Old (n = 12)"]


def test_hue_within_x_statistics_bracket_the_dodged_pair():
    df = _df("two_by_three")
    res = render(_spec({"hue": "subgroup"}, {"enabled": True, "test": "welch_t", "comparison_mode": "within_x"}), df)
    ax = res.figure.axes[0]
    brackets = _brackets(ax)
    assert brackets, "no within-x brackets drawn"
    results = res.metadata["statistics_report"]["results"]
    assert all(r.get("extra", {}).get("within_x") for r in results)
    assert len(results) == 6      # 3 pairs within each of the 2 x levels
    for xs, ys in brackets:
        assert abs(xs[2] - xs[0]) < 0.8          # spans dodged elements, never whole clusters
        # a bracket clears every point of the cluster it sits in
        cluster_max = max(float(c.get_offsets()[:, 1].max()) for c in _point_collections(ax)
                          if abs(float(np.mean(c.get_offsets()[:, 0])) - np.mean(xs)) < 0.6)
        assert ys[0] > cluster_max


def test_hue_default_statistics_use_the_hue_as_subgroup():
    """A StatsSpec without an explicit subgroup_column still compares within x when hue is mapped."""
    from make_my_figure_core.statistics.runner import resolve_columns
    cols = resolve_columns(PT, {"x": "group", "y": "value", "hue": "subgroup"}, {})
    assert cols["group_column"] == "group" and cols["subgroup_column"] == "subgroup"
    cols = resolve_columns(PT, {"x": "group", "y": "value"}, {})
    assert cols["subgroup_column"] is None


# --- order, spacing, n labels ----------------------------------------------------------------

def test_category_order_options():
    df = _df("three_groups_unequal")
    med = df.groupby("group")["value"].median()
    assert render(_spec({"category_order": "data"}), df).metadata["groups"] == list(dict.fromkeys(df["group"]))
    assert render(_spec({"category_order": "alphabetical"}), df).metadata["groups"] == sorted(med.index)
    asc = render(_spec({"category_order": "median_ascending"}), df).metadata["groups"]
    assert asc == list(med.sort_values().index)
    desc = render(_spec({"category_order": "median_descending"}), df)
    assert desc.metadata["groups"] == asc[::-1]
    # the tick labels and the drawn observations follow the order
    ax = desc.figure.axes[0]
    assert [t.get_text() for t in ax.get_xticklabels()] == desc.metadata["groups"]
    for g, coll in zip(desc.metadata["groups"], _point_collections(ax)):
        assert len(coll.get_offsets()) == int((df["group"] == g).sum())
    assert desc.metadata["category_order"] == "median_descending"


def test_group_spacing_scales_positions():
    ax = _render({"group_spacing": 1.5}).figure.axes[0]
    assert list(ax.get_xticks()) == [1.0, 2.5, 4.0]
    assert ax.get_xlim() == (0.25, 4.75)
    for box in ax.patches:                      # width stays the box_width
        ext = box.get_path().get_extents()
        assert abs((ext.x1 - ext.x0) - 0.5) < 1e-9


def test_show_n_labels():
    below = _render({"show_n": "below"}).figure.axes[0]
    texts = [t.get_text() for t in below.texts]
    assert texts == ["n = 5", "n = 8", "n = 11"]
    above = _render({"show_n": "above"})
    ax = above.figure.axes[0]
    labels = [t for t in ax.texts if t.get_text().startswith("n = ")]
    assert [t.get_text() for t in labels] == ["n = 5", "n = 8", "n = 11"]
    for t, coll in zip(labels, _point_collections(ax)):
        assert t.xy[1] >= float(coll.get_offsets()[:, 1].max())
    legend = _render({"show_n": "legend"}).figure.axes[0].get_legend()
    assert [t.get_text() for t in legend.get_texts()] == ["Control (n = 5)", "Low dose (n = 8)", "High dose (n = 11)"]
    assert len(_render({"show_n": "none"}).figure.axes[0].texts) == 0
    # horizontal: n folded into the category names on the left
    h = _render({"show_n": "below", "orientation": "horizontal"}).figure.axes[0]
    assert [t.get_text() for t in h.get_yticklabels()] == ["Control\n(n = 5)", "Low dose\n(n = 8)", "High dose\n(n = 11)"]


# --- statistics brackets clear the points ----------------------------------------------------

def test_two_group_bracket_sits_above_the_highest_point():
    res = render(_spec({}, {"enabled": True, "test": "welch_t"}), _df("unequal_6_vs_17"))
    ax = res.figure.axes[0]
    brackets = _brackets(ax)
    assert len(brackets) == 1
    xs, ys = brackets[0]
    assert (xs[0], xs[2]) == (1.0, 2.0)
    assert ys[0] > _max_point_value(ax)
    assert res.metadata["statistics_report"]["results"][0]["test_id"] == "welch_t"


def test_three_group_posthoc_brackets_sit_above_the_points_they_span():
    res = render(_spec({}, {"enabled": True, "test": "one_way_anova", "posthoc": True}), _df("three_groups_unequal"))
    ax = res.figure.axes[0]
    brackets = _brackets(ax)
    assert len(brackets) == 3
    per_group_max = {float(np.round(np.mean(c.get_offsets()[:, 0]))): float(c.get_offsets()[:, 1].max())
                     for c in _point_collections(ax)}
    for xs, ys in brackets:
        assert ys[0] > max(per_group_max[xs[0]], per_group_max[xs[2]])
    kinds = {r["comparison_type"] for r in res.metadata["statistics_report"]["results"]}
    assert "two_group" in kinds and len(kinds) >= 2


def test_bracket_clears_points_and_outliers_without_points():
    """With points hidden and no outliers the bracket starts at the whisker; with outliers marked it clears them."""
    df = _df("one_extreme_observation")
    res = render(_spec({"points": False, "show_outliers": True}, {"enabled": True, "test": "welch_t"}), df)
    xs, ys = _brackets(res.figure.axes[0])[0]
    assert ys[0] > float(df["value"].max())


def test_bracket_clears_n_labels_above():
    res = render(_spec({"show_n": "above"}, {"enabled": True, "test": "welch_t"}), _df("unequal_6_vs_17"))
    ax = res.figure.axes[0]
    xs, ys = _brackets(ax)[0]
    labels = [t for t in ax.texts if t.get_text().startswith("n = ")]
    assert labels and ys[0] > max(t.xy[1] for t in labels)


# --- axis policy ------------------------------------------------------------------------------

def test_axis_overrides_apply_and_refuse_to_crop_points():
    res = _render({"y_min": 0.0, "y_max": 5.0})
    assert res.figure.axes[0].get_ylim() == (0.0, 5.0)
    assert res.metadata["axis_overrides"]["y_limits"] == [0.0, 5.0]
    with pytest.raises(RenderError):
        _render({"y_max": 1.0})


def test_points_are_never_outside_the_value_axis():
    for mapping in ({}, {"kind": "violin"}, {"kind": "summary"}, {"orientation": "horizontal"}):
        res = _render(mapping, data="one_extreme_observation")
        ax = res.figure.axes[0]
        axis = 0 if mapping.get("orientation") == "horizontal" else 1
        lim = ax.get_xlim() if axis == 0 else ax.get_ylim()
        for c in _point_collections(ax):
            vals = c.get_offsets()[:, axis]
            assert vals.min() >= min(lim) and vals.max() <= max(lim)


# --- metadata -----------------------------------------------------------------------------------

def test_metadata_records_kind_orientation_n_hue_and_options():
    res = render(_spec({"hue": "subgroup", "kind": "violin", "box_fill": "outline", "orientation": "horizontal"}),
                 _df("two_by_three"))
    meta = res.metadata
    assert meta["kind"] == "violin" and meta["orientation"] == "horizontal"
    assert meta["hue_levels"] == ["Young", "Adult", "Old"]
    assert meta["style"]["box_fill"] == "outline"
    assert meta["style"]["observations"]["arrangement"] == "jitter"
    assert meta["summary"]["center"] == "median"
    assert meta["data_columns_used"] == ["group", "value", "subgroup"]


# --- presets ------------------------------------------------------------------------------------

def test_style_preset_round_trips_the_new_style_options_and_not_the_config_ones():
    style_opts = {"kind": "box+violin", "point_arrangement": "beeswarm", "point_fill": "open", "point_size": 12.0,
                  "box_width": 0.7, "box_fill": "outline", "box_line_width": 1.5, "median_line_width": 2.5,
                  "whisker_cap_width": 0.25, "show_outliers": True, "violin_alpha": 0.3,
                  "orientation": "horizontal", "group_spacing": 1.3, "show_n": "legend"}
    spec = _spec({**style_opts, "category_order": "median_ascending", "hue": "subgroup"})
    preset = P.extract_preset(spec, mode="style", name="box style")
    assert preset["options"] == style_opts
    assert "category_order" not in preset["options"]          # config scope
    assert "hue" not in preset["options"]                     # a column role, never in a style preset
    fresh = make_spec(PT, "other.csv", "publication", mapping={"x": "group", "y": "value"})
    applied = P.apply_preset(preset, fresh, columns=["group", "value"])
    for k, v in style_opts.items():
        assert applied.spec["mapping"][k] == v, k
    assert "category_order" not in applied.spec["mapping"]
    # and the applied spec renders on different data with the options honoured
    res = render(applied.spec, _df("unequal_6_vs_17"))
    assert res.metadata["kind"] == "box+violin" and res.metadata["orientation"] == "horizontal"
    assert res.metadata["style"]["box_fill"] == "outline"
    # full preset carries the analytical option and the hue role
    full = P.extract_preset(spec, mode="full", name="box full")
    assert full["config_options"]["category_order"] == "median_ascending"
    assert full["mapping_roles"]["hue"] == "subgroup"
    applied_full = P.apply_preset(full, fresh, columns=["group", "value", "subgroup"])
    assert applied_full.spec["mapping"]["category_order"] == "median_ascending"
    assert applied_full.spec["mapping"]["hue"] == "subgroup"
    assert not applied_full.unresolved_roles


# --- matplotlib version compatibility -----------------------------------------------------------
# ``Axes.boxplot``/``Axes.violinplot`` accept ``orientation=`` only from matplotlib 3.10; the package
# declares ``matplotlib>=3.6`` and the macOS acceptance test (2026-09-17) ran on an older release and
# failed with "boxplot() got an unexpected keyword argument 'orientation'". The renderer must pick
# the keyword the installed matplotlib understands and draw the same geometry either way.

def _geometry(fig):
    ax = fig.axes[0]
    return {
        "xlim": tuple(np.round(ax.get_xlim(), 6)), "ylim": tuple(np.round(ax.get_ylim(), 6)),
        "patches": [np.round(p.get_path().vertices, 6).tolist() for p in ax.patches],
        "lines": [np.round(np.c_[l.get_xdata(), l.get_ydata()], 6).tolist() for l in ax.lines],
        "points": [np.round(c.get_offsets(), 6).tolist() for c in _point_collections(ax)],
        "collections": [np.round(np.concatenate([p.vertices for p in c.get_paths()]), 6).tolist()
                        for c in ax.collections if not isinstance(c, PathCollection) and c.get_paths()],
    }


class _LegacyAxesMethods:
    """Simulate matplotlib < 3.10: ``boxplot``/``violinplot`` know ``vert`` but not ``orientation``."""

    def __init__(self, monkeypatch):
        import inspect
        from matplotlib.axes import Axes
        real_box, real_violin = Axes.boxplot, Axes.violinplot
        if "orientation" not in inspect.signature(real_box).parameters:
            return  # the installed matplotlib already is the legacy API; nothing to simulate

        def boxplot(self, x, *args, vert=True, **kw):
            if "orientation" in kw:
                raise TypeError("boxplot() got an unexpected keyword argument 'orientation'")
            return real_box(self, x, *args, orientation="vertical" if vert else "horizontal", **kw)

        def violinplot(self, dataset, *args, vert=True, **kw):
            if "orientation" in kw:
                raise TypeError("violinplot() got an unexpected keyword argument 'orientation'")
            return real_violin(self, dataset, *args, orientation="vertical" if vert else "horizontal", **kw)

        monkeypatch.setattr(Axes, "boxplot", boxplot)
        monkeypatch.setattr(Axes, "violinplot", violinplot)


def test_orientation_kwargs_follow_the_installed_signature():
    from make_my_figure_core.plots.box_violin import _orientation_kwargs

    def modern(x, orientation="vertical"):
        pass

    def legacy(x, vert=True):
        pass

    assert _orientation_kwargs(modern, "vertical") == {"orientation": "vertical"}
    assert _orientation_kwargs(modern, "horizontal") == {"orientation": "horizontal"}
    assert _orientation_kwargs(legacy, "vertical") == {"vert": True}
    assert _orientation_kwargs(legacy, "horizontal") == {"vert": False}


@pytest.mark.parametrize("kind", ["box", "violin", "box+violin", "summary"])
@pytest.mark.parametrize("orientation", ["vertical", "horizontal"])
@pytest.mark.parametrize("data", ["three_groups_unequal", "two_by_three"])
def test_renders_identically_on_matplotlib_without_orientation_keyword(monkeypatch, kind, orientation, data):
    mapping = {"kind": kind, "orientation": orientation, "points": True, "show_n": "below",
               "seed": 7}
    if data == "two_by_three":
        mapping["hue"] = "subgroup"
    stats = {"enabled": True} if orientation == "vertical" else None
    modern = _geometry(_render(mapping, data, stats).figure)
    plt.close("all")
    _LegacyAxesMethods(monkeypatch)
    legacy_result = _render(mapping, data, stats)
    assert _geometry(legacy_result.figure) == modern
    assert not any("orientation" in w for w in legacy_result.warnings)
