import pytest

from make_my_figure_core.styles.engine import (
    list_profiles,
    load_all_profiles,
    load_profile,
    mm_to_inches,
)


def test_three_starter_profiles_present():
    profiles = list_profiles()
    assert {"nature_like", "science_like", "cell_like"} <= set(profiles)


def test_profile_tokens_and_palette():
    p = load_profile("nature_like")
    assert p.base_font_pt == 7
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
    assert len(allp) >= 3


def test_unknown_profile_raises():
    with pytest.raises(KeyError):
        load_profile("does_not_exist")
