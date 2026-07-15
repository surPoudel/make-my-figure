"""Validate the publication-recreation manifest + provenance (network-free)."""

import json
import os

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_BENCH = os.path.join(_ROOT, "benchmarks", "publication_recreation")
_MANIFEST = os.path.join(_BENCH, "manifest.json")

pytestmark = pytest.mark.skipif(not os.path.exists(_MANIFEST),
                                reason="benchmark manifest not generated")


def _manifest():
    with open(_MANIFEST) as fh:
        return json.load(fh)


def test_manifest_is_valid_json_with_entries():
    man = _manifest()
    assert isinstance(man["benchmarks"], list) and man["benchmarks"]
    assert man["style"] == "publication"


def test_at_least_10_passing_entries():
    man = _manifest()
    passing = [e for e in man["benchmarks"] if e["passed"]]
    assert len(passing) >= 10, f"only {len(passing)} passing"


def test_passing_entries_have_provenance_and_qc():
    man = _manifest()
    for e in man["benchmarks"]:
        if not e["passed"]:
            continue
        assert e["doi_or_url"], e["benchmark_id"]
        assert e["data_source"], e["benchmark_id"]
        assert e["data_license"] and e["license_verified"], e["benchmark_id"]
        # PlotSpec + QC reports exist on disk
        assert os.path.exists(os.path.join(_BENCH, e["plotspec_path"])), e["benchmark_id"]
        qc = os.path.join(_BENCH, e["qc_path"])
        assert os.path.exists(os.path.join(qc, "scientific_qc.md")), e["benchmark_id"]
        assert os.path.exists(os.path.join(qc, "visual_qc.md")), e["benchmark_id"]


def test_no_panel_passes_without_qc_flags():
    man = _manifest()
    for e in man["benchmarks"]:
        if e["passed"]:
            assert e["scientific_qc_pass"] and e["visual_qc_pass"], e["benchmark_id"]
            assert e["iterations"] >= 2, e["benchmark_id"]


def test_permissive_licenses_only():
    man = _manifest()
    allowed = ("cc0", "cc by", "cc-by", "public", "bsd", "mit")
    for e in man["benchmarks"]:
        lic = e["data_license"].lower()
        assert any(a in lic for a in allowed), f"{e['benchmark_id']}: license {e['data_license']}"


def test_no_reference_figure_images_stored():
    man = _manifest()
    for e in man["benchmarks"]:
        assert e["reference_image_stored"] is False
    refdir = os.path.join(_BENCH, "reference_figures")
    if os.path.isdir(refdir):
        for dp, _dn, fn in os.walk(refdir):
            for f in fn:
                assert not f.lower().endswith((".png", ".jpg", ".jpeg", ".svg", ".pdf", ".tif", ".tiff")), \
                    f"unexpected stored figure image: {f}"


def test_no_journal_style_names_or_rnaseq_in_artifacts():
    man = _manifest()
    blob = json.dumps(man).lower()
    for bad in ("nature-like", "science-like", "cell-like", "journal-like",
                "edger", "limma", "voom", "rnaseqspec"):
        assert bad not in blob, f"forbidden term in manifest: {bad}"
    assert man["style"] == "publication"
