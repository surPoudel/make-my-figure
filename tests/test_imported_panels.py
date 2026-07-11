"""Tests for importing external figure files as Figure Builder panels (v0.5)."""

import json
import os

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest

matplotlib.use("Agg")

from make_my_figure_core import figure_import as fi
from make_my_figure_core.panels import (
    FigureLayout,
    MultiPanelFigure,
    Panel,
    build_figure,
    export_multipanel,
    import_external_panel,
    multipanel_sidecar,
    panel_from_dict,
    panel_warnings,
)
from make_my_figure_core.plots.registry import make_spec


@pytest.fixture(autouse=True)
def _close():
    yield
    plt.close("all")


def _make_asset(path, size=(3.0, 2.0), dpi=150):
    fig = plt.figure(figsize=size, dpi=dpi)
    ax = fig.add_subplot(111)
    ax.plot([0, 1, 2, 3], [0, 2, 1, 3])
    ax.set_title(os.path.basename(path))
    fig.savefig(path)
    plt.close(fig)
    return path


@pytest.fixture
def assets(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    files = {}
    for ext in ("png", "jpg", "tif", "pdf", "svg"):
        files[ext] = _make_asset(str(src / f"plot.{ext}"))
    return tmp_path, files


def _adir(tmp_path):
    return str(tmp_path / "figure_builder_assets")


# --- import formats ---------------------------------------------------------
@pytest.mark.parametrize("ext", ["png", "jpg", "tif"])
def test_import_raster_formats(assets, ext):
    tmp_path, files = assets
    res = fi.import_asset(files[ext], _adir(tmp_path))
    assert res.error is None
    assert res.image is not None and res.image.ndim == 3 and res.image.shape[2] == 4
    assert res.metadata["file_type"] == ext
    assert res.metadata["orig_width_px"] > 0 and "sha256" in res.metadata
    # asset copied into the managed folder
    assert os.path.exists(os.path.join(_adir(tmp_path), res.metadata["stored_asset"]))


def test_import_pdf_first_page(assets):
    tmp_path, files = assets
    pytest.importorskip("fitz")
    res = fi.import_asset(files["pdf"], _adir(tmp_path), rasterize_dpi=200)
    assert res.error is None and res.image is not None
    assert res.metadata["rasterization_dpi"] == 200
    assert any("rasterized" in w.lower() for w in res.warnings)


def test_import_svg_supported_or_friendly_message(assets):
    tmp_path, files = assets
    res = fi.import_asset(files["svg"], _adir(tmp_path))
    # either it rasterized (converter present) or returned a clear, non-crashing message
    assert (res.image is not None) or (res.error and "SVG" in res.error)


def test_unsupported_format_friendly_error(tmp_path):
    bad = tmp_path / "notes.txt"
    bad.write_text("hello")
    res = fi.import_asset(str(bad), _adir(tmp_path))
    assert res.image is None and res.error and "Unsupported" in res.error


def test_missing_file_friendly_error(tmp_path):
    res = fi.import_asset(str(tmp_path / "nope.png"), _adir(tmp_path))
    assert res.image is None and "not found" in res.error.lower()


# --- panel metadata + management --------------------------------------------
def test_imported_panel_metadata_stored(assets):
    tmp_path, files = assets
    panel, asset = import_external_panel(files["png"], _adir(tmp_path), label="A", title="Imp",
                                         width_in=3.0)
    assert panel is not None and panel.is_external
    for key in ("original_filename", "stored_asset", "file_type", "sha256", "import_time",
                "orig_width_px", "orig_height_px"):
        assert key in panel.image_meta


def test_low_resolution_warning():
    meta = {"orig_width_px": 300, "is_vector_source": False, "dpi": None}
    warns = fi.resolution_warnings(meta, target_width_in=3.0)  # 100 DPI
    assert any("blurry" in w.lower() or "DPI" in w for w in warns)


def test_aspect_preserved_by_default(assets):
    tmp_path, files = assets
    panel, _ = import_external_panel(files["png"], _adir(tmp_path), width_in=3.0)
    assert panel.preserve_aspect is True and panel.fit_mode == "contain"


def test_crop_changes_image_size():
    arr = np.ones((100, 200, 4))
    out = fi.process_image(arr, crop={"top": 0.1, "left": 0.25})
    assert out.shape[0] == 90 and out.shape[1] == 150


def test_reorder_and_remove_with_generated(assets):
    tmp_path, files = assets
    from make_my_figure_core import examples

    info, _a, _s = examples.load_example("barplot_with_error_bar")
    gen = Panel(plot_spec=make_spec("barplot_with_error_bar", "data.csv", "publication"),
                table=info.dataframe, title="Gen")
    imp, _ = import_external_panel(files["png"], _adir(tmp_path), title="Imp", width_in=3.0)
    mpf = MultiPanelFigure(layout=FigureLayout(ncols=2, panel_dpi=100))
    mpf.add_panel(gen)
    mpf.add_panel(imp)
    assert [p.label for p in mpf.panels] == ["A", "B"]
    mpf.move_panel(0, 1)
    assert mpf.panels[0].is_external      # imported panel now first (A)
    mpf.remove_panel(0)
    assert len(mpf.panels) == 1 and not mpf.panels[0].is_external


# --- build + export + round-trip --------------------------------------------
def test_mixed_figure_builds_and_exports(assets, tmp_path):
    tmp_path2, files = assets
    from make_my_figure_core import examples

    info, _a, _s = examples.load_example("scatterplot_with_regression")
    gen = Panel(plot_spec=make_spec("scatterplot_with_regression", "data.csv", "publication"),
                table=info.dataframe, title="Gen")
    imp, _ = import_external_panel(files["png"], _adir(tmp_path2), title="Imp", width_in=3.0,
                                   border=True,
                                   annotations=[{"kind": "text", "coords": "axes",
                                                 "xy": [0.5, 0.9], "text": "note"}])
    mpf = MultiPanelFigure(layout=FigureLayout(ncols=2, panel_dpi=100))
    mpf.add_panel(gen)
    mpf.add_panel(imp)
    fig = build_figure(mpf)
    assert fig is not None
    files_out = export_multipanel(fig, str(tmp_path / "mixed"), ["svg", "png", "pdf"], dpi=120)
    assert len(files_out) == 3
    for f in files_out:
        assert os.path.exists(f) and os.path.getsize(f) > 300
    svg = next(f for f in files_out if f.endswith(".svg"))
    assert "note" in open(svg, encoding="utf-8").read()   # annotation vector-exported


def test_figurespec_roundtrip_restores_imported_panel(assets, tmp_path):
    tmp_path2, files = assets
    adir = _adir(tmp_path2)
    imp, _ = import_external_panel(files["png"], adir, title="Imp", width_in=3.0,
                                   fit_mode="contain", rotate=90)
    mpf = MultiPanelFigure(name="Fig", layout=FigureLayout(ncols=1, panel_dpi=100))
    mpf.add_panel(imp)
    side = multipanel_sidecar(mpf, str(tmp_path / "figspec"))
    spec = json.load(open(side, encoding="utf-8"))
    pd0 = spec["figure"]["panels"][0]
    assert pd0["panel_kind"] == "external_figure_panel"
    assert pd0["image_path"] == os.path.basename(imp.image_path)   # basename only (no private path)
    assert pd0["rotate"] == 90
    # reload + rebuild
    reloaded = panel_from_dict(pd0, assets_dir=adir)
    assert reloaded.is_external and reloaded.rotate == 90
    mpf2 = MultiPanelFigure(layout=FigureLayout(ncols=1, panel_dpi=100))
    mpf2.add_panel(reloaded)
    assert build_figure(mpf2) is not None


def test_low_res_warning_surfaced_on_build(assets):
    tmp_path, files = assets
    # a deliberately small source -> low DPI at 6 inches
    small = _make_asset(os.path.join(str(tmp_path), "small.png"), size=(1.0, 1.0), dpi=80)
    imp, _ = import_external_panel(small, _adir(tmp_path), width_in=6.0)
    mpf = MultiPanelFigure(layout=FigureLayout(ncols=1, panel_dpi=100))
    mpf.add_panel(imp)
    fig = build_figure(mpf)
    assert any("DPI" in w or "blurry" in w.lower() for w in panel_warnings(fig))
