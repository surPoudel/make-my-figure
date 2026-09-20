"""Desktop controller + Export-all integration for figure packages (no Qt needed)."""
from __future__ import annotations

import io
import json
import zipfile

import matplotlib

matplotlib.use("Agg")

import pandas as pd
import pytest

from apps.desktop_app.controller import DesktopController
from make_my_figure_core.package import PACKAGE_EXTENSION, MatrixContext, open_figure_package, verify_preprocessing


@pytest.fixture(scope="module")
def controller():
    return DesktopController()


@pytest.fixture(autouse=True)
def _close():
    yield
    import matplotlib.pyplot as plt

    plt.close("all")


def test_export_all_contains_publication_files_specs_and_package(controller):
    data = controller.load_example("boxplot_or_violin_with_points")
    spec = controller.build_spec("boxplot_or_violin_with_points", "publication", data.table_name,
                                 controller.default_mapping("boxplot_or_violin_with_points"),
                                 statistics={"enabled": True, "test": "welch_t", "comparison_mode": "all_pairs"})
    result = controller.render(spec, data)
    blob = controller.export_all_bundle(data, spec, result, formats=["svg", "png", "pdf"], basename="box")
    z = zipfile.ZipFile(io.BytesIO(blob))
    names = set(z.namelist())
    assert {"box.svg", "box.png", "box.pdf", "box.plot_spec.json", "box.stats_spec.json",
            f"box{PACKAGE_EXTENSION}", "README.txt"} <= names
    side = json.loads(z.read("box.plot_spec.json"))
    assert side["plot_spec"]["source"]["source_table_sha256"]          # digest travels with the exported PlotSpec
    pkg = open_figure_package(z.read(f"box{PACKAGE_EXTENSION}"))
    assert pkg.stats_payload and len(pkg.stats_payload["results"]) == len(result.stats_report.results)
    loaded, spec2 = controller.loaded_from_package(pkg)
    pd.testing.assert_frame_equal(loaded.info.dataframe, data.info.dataframe, check_exact=True)
    assert loaded.source_path is None and loaded.table_name == spec["input_table"]
    controller.render(spec2, loaded)


def test_legacy_export_bundle_unchanged(controller):
    data = controller.load_example("scatterplot_with_regression")
    spec = controller.build_spec("scatterplot_with_regression", "publication", data.table_name,
                                 controller.default_mapping("scatterplot_with_regression"))
    result = controller.render(spec, data)
    blob = controller.export_bundle(spec, result, ["svg", "png", "pdf"], basename="scatter")
    assert {"scatter.svg", "scatter.png", "scatter.pdf", "scatter.plot_spec.json"} == set(zipfile.ZipFile(io.BytesIO(blob)).namelist())


def test_package_content_with_matrix_context(controller):
    import make_my_figure_core.matrix_workflow as mw

    data = controller.load_example("heatmap_clustered_matrix")
    df = data.info.dataframe
    num = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    fid = [c for c in df.columns if c not in num][0]
    mspec = mw.MatrixSpec(source_file=data.table_name, feature_id_column=fid, value_columns=num,
                          value_type="intensity", confirmed_by_user=True)
    derived, dspec, ps = controller.matrix_apply_preprocessing(data, mspec, [{"method": "row_zscore", "params": {}}])
    spec = controller.build_spec("heatmap_clustered_matrix", "publication", derived.table_name,
                                 {"feature_id": fid, "value_columns": num},
                                 source={"source_workflow": "matrix"})
    result = controller.render(spec, derived)
    mc = MatrixContext(source_dataframe=df, source_name=data.table_name, matrix_spec=dspec, preprocessing_spec=ps)
    content = controller.package_content(derived, spec, result, matrix=mc, name="heat")
    assert {t.role for t in content.tables} == {"source_table", "derived_table"}
    pkg = controller.open_package(controller.package_bytes(content))
    assert pkg.preprocessing_spec and pkg.matrix_spec
    assert verify_preprocessing(pkg)["status"] == "identical"
    loaded, spec2 = controller.loaded_from_package(pkg)
    pd.testing.assert_frame_equal(loaded.info.dataframe, derived.info.dataframe, check_exact=True)


def test_every_plot_type_packages_and_reopens(controller):
    from make_my_figure_core.plots.registry import available_plot_types

    failures = []
    for pt in available_plot_types():
        try:
            data = controller.load_example(pt)
            spec = controller.build_spec(pt, "publication", data.table_name, controller.default_mapping(pt))
            result = controller.render(spec, data)
            pkg = controller.open_package(controller.package_bytes(controller.package_content(data, spec, result, name=pt)))
            loaded2, spec2 = controller.loaded_from_package(pkg)
            r2 = controller.render(spec2, loaded2)
            assert r2.metadata.get("plot_type") == result.metadata.get("plot_type")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{pt}: {exc}")
    assert not failures, failures


def test_open_package_errors_are_package_errors(controller, tmp_path):
    from make_my_figure_core.package import PackageError

    bad = tmp_path / "x.mmfpackage"
    bad.write_bytes(b"not a zip")
    with pytest.raises(PackageError):
        controller.open_package(str(bad))
