"""Preview-before-apply and the drawn-figure layout QC.

The preview must render before/after on the synthetic example data without touching the caller's
spec, list every change, and refuse a *style* preset that changes anything analytical. The layout
QC must measure overlap, legend collisions and physical size on the drawn figure - and must
report, not fix.
"""

from __future__ import annotations

import copy

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

from make_my_figure_core import preset_preview as pp
from make_my_figure_core import presets
from make_my_figure_core.plots import registry
from make_my_figure_core.qc.text_layout_qc import check_text_layout
from make_my_figure_core.styles.engine import load_profile, resolve_width_mm


@pytest.fixture(autouse=True)
def _close():
    yield
    plt.close("all")


def _style_preset(**style):
    return {"format": presets.PRESET_FORMAT, "format_version": 1, "name": "t", "mode": "style",
            "plot_type": "boxplot_or_violin_with_points", "journal_style": "publication",
            "style": style or {"tick_label_pt": 7.0, "spine_width_pt": 0.5},
            "layout": {"column_width": "89mm"}, "options": {}, "output": {"dpi": 300},
            "universal": True}


# --- physical width ---------------------------------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    ("single", 110.0), ("double", 180.0), ("89mm", 89.0), ("89 mm", 89.0), (183, 183.0),
    ("55", 55.0), ("bogus", None), (10, None), (400, None), (None, None), (True, None),
])
def test_resolve_width_mm(value, expected):
    assert resolve_width_mm(value) == expected


def test_numeric_column_width_sets_the_figure_width():
    style = load_profile("publication")
    w_in, h_in = style.figure_size_inches("89mm", aspect=0.5)
    assert abs(w_in * 25.4 - 89.0) < 1e-6
    assert abs(h_in / w_in - 0.5) < 1e-6
    # unknown strings still fall back to the default alias, as before
    assert style.figure_size_inches("nonsense") == style.figure_size_inches("default")


def test_renderer_honours_numeric_width():
    spec, df, aux = pp.synthetic_spec("boxplot_or_violin_with_points")
    spec["layout"] = {**spec.get("layout", {}), "column_width": "89mm"}
    res = registry.render(spec, df, aux=aux)
    assert abs(res.figure.get_size_inches()[0] * 25.4 - 89.0) < 0.5


# --- preview ----------------------------------------------------------------------------------

def test_preview_pair_renders_both_images_and_lists_changes():
    preset = _style_preset()
    r = pp.preview_pair(preset, "boxplot_or_violin_with_points")
    assert r.before_png[:8] == b"\x89PNG\r\n\x1a\n" and r.after_png[:8] == b"\x89PNG\r\n\x1a\n"
    assert r.before_png != r.after_png
    labels = {c.label for c in r.changes}
    assert {"style.tick_label_pt", "style.spine_width_pt", "layout.column_width"} <= labels
    assert r.safe_to_apply and not r.protected_violations
    assert "synthetic" in r.synthetic_data_notice


def test_preview_carries_the_users_current_look_into_the_before_image():
    preset = _style_preset()
    base = {"style": {"tick_label_pt": 14.0}, "layout": {"title": "MUST NOT LEAK", "aspect": 0.9}}
    r = pp.preview_pair(preset, "boxplot_or_violin_with_points", base_spec=base)
    # the before image used 14 pt ticks, so the preset's 7 pt is a change from 14
    tick = next(c for c in r.changes if c.label == "style.tick_label_pt")
    assert tick.old == 14.0 and tick.new == 7.0
    # data-describing layout keys from the caller are never used
    assert all(c.key != "title" for c in r.changes)


def test_preview_does_not_mutate_the_caller_preset_or_base():
    preset = _style_preset()
    base = {"style": {"tick_label_pt": 14.0}}
    p0, b0 = copy.deepcopy(preset), copy.deepcopy(base)
    pp.preview_pair(preset, "kaplan_meier_survival_curve", base_spec=base)
    assert preset == p0 and base == b0


def test_preview_works_for_every_registered_plot_type_smoke():
    """Cheap smoke: only the three families most sensitive to sizing; the full sweep is in the
    preset QC script."""
    preset = _style_preset()
    for pt in ("heatmap_clustered_matrix", "volcano_plot", "network_graph"):
        r = pp.preview_pair(preset, pt)
        assert r.after_png and r.safe_to_apply


# --- data-safety guard ------------------------------------------------------------------------

def test_style_guard_catches_a_threshold_smuggled_as_an_option():
    bad = _style_preset()
    bad["plot_type"] = "volcano_plot"
    bad["options"] = {"lfc_cutoff": 3.0}
    spec, df, _ = pp.synthetic_spec("volcano_plot")
    with pytest.raises(presets.PresetError, match="lfc_cutoff"):
        pp.apply_with_guard(bad, spec, columns=list(df.columns))
    r = pp.preview_pair(bad, "volcano_plot")
    assert "mapping.lfc_cutoff" in r.protected_violations and not r.safe_to_apply


def test_style_guard_lets_a_purely_visual_preset_through():
    good = _style_preset(palette_name="grayscale", legend_frameon=False)
    spec, df, _ = pp.synthetic_spec("boxplot_or_violin_with_points")
    res = pp.apply_with_guard(good, spec, columns=list(df.columns))
    assert "style.palette_name" in res.applied
    assert pp.assert_style_safe(spec, res.spec) == []


def test_assert_style_safe_protects_roles_labels_and_tests():
    spec, _, _ = pp.synthetic_spec("boxplot_or_violin_with_points")
    changed = copy.deepcopy(spec)
    changed["mapping"]["x"] = "another_column"
    changed.setdefault("layout", {})["y_label"] = "changed"
    changed["statistics"] = {**(spec.get("statistics") or {}), "test": "mannwhitney"}
    v = pp.assert_style_safe(spec, changed)
    assert "mapping.x" in v and "layout.y_label" in v and "statistics.test" in v


# --- layout QC --------------------------------------------------------------------------------

def test_layout_qc_measures_size_and_fonts_at_target_width():
    spec, df, aux = pp.synthetic_spec("grouped_barplot_with_error_bar")
    spec["layout"] = {**spec.get("layout", {}), "column_width": "89mm"}
    spec["style"] = {"tick_label_pt": 6.0, "axis_font_pt": 7.0, "legend_pt": 6.0}
    res = registry.render(spec, df, aux=aux)
    qc = check_text_layout(res.figure, target_width_mm=89, min_font_pt=5)
    assert qc.drawn_width_mm == 89.0
    assert qc.min_font_pt == 6.0
    assert qc.effective_min_font_pt is not None and 4.5 < qc.effective_min_font_pt < 8.0
    assert qc.n_text > 5 and isinstance(qc.as_row()["issues"], str)


def test_layout_qc_flags_a_font_below_the_required_minimum():
    spec, df, aux = pp.synthetic_spec("boxplot_or_violin_with_points")
    spec["style"] = {"tick_label_pt": 3.0}
    res = registry.render(spec, df, aux=aux)
    qc = check_text_layout(res.figure, target_width_mm=89, min_font_pt=5)
    assert any("minimum 5" in i for i in qc.issues)


def test_layout_qc_detects_overlapping_text():
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.text(0.5, 0.5, "AAAAAAAAAA", transform=ax.transAxes, fontsize=14)
    ax.text(0.52, 0.5, "BBBBBBBBBB", transform=ax.transAxes, fontsize=14)
    qc = check_text_layout(fig)
    assert qc.n_overlapping_pairs >= 1 and any("overlapping" in i for i in qc.issues)


def test_layout_qc_detects_a_legend_sitting_on_the_data():
    fig, ax = plt.subplots(figsize=(3, 2))
    x = [0, 1, 2, 3, 4]
    ax.plot(x, [0.5] * 5, label="flat line through the middle")
    ax.set_ylim(0, 1)
    ax.legend(loc="center")
    qc = check_text_layout(fig)
    assert qc.legend_overlaps_data
    fig2, ax2 = plt.subplots(figsize=(3, 2))
    ax2.plot(x, [0.1] * 5, label="low line")
    ax2.set_ylim(0, 1)
    ax2.legend(loc="upper left")
    assert not check_text_layout(fig2).legend_overlaps_data


# --- observation overlay: 0 means adaptive, never invisible -----------------------------------

def test_point_alpha_and_size_zero_mean_adaptive_not_invisible():
    from matplotlib.collections import PathCollection

    from make_my_figure_core.plots.observations import ObservationStyle

    obs = ObservationStyle.from_mapping({"point_alpha": 0.0, "point_size": 0, "point_arrangement": "jitter"})
    assert obs.alpha is None and obs.size is None
    obs2 = ObservationStyle.from_mapping({"point_alpha": 0.5, "point_size": 30})
    assert obs2.alpha == 0.5 and obs2.size == 30.0
    # end to end: a bar plot with points and adaptive opacity draws visible markers
    import pandas as pd
    df = pd.DataFrame({"g": ["a"] * 5 + ["b"] * 7, "v": list(range(5)) + list(range(7))})
    spec = registry.make_spec("barplot_with_error_bar", "t", "publication",
                              mapping={"x": "g", "y": "v", "points": True, "point_alpha": 0.0, "point_size": 0.0})
    out = registry.render(spec, df)
    scat = [c for c in out.figure.axes[0].collections if isinstance(c, PathCollection)]
    assert scat and all((c.get_alpha() or 0) > 0.3 for c in scat)
    assert sum(len(c.get_offsets()) for c in scat) == 12
