"""Figure Presets: the configuration of a figure, separated from its data, for every plot type.

What is pinned here is the separation itself. A preset that quietly carried a table name, a
column name or a threshold into a lab's shared style would produce figures that *look* finished
and are wrong for the new data. So the tests check, for every registered plot type, that a style
preset contains nothing data-bound; that a full preset carries roles but never row values; that
applying either onto a different table leaves that table's identity intact; and that a role the
new table cannot satisfy is reported, never substituted.

All fixtures are the bundled synthetic examples and mock samples.
"""

from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

from make_my_figure_core import examples as ex
from make_my_figure_core import presets as P
from make_my_figure_core import ui_hints
from make_my_figure_core.plots.registry import available_plot_types, make_spec, render

ALL_TYPES = available_plot_types()


def _example(plot_type):
    info, aux, spec = ex.load_example(plot_type)
    return info, aux, dict(spec)


def _render(spec, info, aux):
    return render(spec, info.dataframe, aux={k: v.dataframe for k, v in aux.items()} if aux else None)


@pytest.fixture(autouse=True)
def _close():
    yield
    plt.close("all")


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("MAKE_MY_FIGURE_PRESETS", str(tmp_path / "presets"))
    return P.PresetStore()


# --------------------------------------------------------------------------------------
# scope declarations are complete and sane
# --------------------------------------------------------------------------------------

def test_every_option_declares_a_valid_scope():
    for pt in ALL_TYPES:
        for opt in ui_hints.options(pt):
            assert opt.scope in ui_hints.OPTION_SCOPES, f"{pt}.{opt.key}"


def test_invalid_scope_is_rejected_at_definition():
    with pytest.raises(ValueError, match="scope"):
        ui_hints.Option("k", "K", "bool", False, scope="visual")


@pytest.mark.parametrize("pt,key", [
    ("volcano_plot", "lfc_cutoff"), ("volcano_plot", "p_cutoff"),
    ("manhattan_plot", "genome_wide_threshold"), ("ma_plot", "p_cutoff"),
    ("histogram_distribution", "bins"), ("histogram_distribution", "x_min"),
    ("heatmap_clustered_matrix", "linkage_method"), ("network_graph", "corr_cutoff"),
    ("kaplan_meier_survival_curve", "input_form"),
])
def test_thresholds_and_data_dependent_options_are_config_scoped(pt, key):
    """A lab style must never carry a scientific threshold or a data-shape decision."""
    scopes = P.option_scopes(pt)
    assert scopes[key] == "config", f"{pt}.{key} leaked into style scope"


@pytest.mark.parametrize("pt,key", [
    ("boxplot_or_violin_with_points", "kind"), ("histogram_distribution", "draw_style"),
    ("heatmap_clustered_matrix", "colormap"), ("network_graph", "node_color"),
    ("barplot_with_error_bar", "x_tick_rotation"), ("forest_plot", "reference"),
])
def test_visual_options_are_style_scoped(pt, key):
    assert P.option_scopes(pt)[key] == "style"


# --------------------------------------------------------------------------------------
# every registered plot type: style preset carries no data
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("pt", ALL_TYPES)
def test_style_preset_has_no_data_for_every_plot_type(pt):
    info, aux, spec = _example(pt)
    spec["style"] = {"title_font_pt": 15.5, "palette_name": "high_contrast"}
    spec["layout"] = {**(spec.get("layout") or {}), "title": "SECRET TITLE", "x_label": "SECRET X",
                      "x_tick_rotation": 45}
    preset = P.extract_preset(spec, mode="style", name=f"{pt} style")
    P.validate_preset(preset)
    assert preset["mode"] == "style"
    assert P.preset_contains_data(preset) == []
    text = json.dumps(preset)
    # no table, no provenance, no column names, no labels
    assert spec["input_table"] not in text
    assert "SECRET" not in text
    for role, col in P.split_mapping(pt, spec["mapping"]).roles.items():
        for c in (col if isinstance(col, list) else [col]):
            if c and isinstance(c, str) and len(c) > 2:
                assert f'"{c}"' not in text, f"{pt}: column {c!r} for role {role} leaked"
    # and no row values
    df = info.dataframe
    for col in df.columns[:3]:
        for v in df[col].head(3):
            if isinstance(v, str) and len(v) > 4:
                assert v not in text
    # what it does carry
    assert preset["style"]["title_font_pt"] == 15.5
    assert preset["layout"]["x_tick_rotation"] == 45


@pytest.mark.parametrize("pt", ALL_TYPES)
def test_full_preset_carries_roles_but_never_the_table(pt):
    info, aux, spec = _example(pt)
    spec["layout"] = {**(spec.get("layout") or {}), "title": "Kept title"}
    preset = P.extract_preset(spec, mode="full", name=f"{pt} full")
    P.validate_preset(preset)
    assert preset["mode"] == "full"
    assert P.preset_contains_data(preset) == []
    assert "input_table" not in preset and "source" not in preset
    assert preset["labels"].get("title") == "Kept title"
    roles = P.split_mapping(pt, spec["mapping"]).roles
    assert preset["mapping_roles"] == roles


# --------------------------------------------------------------------------------------
# apply: new data stays new data, settings come back
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("pt", ALL_TYPES)
def test_style_preset_applies_to_a_fresh_spec_and_renders(pt):
    info, aux, spec = _example(pt)
    spec["style"] = {"title_font_pt": 15.5, "axis_font_pt": 11.0, "palette_name": "grayscale",
                     "line_width_pt": 2.4}
    spec["layout"] = {**(spec.get("layout") or {}), "x_tick_rotation": 45,
                      "legend_location": "outside right", "margin_left": 0.2}
    spec["output"] = {**spec["output"], "dpi": 450}
    preset = P.extract_preset(spec, mode="style")

    fresh = make_spec(pt, "brand_new_table.csv", "publication", mapping=dict(spec["mapping"]))
    res = P.apply_preset(preset, fresh, columns=info.columns)
    assert res.spec["input_table"] == "brand_new_table.csv"          # identity untouched
    assert res.spec["style"]["title_font_pt"] == 15.5
    assert res.spec["style"]["palette_name"] == "grayscale"
    assert res.spec["layout"]["x_tick_rotation"] == 45
    assert res.spec["layout"]["legend_location"] == "outside right"
    assert res.spec["output"]["dpi"] == 450
    assert not res.unresolved_roles
    r = _render(res.spec, info, aux)
    assert r.figure is not None
    assert r.metadata["n_rows"] == len(info.dataframe)
    # the source spec was not modified by apply
    assert "title_font_pt" not in (fresh.get("style") or {})


def test_apply_never_substitutes_a_missing_column():
    info, aux, spec = _example("scatterplot_with_regression")
    preset = P.extract_preset(spec, mode="full")
    fresh = make_spec("scatterplot_with_regression", "other.csv", "publication", mapping={})
    res = P.apply_preset(preset, fresh, columns=["dose", "response", "arm"])
    # every role the new table lacks is reported, and nothing was written for it
    for role, wanted in preset["mapping_roles"].items():
        if wanted not in ("dose", "response", "arm"):
            assert role in res.unresolved_roles
            assert res.spec["mapping"].get(role) in (None, "")
    assert res.needs_remapping
    assert any("nothing was substituted" in w for w in res.warnings)


def test_apply_maps_roles_when_the_new_table_has_them():
    info, aux, spec = _example("scatterplot_with_regression")
    preset = P.extract_preset(spec, mode="full")
    fresh = make_spec("scatterplot_with_regression", "other.csv", "publication", mapping={})
    res = P.apply_preset(preset, fresh, columns=info.columns)
    assert not res.unresolved_roles
    for role, wanted in preset["mapping_roles"].items():
        assert res.spec["mapping"][role] == wanted


def test_multi_column_role_requires_every_listed_column():
    spec = make_spec("kaplan_meier_survival_curve", "a.csv", "publication",
                     mapping={"input_form": "precomputed", "time": "t",
                              "survival_columns": ["s1", "s2", "s3"]})
    preset = P.extract_preset(spec, mode="full")
    fresh = make_spec("kaplan_meier_survival_curve", "b.csv", "publication", mapping={})
    res = P.apply_preset(preset, fresh, columns=["t", "s1", "s2"])       # s3 missing
    assert "survival_columns" in res.unresolved_roles
    assert res.spec["mapping"].get("survival_columns") is None


def test_full_preset_for_another_plot_type_is_refused():
    _, _, spec = _example("volcano_plot")
    preset = P.extract_preset(spec, mode="full")
    fresh = make_spec("barplot_with_error_bar", "x.csv", "publication")
    with pytest.raises(P.PresetError, match="cannot be applied"):
        P.apply_preset(preset, fresh, columns=["k", "v"])


def test_style_preset_for_another_plot_type_applies_universal_parts_only():
    """The lab-wide typography case: apply, but drop and list the plot-specific options."""
    _, _, spec = _example("boxplot_or_violin_with_points")
    spec["style"] = {"title_font_pt": 17}
    spec["mapping"]["kind"] = "violin"
    preset = P.extract_preset(spec, mode="style")
    fresh = make_spec("barplot_with_error_bar", "x.csv", "publication")
    res = P.apply_preset(preset, fresh, columns=["k", "v"])
    assert res.spec["style"]["title_font_pt"] == 17
    assert "kind" not in res.spec["mapping"]
    assert any("options.kind" in s for s in res.skipped)
    assert any("universal settings" in w for w in res.warnings)


def test_thresholds_travel_only_in_full_mode():
    _, _, spec = _example("volcano_plot")
    spec["mapping"]["lfc_cutoff"] = 2.5
    spec["mapping"]["label_box"] = True
    style = P.extract_preset(spec, mode="style")
    full = P.extract_preset(spec, mode="full")
    assert "lfc_cutoff" not in style["options"]
    assert style["options"]["label_box"] is True
    assert full["config_options"]["lfc_cutoff"] == 2.5


def test_statistics_display_is_style_but_the_test_is_config():
    spec = make_spec("barplot_with_error_bar", "x.csv", "publication",
                     mapping={"x": "k", "y": "v"},
                     statistics={"enabled": True, "test": "welch_t", "comparison_mode": "vs_control",
                                 "reference_group": "control", "group_column": "k",
                                 "annotation": {"content": "stars", "placement": "above_bar"},
                                 "source": {"source_sheet_name": "Sheet1"}})
    style = P.extract_preset(spec, mode="style")
    full = P.extract_preset(spec, mode="full")
    assert style["statistics_display"]["annotation"]["placement"] == "above_bar"
    assert "statistics" not in style
    assert full["statistics"]["test"] == "welch_t"
    assert "source" not in full["statistics"]          # provenance never travels
    # applying the style preset reinstates the display settings without inventing a test
    fresh = make_spec("barplot_with_error_bar", "y.csv", "publication", mapping={"x": "k", "y": "v"})
    res = P.apply_preset(style, fresh, columns=["k", "v"])
    assert res.spec["statistics"]["annotation"]["placement"] == "above_bar"
    assert not res.spec["statistics"].get("enabled")


def test_statistics_group_column_missing_on_new_table_is_reported():
    spec = make_spec("barplot_with_error_bar", "x.csv", "publication",
                     mapping={"x": "k", "y": "v"},
                     statistics={"enabled": True, "test": "welch_t", "group_column": "k",
                                 "comparison_mode": "all_pairs"})
    full = P.extract_preset(spec, mode="full")
    fresh = make_spec("barplot_with_error_bar", "y.csv", "publication", mapping={})
    res = P.apply_preset(full, fresh, columns=["condition", "value"])
    assert "statistics.group_column" in res.unresolved_roles
    assert res.spec["statistics"]["group_column"] is None


def test_click_picks_and_offsets_never_enter_a_preset():
    """Selected point ids and manual label offsets are about specific rows."""
    spec = make_spec("volcano_plot", "x.csv", "publication",
                     mapping={"x": "logFC", "p": "P", "label": "gene",
                              "selected_labels": ["TP53", "MYC"], "label_offsets": "{}",
                              "selected_points": [3, 9]})
    for mode in P.PRESET_MODES:
        preset = P.extract_preset(spec, mode=mode)
        text = json.dumps(preset)
        assert "TP53" not in text and "selected_points" not in text and "label_offsets" not in text


def test_unknown_style_keys_are_dropped_with_a_note():
    spec = make_spec("barplot_with_error_bar", "x.csv", "publication")
    spec["style"] = {"title_font_pt": 12, "totally_made_up": 3}
    preset = P.extract_preset(spec, mode="style")
    assert "totally_made_up" not in preset["style"]
    assert any("totally_made_up" in n for n in preset.get("notes", []))


# --------------------------------------------------------------------------------------
# files, the library, legacy inputs
# --------------------------------------------------------------------------------------

def test_save_load_roundtrip_is_exact(tmp_path):
    _, _, spec = _example("heatmap_clustered_matrix")
    spec["style"] = {"tick_label_pt": 9}
    preset = P.extract_preset(spec, mode="style", name="Lab heatmap")
    path = P.save_preset(preset, str(tmp_path / "Lab_Default_Heatmap"))
    assert path.endswith(P.PRESET_EXTENSION)
    back = P.load_preset(path)
    assert back == preset


def test_save_refuses_a_preset_that_carries_data(tmp_path):
    _, _, spec = _example("barplot_with_error_bar")
    preset = P.extract_preset(spec, mode="style")
    preset["input_table"] = "private.csv"
    with pytest.raises(P.PresetError, match="carries data"):
        P.save_preset(preset, str(tmp_path / "bad"))


def test_wrong_format_and_newer_version_are_refused(tmp_path):
    with pytest.raises(P.PresetError, match="not a Figure Preset"):
        P.validate_preset({"format": "something_else", "mode": "style", "plot_type": "x"})
    _, _, spec = _example("barplot_with_error_bar")
    preset = P.extract_preset(spec, mode="style")
    preset["format_version"] = P.PRESET_FORMAT_VERSION + 1
    with pytest.raises(P.PresetError, match="newer version"):
        P.validate_preset(preset)


def test_a_raw_plotspec_loads_as_a_full_preset(tmp_path):
    """Backward compatibility: figures saved before presets existed are presets already."""
    _, _, spec = _example("forest_plot")
    p = tmp_path / "old.plot_spec.json"
    p.write_text(json.dumps(spec), encoding="utf-8")
    preset = P.load_preset(str(p))
    assert preset["format"] == P.PRESET_FORMAT and preset["mode"] == "full"
    assert preset["plot_type"] == "forest_plot"
    assert "input_table" not in preset
    assert any("converted from a PlotSpec" in n for n in preset["notes"])


def test_an_exported_sidecar_loads_as_a_preset(tmp_path):
    _, _, spec = _example("roc_curve")
    p = tmp_path / "fig.plot_spec.json"
    p.write_text(json.dumps({"plot_spec": spec, "render_metadata": {"n_rows": 999}}), encoding="utf-8")
    preset = P.load_preset(str(p))
    assert preset["plot_type"] == "roc_curve"
    assert "render_metadata" not in preset and "999" not in json.dumps(preset)


def test_legacy_journal_style_names_are_migrated_on_load(tmp_path):
    _, _, spec = _example("barplot_with_error_bar")
    spec["journal_style"] = "nature_like"
    p = tmp_path / "legacy.json"
    p.write_text(json.dumps(spec), encoding="utf-8")
    assert P.load_preset(str(p))["journal_style"] == "publication"


def test_store_lists_saves_deletes_and_filters_by_plot_type(store):
    _, _, s1 = _example("barplot_with_error_bar")
    _, _, s2 = _example("volcano_plot")
    store.save(P.extract_preset(s1, mode="style", name="Bars"))
    store.save(P.extract_preset(s2, mode="full", name="Volcano full"))
    store.save(P.universal_preset_from(P.extract_preset(s1, mode="style", name="Lab"), name="Lab fonts"))
    names = {e.name for e in store.list()}
    assert names == {"Bars", "Volcano full", "Lab fonts"}
    # per type: own presets plus universal ones
    assert {e.name for e in store.list("volcano_plot")} == {"Volcano full", "Lab fonts"}
    assert {e.name for e in store.list("barplot_with_error_bar")} == {"Bars", "Lab fonts"}
    assert store.delete("Bars") is True
    assert "Bars" not in {e.name for e in store.list()}
    assert store.delete("never existed") is False


def test_store_ignores_foreign_json_files(store):
    store._ensure()
    with open(os.path.join(store.directory, "notes.json"), "w", encoding="utf-8") as fh:
        fh.write('{"hello": "world"}')
    assert store.list() == []


def test_store_import_and_export(store, tmp_path):
    _, _, spec = _example("dose_response_curve")
    preset = P.extract_preset(spec, mode="style", name="Dose")
    external = P.save_preset(preset, str(tmp_path / "shared"))
    store.import_file(external, rename="Dose (imported)")
    assert "Dose (imported)" in {e.name for e in store.list()}
    out = store.export_file("Dose (imported)", str(tmp_path / "out"))
    assert P.load_preset(out)["name"] == "Dose (imported)"


def test_safe_filename_strips_path_characters():
    assert "/" not in P.safe_filename("../../etc/passwd") and ".." not in P.safe_filename("../x")
    assert P.safe_filename("Lab Default: Heatmap!") == "Lab_Default_Heatmap"


def test_default_dir_honours_the_environment_override(monkeypatch, tmp_path):
    monkeypatch.setenv("MAKE_MY_FIGURE_PRESETS", str(tmp_path / "p"))
    assert P.default_preset_dir() == str(tmp_path / "p")


# --------------------------------------------------------------------------------------
# Figure Builder layout presets
# --------------------------------------------------------------------------------------

def _mpf():
    from make_my_figure_core.panels import FigureLayout, MultiPanelFigure, Panel
    i1, _, s1 = _example("barplot_with_error_bar")
    i2, _, s2 = _example("scatterplot_with_regression")
    i3, _, s3 = _example("volcano_plot")
    mpf = MultiPanelFigure(name="Figure 2", layout=FigureLayout(
        ncols=2, nrows=2, wspace=0.3, hspace=0.35, label_style="a", label_size=16,
        fig_width_mm=170, height_ratios=[2, 1], base_font_pt=9.5))
    mpf.add_panel(Panel(plot_spec=s1, table=i1.dataframe, width_in=6.0, height_in=2.5,
                        title="PRIVATE PANEL TITLE"))
    mpf.add_panel(Panel(plot_spec=s2, table=i2.dataframe, width_in=3.0))
    mpf.add_panel(Panel(plot_spec=s3, table=i3.dataframe, width_in=3.0))
    return mpf


def test_layout_preset_keeps_geometry_and_drops_content(tmp_path):
    mpf = _mpf()
    preset = P.extract_layout_preset(mpf, name="Lab two-row layout")
    P.validate_layout_preset(preset)
    text = json.dumps(preset)
    assert "plot_spec" not in text
    assert "PRIVATE PANEL TITLE" not in text
    assert "volcano" not in text and "logFC" not in text
    assert preset["n_panels"] == 3
    assert preset["layout"]["ncols"] == 2 and preset["layout"]["height_ratios"] == [2, 1]
    assert preset["panel_sizes"][0] == {"width_in": 6.0, "height_in": 2.5}
    path = P.save_layout_preset(preset, str(tmp_path / "layout"))
    assert P.load_layout_preset(path) == preset


def test_layout_preset_applies_to_another_composite_and_warns_on_count_mismatch():
    from make_my_figure_core.panels import FigureLayout, MultiPanelFigure, Panel, build_figure
    preset = P.extract_layout_preset(_mpf())
    info, _, s = _example("roc_curve")
    other = MultiPanelFigure(name="Other", layout=FigureLayout())
    other.add_panel(Panel(plot_spec=s, table=info.dataframe))
    other.add_panel(Panel(plot_spec=s, table=info.dataframe))
    res = P.apply_layout_preset(preset, other)
    assert other.layout.ncols == 2 and other.layout.label_style == "a"
    assert other.panels[0].width_in == 6.0 and other.panels[1].width_in == 3.0
    assert other.panels[0].plot_spec is s                                  # content untouched
    assert any("saved for 3 panel" in w for w in res.warnings)
    fig = build_figure(other)
    assert fig is not None
    plt.close(fig)


def test_layout_preset_refuses_panel_content():
    with pytest.raises(P.PresetError, match="panel content"):
        P.validate_layout_preset({"format": P.LAYOUT_PRESET_FORMAT, "format_version": 1,
                                  "layout": {}, "panels": [{"plot_spec": {}}]})


def test_exported_figurespec_loads_as_a_layout_preset(tmp_path):
    from make_my_figure_core.panels import multipanel_sidecar
    mpf = _mpf()
    mpf.legend_text = "x"
    path = multipanel_sidecar(mpf, str(tmp_path / "fig"))
    preset = P.load_layout_preset(path)
    assert preset["n_panels"] == 3 and preset["layout"]["ncols"] == 2
    assert "plot_spec" not in json.dumps(preset)


def test_figure_layout_roundtrips_through_dict():
    from make_my_figure_core.panels import FigureLayout
    lay = FigureLayout(ncols=3, nrows=1, wspace=0.4, label_dx=-0.05, label_dy=1.1,
                       width_ratios=[1, 2, 1], background="transparent")
    back = FigureLayout.from_dict(lay.to_dict())
    assert back == lay
    # unknown keys are ignored rather than fatal
    assert FigureLayout.from_dict({"ncols": 2, "future_key": 1}).ncols == 2
