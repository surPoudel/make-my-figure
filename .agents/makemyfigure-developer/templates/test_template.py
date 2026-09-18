"""Tests for ``__PLOT_TYPE__`` (__DISPLAY_NAME__).

Focused tests a renderer needs (see references/testing.md): registration, column validation,
render from the bundled example, missing values, edge cases, style/option controls, statistics
(if applicable), PlotSpec round trip, preset extraction/apply, Figure Builder panel, export.
Registry-wide suites (preset QC, examples, UI wiring, capabilities audit) pick the plot up
automatically; they are listed in .agents/makemyfigure-developer/references/testing.md.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from make_my_figure_core import examples
from make_my_figure_core.plots.base import RenderError
from make_my_figure_core.plots.registry import (available_plot_types, default_mapping, display_name,
                                                make_spec, render, render_to_files)
from make_my_figure_core.spec.validate import validate_plot_spec

PT = "__PLOT_TYPE__"


@pytest.fixture(autouse=True)
def _close():
    yield
    plt.close("all")


@pytest.fixture
def example():
    info, aux, spec = examples.load_example(PT)
    return info.dataframe, {k: v.dataframe for k, v in aux.items()}, spec


def _digest(df: pd.DataFrame) -> str:
    return hashlib.sha256(pd.util.hash_pandas_object(df, index=True).to_numpy().tobytes()).hexdigest()


# --- registration -----------------------------------------------------------------------------
def test_registered_with_display_name_and_default_mapping():
    assert PT in available_plot_types()
    assert display_name(PT) != PT
    assert default_mapping(PT)


def test_bundled_example_exists_and_renders(example):
    df, aux, spec = example
    result = render(spec, df, aux=aux or None)
    assert result.figure.axes
    assert result.metadata.get("plot_type") == PT


# --- column validation ------------------------------------------------------------------------
def test_missing_required_column_raises_clear_error(example):
    df, aux, spec = example
    bad = copy.deepcopy(spec)
    bad["mapping"]["y"] = "__absent__"          # adapt the role name to the plot
    with pytest.raises(RenderError):
        render(bad, df, aux=aux or None)


# --- scientific freeze: rendering never changes the data --------------------------------------
def test_render_does_not_mutate_input(example):
    df, aux, spec = example
    before = _digest(df)
    render(spec, df, aux=aux or None)
    assert _digest(df) == before


# --- missing values and edge cases -----------------------------------------------------------
def test_missing_values_are_dropped_with_a_warning(example):
    df, aux, spec = example
    y = spec["mapping"]["y"]                     # adapt
    df2 = df.copy(); df2.loc[df2.index[:3], y] = np.nan
    result = render(spec, df2, aux=aux or None)
    assert any("missing" in w.lower() or "not drawn" in w.lower() for w in result.warnings)


@pytest.mark.parametrize("n_rows", [3, 6])
def test_small_n_renders(example, n_rows):
    df, aux, spec = example
    render(spec, df.head(n_rows), aux=aux or None)


def test_long_labels_render_without_exception(example):
    df, aux, spec = example
    x = spec["mapping"]["x"]                     # adapt
    df2 = df.copy(); df2[x] = df2[x].astype(str) + " with a much longer category label"
    render(spec, df2, aux=aux or None)


# --- options ----------------------------------------------------------------------------------
@pytest.mark.parametrize("option", [{"orientation": "horizontal"}, {"points": False}])
def test_options_render(example, option):
    df, aux, spec = example
    s = copy.deepcopy(spec); s["mapping"].update(option)
    render(s, df, aux=aux or None)


# --- PlotSpec round trip ----------------------------------------------------------------------
def test_plotspec_round_trip_reproduces_metadata(example, tmp_path):
    df, aux, spec = example
    validate_plot_spec(spec)
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    spec2 = json.loads(path.read_text(encoding="utf-8"))
    m1 = render(spec, df, aux=aux or None).metadata
    m2 = render(spec2, df, aux=aux or None).metadata
    assert json.dumps(m1, sort_keys=True, default=str) == json.dumps(m2, sort_keys=True, default=str)


# --- export -----------------------------------------------------------------------------------
def test_exports_all_formats_with_sidecar(example, tmp_path):
    df, aux, spec = example
    s = copy.deepcopy(spec); s["output"]["formats"] = ["svg", "png", "pdf"]
    # render_to_files(spec, df, base_path, *, formats=None, style=None, aux=None) -> dict with the
    # written paths (see make_my_figure_core/plots/registry.py); the PlotSpec sidecar is written too.
    render_to_files(s, df, str(tmp_path / "fig"), aux=aux or None)
    written = sorted(p.name for p in tmp_path.iterdir())
    assert any(n.endswith(".svg") for n in written) and any(n.endswith(".pdf") for n in written)
    assert any(n.endswith(".plot_spec.json") for n in written), written
