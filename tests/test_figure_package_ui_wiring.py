"""Source-text guardrails: both frontends expose the figure package through the shared core,
and the wording keeps PlotSpec / Figure preset / Figure package distinct (Qt and Streamlit
cannot run in the test sandbox, so the wiring is checked from the source)."""
from __future__ import annotations

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


def test_desktop_uses_core_package_module_only():
    main = _read("apps", "desktop_app", "main.py")
    ctrl = _read("apps", "desktop_app", "controller.py")
    assert "from make_my_figure_core.package import" in main and "make_my_figure_core.package" in ctrl
    assert "zipfile" not in main.split("def action_save_package")[1].split("def action_open_package")[0], \
        "the window must not build package ZIPs itself"


def test_desktop_landing_page_and_menu_have_open_figure_package():
    main = _read("apps", "desktop_app", "main.py")
    assert '("Open Figure Package", self.action_open_package)' in main
    assert '("Open data file", self.action_open_file)' in main and '("Recent files", self.action_recent_dialog)' in main
    assert "Open Figure Package…" in main and "Save Reproducible Figure Package…" in main
    assert "Save Figure Package (.mmfpackage)" in main


def test_desktop_plotspec_wording_is_explicit_and_package_privacy_shown():
    main = _read("apps", "desktop_app", "main.py")
    assert "Export PlotSpec JSON (specification only)" in main
    assert "specification only; needs the data file" in main
    assert "Figure packages include the data required to reproduce the figure." in main
    assert "PACKAGE_PRIVACY_NOTICE" in main


def test_desktop_routes_packages_through_loader_and_recent_files():
    main = _read("apps", "desktop_app", "main.py")
    lp = main.split("def load_path(self, path: str):")[1].split("def load_example")[0]
    assert "is_package_path(path)" in lp and "self.open_package_path(path)" in lp
    rec = main.split("def _refresh_recent_menu")[1]
    assert "is_package_path(p)" in rec


def test_desktop_open_package_verifies_records_and_handles_errors():
    main = _read("apps", "desktop_app", "main.py")
    body = main.split("def open_package_path")[1].split("def _open_composite_package")[0]
    assert "except PackageError as exc" in body and "QMessageBox.critical" in body
    assert "verify_statistics" in body and "verify_preprocessing" in body
    assert "integrity verified" in body


def test_desktop_export_all_includes_package_and_selftest_covers_round_trip():
    main = _read("apps", "desktop_app", "main.py")
    assert "export_all_bundle(" in main.split("def export_zip")[1].split("def _recent_files")[0]
    st = main.split("def _selftest")[1]
    assert "package_content" in st and "open_package" in st and "loaded_from_package" in st


def test_figure_builder_has_save_package_and_layout_restore():
    sp = _read("apps", "desktop_app", "stats_panel.py")
    assert 'QPushButton("Save Figure Package…")' in sp and "def _save_package" in sp
    assert "content_for_composite" in sp and "initial_layout" in sp and "_apply_layout_to_controls(FigureLayout.from_dict(initial_layout))" in sp


def test_streamlit_has_open_and_download_package_via_core():
    app = _read("apps", "streamlit_app", "streamlit_app.py")
    assert '"Open Figure Package"' in app and "open_figure_package(" in app and "build_package_bytes" in app
    assert "content_for_single_plot" in app and "rebuild_composite" in app
    assert "Figure packages include the data required to reproduce the figure." in app
    assert "zipfile" not in app, "Streamlit must not build package ZIPs itself"


def test_help_text_distinguishes_the_three_artifacts():
    hc = _read("apps", "desktop_app", "help_content.py")
    for word in ("PlotSpec", "Figure preset", "Figure package", "does NOT contain the data", "Never contains data"):
        assert word in hc
    from make_my_figure_core.package import ARTIFACT_DESCRIPTIONS

    assert set(ARTIFACT_DESCRIPTIONS) == {"plot_spec", "figure_preset", "figure_package"}
    assert "source data are required" in ARTIFACT_DESCRIPTIONS["plot_spec"]
    assert "no data" in ARTIFACT_DESCRIPTIONS["figure_preset"]
    assert "frozen data" in ARTIFACT_DESCRIPTIONS["figure_package"]


def test_schema_is_bundled():
    from make_my_figure_core.resources import resource_path

    assert os.path.exists(resource_path("schemas", "figure_package_manifest.schema.json"))
    spec = _read("packaging", "make_my_figure.spec")
    assert "schemas" in spec
