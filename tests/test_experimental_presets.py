"""The experimental preset library: read-only, style-only, neutral names, honest provenance.

The rules a bundled experimental preset must satisfy are enforced by ``validate_experimental_preset``
and exercised here on synthetic files, then on every file actually shipped in
``style_profiles/experimental_publication_presets`` (if any). The shipped files are also rendered on
every registered plot type through the guarded apply path, so a preset that breaks a renderer or
changes anything analytical fails the suite.
"""

from __future__ import annotations

import copy
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

from make_my_figure_core import experimental_presets as xp
from make_my_figure_core import preset_preview as pv
from make_my_figure_core import presets
from make_my_figure_core.plots import registry
from make_my_figure_core.plots.registry import available_plot_types


@pytest.fixture(autouse=True)
def _close():
    yield
    plt.close("all")


def _good():
    return {
        "format": presets.PRESET_FORMAT, "format_version": 1, "name": "Compact single column (test)",
        "description": "test", "mode": "style", "plot_type": "boxplot_or_violin_with_points",
        "journal_style": "publication",
        "style": {"tick_label_pt": 6.0, "axis_font_pt": 7.0, "spine_width_pt": 0.5},
        "layout": {"column_width": "89mm"}, "options": {}, "output": {"width_mm": 89.0, "dpi": 300},
        "universal": True,
        "experimental": {"preset_id": "t_compact", "status": "experimental", "evidence_family": "test",
                         "evidence_summary": "unit test", "derived_from": {"papers": 0},
                         "not_official": True, "target_width_mm": 89.0, "width_class": "single"},
    }


def test_valid_experimental_preset_passes():
    xp.validate_experimental_preset(_good())


@pytest.mark.parametrize("mutate,match", [
    (lambda p: p.update(mode="full"), "style presets"),
    (lambda p: p.update(mapping_roles={"x": "a"}), "must not carry"),
    (lambda p: p["options"].update(lfc_cutoff=2.0), "change what is computed"),
    (lambda p: p["options"].update(error="sd"), "change what is computed"),
    (lambda p: p.pop("experimental"), "provenance block"),
    (lambda p: p["experimental"].update(not_official=False), "not_official"),
    (lambda p: p.update(name="Nature preset"), "journal or compliance wording"),
    (lambda p: p.update(name="Journal-ready compact"), "journal or compliance wording"),
    (lambda p: p["layout"].update(column_width="single"), "column_width must equal"),
    (lambda p: p["output"].update(width_mm=120.0), "output.width_mm"),
    (lambda p: p["experimental"].update(target_width_mm=10), "between 30 and 300"),
])
def test_rules_are_enforced(mutate, match):
    p = _good()
    mutate(p)
    with pytest.raises(presets.PresetError, match=match):
        xp.validate_experimental_preset(p)


def test_cell_is_allowed_inside_a_description_but_not_as_a_journal_name():
    p = _good()
    p["description"] = "suits single-cell expression panels"
    xp.validate_experimental_preset(p)
    p["name"] = "Cell style"
    with pytest.raises(presets.PresetError):
        xp.validate_experimental_preset(p)


def test_listing_skips_invalid_files_and_filters_by_plot_type(tmp_path):
    good = _good()
    json.dump(good, open(tmp_path / "a.mmfpreset.json", "w"))
    bad = _good()
    bad["mode"] = "full"
    json.dump(bad, open(tmp_path / "b.mmfpreset.json", "w"))
    specific = _good()
    specific["universal"] = False
    specific["plot_type"] = "volcano_plot"
    specific["experimental"]["preset_id"] = "t_volcano"
    json.dump(specific, open(tmp_path / "c.mmfpreset.json", "w"))
    entries = xp.list_experimental_presets(str(tmp_path))
    assert [e.preset_id for e in entries] == ["t_compact", "t_volcano"]
    assert [e.preset_id for e in xp.list_experimental_presets(str(tmp_path), plot_type="heatmap_clustered_matrix")] == ["t_compact"]
    assert entries[0].label.endswith("[experimental, 89 mm]")
    loaded = xp.load_experimental_preset("t_volcano", str(tmp_path))
    assert loaded["plot_type"] == "volcano_plot"
    with pytest.raises(presets.PresetError):
        xp.load_experimental_preset("nope", str(tmp_path))


def test_missing_directory_lists_nothing(tmp_path):
    assert xp.list_experimental_presets(str(tmp_path / "absent")) == []


def test_clone_for_lab_is_a_plain_user_preset_with_provenance():
    c = xp.clone_for_lab(_good(), name="Our lab")
    assert not xp.is_experimental(c)
    presets.validate_preset(c)
    assert c["provenance"]["experimental_preset_id"] == "t_compact"
    assert any("lab copy" in n for n in c["notes"])
    assert presets.preset_contains_data(c) == []


def test_provenance_text_mentions_the_notice_and_the_width():
    t = xp.provenance_text(_good())
    assert "not official journal templates" in t and "89 mm" in t


# --- the shipped library --------------------------------------------------------------------

SHIPPED = xp.list_experimental_presets()


@pytest.mark.parametrize("entry", SHIPPED, ids=lambda e: e.preset_id)
def test_shipped_preset_obeys_the_rules_and_names_its_evidence(entry):
    p = xp.load_experimental_preset(entry.path)
    xp.validate_experimental_preset(p)
    exp = p["experimental"]
    d = exp["derived_from"]
    assert d.get("papers", 0) >= 30, "a shipped preset needs at least 30 papers behind it"
    assert exp.get("value_evidence"), "every shipped preset states the evidence class of its values"
    assert set(exp["value_evidence"]).issubset(set(p["style"]) | set(p["layout"]) | set(p["output"])
                                               | set(p.get("options") or {}) | {"palette", "legend_location"})
    assert all(v.split(":")[0] in ("OBSERVED", "INFERRED", "ESTIMATED", "OFFICIAL", "SHARED")
               for v in exp["value_evidence"].values())
    # style tokens must be ones the engine can apply
    assert set(p["style"]) <= presets.STYLE_TOKEN_KEYS


@pytest.mark.parametrize("entry", SHIPPED, ids=lambda e: e.preset_id)
@pytest.mark.parametrize("pt", available_plot_types())
def test_shipped_preset_renders_every_plot_type_without_touching_analysis(entry, pt):
    p = xp.load_experimental_preset(entry.path)
    spec, df, aux = pv.synthetic_spec(pt)
    before = copy.deepcopy(spec)
    res = pv.apply_with_guard(p, spec, columns=list(df.columns))
    assert pv.assert_style_safe(before, res.spec) == []
    out = registry.render(res.spec, df, aux=aux)
    assert out.figure is not None
    if p["experimental"].get("target_width_mm") and pt not in p["experimental"].get("width_exempt_plot_types", []):
        assert abs(out.figure.get_size_inches()[0] * 25.4 - p["experimental"]["target_width_mm"]) < 0.5


def test_annotation_geometry_allowed_but_not_content():
    p = _good()
    p["statistics_display"] = {"annotation": {"font_size": 6.0, "line_width": 0.6, "gap_frac": 0.05}}
    xp.validate_experimental_preset(p)
    p["statistics_display"]["annotation"]["content"] = "stars"
    with pytest.raises(presets.PresetError, match="not what they say"):
        xp.validate_experimental_preset(p)
