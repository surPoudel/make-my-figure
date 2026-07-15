"""Pipeline runs offline on a cached/builtin dataset and produces QC (network-free)."""

import importlib.util
import os
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SCRIPTS = os.path.join(_ROOT, "benchmarks", "publication_recreation", "scripts")

pytestmark = pytest.mark.skipif(
    not os.path.exists(os.path.join(_SCRIPTS, "pipeline.py")),
    reason="benchmark scripts not present")


@pytest.fixture(scope="module")
def pipeline():
    for p in (_SCRIPTS, _ROOT):
        if p not in sys.path:
            sys.path.insert(0, p)
    import benchmark_lib  # noqa: F401
    import pipeline as P
    return P


def test_builtin_dataset_recreates_offline(pipeline):
    """karate_network uses a NetworkX built-in — always available, no network."""
    P = pipeline
    bench = next(b for b in P.BENCHMARKS if b.id == "karate_network")
    curated = P.curate(bench, offline_ok=True)
    assert curated is not None and "data" in curated
    result = P.recreate(bench)
    assert result["iterations"] >= 2
    assert result["sci_ok"] and result["vis_ok"]
    # exports produced on disk, non-empty
    figs = os.path.join(bench.dir(), "figures")
    for ext in ("png", "svg", "pdf"):
        fp = os.path.join(figs, f"recreated.{ext}")
        assert os.path.exists(fp) and os.path.getsize(fp) > 1024


def test_download_skips_gracefully_offline(pipeline, monkeypatch):
    """A network dataset returns None (not an exception) when offline."""
    P = pipeline
    ds = P.DATASETS["gapminder"]
    # force the cache miss + simulate offline by pointing requests at a bad host
    import benchmark_lib as B
    monkeypatch.setattr(ds, "data_url", "https://nonexistent.invalid.example/none.csv")
    # only exercises the graceful path if not already cached
    if os.path.exists(os.path.join(ds.raw_dir(), "raw.csv")):
        pytest.skip("gapminder already cached; offline path not exercised")
    assert ds.acquire(offline_ok=True) is None


def test_curation_is_deterministic(pipeline):
    P = pipeline
    bench = next(b for b in P.BENCHMARKS if b.id == "iris_confusion")
    c1 = P.curate(bench, offline_ok=True)
    c2 = P.curate(bench, offline_ok=True)
    assert c1["data"].equals(c2["data"])
