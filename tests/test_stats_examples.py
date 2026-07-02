"""Every bundled statistics example must load, render, and report a method."""

import json
import os

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

from make_my_figure_core.io.loaders import load_table
from make_my_figure_core.plots.registry import render

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_STATS_DIR = os.path.join(_ROOT, "examples", "statistics")


def _slugs():
    manifest = os.path.join(_STATS_DIR, "manifest.json")
    if not os.path.exists(manifest):
        return []
    data = json.load(open(manifest))
    return [e["slug"] for e in data["examples"]]


@pytest.mark.skipif(not _slugs(), reason="statistics examples not generated")
@pytest.mark.parametrize("slug", _slugs())
def test_statistics_example_renders_with_method(slug):
    folder = os.path.join(_STATS_DIR, slug)
    spec = json.load(open(os.path.join(folder, "plotspec.json")))
    df = load_table(os.path.join(folder, "data.csv")).dataframe
    res = render(spec, df)
    assert res.figure is not None
    # Statistics were requested in every example -> a report must exist.
    assert res.stats_report is not None
    # At least a method paragraph OR an explicit warning (never silent).
    assert res.stats_report.method_paragraph or res.stats_report.warnings
    plt.close(res.figure)


@pytest.mark.skipif(not _slugs(), reason="statistics examples not generated")
@pytest.mark.parametrize("slug", _slugs())
def test_statistics_example_has_all_files(slug):
    folder = os.path.join(_STATS_DIR, slug)
    for fn in ("data.csv", "data.tsv", "plotspec.json", "statsspec.json",
               "README.md", "expected_method_report.md"):
        assert os.path.exists(os.path.join(folder, fn)), f"missing {fn} in {slug}"
