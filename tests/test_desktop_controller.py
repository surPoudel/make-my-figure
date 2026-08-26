"""Tests for the desktop controller (no Qt event loop required)."""

import os
import sys
import zipfile

import matplotlib
import matplotlib.pyplot as plt
import pytest

matplotlib.use("Agg")

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from apps.desktop_app.controller import DesktopController
from make_my_figure_core.plots.registry import available_plot_types


@pytest.fixture(scope="module")
def controller():
    return DesktopController()


def test_catalog(controller):
    # A deliberate tripwire: bump it when a plot type is added, so the desktop
    # catalogue and the registry cannot silently drift apart.
    assert len(controller.plot_types()) == 38
    styles = dict(controller.styles())
    # v0.6: a single Publication style identity (no journal-named profiles).
    assert set(styles) == {"publication"}
    assert styles["publication"] == "Publication"


def test_every_example_loads_and_renders(controller):
    for pt in available_plot_types():
        data = controller.load_example(pt)
        assert data.info.n_rows > 0
        mapping = controller.default_mapping(pt)
        spec = controller.build_spec(pt, "nature_like", data.table_name, mapping)
        result = controller.render(spec, data)
        assert result.figure is not None
        assert result.metadata["plot_type"] == pt
        plt.close(result.figure)


def test_pca_example_has_metadata(controller):
    data = controller.load_example("pca_scatter_from_matrix")
    assert "metadata" in data.aux
    spec = controller.build_spec("pca_scatter_from_matrix", "cell_like",
                                 data.table_name, controller.default_mapping("pca_scatter_from_matrix"))
    result = controller.render(spec, data)
    assert result.metadata["color_by"] == "group"


def test_export_all_formats(controller, tmp_path):
    data = controller.load_example("volcano_plot")
    spec = controller.build_spec("volcano_plot", "science_like", data.table_name,
                                 controller.default_mapping("volcano_plot"))
    result = controller.render(spec, data)
    base = str(tmp_path / "volcano")
    out = controller.export_files(spec, result, base, ["svg", "png", "pdf"], dpi=200)
    assert len(out["files"]) == 3
    for f in out["files"]:
        assert os.path.getsize(f) > 200
    assert os.path.exists(out["sidecar"])


def test_export_zip_bundle(controller, tmp_path):
    data = controller.load_example("scatterplot_with_regression")
    spec = controller.build_spec("scatterplot_with_regression", "nature_like",
                                 data.table_name, controller.default_mapping("scatterplot_with_regression"))
    result = controller.render(spec, data)
    blob = controller.export_bundle(spec, result, ["svg", "png", "pdf"], basename="scatter")
    z = zipfile.ZipFile(__import__("io").BytesIO(blob))
    names = set(z.namelist())
    assert {"scatter.svg", "scatter.png", "scatter.pdf", "scatter.plot_spec.json"} <= names


def test_save_template(controller, tmp_path):
    dest = str(tmp_path / "tmpl.csv")
    controller.save_template("barplot_with_error_bar", dest)
    assert os.path.exists(dest)
    with open(dest) as fh:
        assert "condition" in fh.readline()


def test_options_and_column_fields(controller):
    cols = controller.column_fields("grouped_barplot_with_error_bar")
    assert cols == ["x", "group", "y"]
    opts = {o.key for o in controller.options("heatmap_clustered_matrix")}
    assert {"cluster_rows", "cluster_columns", "color_scale"} <= opts
