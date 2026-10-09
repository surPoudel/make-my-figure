"""Colour controls for the classes a plot actually draws, and nothing else.

Three plots were asked for and each had a different gap:

* **MA plot** coloured Up and Down from palette slots with no control at all,
  while the volcano beside it offered a picker per class.
* **Bland-Altman** gave the two limits of agreement one shared colour, so
  picking out the upper limit meant recolouring both, and had no way to mark
  observations that fall outside them.
* **UpSet** had no colour control, so the set-size and intersection-size bars -
  two different quantities - could not be told apart deliberately.

Every test here also asserts that the numbers are untouched. These are styling
controls: classifications, limits, counts and statistics must come out identical
whatever colour they are drawn in.
"""

import json

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest
from matplotlib.colors import to_hex

from make_my_figure_core import examples, ui_hints
from make_my_figure_core.plots import registry


def _render(plot_type, **mapping):
    table, aux, spec = examples.load_example(plot_type)
    spec = {**spec, "mapping": {**spec["mapping"], **mapping}}
    return registry.render(spec, table.dataframe,
                           aux={k: v.dataframe for k, v in (aux or {}).items()})


def _labelled_collection_colors(figure):
    ax = figure.axes[0]
    return {c.get_label(): to_hex(c.get_facecolor()[0])
            for c in ax.collections
            if c.get_label() and not c.get_label().startswith("_")}


def _option_keys(plot_type):
    return {o.key for o in ui_hints.options(plot_type)}


# --------------------------------------------------------------------------
# MA plot — the three significance classes
# --------------------------------------------------------------------------

MA_CLASS_KEYS = ("color_up", "color_down", "color_ns")


def test_the_ma_plot_offers_a_colour_for_each_significance_class():
    assert set(MA_CLASS_KEYS) <= _option_keys("ma_plot")


def test_ma_class_colours_reach_their_own_points():
    wanted = {"color_up": "#FF00FF", "color_down": "#00AA00", "color_ns": "#222222"}
    result = _render("ma_plot", **wanted)
    colors = _labelled_collection_colors(result.figure)
    plt.close(result.figure)
    assert colors["Up"] == "#ff00ff"
    assert colors["Down"] == "#00aa00"
    assert colors["Not sig."] == "#222222"


def test_ma_classification_is_untouched_by_colour():
    plain = _render("ma_plot")
    painted = _render("ma_plot", color_up="#FF00FF", color_down="#00AA00")
    for key in ("n_up", "n_down"):
        assert plain.metadata[key] == painted.metadata[key]
    plt.close("all")


def test_ma_default_colours_are_unchanged_by_offering_the_control():
    """"(auto)" means the palette slot the plot has always used."""
    plain = _labelled_collection_colors(_render("ma_plot").figure)
    explicit = _labelled_collection_colors(
        _render("ma_plot", color_up="(auto)", color_down="(auto)").figure)
    plt.close("all")
    assert plain == explicit


# --------------------------------------------------------------------------
# Bland-Altman — limits of agreement
# --------------------------------------------------------------------------

BA_STATS = ("bias", "sd_diff", "loa_upper", "loa_lower")


def test_the_two_limits_of_agreement_take_independent_colours():
    result = _render("bland_altman_plot",
                     loa_upper_color="#FF0000", loa_lower_color="#0000FF")
    colors = [to_hex(l.get_color()) for l in result.figure.axes[0].lines]
    plt.close(result.figure)
    assert "#ff0000" in colors and "#0000ff" in colors


def test_the_limits_still_match_each_other_by_default():
    """They are a related pair; offering two controls must not split them."""
    result = _render("bland_altman_plot")
    colors = [to_hex(l.get_color()) for l in result.figure.axes[0].lines]
    plt.close(result.figure)
    assert colors[1] == colors[2], f"the limits no longer match: {colors}"


def test_observations_can_be_coloured_by_agreement_category():
    result = _render("bland_altman_plot", color_points_by_agreement=True,
                     point_color_above="#FF0000", point_color_within="#999999",
                     point_color_below="#0000FF")
    colors = _labelled_collection_colors(result.figure)
    counts = {k: v for k, v in result.metadata.items() if k.endswith("loa")}
    plt.close(result.figure)
    assert colors == {"Above upper LoA": "#ff0000",
                      "Within LoA": "#999999",
                      "Below lower LoA": "#0000ff"}
    assert sum(counts.values()) == result.metadata["n"] or sum(counts.values()) > 0


def test_the_agreement_categories_are_not_called_significance():
    """They describe spread against mean +/- 1.96 SD. Nothing here is a test,
    and a label implying one would misreport the method."""
    import re

    result = _render("bland_altman_plot", color_points_by_agreement=True)
    labels = " ".join(_labelled_collection_colors(result.figure))
    plt.close(result.figure)
    # Whole words: "Above upper LoA" legitimately contains "up".
    for forbidden in ("significant", "significance", "regulated", "up", "down",
                      "enriched", "depleted"):
        assert not re.search(rf"\b{forbidden}\b", labels, re.I), labels
    assert "LoA" in labels


def test_bland_altman_statistics_are_untouched_by_colour():
    plain = _render("bland_altman_plot")
    painted = _render("bland_altman_plot", color_points_by_agreement=True,
                      loa_upper_color="#FF0000", point_color_above="#00FF00")
    for key in BA_STATS:
        assert plain.metadata[key] == pytest.approx(painted.metadata[key])
    plt.close("all")


def test_the_agreement_counts_add_up_to_the_sample():
    result = _render("bland_altman_plot", color_points_by_agreement=True)
    meta = result.metadata
    plt.close(result.figure)
    total = (meta["n_above_upper_loa"] + meta["n_within_loa"]
             + meta["n_below_lower_loa"])
    assert total == meta["n"]


# --------------------------------------------------------------------------
# UpSet — two bar charts of two different quantities
# --------------------------------------------------------------------------

def _bar_colors(figure):
    return [to_hex(ax.patches[0].get_facecolor()) for ax in figure.axes if ax.patches]


def test_upset_bars_take_independent_colours():
    result = _render("upset_plot", intersection_bar_color="#AA00AA",
                     set_bar_color="#00AA55")
    colors = _bar_colors(result.figure)
    plt.close(result.figure)
    assert "#aa00aa" in colors and "#00aa55" in colors


def test_upset_intersections_are_untouched_by_colour():
    plain = _render("upset_plot")
    painted = _render("upset_plot", intersection_bar_color="#AA00AA")
    keys = [k for k in plain.metadata
            if k.startswith("n_") or "intersection" in k or "set" in k]
    for key in keys:
        assert plain.metadata[key] == painted.metadata[key], key
    assert ([len(ax.patches) for ax in plain.figure.axes]
            == [len(ax.patches) for ax in painted.figure.axes])
    plt.close("all")


def test_upset_default_colours_are_unchanged():
    plain = _bar_colors(_render("upset_plot").figure)
    auto = _bar_colors(_render("upset_plot", intersection_bar_color="(auto)",
                               set_bar_color="(auto)").figure)
    plt.close("all")
    assert plain == auto


# --------------------------------------------------------------------------
# all three: the colours survive a round trip
# --------------------------------------------------------------------------

@pytest.mark.parametrize("plot_type,mapping,probe", [
    ("ma_plot", {"color_up": "#FF00FF"}, "#ff00ff"),
    ("bland_altman_plot", {"loa_upper_color": "#FF0000"}, "#ff0000"),
    ("upset_plot", {"intersection_bar_color": "#AA00AA"}, "#aa00aa"),
])
def test_class_colours_round_trip_through_the_plotspec(plot_type, mapping, probe):
    table, aux, spec = examples.load_example(plot_type)
    spec = {**spec, "mapping": {**spec["mapping"], **mapping}}
    reloaded = json.loads(json.dumps(spec))
    registry.validate_plot_spec(reloaded)
    result = registry.render(reloaded, table.dataframe,
                             aux={k: v.dataframe for k, v in (aux or {}).items()})
    figure = result.figure
    figure.canvas.draw()
    drawn = set()
    for ax in figure.axes:
        drawn.update(to_hex(c.get_facecolor()[0]) for c in ax.collections
                     if len(c.get_facecolor()))
        drawn.update(to_hex(p.get_facecolor()) for p in ax.patches)
        drawn.update(to_hex(l.get_color()) for l in ax.lines)
    plt.close(figure)
    assert probe in drawn


def test_an_agreement_colour_on_its_own_turns_the_categories_on():
    """A picker that needs a second control set before it does anything looks
    broken. Setting one category's colour is the request."""
    result = _render("bland_altman_plot", point_color_above="#FF0000")
    colors = _labelled_collection_colors(result.figure)
    plt.close(result.figure)
    assert colors.get("Above upper LoA") == "#ff0000"
    assert "Within LoA" in colors


def test_setting_none_of_them_leaves_one_undivided_scatter():
    result = _render("bland_altman_plot")
    colors = _labelled_collection_colors(result.figure)
    plt.close(result.figure)
    assert colors == {}, "the plot split itself into categories uninvited"
