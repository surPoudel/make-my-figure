"""Categorical colour: enough of it, the right kind of it, and overridable.

Three things were wrong and all three are fixed at the one place every plot type
gets a categorical colour from - ``StyleProfile.color_for`` - rather than in the
38 renderers that call it:

* ten groups on an eight-colour palette silently gave two groups one colour;
* there was no way to say "make Drug_B orange";
* the chooser offered four palettes and no way to see what else would fit, and
  nothing distinguished a palette for categories from a colormap for magnitudes.
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from matplotlib.colors import to_hex

from make_my_figure_core import examples
from make_my_figure_core.plots import registry
from make_my_figure_core.styles import engine

_RNG = np.random.default_rng(11)


def _grouped_frame(n_groups):
    return pd.DataFrame({"c": [f"G{i:02d}" for i in range(n_groups) for _ in range(5)],
                         "m": _RNG.normal(1.0, 0.2, n_groups * 5)})


def _bar_colors(n_groups, **style):
    spec = registry.make_spec("barplot_with_error_bar", "t.csv", "publication")
    spec["mapping"] = {"x": "c", "y": "m", "color": "c", "error": "sem"}
    if style:
        spec["style"] = style
    result = registry.render(spec, _grouped_frame(n_groups))
    colors = [to_hex(p.get_facecolor()) for p in result.figure.axes[0].patches][:n_groups]
    warned = [w for w in result.warnings if "categories were drawn" in w]
    plt.close(result.figure)
    return colors, warned


# --------------------------------------------------------------------------
# N categories
# --------------------------------------------------------------------------

@pytest.mark.parametrize("n", [2, 3, 5, 8])
def test_every_group_gets_its_own_colour_within_the_palette(n):
    colors, warned = _bar_colors(n)
    assert len(set(colors)) == n, f"{n} groups share {len(set(colors))} colours"
    assert warned == [], "warned about a palette that was big enough"


@pytest.mark.parametrize("n", [10, 14])
def test_more_groups_than_colours_is_reported_not_hidden(n):
    """The defect: two different groups quietly drawn in one colour."""
    colors, warned = _bar_colors(n)
    assert len(set(colors)) < n          # the palette genuinely cannot do it
    assert warned, f"{n} groups on an 8-colour palette passed without a word"
    assert "repeat" in warned[0]


def test_the_warning_names_a_palette_that_would_actually_work():
    """An alternative that cannot do the job either is not an alternative."""
    _colors, warned = _bar_colors(14)
    suggested = [p for p in engine.PALETTE_GROUPS["qualitative"] if p in warned[0]]
    assert suggested, warned[0]
    for name in suggested:
        assert engine.palette_capacity(name) >= 14, name


def test_the_suggested_palette_really_gives_distinct_colours():
    colors, warned = _bar_colors(14, palette_name="tab20")
    assert len(set(colors)) == 14
    assert warned == []


# --------------------------------------------------------------------------
# individual overrides
# --------------------------------------------------------------------------

def test_a_colour_can_be_given_by_position():
    colors, _ = _bar_colors(4, color_overrides={"0": "#FF00FF"})
    assert colors[0] == "#ff00ff"


def test_a_colour_can_be_given_as_a_plain_list_in_group_order():
    colors, _ = _bar_colors(4, color_overrides=["#111111", "#222222"])
    assert colors[0] == "#111111" and colors[1] == "#222222"


def test_a_colour_can_be_given_by_group_name():
    table, aux, spec = examples.load_example("scatterplot_with_regression")
    spec = {**spec, "style": {"color_overrides": {"Responder": "#FF00FF"}}}
    result = registry.render(spec, table.dataframe,
                             aux={k: v.dataframe for k, v in (aux or {}).items()})
    drawn = {c.get_label(): to_hex(c.get_facecolor()[0])
             for c in result.figure.axes[0].collections
             if not c.get_label().startswith("_")}
    plt.close(result.figure)
    assert drawn["Responder"] == "#ff00ff"
    assert drawn["Non_responder"] != "#ff00ff", "it recoloured a group it was not given"


def test_a_name_that_matches_no_group_says_so():
    table, aux, spec = examples.load_example("scatterplot_with_regression")
    spec = {**spec, "style": {"color_overrides": {"NotAGroup": "#FF00FF"}}}
    result = registry.render(spec, table.dataframe,
                             aux={k: v.dataframe for k, v in (aux or {}).items()})
    plt.close(result.figure)
    assert any("No drawn group is named" in w for w in result.warnings)


def test_an_override_does_not_disturb_the_groups_it_was_not_given():
    plain, _ = _bar_colors(5)
    painted, _ = _bar_colors(5, color_overrides={"2": "#FF00FF"})
    assert painted[2] == "#ff00ff"
    assert [c for i, c in enumerate(painted) if i != 2] == \
           [c for i, c in enumerate(plain) if i != 2]


# --------------------------------------------------------------------------
# the catalogue
# --------------------------------------------------------------------------

def test_the_catalogue_keeps_the_four_kinds_of_palette_apart():
    groups = engine.PALETTE_GROUPS
    assert set(groups) == {"qualitative", "sequential", "diverging", "grayscale"}
    # A continuous map must not be offered as a palette for nominal categories.
    assert not set(groups["sequential"]) & set(groups["qualitative"])
    assert not set(groups["diverging"]) & set(groups["qualitative"])


def test_the_existing_palettes_are_still_there_and_still_first():
    """Preserving the defaults is part of the contract."""
    qualitative = engine.PALETTE_GROUPS["qualitative"]
    assert qualitative[:4] == engine.USER_PALETTES
    for name in engine.USER_PALETTES:
        assert engine.qualitative_palette(name) == list(engine.NAMED_PALETTES[name])


def test_every_catalogued_name_resolves():
    import matplotlib as mpl

    for name in engine.PALETTE_GROUPS["qualitative"]:
        assert engine.palette_capacity(name) >= 3, name
    for group in ("sequential", "diverging"):
        for name in engine.PALETTE_GROUPS[group]:
            assert name in mpl.colormaps, name


def test_capacity_is_distinct_colours_not_list_length():
    assert engine.palette_capacity("publication") == len(
        {c.lower() for c in engine.NAMED_PALETTES["publication"]})
    assert engine.palette_capacity("tab20") == 20


def test_an_unknown_palette_name_is_simply_not_offered():
    assert engine.qualitative_palette("not_a_palette") == []
    assert engine.palette_capacity("not_a_palette") == 0


# --------------------------------------------------------------------------
# nothing changes unless asked
# --------------------------------------------------------------------------

def test_default_colours_are_what_they_always_were():
    colors, warned = _bar_colors(4)
    assert colors == [c.lower() for c in engine.NAMED_PALETTES["publication"][:4]]
    assert warned == []


def test_an_empty_override_map_changes_nothing():
    plain, _ = _bar_colors(4)
    empty, _ = _bar_colors(4, color_overrides={})
    assert plain == empty


def test_overrides_round_trip_through_the_plotspec():
    import json

    spec = registry.make_spec("barplot_with_error_bar", "t.csv", "publication")
    spec["mapping"] = {"x": "c", "y": "m", "color": "c", "error": "sem"}
    spec["style"] = {"color_overrides": {"0": "#FF00FF"}}
    reloaded = json.loads(json.dumps(spec))
    registry.validate_plot_spec(reloaded)
    result = registry.render(reloaded, _grouped_frame(4))
    first = to_hex(result.figure.axes[0].patches[0].get_facecolor())
    plt.close(result.figure)
    assert first == "#ff00ff"
