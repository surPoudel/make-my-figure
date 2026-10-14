"""General-table workflow, end to end, on the real bee workbook and the real window.

Import the workbook → assign roles → preview and apply log10 → plot the derived
column → the raw table is untouched → the three-way design is explained as not
estimable → export the derived table → save a Figure Package → reopen it in a
fresh process with the source file gone → identical values; tampering is caught.
"""
import json
import math
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import pytest

matplotlib.use("Agg")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtWidgets import QApplication, QDialog

    from apps.desktop_app import table_workflow
    from apps.desktop_app.main import MainWindow
except Exception as exc:  # noqa: BLE001
    pytest.skip(f"PySide6/Qt unavailable: {exc}", allow_module_level=True)

from make_my_figure_core.tabular import TableTransform  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BEE = ROOT / "tests" / "fixtures" / "bee_demo_workbook.xlsx"
SIZE = "bee body size_mm"
LOGSIZE = f"log10({SIZE})"


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def bee_copy(tmp_path):
    p = tmp_path / "demo data.xlsx"
    shutil.copy(BEE, p)
    return p


def _open(win, path):
    win.load_path(str(path))
    QApplication.processEvents()
    assert win.data is not None and list(win.data.info.dataframe.columns)[0] == "sample id"


def _drive_dialog(monkeypatch, actions):
    """Replace exec() so the real dialog runs ``actions(dlg)`` and then returns."""
    def fake_exec(dlg):
        actions(dlg)
        return QDialog.Accepted if dlg.result_data is not None else QDialog.Rejected

    monkeypatch.setattr(table_workflow.TableWorkflowDialog, "exec", fake_exec)


def _log10_size(dlg):
    dlg.tf_column.setCurrentText(SIZE)
    dlg.tf_method.setCurrentIndex(dlg.tf_method.findData("log10"))
    assert dlg.btn_add.isEnabled(), dlg.tf_summary.text()
    assert "Valid: 4 · invalid: 0 · missing: 0" in dlg.tf_summary.text()
    # the preview shows original and transformed side by side
    assert dlg.preview_table.item(0, 0).text() == "3.1"
    assert float(dlg.preview_table.item(0, 1).text()) == pytest.approx(math.log10(3.1), rel=1e-5)
    dlg._add_transform()
    dlg.an_response.setCurrentText(LOGSIZE)
    dlg._apply()


def test_bee_workbook_roles_transform_plot_and_raw_untouched(app, bee_copy, monkeypatch):
    win = MainWindow()
    _open(win, bee_copy)
    raw_before = win.data.info.dataframe.copy()
    _drive_dialog(monkeypatch, _log10_size)
    win.action_table_workflow()

    df = win.data.info.dataframe
    assert LOGSIZE in df.columns and SIZE in df.columns
    np.testing.assert_allclose(df[LOGSIZE], np.log10(raw_before[SIZE]), rtol=0, atol=1e-15)
    pd.testing.assert_frame_equal(win.controller.raw_of(win.data).info.dataframe, raw_before)
    pd.testing.assert_frame_equal(df[raw_before.columns], raw_before)
    # the editor now plots the derived response by the first factor
    assert win._mapping_widgets["y"].currentText() == LOGSIZE
    assert win._mapping_widgets["x"].currentText() == "treatment"
    ax = win._canvas.figure.axes[0]
    pts = np.concatenate([c.get_offsets()[:, 1] for c in ax.collections if len(c.get_offsets())])
    np.testing.assert_allclose(np.sort(pts), np.sort(np.log10(raw_before[SIZE])), atol=1e-12)
    # a log axis on the already-logged column is refused (no double log)
    win._style_box.setChecked(True)
    w = win._axis_scale_widgets["y"]
    w["scale"].setCurrentIndex(w["scale"].findData("log10"))
    win.render_preview()
    assert win._canvas.figure.axes[0].get_yscale() == "linear"
    assert any("twice" in m for m in win._current_result.warnings)
    # revert brings back the original table
    assert win.revert_btn.isVisibleTo(win)
    win.action_revert_data()
    pd.testing.assert_frame_equal(win.data.info.dataframe, raw_before)
    win.close()


def test_three_way_design_on_the_bee_workbook_is_explained_not_computed(app, bee_copy, monkeypatch):
    win = MainWindow()
    _open(win, bee_copy)
    dlg = table_workflow.TableWorkflowDialog(win.controller, win.data, win)
    for i, f in enumerate(("treatment", "social setting", "time")):
        dlg.an_factors[i].setCurrentText(f)
    dlg.an_response.setCurrentText("total quantity")
    dlg.an_subject.setCurrentText("(none)")
    dlg._run()
    text = dlg.an_report.toPlainText()
    assert "cannot be estimated" in text
    for reason in ("same value (100) in every row", "completely confounded", "no observations",
                   "No residual degrees of freedom"):
        assert reason in text, reason
    assert dlg.an_table.rowCount() == 0 and not dlg.btn_export_anova.isEnabled()
    dlg.close()
    win.close()


def test_zero_and_negative_values_need_an_explicit_decision(app, tmp_path):
    win = MainWindow()
    p = tmp_path / "counts.csv"
    pd.DataFrame({"plot": ["a", "b", "c", "d", "e"], "count": [0, 3, 10, -1, 25]}).to_csv(p, index=False)
    win.load_path(str(p))
    dlg = table_workflow.TableWorkflowDialog(win.controller, win.data, win)
    dlg.tf_column.setCurrentText("count")
    dlg.tf_method.setCurrentIndex(dlg.tf_method.findData("log10"))
    assert not dlg.btn_add.isEnabled()
    assert "2 of 5 value(s)" in dlg.tf_summary.text()
    dlg.tf_invalid.setCurrentIndex(dlg.tf_invalid.findData("missing"))
    assert dlg.btn_add.isEnabled()
    dlg._add_transform()
    dlg._apply()
    derived = dlg.result_data.info.dataframe
    assert derived["log10(count)"].isna().sum() == 2
    assert derived["count"].tolist() == [0, 3, 10, -1, 25]          # originals kept
    record = dlg.result_data.table_context["record"]
    assert record.preprocessing_steps[0].parameters["n_invalid"] == 2
    assert record.preprocessing_steps[0].parameters["invalid"] == "missing"
    dlg.close()
    win.close()


def test_export_and_package_round_trip_in_a_fresh_process(app, bee_copy, monkeypatch, tmp_path):
    win = MainWindow()
    _open(win, bee_copy)
    _drive_dialog(monkeypatch, _log10_size)
    win.action_table_workflow()
    derived = win.data.info.dataframe.copy()

    # export: actual values + record with checksums
    out = tmp_path / "derived.csv"
    written = win.controller.export_derived_table(win.data, str(out))
    back = pd.read_csv(out)
    np.testing.assert_allclose(back[LOGSIZE], derived[LOGSIZE], rtol=1e-15)
    rec = json.loads(Path(written[1]).read_text())
    assert rec["workflow"] == "table" and rec["source_sheet"] == "Sheet1"
    assert rec["source_sha256"] and len(rec["source_sha256"]) == 64
    step = rec["preprocessing_steps"][0]["parameters"]
    assert step["column"] == SIZE and step["output_column"] == LOGSIZE and step["base"] == 10.0
    assert step["offset"] == 0.0 and step["invalid"] == "refuse"
    assert rec["output_table_digest"] and rec["exported_table_digest"]

    # package
    win.render_preview()
    content = win.controller.package_content(win.data, win._current_spec, win._current_result,
                                             matrix=win._matrix_context(), name="bee")
    pkg_path = tmp_path / "bee.mmfpackage"
    pkg_path.write_bytes(win.controller.package_bytes(content))
    win.close()

    # the source changes after packaging, then disappears; the package must not care
    pd.DataFrame({"x": [1]}).to_excel(bee_copy, index=False)
    moved = tmp_path / "moved" / "bee.mmfpackage"
    moved.parent.mkdir()
    shutil.move(pkg_path, moved)
    os.remove(bee_copy)

    probe = f"""
import json, sys
sys.path.insert(0, {str(ROOT)!r})
from apps.desktop_app.controller import DesktopController
from make_my_figure_core.package.reader import verify_preprocessing
c = DesktopController()
pkg = c.open_package(open({str(moved)!r}, 'rb').read())
data, spec = c.loaded_from_package(pkg)
res = c.render(spec, data)
print(json.dumps({{"values": data.info.dataframe[{LOGSIZE!r}].tolist(),
                  "raw": c.raw_of(data).info.dataframe[{SIZE!r}].tolist(),
                  "verify": verify_preprocessing(pkg)["status"], "y": spec["mapping"]["y"],
                  "derived_cols": data.table_context["record"].derived_columns}}))
"""
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "MPLBACKEND": "Agg"}
    out = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, env=env, timeout=300)
    assert out.returncode == 0, out.stderr[-2000:]
    got = json.loads(out.stdout.strip().splitlines()[-1])
    assert got["values"] == derived[LOGSIZE].tolist()
    assert got["raw"] == derived[SIZE].tolist()
    assert got["verify"] == "identical" and got["y"] == LOGSIZE and got["derived_cols"] == [LOGSIZE]

    # tampering with the frozen derived table is detected
    from apps.desktop_app.controller import DesktopController
    from make_my_figure_core.package import PackageIntegrityError

    tampered = tmp_path / "tampered.mmfpackage"
    with zipfile.ZipFile(moved) as zin, zipfile.ZipFile(tampered, "w") as zout:
        for item in zin.infolist():
            blob = zin.read(item.filename)
            if item.filename.endswith("derived_table.mmftable.json"):
                blob = blob.replace(b"0.49", b"0.48", 1)
            zout.writestr(item, blob)
    with pytest.raises(PackageIntegrityError):
        DesktopController().open_package(tampered.read_bytes())


def test_analysis_tab_builds_the_derived_table_once_per_transformation_list(app, tmp_path, monkeypatch):
    # Refreshing the analysis lists rebuilt the derived table once per numeric
    # column, with full checksums: 3.8 s per rebuild on a million-row table.
    import make_my_figure_core.tabular as tab

    win = MainWindow()
    p = tmp_path / "big.csv"
    rng = np.random.default_rng(0)
    pd.DataFrame({"g": rng.choice(list("abc"), 5000), "y": rng.lognormal(3, 1, 5000),
                  "z": rng.normal(0, 1, 5000), "w": rng.normal(5, 1, 5000)}).to_csv(p, index=False)
    win.load_path(str(p))
    dlg = table_workflow.TableWorkflowDialog(win.controller, win.data, win)
    dlg.tf_column.setCurrentText("y")
    dlg.tf_method.setCurrentIndex(dlg.tf_method.findData("log10"))
    dlg._add_transform()
    calls = []
    real = tab.apply_table_transforms

    def counting(*a, **k):
        calls.append(k.get("with_checksums", True))
        return real(*a, **k)

    monkeypatch.setattr(tab, "apply_table_transforms", counting)
    for _ in range(5):
        dlg._fill_analysis_from_roles()
    assert len(calls) <= 1 and calls == [False] * len(calls), calls
    dlg.close()
    win.close()


def test_every_invalid_row_in_the_preview_is_marked(app, tmp_path):
    win = MainWindow()
    p = tmp_path / "many_zeros.csv"
    pd.DataFrame({"g": ["a"] * 60, "y": [0.0] * 30 + list(range(1, 31))}).to_csv(p, index=False)
    win.load_path(str(p))
    dlg = table_workflow.TableWorkflowDialog(win.controller, win.data, win)
    dlg.tf_column.setCurrentText("y")
    dlg.tf_method.setCurrentIndex(dlg.tf_method.findData("log10"))
    marked = sum(1 for i in range(dlg.preview_table.rowCount()) if dlg.preview_table.item(i, 1).text() == "invalid")
    assert marked == 30          # rows past the 20th used to show "—"
    dlg.close()
    win.close()
