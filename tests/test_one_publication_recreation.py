"""Tests for the one-publication recreation pilot (Gorman et al. 2014 penguins).

Offline-safe: operates on the committed benchmark artifacts; does not download.
"""

import json
import os

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BASE = os.path.join(ROOT, "benchmarks", "one_publication_recreation")
PANELS = os.path.join(BASE, "recreated_panels")

pytestmark = pytest.mark.skipif(
    not os.path.isdir(BASE),
    reason="one_publication_recreation benchmark not present")

PANEL_DIRS = ["panel_A", "panel_B", "panel_C"]
STATS_PANELS = {"panel_B"}  # panels that show statistics


def _nonempty(path):
    return os.path.exists(path) and os.path.getsize(path) > 0


def test_manifest_valid_and_has_publication():
    with open(os.path.join(BASE, "publication_manifest.json"), encoding="utf-8") as fh:
        m = json.load(fh)
    assert m["publication_id"] and m["doi"]
    assert m["article_license"] and m["data_license"]
    assert len(m["panels"]) >= 2


def test_at_least_two_panels_recreated():
    present = [d for d in PANEL_DIRS if os.path.isdir(os.path.join(PANELS, d))]
    assert len(present) >= 2


@pytest.mark.parametrize("panel", PANEL_DIRS)
def test_each_panel_has_data_spec_and_exports(panel):
    p = os.path.join(PANELS, panel)
    assert _nonempty(os.path.join(p, "processed_data.csv"))       # source data
    assert _nonempty(os.path.join(p, "plotspec.json"))            # PlotSpec
    assert _nonempty(os.path.join(p, "target_panel_spec.json"))
    for ext in ("png", "svg", "pdf"):                             # exports non-empty
        assert _nonempty(os.path.join(p, f"recreated.{ext}")), f"{panel}: empty {ext}"
    assert _nonempty(os.path.join(p, "scientific_qc.md"))
    assert _nonempty(os.path.join(p, "visual_qc.md"))
    # PlotSpec uses the single Publication style
    with open(os.path.join(p, "plotspec.json"), encoding="utf-8") as fh:
        assert json.load(fh)["journal_style"] == "publication"


def test_statspec_present_where_stats_shown():
    for panel in STATS_PANELS:
        assert _nonempty(os.path.join(PANELS, panel, "statspec.json"))


def test_figure_builder_figurespec_and_exports():
    fb = os.path.join(BASE, "figure_builder")
    assert _nonempty(os.path.join(fb, "figure_spec.json"))
    for ext in ("png", "svg", "pdf"):
        assert _nonempty(os.path.join(fb, f"assembled_figure.{ext}"))


def test_no_copyrighted_reference_image_committed():
    # No image files anywhere except the panels/figure we generated ourselves.
    allowed = {"recreated.png", "recreated.svg", "recreated.pdf",
               "assembled_figure.png", "assembled_figure.svg", "assembled_figure.pdf"}
    for dirpath, _dirs, files in os.walk(BASE):
        for fn in files:
            if fn.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff", ".gif", ".svg")):
                assert fn in allowed, f"unexpected image asset committed: {os.path.join(dirpath, fn)}"


def test_no_journal_style_names_or_rnaseq_in_benchmark():
    import re
    forbidden = re.compile(r"nature-like|science-like|cell-like|journal-like|"
                           r"edger|limma|voom|rnaseqspec", re.IGNORECASE)
    for dirpath, _dirs, files in os.walk(BASE):
        for fn in files:
            if fn.endswith((".md", ".json", ".py", ".csv")):
                with open(os.path.join(dirpath, fn), encoding="utf-8", errors="ignore") as fh:
                    text = fh.read()
                hits = [ln for ln in text.splitlines() if forbidden.search(ln)]
                assert not hits, f"forbidden term in {fn}: {hits[:2]}"


def test_recreation_report_exists_and_labeled():
    rep = os.path.join(BASE, "qc", "recreation_report.md")
    assert _nonempty(rep)
    text = open(rep, encoding="utf-8").read().lower()
    assert "publication-grade recreation" in text  # honest label, not "exact"
    assert "exact reproduction" not in text.replace("not \"exact\"", "")
