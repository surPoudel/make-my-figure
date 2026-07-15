"""Every passing benchmark has a PlotSpec + QC + a documented/produced export set."""

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


def test_passing_entries_declare_exports_and_plotspec():
    man = _manifest()
    for e in man["benchmarks"]:
        if not e["passed"]:
            continue
        # PlotSpec committed
        ps = os.path.join(_BENCH, e["plotspec_path"])
        assert os.path.exists(ps), e["benchmark_id"]
        with open(ps) as fh:
            spec = json.load(fh)
        assert spec["journal_style"] == "publication", e["benchmark_id"]
        assert set(spec["output"]["formats"]) >= {"png", "svg", "pdf"}, e["benchmark_id"]
        # exports_pass recorded true (figures themselves are git-ignored/regenerable)
        assert e["exports_pass"], e["benchmark_id"]


def test_statistics_panels_have_statspec():
    man = _manifest()
    for e in man["benchmarks"]:
        sp = os.path.join(_BENCH, "recreated_panels", e["benchmark_id"], "statspec.json")
        if os.path.exists(sp):
            with open(sp) as fh:
                stats = json.load(fh)
            assert stats.get("enabled") is True and stats.get("test")


def test_processed_data_committed_and_small():
    """Processed CSVs are committed and stay small (raw is git-ignored)."""
    dsdir = os.path.join(_BENCH, "datasets")
    found = 0
    for dp, _dn, fn in os.walk(dsdir):
        if os.path.basename(dp) == "raw":
            continue
        for f in fn:
            if f.endswith(".csv"):
                found += 1
                assert os.path.getsize(os.path.join(dp, f)) < 1_000_000, f
    assert found >= 10
