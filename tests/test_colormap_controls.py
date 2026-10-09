"""The two continuous-colormap controls: offered only where they act.

Four reports, one pattern. A "Diverging map" chooser sat beside a dot plot that
ramps a single magnitude; a "Sequential map" chooser sat beside three matrices
that are centred or z-scored and therefore drawn with the diverging map. In every
case the control was visible and could do nothing.

Two different causes, so two different fixes, both tested here:

* the plot type reads only ONE of the two — a static fact, so the capability
  registry declares them separately and the panel hides the other;
* the plot type reads both and the DATA decides — not a static fact, so the
  render reports which one it actually used and the panel follows that.

The second is why the check below is "does the reported role match which control
really changes the figure", asked of every registered plot type.
"""

import io
import hashlib
import json

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

from make_my_figure_core import examples
from make_my_figure_core.plots import base, registry
from make_my_figure_core.styles.capabilities import get_style_capabilities

PLOT_TYPES = [p for p in sorted(registry.available_plot_types()) if examples.entry(p)]
DPI = 60


def _digest(figure):
    figure.savefig(io.BytesIO(), format="png", dpi=DPI)      # settle at this dpi
    buf = io.BytesIO()
    figure.savefig(buf, format="png", dpi=DPI)
    return hashlib.sha256(buf.getvalue()).hexdigest()[:16]


def _render(plot_type, mapping=None, **style):
    table, aux, spec = examples.load_example(plot_type)
    spec = json.loads(json.dumps(spec))
    if mapping:
        spec["mapping"].update(mapping)
    if style:
        spec["style"] = {**(spec.get("style") or {}), **style}
    return registry.render(spec, table.dataframe,
                           aux={k: v.dataframe for k, v in (aux or {}).items()})


def _role_and_effects(plot_type, mapping=None):
    """``(role, sequential_acts, diverging_acts)`` for one configuration."""
    baseline = _render(plot_type, mapping)
    role = baseline.metadata.get("colormap_role")
    reference = _digest(baseline.figure)
    plt.close(baseline.figure)
    effects = []
    for key, value in (("sequential_cmap", "Greys"), ("diverging_cmap", "PuOr")):
        result = _render(plot_type, mapping, **{key: value})
        effects.append(_digest(result.figure) != reference)
        plt.close(result.figure)
    return role, effects[0], effects[1]


# --------------------------------------------------------------------------
# every plot type: what is reported is what happens
# --------------------------------------------------------------------------

@pytest.mark.parametrize("plot_type", PLOT_TYPES)
def test_the_reported_colormap_role_is_the_control_that_acts(plot_type):
    """The whole mechanism in one assertion, on all 45 plot types.

    The panel shows a colormap chooser when, and only when, the render says that
    one governs the figure. If the report and the reality ever disagree, the
    panel is lying in one direction or the other.
    """
    role, sequential_acts, diverging_acts = _role_and_effects(plot_type)
    assert (role == "sequential") == sequential_acts, (
        f"{plot_type}: role={role!r} but the sequential map "
        f"{'changes' if sequential_acts else 'does not change'} the figure")
    assert (role == "diverging") == diverging_acts, (
        f"{plot_type}: role={role!r} but the diverging map "
        f"{'changes' if diverging_acts else 'does not change'} the figure")


# --------------------------------------------------------------------------
# the static half: a plot that reads one map does not advertise the other
# --------------------------------------------------------------------------

def test_the_capability_registry_declares_the_two_maps_separately():
    """One flag for both is what put a Diverging chooser beside a dot plot."""
    caps = get_style_capabilities("enrichment_dotplot")
    assert caps.supports_sequential_cmap is True
    assert caps.supports_diverging_cmap is False
    assert caps.supports_continuous_colormap is True      # "either kind applies"


@pytest.mark.parametrize("plot_type", PLOT_TYPES)
def test_every_declared_colormap_flag_matches_the_renderer_source(plot_type):
    import pathlib
    import re

    caps = get_style_capabilities(plot_type)
    declared = (caps.supports_sequential_cmap, caps.supports_diverging_cmap)
    reads = (False, False)
    for path in pathlib.Path("make_my_figure_core/plots").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        if re.search(rf'PLOT_TYPE\s*=\s*"{plot_type}"', source):
            reads = ("sequential_cmap" in source, "diverging_cmap" in source)
            break
    assert declared == reads, f"{plot_type}: declares {declared}, source reads {reads}"


# --------------------------------------------------------------------------
# the data-dependent half
# --------------------------------------------------------------------------

@pytest.mark.parametrize("plot_type,switch", [
    ("heatmap_clustered_matrix", {"scale": "none", "color_scale": "sequential"}),
    ("hierarchical_clustering", {"scale": "none"}),
    ("neighborhood_enrichment_matrix", {"color_scale": "sequential"}),
])
def test_a_matrix_swaps_which_map_governs_it_when_the_scale_changes(plot_type, switch):
    """Centred or z-scored it is drawn diverging; unscaled it is drawn
    sequential. Both controls are real - they just take turns."""
    diverging_role, seq_before, div_before = _role_and_effects(plot_type)
    sequential_role, seq_after, div_after = _role_and_effects(plot_type, switch)
    assert diverging_role == "diverging" and div_before and not seq_before
    assert sequential_role == "sequential" and seq_after and not div_after


def test_the_neighbourhood_matrix_colour_scale_is_reachable():
    """It was decided by the spec block alone, so the sequential map could never
    be made to apply from the app - a live control with no way to reach it."""
    from make_my_figure_core import ui_hints

    assert "color_scale" in {o.key for o in ui_hints.options(
        "neighborhood_enrichment_matrix")}


def test_setting_the_map_that_is_not_in_charge_says_so():
    result = _render("heatmap_clustered_matrix", sequential_cmap="Greys")
    notes = [w for w in result.warnings if "colormap" in w.lower()]
    plt.close(result.figure)
    assert notes, "no explanation for a colormap that was set and not used"
    assert "diverging" in notes[0] and "RdBu_r" in notes[0]


def test_the_map_that_is_in_charge_draws_no_complaint():
    result = _render("heatmap_clustered_matrix", diverging_cmap="PuOr")
    notes = [w for w in result.warnings if "is not what this figure" in w]
    plt.close(result.figure)
    assert notes == []


def test_a_plot_with_no_colormap_reports_no_role_and_is_never_warned_at():
    result = _render("barplot_with_error_bar", sequential_cmap="Greys",
                     diverging_cmap="PuOr")
    notes = [w for w in result.warnings if "is not what this figure" in w]
    role = result.metadata.get("colormap_role")
    plt.close(result.figure)
    assert role is None and notes == []


def test_the_primary_colormap_is_the_plots_own_not_a_decoration():
    """A matrix with a cluster strip and a colourbar draws with three colormaps;
    only one of them is the figure."""
    result = _render("heatmap_clustered_matrix")
    names = base.figure_colormaps(result.figure)
    plt.close(result.figure)
    assert names and names[0] == "RdBu_r", names
