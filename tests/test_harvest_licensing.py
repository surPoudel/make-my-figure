"""Offline tests for the license gate and harvest helpers (no network)."""

import pytest

from make_my_figure_core.harvest.licensing import (
    LicenseClass,
    classify_license,
    is_permissive,
)
from make_my_figure_core.harvest.pipeline import (
    extract_panel_labels,
    _build_query,
    _slug,
    _NON_ARTICLE_RE,
)


@pytest.mark.parametrize("title,is_notice", [
    ("Author Correction: RNaseH2A downregulation drives inflammation", True),
    ("Publisher Correction: A study of X", True),
    ("Retraction Note: Something", True),
    ("Erratum: Another thing", True),
    ("Comment on 'A paper'", True),
    ("A rigorous theoretical model of fluorescence", False),
    ("Correctional facilities and health outcomes", False),  # 'correction' not a notice prefix
])
def test_non_article_filter(title, is_notice):
    assert bool(_NON_ARTICLE_RE.match(title)) == is_notice


@pytest.mark.parametrize("raw,expected_class,permits", [
    ("CC BY", LicenseClass.PERMISSIVE, True),
    ("cc by", LicenseClass.PERMISSIVE, True),
    ("CC BY 4.0", LicenseClass.PERMISSIVE, True),
    ("CC BY-SA", LicenseClass.PERMISSIVE, True),
    ("CC0", LicenseClass.PERMISSIVE, True),
    ("CC BY-NC", LicenseClass.NONCOMMERCIAL, False),
    ("CC BY-NC-ND", LicenseClass.NODERIV, False),
    ("CC BY-ND", LicenseClass.NODERIV, False),
    ("Subscription required", LicenseClass.RESTRICTED, False),
    ("", LicenseClass.UNKNOWN, False),
    (None, LicenseClass.UNKNOWN, False),
    ("some weird license", LicenseClass.UNKNOWN, False),
])
def test_classify_license(raw, expected_class, permits):
    info = classify_license(raw)
    assert info.klass == expected_class
    assert info.permits_reuse == permits
    assert is_permissive(raw) == permits


def test_noncommercial_permits_tdm_but_not_reuse():
    info = classify_license("CC BY-NC")
    assert info.permits_tdm is True
    assert info.permits_reuse is False


def test_panel_label_extraction_sequential():
    cap = "a Relative gene copies for individuals. b Survival curves of ants. c Micro-CT scan."
    out = extract_panel_labels(cap)
    assert out["labels"] == ["a", "b", "c"]
    assert out["confidence"].startswith("heuristic")


def test_panel_label_extraction_none():
    out = extract_panel_labels("A single-panel figure with no sub-labels here.")
    assert out["labels"] == []
    assert out["confidence"] in ("none", "heuristic_low")


def test_panel_label_no_caption():
    out = extract_panel_labels(None)
    assert out["labels"] == []
    assert out["confidence"] == "none"


def test_query_uses_unquoted_license_and_year_range():
    q = _build_query("Nature Communications", 2021)
    assert "LICENSE:cc by" in q          # unquoted (quoting returns 0 hits in EPMC)
    assert 'JOURNAL:"Nature Communications"' in q
    assert "PUB_YEAR:[2021 TO 2025]" in q
    assert "OPEN_ACCESS:y" in q


def test_slug():
    assert _slug("A Study of Soil Pathogens!") == "a_study_of_soil_pathogens"
    assert _slug("") == "untitled"
