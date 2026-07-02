"""Tests for learned journal-like style profiles (style_profiles/learned/)."""

import json
import os

import matplotlib
import matplotlib.pyplot as plt
import pytest

matplotlib.use("Agg")

from make_my_figure_core.io.loaders import load_table
from make_my_figure_core.plots.registry import available_plot_types, make_spec, render
from make_my_figure_core.styles.engine import list_profiles, load_profile

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_LEARNED_DIR = os.path.join(_ROOT, "style_profiles", "learned")

LEARNED_NAMES = ["nature_like_learned", "science_like_learned", "cell_like_learned"]

REQUIRED_TOP_KEYS = {"profile_name", "base_profile", "provenance", "typography",
                     "lines", "layout", "color", "legend", "panel_label",
                     "markers", "export"}
REQUIRED_PROVENANCE_KEYS = {"papers_inspected", "figures_inspected", "source_licenses",
                            "source", "date_generated", "not_official_compliance",
                            "no_copied_figures_or_data"}


@pytest.fixture(autouse=True)
def _close_figs():
    yield
    plt.close("all")


def test_learned_profiles_present_in_list():
    profiles = list_profiles()
    for name in LEARNED_NAMES:
        assert name in profiles, f"{name} not exposed by list_profiles()"
    # starter profiles still present
    assert {"nature_like", "science_like", "cell_like"} <= set(profiles)


@pytest.mark.parametrize("name", LEARNED_NAMES)
def test_learned_json_valid_and_complete(name):
    path = os.path.join(_LEARNED_DIR, f"{name}.json")
    assert os.path.exists(path)
    raw = json.load(open(path, encoding="utf-8"))
    assert REQUIRED_TOP_KEYS <= set(raw), f"missing: {REQUIRED_TOP_KEYS - set(raw)}"
    assert REQUIRED_PROVENANCE_KEYS <= set(raw["provenance"])
    # provenance must record CC-licensed sources and no-copy guarantees
    assert raw["provenance"]["no_copied_figures_or_data"] is True
    assert raw["provenance"]["not_official_compliance"] is True
    assert all("CC" in lic.upper() for lic in raw["provenance"]["source_licenses"])


@pytest.mark.parametrize("name", LEARNED_NAMES)
def test_learned_profile_loads_with_no_missing_keys(name):
    p = load_profile(name)
    assert p.is_learned is True
    assert p.palette and all(c.startswith("#") for c in p.palette)
    # core StyleProfile fields are populated (non-None / sane)
    assert p.base_font_pt > 0 and p.axis_font_pt > 0 and p.title_font_pt > 0
    assert p.line_width_pt > 0 and p.spine_width_pt > 0
    assert p.single_column_width_mm > 0 and p.double_column_width_mm > 0
    assert p.preferred_exports
    assert p.extra.get("provenance")   # metadata preserved


@pytest.mark.parametrize("name", LEARNED_NAMES)
def test_every_plot_type_renders_with_learned_profile(name):
    from make_my_figure_core import examples

    for pt in available_plot_types():
        info, aux, _spec = examples.load_example(pt)
        aux_dfs = {k: v.dataframe for k, v in aux.items()} or None
        spec = make_spec(pt, info.source_name, name, mapping=None)
        result = render(spec, info.dataframe, aux=aux_dfs)
        assert result.figure is not None
        assert result.metadata["style_profile"] == name
        plt.close(result.figure)


def test_audit_doc_mentions_provenance_and_license():
    audit = os.path.join(_ROOT, "docs", "STYLE_REFERENCE_AUDIT.md")
    assert os.path.exists(audit)
    text = open(audit, encoding="utf-8").read().lower()
    assert "cc by" in text
    assert "copy" in text          # addresses the no-copying policy
    assert "official journal compliance" in text
    assert "aggregate" in text
