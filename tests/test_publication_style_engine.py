"""The single Publication style + its accessibility variants."""

from make_my_figure_core.styles.publication_style_engine import (
    LEGEND_OUTSIDE_SERIES_THRESHOLD,
    PUBLICATION_PALETTES,
    available_palette_names,
    publication_profile,
    publication_variant,
    recommended_overrides,
)


def test_publication_profile_is_readable():
    p = publication_profile()
    assert p.name == "publication"
    assert p.base_font_pt >= 10 and p.axis_font_pt >= 11
    assert p.palette and all(c.startswith("#") for c in p.palette)


def test_accessibility_variants_swap_palette_only():
    base = publication_profile()
    acc = publication_variant("publication_accessible")
    gray = publication_variant("publication_grayscale")
    # same readable typography, different palettes
    assert acc.base_font_pt == base.base_font_pt
    assert acc.palette != base.palette
    assert gray.palette != base.palette
    assert acc.palette != gray.palette


def test_no_journal_names_in_palette_choices():
    names = available_palette_names()
    assert "publication" in names
    assert not ({"nature_like", "science_like", "cell_like"} & set(names))
    assert set(PUBLICATION_PALETTES) == {"publication", "publication_accessible",
                                         "publication_grayscale"}


def test_recommended_overrides_moves_legend_outside_for_many_series():
    assert recommended_overrides(n_series=1) == {}
    ov = recommended_overrides("lineplot_timecourse_with_error_band",
                               n_series=LEGEND_OUTSIDE_SERIES_THRESHOLD)
    assert ov.get("legend_outside") is True
