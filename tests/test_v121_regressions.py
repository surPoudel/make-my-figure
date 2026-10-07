"""The six v1.2.0 regressions, so none of them can return quietly.

Each test here failed on the v1.2.0 tag and passes on the fix. They are written
against observable behaviour - a rendered colour, a widget value, a drawn font
size - rather than against the implementation, so a future refactor is free to
change how, but not whether.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("matplotlib")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


# --------------------------------------------------------------------------
# BUG 5 — the palette chooser must offer palettes that differ
# --------------------------------------------------------------------------

def test_every_offered_palette_is_visibly_different_from_every_other():
    """`publication` and `colorblind_safe` differed at one of eight entries.

    Any figure with six categories or fewer was therefore pixel-identical
    between them - 40 of the 45 plot types - so the chooser looked broken.
    """
    from itertools import combinations

    from make_my_figure_core.styles.engine import NAMED_PALETTES, USER_PALETTES

    for a, b in combinations(USER_PALETTES, 2):
        pa, pb = NAMED_PALETTES[a], NAMED_PALETTES[b]
        differing = sum(1 for x, y in zip(pa[:6], pb[:6]) if x != y)
        assert differing >= 4, (
            f"palettes '{a}' and '{b}' differ at only {differing} of their first six "
            f"entries; a user switching between them would see almost no change")


def test_the_first_colour_differs_across_palettes():
    """Several plots use only palette index 0; it was blue, blue, black, black."""
    from make_my_figure_core.styles.engine import NAMED_PALETTES, USER_PALETTES

    firsts = [NAMED_PALETTES[p][0] for p in USER_PALETTES]
    assert len(set(firsts)) == len(firsts), (
        f"index 0 is not unique across palettes: {dict(zip(USER_PALETTES, firsts))}")


@pytest.mark.parametrize("plot_type", ["beeswarm_plot", "dot_strip_plot"])
def test_three_groups_get_three_colours(plot_type):
    """These fell back to one colour for every group, and refused a colour
    column that named the x column - which is the obvious way to ask."""
    from make_my_figure_core import examples
    from make_my_figure_core.plots import registry

    table, aux, spec = examples.load_example(plot_type)
    x = (spec.get("mapping") or {}).get("x")
    spec = {**spec, "mapping": {**(spec.get("mapping") or {}), "color": x}}
    result = registry.render(spec, table.dataframe, aux={})
    ax = result.figure.axes[0]
    colours = {tuple(np.round(row[:3], 3))
               for coll in ax.collections for row in coll.get_facecolor()}
    legend = ax.get_legend()
    n_entries = len(legend.get_texts()) if legend else 0
    plt.close(result.figure)
    assert len(colours) >= 3, f"{plot_type}: 3 groups drew {len(colours)} colour(s)"
    assert n_entries >= 3, f"{plot_type}: 3 groups produced {n_entries} legend entries"


# --------------------------------------------------------------------------
# BUG 4 — spatial ROI colours
# --------------------------------------------------------------------------

def test_roi_regions_are_coloured_without_a_category_column():
    """Every region fell back to style.text_color and drew unfilled, so a user's
    own ROI table was a near-black wireframe."""
    from make_my_figure_core import examples
    from make_my_figure_core.plots import registry

    table, aux, spec = examples.load_example("spatial_roi_map")
    mapping = dict(spec.get("mapping") or {})
    mapping.pop("roi_category", None)
    result = registry.render({**spec, "mapping": mapping}, table.dataframe,
                             aux={k: v.dataframe for k, v in (aux or {}).items()})
    ax = result.figure.axes[0]
    edges = {tuple(np.round(row[:3], 3))
             for coll in ax.collections for row in coll.get_edgecolor()}
    plt.close(result.figure)
    assert len(edges) >= 2, f"regions share one outline colour: {edges}"
    near_black = {e for e in edges if max(e) < 0.2}
    assert not near_black, f"regions drew near-black: {sorted(near_black)}"


@pytest.mark.parametrize("key", ["roi_edgecolor", "roi_fill_alpha", "roi_linewidth"])
def test_roi_appearance_controls_are_reachable_and_live(key):
    """These existed in the renderer but were absent from the GUI-settable keys,
    so they could not be set from either frontend."""
    import hashlib
    import io

    from make_my_figure_core import examples, ui_hints
    from make_my_figure_core.plots._spatial_shared import GUI_SETTABLE_SPATIAL_KEYS
    from make_my_figure_core.plots import registry

    assert key in GUI_SETTABLE_SPATIAL_KEYS, f"{key} cannot be set from a frontend"
    assert any(o.key == key for o in ui_hints.OPTIONS["spatial_roi_map"]), \
        f"{key} is not offered in the options panel"

    table, aux, spec = examples.load_example("spatial_roi_map")
    aux_frames = {k: v.dataframe for k, v in (aux or {}).items()}

    def digest(extra):
        s = {**spec, "mapping": {**(spec.get("mapping") or {}), **extra}}
        res = registry.render(s, table.dataframe, aux=aux_frames)
        buf = io.BytesIO()
        res.figure.savefig(buf, format="png", dpi=72)
        plt.close(res.figure)
        return hashlib.sha256(buf.getvalue()).hexdigest()

    changed = {"roi_edgecolor": "#CC6677", "roi_fill_alpha": 0.7, "roi_linewidth": 4.0}[key]
    assert digest({}) != digest({key: changed}), f"{key} is offered but changes nothing"


# --------------------------------------------------------------------------
# BUG 6 — PCA must use confirmed metadata groups, and must not change the maths
# --------------------------------------------------------------------------

def _matrix_and_metadata(groups):
    import pandas as pd

    from make_my_figure_core.matrix_workflow.matrix_spec import MatrixSpec
    from make_my_figure_core.matrix_workflow.metadata_spec import SampleMetadataSpec

    rng = np.random.default_rng(0)
    samples = list(groups)
    data = {"feature_id": [f"F{i}" for i in range(40)]}
    for s in samples:
        data[s] = rng.normal(10.0 if s.startswith("B") else 0.0, 1.0, 40)
    frame = pd.DataFrame(data)
    spec = MatrixSpec(feature_id_column="feature_id", value_columns=samples,
                      confirmed_by_user=True)
    meta = SampleMetadataSpec(sample_to_group=dict(groups), confirmed_by_user=True)
    return frame, spec, meta


def _render_pca(frame, matrix_spec, metadata, key="pca"):
    from make_my_figure_core.matrix_workflow.plot_builder import build_plot_inputs
    from make_my_figure_core.matrix_workflow.recommendations import RecommendedPlot
    from make_my_figure_core.plots import registry

    inputs = build_plot_inputs(
        RecommendedPlot(plot_type="pca_scatter_from_matrix", label="PCA", reason="", key=key),
        frame, matrix_spec, metadata=metadata)
    spec = registry.make_spec("pca_scatter_from_matrix", "matrix.csv", "publication",
                              mapping=inputs.mapping)
    return registry.render(spec, inputs.dataframe, aux=inputs.aux or None)


@pytest.mark.parametrize("n_groups", [2, 3, 4])
def test_plain_pca_uses_confirmed_sample_groups(n_groups):
    """Grouping depended on which of two recommendations was picked, and the
    obvious one - "PCA scatter" - ignored groups the user had confirmed."""
    samples = [f"{'AB'[i % 2]}{i}" for i in range(6)]
    groups = {s: f"g{i % n_groups}" for i, s in enumerate(samples)}
    result = _render_pca(*_matrix_and_metadata(groups))
    ax = result.figure.axes[0]
    colours = {tuple(np.round(c.get_facecolor()[0][:3], 3)) for c in ax.collections}
    legend = ax.get_legend()
    entries = len(legend.get_texts()) if legend else 0
    plt.close(result.figure)
    assert len(colours) == n_groups, f"{n_groups} groups drew {len(colours)} colours"
    assert entries == n_groups, f"{n_groups} groups produced {entries} legend entries"


def test_grouping_never_changes_the_principal_components():
    """The renderer restricted samples to those listed in the metadata BEFORE
    the SVD, so incomplete metadata silently deleted samples and moved every
    score - dropping one of six moved PC1 by about 20%."""
    samples = ["A1", "A2", "A3", "B1", "B2", "B3"]
    full = {s: ("ctrl" if s[0] == "A" else "treat") for s in samples}
    frame, spec, meta_full = _matrix_and_metadata(full)
    partial = {k: v for k, v in full.items() if k != "B3"}
    _, _, meta_partial = _matrix_and_metadata(partial)

    def coords(metadata):
        res = _render_pca(frame, spec, metadata)
        pts = np.array([c.get_offsets()[0] for c in res.figure.axes[0].collections])
        plt.close(res.figure)
        return pts[np.lexsort((pts[:, 1], pts[:, 0]))]

    ungrouped = coords(None)
    assert np.allclose(ungrouped, coords(meta_full)), "grouping moved the points"
    assert len(coords(meta_partial)) == len(samples), "a sample was dropped from the PCA"
    assert np.allclose(ungrouped, coords(meta_partial)), (
        "incomplete metadata changed the principal components")


# --------------------------------------------------------------------------
# BUG 2B — statistics text
# --------------------------------------------------------------------------

@pytest.mark.parametrize("size", [6.0, 16.0])
def test_the_annotation_font_control_sizes_the_corner_statistics(size):
    """6 pt and 20 pt both rendered 7.83: the bracket engine honoured the
    control, the corner panel ignored it."""
    from make_my_figure_core import examples
    from make_my_figure_core.plots import registry

    table, aux, spec = examples.load_example("boxplot_or_violin_with_points")
    stats = {**(spec.get("statistics") or {}), "enabled": True}
    stats["annotation"] = {**(stats.get("annotation") or {}), "font_size": size}
    result = registry.render({**spec, "statistics": stats}, table.dataframe, aux={})
    panel = [t for t in result.figure.axes[0].texts
             if "ANOVA" in t.get_text() or "Kruskal" in t.get_text()]
    plt.close(result.figure)
    assert panel, "no corner statistics panel was drawn"
    drawn = panel[0].get_fontsize()
    assert abs(drawn - size) <= 1.0, f"asked for {size} pt, drew {drawn} pt"


@pytest.mark.parametrize("width_mm", [81.3, 45.7])
def test_statistics_text_is_never_cut_off_by_the_canvas(width_mm):
    """"p < 0." was a correctly formatted string running off the canvas; at a
    three-up panel width only 26% of it was visible."""
    from make_my_figure_core import examples
    from make_my_figure_core.plots import registry

    table, aux, spec = examples.load_example("boxplot_or_violin_with_points")
    spec = {**spec,
            "statistics": {**(spec.get("statistics") or {}), "enabled": True},
            "layout": {**(spec.get("layout") or {}), "width_mm": width_mm,
                       "height_mm": width_mm * 0.75}}
    result = registry.render(spec, table.dataframe, aux={})
    figure = result.figure
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    panel = [t for t in figure.axes[0].texts
             if "ANOVA" in t.get_text() or "Kruskal" in t.get_text()]
    assert panel, "no corner statistics panel was drawn"
    box = panel[0].get_window_extent(renderer)
    overflow = max(0.0, -box.x0, box.x1 - figure.bbox.width)
    plt.close(figure)
    assert overflow <= 1.0, (
        f"{overflow:.0f}px of the statistics text falls outside a {width_mm:.0f}mm figure")


def test_p_values_never_format_as_a_truncated_decimal():
    """A significant p must not be reported as 'p = 0.0'."""
    from make_my_figure_core.statistics.method_reporting import format_p

    for p in (0.12, 0.049, 0.001, 1e-8, 0.0):
        for digits in (1, 2, 3, 6):
            text = format_p(p, digits=digits)
            assert text.rstrip("0").rstrip(".") not in ("p = 0", "p ="), \
                f"format_p({p}, digits={digits}) == {text!r}"
            assert not text.endswith("0."), f"format_p({p}, digits={digits}) == {text!r}"


# --------------------------------------------------------------------------
# No visible colour control may do nothing
# --------------------------------------------------------------------------

_ROLE_PLOTS = ["calibration_plot", "bland_altman_plot", "qq_plot", "forest_plot",
               "hierarchical_dendrogram"]


@pytest.mark.parametrize("plot_type", _ROLE_PLOTS)
def test_every_role_colour_picker_changes_the_figure(plot_type):
    """A plot that is scientifically one colour gets a picker per artist it
    draws - and a picker that changes nothing is worse than no picker."""
    import hashlib
    import io

    from make_my_figure_core import examples, ui_hints
    from make_my_figure_core.plots import registry

    table, aux, spec = examples.load_example(plot_type)
    aux_frames = {k: v.dataframe for k, v in (aux or {}).items()}
    # The Bland-Altman confidence band is only drawn when it is switched on.
    base_mapping = {"show_ci": True} if plot_type == "bland_altman_plot" else {}

    def digest(extra):
        s = {**spec, "mapping": {**(spec.get("mapping") or {}), **base_mapping, **extra}}
        res = registry.render(s, table.dataframe, aux=aux_frames)
        buf = io.BytesIO()
        res.figure.savefig(buf, format="png", dpi=72)
        plt.close(res.figure)
        return hashlib.sha256(buf.getvalue()).hexdigest()

    roles = [o.key for o in ui_hints.OPTIONS[plot_type] if o.default == "(auto)"]
    assert roles, f"{plot_type} declares no role colour pickers"
    base = digest({})
    dead = [k for k in roles if digest({k: "#CC6677"}) == base]
    assert not dead, f"{plot_type}: these pickers change nothing: {dead}"
