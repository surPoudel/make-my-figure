"""Renderer unit + visual smoke tests.

For every (plot_type, mock_file) pair and every style profile we render the
figure and confirm it produces a non-trivial vector (SVG) and raster (PNG)
export. We also check the no-silent-mutation contract and a couple of
renderer-specific numeric assertions.
"""

import os

import matplotlib.pyplot as plt
import pandas as pd
import pytest

from make_my_figure_core.io.loaders import load_table
from make_my_figure_core.plots.base import RenderError
from make_my_figure_core.plots.registry import (
    export_figure,
    make_spec,
    render,
    render_to_files,
    write_sidecar,
)
from make_my_figure_core.styles.engine import list_profiles


def test_renders_for_all_plot_types_and_styles(plot_case):
    plot_type, path, filename = plot_case
    info = load_table(path)
    for style_name in list_profiles():
        spec = make_spec(plot_type, filename, style_name)
        result = render(spec, info.dataframe)
        assert result.figure is not None
        assert result.metadata["plot_type"] == plot_type
        assert result.metadata["style_profile"] == style_name
        assert "disclaimer" in result.metadata
        plt.close(result.figure)


def test_renderer_does_not_mutate_input(plot_case):
    plot_type, path, filename = plot_case
    info = load_table(path)
    before = info.dataframe.copy(deep=True)
    spec = make_spec(plot_type, filename, "nature_like")
    result = render(spec, info.dataframe)
    plt.close(result.figure)
    pd.testing.assert_frame_equal(info.dataframe, before)


def test_export_svg_png_pdf(plot_case, tmp_path):
    plot_type, path, filename = plot_case
    info = load_table(path)
    spec = make_spec(plot_type, filename, "science_like")
    base = str(tmp_path / plot_type)
    out = render_to_files(spec, info.dataframe, base, formats=["svg", "png", "pdf"])
    assert len(out["files"]) == 3
    for f in out["files"]:
        assert os.path.exists(f)
        assert os.path.getsize(f) > 200  # non-empty figure
    # reproducibility sidecar written and well-formed
    assert os.path.exists(out["sidecar"])
    import json

    with open(out["sidecar"]) as fh:
        payload = json.load(fh)
    assert payload["plot_spec"]["plot_type"] == plot_type


def test_missing_column_raises_clear_error(mock_dir):
    info = load_table(os.path.join(mock_dir, "barplot_error_raw.csv"))
    spec = make_spec("barplot_with_error_bar", "barplot_error_raw.csv", "nature_like")
    spec["mapping"]["y"] = "no_such_column"
    with pytest.raises(RenderError) as exc:
        render(spec, info.dataframe)
    assert "no_such_column" in str(exc.value)


def test_volcano_counts_significant(mock_dir):
    info = load_table(os.path.join(mock_dir, "volcano_plot.csv"))
    spec = make_spec("volcano_plot", "volcano_plot.csv", "nature_like")
    result = render(spec, info.dataframe)
    m = result.metadata
    assert m["n_up"] + m["n_down"] + m["n_ns"] == info.n_rows
    assert m["n_up"] > 0 and m["n_down"] > 0
    plt.close(result.figure)


def test_scatter_regression_metadata(mock_dir):
    info = load_table(os.path.join(mock_dir, "scatter_regression.csv"))
    spec = make_spec("scatterplot_with_regression", "scatter_regression.csv", "nature_like")
    result = render(spec, info.dataframe)
    assert result.metadata["fit_line"] is True
    assert result.metadata["regression"]  # at least one fit recorded
    plt.close(result.figure)


def test_heatmap_clusters_when_requested(mock_dir):
    info = load_table(os.path.join(mock_dir, "heatmap_expression_matrix.tsv"))
    spec = make_spec("heatmap_clustered_matrix", "heatmap_expression_matrix.tsv", "nature_like")
    result = render(spec, info.dataframe)
    assert result.metadata["clustered_rows"] is True
    assert result.metadata["clustered_columns"] is True
    plt.close(result.figure)


def test_barplot_error_none_disables_error(mock_dir):
    info = load_table(os.path.join(mock_dir, "barplot_error_raw.csv"))
    spec = make_spec("barplot_with_error_bar", "barplot_error_raw.csv", "nature_like")
    spec["mapping"]["error"] = "none"
    result = render(spec, info.dataframe)
    assert result.metadata["error_method"] == "none"
    plt.close(result.figure)
