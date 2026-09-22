"""Tests for ``chord_diagram`` (Circos-style chord diagram).

Focused tests a renderer needs (see .agents/makemyfigure-developer/references/testing.md):
registration, column validation, render from the bundled example, numeric truth of the geometry,
missing values, edge cases, option controls, PlotSpec round trip, preset extraction, export.
Registry-wide suites (preset QC, examples, UI wiring, capabilities audit) pick the plot up
automatically.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from make_my_figure_core import examples, ui_hints
from make_my_figure_core.plots import registry
from make_my_figure_core.plots.base import RenderError
from make_my_figure_core.plots.registry import (available_plot_types, default_mapping, display_name,
                                                make_spec, render, render_to_files)
from make_my_figure_core.spec.validate import validate_plot_spec

PT = "chord_diagram"


@pytest.fixture(autouse=True)
def _close():
    yield
    plt.close("all")


@pytest.fixture
def example():
    info, aux, spec = examples.load_example(PT)
    return info.dataframe, spec


def _digest(df: pd.DataFrame) -> str:
    return hashlib.sha256(pd.util.hash_pandas_object(df, index=True).to_numpy().tobytes()).hexdigest()


def _spec(mapping, **layout):
    spec = make_spec(PT, "links.csv", "publication", mapping=mapping)
    if layout:
        spec["layout"] = layout
    return spec


def _small():
    return pd.DataFrame({
        "from": ["A", "A", "B", "C", "C", "A"],
        "to": ["B", "C", "C", "A", "C", "A"],
        "n": [10.0, 5.0, 20.0, 15.0, 4.0, 6.0],
        "kind": ["x", "x", "y", "z", "z", "x"],
    })


def _spans(meta):
    return {c: abs(a - b) for c, (a, b) in meta["segment_spans_deg"].items()}


# --- registration -----------------------------------------------------------------------------
def test_plot_type_is_wired_into_every_surface():
    assert PT in registry._RENDERERS and PT in registry._DEFAULT_MAPPINGS and PT in registry._DISPLAY_NAMES
    assert PT in available_plot_types()
    assert display_name(PT) == "Circos-style chord diagram"
    assert ui_hints.column_fields(PT) == ["source", "target", "value", "group"]
    keys = {o.key for o in ui_hints.options(PT)}
    assert keys == {"segment_order", "gap_degrees", "start_angle", "ribbon_color_by", "ribbon_alpha",
                    "min_value", "directed", "draw_self_links", "show_labels", "label_placement",
                    "show_ticks", "show_legend"}
    scopes = {o.key: o.scope for o in ui_hints.options(PT)}
    assert {k for k, v in scopes.items() if v == "config"} == {"min_value", "directed", "draw_self_links"}


def test_example_plotspec_validates_against_registry(example):
    _, spec = example
    validate_plot_spec(spec, known_plot_types=available_plot_types())


def test_bundled_example_renders_with_six_segments_and_a_group_band(example):
    df, spec = example
    result = render(spec, df)
    meta = result.metadata
    assert meta["plot_type"] == PT
    assert meta["n_categories"] == 6
    assert set(meta["category_groups"].values()) == {"Immune", "Stromal", "Epithelial"}
    assert meta["n_self_links"] == 6
    assert result.warnings == []
    assert result.figure.axes[0].get_legend() is not None


# --- column validation ------------------------------------------------------------------------
@pytest.mark.parametrize("role", ["source", "target"])
def test_missing_required_role_is_reported_by_name(example, role):
    df, spec = example
    bad = copy.deepcopy(spec)
    bad["mapping"][role] = "__absent__"
    with pytest.raises(RenderError, match="__absent__"):
        render(bad, df)


def test_unmapped_required_role_raises(example):
    df, spec = example
    bad = copy.deepcopy(spec)
    del bad["mapping"]["source"]
    with pytest.raises(RenderError, match="source"):
        render(bad, df)


def test_value_column_with_no_numbers_is_an_error():
    df = _small()
    df["n"] = "abc"
    with pytest.raises(RenderError, match="numeric"):
        render(_spec({"source": "from", "target": "to", "value": "n"}), df)


# --- numeric truth of the geometry ------------------------------------------------------------
def test_segment_spans_are_proportional_to_category_totals():
    df = _small()
    meta = render(_spec({"source": "from", "target": "to", "value": "n", "gap_degrees": 2}), df).metadata
    totals = meta["category_totals"]
    # undirected: A-B 10, A-C 5+15 = 20 (merged), B-C 20, C-C 4 (self once), A-A 6 (self once)
    assert totals == {"A": 36.0, "B": 30.0, "C": 44.0}
    spans = _spans(meta)
    usable = 360.0 - 3 * 2.0
    for c, t in totals.items():
        assert spans[c] == pytest.approx(usable * t / sum(totals.values()), abs=1e-3)  # spans stored to 4 dp
    assert meta["n_links_drawn"] == 5  # A-B, A-C (merged), B-C, C-C, A-A


def test_directed_keeps_both_directions_and_counts_in_and_out_flow():
    df = _small()
    meta = render(_spec({"source": "from", "target": "to", "value": "n", "directed": True}), df).metadata
    assert meta["directed"] is True
    assert meta["n_links_drawn"] == 6
    # A: out 10+5+6(self) ; in 15 -> 36 ; B: out 20, in 10 -> 30 ; C: out 15+4, in 5+20 -> 44
    assert meta["category_totals"] == {"A": 36.0, "B": 30.0, "C": 44.0}


def test_equal_weights_when_no_value_column():
    df = _small()
    meta = render(_spec({"source": "from", "target": "to"}), df).metadata
    assert meta["weights"].startswith("equal")
    assert meta["value_column"] is None
    # every row weighs 1; the two A-C rows merge into one undirected link of weight 2
    assert meta["category_totals"] == {"A": 4.0, "B": 2.0, "C": 4.0}


def test_duplicate_rows_are_summed_into_one_ribbon():
    df = pd.DataFrame({"s": ["A", "A", "B"], "t": ["B", "B", "C"], "v": [1, 2, 3]})
    meta = render(_spec({"source": "s", "target": "t", "value": "v"}), df).metadata
    assert meta["n_links_drawn"] == 2
    assert meta["category_totals"]["A"] == 3.0


@pytest.mark.parametrize("order,expected", [
    ("input", ["A", "B", "C"]),
    ("alphabetical", ["A", "B", "C"]),
    ("by_total_flow", ["C", "A", "B"]),
])
def test_segment_order_option(order, expected):
    df = _small()
    meta = render(_spec({"source": "from", "target": "to", "value": "n", "segment_order": order}), df).metadata
    assert meta["categories"] == expected
    assert meta["segment_order"] == order


def test_start_angle_and_gap_are_honoured():
    df = _small()
    meta = render(_spec({"source": "from", "target": "to", "value": "n",
                         "start_angle": 0, "gap_degrees": 10}), df).metadata
    first = meta["categories"][0]
    assert meta["segment_spans_deg"][first][0] == pytest.approx(0.0)
    assert meta["gap_degrees"] == 10.0
    assert sum(_spans(meta).values()) == pytest.approx(360.0 - 3 * 10.0)


# --- filtering options (config scope) ---------------------------------------------------------
def test_min_value_threshold_drops_and_counts_links():
    df = _small()
    r = render(_spec({"source": "from", "target": "to", "value": "n", "min_value": 6, "directed": True}), df)
    assert r.metadata["n_rows_dropped"] == {"below_min_value": 2}   # 5 and 4
    assert any("below min value" in w for w in r.warnings)
    assert r.metadata["n_links_drawn"] == 4


def test_self_links_can_be_hidden():
    df = _small()
    r = render(_spec({"source": "from", "target": "to", "value": "n", "draw_self_links": False}), df)
    assert r.metadata["n_self_links"] == 0
    assert r.metadata["n_rows_dropped"]["self_link_hidden"] == 2
    assert r.metadata["category_totals"] == {"A": 30.0, "B": 30.0, "C": 40.0}


def test_every_link_filtered_out_is_a_clear_error():
    df = _small()
    with pytest.raises(RenderError, match="no links"):
        render(_spec({"source": "from", "target": "to", "value": "n", "min_value": 1e6}), df)


# --- groups -----------------------------------------------------------------------------------
def test_group_is_looked_up_for_source_and_target_categories():
    # "C" never appears as a source in this table, so its group comes from the row where it is the target.
    df = pd.DataFrame({"s": ["A", "B"], "t": ["B", "C"], "v": [1, 2], "g": ["g1", "g2"]})
    r = render(_spec({"source": "s", "target": "t", "value": "v", "group": "g"}), df)
    assert r.metadata["category_groups"] == {"A": "g1", "B": "g2", "C": "g2"}
    assert r.metadata["group_levels"] == ["g1", "g2"]


def test_conflicting_group_assignment_keeps_first_and_warns():
    df = pd.DataFrame({"s": ["A", "A", "B"], "t": ["B", "B", "A"], "v": [1, 1, 1], "g": ["g1", "g2", "g1"]})
    r = render(_spec({"source": "s", "target": "t", "value": "v", "group": "g"}), df)
    assert r.metadata["category_groups"]["A"] == "g1"
    assert any("more than one group" in w for w in r.warnings)


def test_ribbon_colour_by_group_without_group_column_falls_back_with_warning():
    df = _small()
    r = render(_spec({"source": "from", "target": "to", "value": "n", "ribbon_color_by": "group"}), df)
    assert r.metadata["ribbon_color_by"] == "source"
    assert any("group column" in w for w in r.warnings)


def test_no_legend_without_group_or_when_hidden(example):
    df, spec = example
    s = copy.deepcopy(spec)
    del s["mapping"]["group"]
    assert render(s, df).figure.axes[0].get_legend() is None
    s2 = copy.deepcopy(spec)
    s2["mapping"]["show_legend"] = False
    assert render(s2, df).figure.axes[0].get_legend() is None


# --- missing values and edge cases -----------------------------------------------------------
def test_missing_negative_and_blank_rows_are_dropped_with_one_warning(example):
    df, spec = example
    df2 = df.copy()
    df2.loc[df2.index[0], "interactions"] = np.nan
    df2.loc[df2.index[1], "interactions"] = -3
    df2.loc[df2.index[2], "target_cell"] = ""
    r = render(spec, df2)
    assert r.metadata["n_rows_dropped"] == {"blank_category": 1, "missing_or_non_numeric_value": 1,
                                            "negative_value": 1}
    assert len([w for w in r.warnings if "not drawn" in w]) == 1


def test_two_categories_and_a_single_link_still_draw():
    df = pd.DataFrame({"s": ["A"], "t": ["B"], "v": [3]})
    meta = render(_spec({"source": "s", "target": "t", "value": "v"}), df).metadata
    assert meta["n_categories"] == 2
    assert sum(_spans(meta).values()) == pytest.approx(360.0 - 2 * 3.0)


def test_many_categories_reduce_the_gap_and_warn_about_labels():
    n = 30
    cats = [f"cat{i:02d}" for i in range(n)]
    df = pd.DataFrame({"s": cats, "t": cats[1:] + cats[:1], "v": np.arange(1, n + 1)})
    r = render(_spec({"source": "s", "target": "t", "value": "v", "gap_degrees": 20}), df)
    assert r.metadata["gap_degrees"] < 20
    assert any("labels may overlap" in w for w in r.warnings)


def test_long_labels_are_wrapped_not_shrunk(example):
    df, spec = example
    df2 = df.copy()
    for col in ("source_cell", "target_cell"):
        df2[col] = df2[col].astype(str) + " with a longer name"
    r = render(spec, df2)
    texts = [t.get_text() for t in r.figure.axes[0].texts]
    assert any("\n" in t for t in texts)
    assert not any("shrunk" in w for w in r.warnings)


def test_input_dataframe_is_not_mutated(example):
    df, spec = example
    before = _digest(df)
    render(spec, df)
    assert _digest(df) == before


# --- presentation options (style scope) -------------------------------------------------------
@pytest.mark.parametrize("option", [
    {"label_placement": "tangential"}, {"show_labels": False}, {"show_ticks": True},
    {"ribbon_color_by": "target"}, {"ribbon_color_by": "group"}, {"ribbon_alpha": 1.0},
    {"directed": True, "show_ticks": True, "label_placement": "tangential"},
])
def test_presentation_options_render(example, option):
    df, spec = example
    s = copy.deepcopy(spec)
    s["mapping"].update(option)
    r = render(s, df)
    assert r.figure.axes


def test_ticks_record_the_step_and_append_totals_to_labels(example):
    df, spec = example
    s = copy.deepcopy(spec)
    s["mapping"]["show_ticks"] = True
    r = render(s, df)
    assert r.metadata["tick_step"] == 50.0
    texts = " ".join(t.get_text() for t in r.figure.axes[0].texts)
    assert "(189)" in texts and "ticks every 50" in texts


def test_invalid_option_values_fall_back_to_defaults(example):
    df, spec = example
    s = copy.deepcopy(spec)
    s["mapping"].update({"segment_order": "sideways", "ribbon_alpha": "lots", "gap_degrees": -5,
                         "label_placement": "diagonal", "directed": "yes"})
    meta = render(s, df).metadata
    assert meta["segment_order"] == "input"
    assert meta["ribbon_alpha"] == 0.65
    assert meta["gap_degrees"] == 0.0
    assert meta["label_placement"] == "radial"
    assert meta["directed"] is True


def test_layout_title_and_legend_location_are_honoured(example):
    df, spec = example
    s = copy.deepcopy(spec)
    s["layout"] = {**s.get("layout", {}), "title": "Interactions", "legend_location": "outside right"}
    r = render(s, df)
    ax = r.figure.axes[0]
    assert ax.get_title() == "Interactions"
    assert ax.get_legend() is not None


def test_no_statistics_are_computed_or_claimed(example):
    df, spec = example
    meta = render(spec, df).metadata
    assert "statistics_report" not in meta
    assert "No inferential statistics" in meta["statistics_note"]


# --- PlotSpec round trip / reproducibility ----------------------------------------------------
def test_plotspec_round_trip_reproduces_metadata(example, tmp_path):
    df, spec = example
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    spec2 = json.loads(path.read_text(encoding="utf-8"))
    m1 = render(spec, df).metadata
    m2 = render(spec2, df).metadata
    for m in (m1, m2):
        m.pop("spec", None)
    assert json.dumps(m1, sort_keys=True, default=str) == json.dumps(m2, sort_keys=True, default=str)


def test_metadata_is_json_serialisable(example):
    df, spec = example
    json.dumps(render(spec, df).metadata)


def test_style_preset_carries_style_options_but_not_config_or_columns(example):
    from make_my_figure_core import presets
    df, spec = example
    s = copy.deepcopy(spec)
    s["mapping"].update({"ribbon_alpha": 0.9, "min_value": 12})
    style_preset = presets.extract_preset(s, mode="style") if hasattr(presets, "extract_preset") else None
    if style_preset is None:
        pytest.skip("presets.extract_preset not available in this checkout")
    dumped = json.dumps(style_preset)
    assert "ribbon_alpha" in dumped
    assert "min_value" not in dumped
    assert "source_cell" not in dumped and "target_cell" not in dumped


# --- export -----------------------------------------------------------------------------------
def test_exports_all_formats_with_sidecar(example, tmp_path):
    df, spec = example
    s = copy.deepcopy(spec)
    s["output"]["formats"] = ["svg", "png", "pdf"]
    render_to_files(s, df, str(tmp_path / "fig"))
    written = sorted(p.name for p in tmp_path.iterdir())
    assert any(n.endswith(".svg") for n in written) and any(n.endswith(".pdf") for n in written)
    assert any(n.endswith(".plot_spec.json") for n in written), written
