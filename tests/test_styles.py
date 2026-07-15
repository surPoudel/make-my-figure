import pytest

from make_my_figure_core.styles.engine import (
    list_profiles,
    load_all_profiles,
    load_profile,
    mm_to_inches,
)


def test_publication_is_the_single_listed_profile():
    profiles = list_profiles()
    assert "publication" in profiles
    # v0.6: journal-named profiles are not surfaced.
    assert not ({"nature_like", "science_like", "cell_like"} & set(profiles))


def test_profile_tokens_and_palette():
    # Legacy journal names migrate to Publication but still yield valid tokens.
    p = load_profile("nature_like")
    # Publication-ready readable defaults (not tiny journal-print 7pt).
    assert p.base_font_pt >= 10
    assert p.axis_font_pt >= 11
    assert p.marker_size >= 30
    assert p.spine_width_pt >= 1.0
    assert p.palette and all(c.startswith("#") for c in p.palette)
    # colors cycle without index error
    assert p.color_for(0) == p.color_for(len(p.palette))


def test_figure_size_single_vs_double():
    p = load_profile("nature_like")
    w_single, _ = p.figure_size_inches("single")
    w_double, _ = p.figure_size_inches("double")
    assert w_double > w_single
    assert w_single == pytest.approx(mm_to_inches(p.single_column_width_mm))


def test_rc_params_keep_text_editable():
    p = load_profile("cell_like")
    rc = p.rc_params()
    assert rc["svg.fonttype"] == "none"
    assert rc["pdf.fonttype"] == 42


def test_load_all_profiles():
    allp = load_all_profiles()
    assert "publication" in allp
    assert len(allp) >= 1


def test_unknown_profile_raises():
    with pytest.raises(KeyError):
        load_profile("does_not_exist")
