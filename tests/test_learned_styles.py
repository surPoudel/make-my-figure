"""Learned-style machinery + v0.6 single-Publication migration.

v0.6 removed the journal-named profiles (Nature-/Science-/Cell-like and their
"learned" variants) as separate styles. The *learned* mechanism itself remains
for benchmark-derived aggregate Publication defaults (``publication*`` files);
legacy journal names migrate transparently to Publication so old PlotSpecs load.
"""

import os

import matplotlib
import matplotlib.pyplot as plt
import pytest

matplotlib.use("Agg")

from make_my_figure_core.plots.registry import available_plot_types, make_spec, render
from make_my_figure_core.styles.engine import (
    is_legacy_style_name,
    list_profiles,
    load_profile,
    normalize_style_name,
)

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

LEGACY_LEARNED = ["nature_like_learned", "science_like_learned", "cell_like_learned"]
LEGACY_JOURNAL = ["nature_like", "science_like", "cell_like", "journal_like"]


@pytest.fixture(autouse=True)
def _close_figs():
    yield
    plt.close("all")


def test_only_publication_is_listed():
    profiles = list_profiles()
    assert "publication" in profiles
    # No journal-named profiles are surfaced.
    for name in LEGACY_JOURNAL + LEGACY_LEARNED:
        assert name not in profiles


@pytest.mark.parametrize("name", LEGACY_JOURNAL + LEGACY_LEARNED)
def test_legacy_names_migrate_to_publication(name):
    assert is_legacy_style_name(name)
    assert normalize_style_name(name) == "publication"
    p = load_profile(name)          # must not raise
    assert p.name == "publication"


@pytest.mark.parametrize("name", LEGACY_LEARNED + ["nature_like"])
def test_every_plot_type_renders_after_migration(name):
    """Old specs referencing removed profiles still render (mapped to Publication)."""
    from make_my_figure_core import examples

    for pt in available_plot_types():
        info, aux, _spec = examples.load_example(pt)
        aux_dfs = {k: v.dataframe for k, v in aux.items()} or None
        spec = make_spec(pt, info.source_name, name, mapping=None)
        result = render(spec, info.dataframe, aux=aux_dfs)
        assert result.figure is not None
        # migrated to the Publication identity
        assert result.metadata["style_profile"] == "publication"
        # a non-intrusive migration notice is surfaced
        assert any("Publication style" in w for w in result.warnings)
        plt.close(result.figure)


def test_learned_machinery_available_for_publication_profiles():
    """If a benchmark-derived publication-learned profile exists, it must load."""
    from make_my_figure_core.styles.engine import _load_learned_raw

    learned = _load_learned_raw()
    pub_learned = [n for n in learned if n.startswith("publication")]
    for name in pub_learned:
        p = load_profile(name)
        assert p.palette and all(c.startswith("#") for c in p.palette)
        assert p.base_font_pt > 0 and p.axis_font_pt > 0
