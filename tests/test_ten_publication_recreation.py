"""Validate the ten-publication recreation benchmark artifacts.

Offline-safe: checks the committed manifest + per-publication artifacts (no
network, no re-download). Verifies each publication is a real, license-recorded,
app-rendered recreation with QC, spanning >=10 distinct plot types, with no
copyrighted figure images and no overclaiming.
"""

import glob
import json
import os

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_BASE = os.path.join(_ROOT, "benchmarks", "ten_publication_recreation")
_MANIFEST = os.path.join(_BASE, "manifest.json")

pytestmark = pytest.mark.skipif(not os.path.exists(_MANIFEST),
                                reason="ten_publication_recreation manifest missing")

# journal-style names must not appear in benchmark artifacts; RNA-seq analysis
# workflows must not be reintroduced.
_FORBIDDEN_STYLE = ("nature-like", "science-like", "cell-like", "journal-like")
_FORBIDDEN_RNASEQ = ("edger", "limma", "voom", "rnaseqspec")


def _manifest():
    return json.load(open(_MANIFEST, encoding="utf-8"))


def _pubs():
    return _manifest()["publications"]


def test_manifest_valid_and_has_ten():
    man = _manifest()
    assert isinstance(man.get("publications"), list)
    assert man["n_publications"] >= 10
    assert len(man["publications"]) == man["n_publications"]


def test_ten_distinct_plot_types():
    types = {p["plot_type"] for p in _pubs()}
    assert len(types) >= 10, f"only {len(types)} distinct plot types: {sorted(types)}"


@pytest.mark.parametrize("pub", _pubs() if os.path.exists(_MANIFEST) else [],
                         ids=lambda p: p["id"])
def test_publication_artifacts_complete(pub):
    d = os.path.join(_BASE, "publications", pub["id"])
    assert os.path.isdir(d), f"missing publication dir {pub['id']}"
    # provenance + license + DOI/URL
    assert os.path.exists(os.path.join(d, "source", "provenance.json"))
    assert str(pub.get("data_license", "")).strip() not in ("", "?", "None")
    assert str(pub.get("doi_or_url", "")).strip() not in ("", "?", "None")
    # a rendered panel: plotspec + non-empty PNG/SVG/PDF + QC
    plotspecs = glob.glob(os.path.join(d, "recreated_panels", "*", "plotspec.json"))
    assert plotspecs, f"no plotspec for {pub['id']}"
    panel = os.path.dirname(plotspecs[0])
    for ext in ("png", "svg", "pdf"):
        f = os.path.join(panel, f"recreated.{ext}")
        assert os.path.exists(f) and os.path.getsize(f) > 0, f"empty/missing {ext} for {pub['id']}"
    assert os.path.exists(os.path.join(panel, "scientific_qc.md"))
    assert os.path.exists(os.path.join(panel, "visual_qc.md"))
    # source data present (raw or processed)
    assert (glob.glob(os.path.join(d, "raw_data", "*")) or
            glob.glob(os.path.join(d, "processed_data", "*"))), f"no data for {pub['id']}"


def test_no_exact_reproduction_claim():
    # "exact reproduction" as a classification label is forbidden; the word
    # "exact" is allowed in truthful phrases (e.g. "exact node/edge set").
    for p in _pubs():
        assert "exact reproduction" not in str(p["classification"]).lower(), p["id"]


def test_no_reference_images_committed():
    for p in _pubs():
        assert p.get("reference_image_stored") is False
    # no obvious reference-figure image files committed under the benchmark
    assert not glob.glob(os.path.join(_BASE, "**", "reference_*.png"), recursive=True)
    assert not glob.glob(os.path.join(_BASE, "**", "reference_figures", "**", "*"), recursive=True)


def test_no_journal_style_or_rnaseq_terms():
    hits = []
    for path in glob.glob(os.path.join(_BASE, "**", "*"), recursive=True):
        if not path.endswith((".json", ".md", ".py", ".csv")):
            continue
        try:
            text = open(path, encoding="utf-8").read().lower()
        except (OSError, UnicodeDecodeError):
            continue
        for bad in _FORBIDDEN_STYLE + _FORBIDDEN_RNASEQ:
            if bad in text:
                hits.append(f"{os.path.relpath(path, _ROOT)}: {bad}")
    assert not hits, "forbidden terms in benchmark artifacts:\n" + "\n".join(hits)


def test_summary_table_exists_with_rows():
    csv_path = os.path.join(_BASE, "reports", "summary_table.csv")
    assert os.path.exists(csv_path)
    lines = [ln for ln in open(csv_path, encoding="utf-8").read().splitlines() if ln.strip()]
    assert len(lines) >= 11  # header + >=10 rows
