"""Packaging smoke tests (no full PyInstaller build required).

A real PyInstaller build is slow and platform-specific; it is exercised by the
build scripts / CI. Here we check the things that commonly break packaging:
single-source version, presence + sanity of the spec, build scripts, the CI
workflow, and that frozen resource resolution would work.
"""

import os

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _read(*parts):
    with open(os.path.join(_ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


def test_version_single_source():
    from make_my_figure_core import __version__
    from make_my_figure_core.version import __version__ as v2

    assert __version__ == v2
    pyproject = _read("pyproject.toml")
    # pyproject must read the version dynamically from the single source.
    assert 'dynamic = ["version"]' in pyproject
    assert "make_my_figure_core.version.__version__" in pyproject


def test_pyinstaller_spec_present_and_sane():
    spec = _read("packaging", "make_my_figure.spec")
    assert "apps" in spec and "desktop_app" in spec and "main.py" in spec
    for res in ("schemas", "style_profiles", "mock_data", "assets"):
        assert res in spec, f"spec must bundle {res}"
    assert "BUNDLE(" in spec  # macOS .app


@pytest.mark.parametrize("path", [
    ("scripts", "build_desktop.py"),
    ("scripts", "build_windows.ps1"),
    ("scripts", "build_macos.sh"),
    ("scripts", "build_linux.sh"),
    ("scripts", "make_icons.py"),
    ("packaging", "windows_installer.iss"),
    (".github", "workflows", "build_desktop_releases.yml"),
])
def test_build_artifacts_present(path):
    full = os.path.join(_ROOT, *path)
    assert os.path.exists(full), f"missing {path}"
    assert os.path.getsize(full) > 50


def test_ci_matrix_covers_three_os():
    wf = _read(".github", "workflows", "build_desktop_releases.yml")
    for os_name in ("windows-latest", "macos-latest", "ubuntu-latest"):
        assert os_name in wf
    # signing must be optional (guarded by secrets), not required
    assert "secrets." in wf


def test_icons_exist():
    for f in ("icon.png", "icon.ico", "icon_256.png"):
        assert os.path.exists(os.path.join(_ROOT, "assets", "icons", f))


def test_frozen_resource_resolution(tmp_path, monkeypatch):
    """Simulate a frozen app: _MEIPASS dir with bundled resources resolves."""
    import importlib

    # Build a fake bundle dir with the resource folders.
    (tmp_path / "schemas").mkdir()
    (tmp_path / "style_profiles").mkdir()
    import sys

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    import make_my_figure_core.resources as res
    importlib.reload(res)
    assert res.project_base() == str(tmp_path)
    assert res.resource_path("schemas").endswith("schemas")
    # restore for other tests
    monkeypatch.undo()
    importlib.reload(res)
