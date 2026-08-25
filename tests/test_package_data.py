"""The built distribution must carry the resources the package reads at runtime.

Every published wheel shipped without ``schemas/``, ``style_profiles/``, ``mock_data/`` and
``examples/``, because a wheel contains only the package directory and those folders sit at the
project root. The result was that ``pip install make_my_figure_core`` produced a package which
raised ``FileNotFoundError`` on ``schemas/plot_spec.schema.json`` the first time anything was
rendered - the primary operation of the library. It went unnoticed because everything in this
repository runs from a checkout, where the root copies are found.

The cheap checks here run always. The expensive one - build a wheel, install it into a throwaway
virtual environment and render from it - is opt-in via RUN_PACKAGING_BUILD_TESTS=1, because a build
plus an install takes a few minutes and needs network access for dependencies.
"""

from __future__ import annotations

import os
import subprocess
import sys
import zipfile

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _read(*parts):
    with open(os.path.join(_ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


# --------------------------------------------------------------------------------------
# configuration: the build must be told to carry the resources
# --------------------------------------------------------------------------------------

def test_bundled_dir_lists_agree():
    """setup.py stages the folders; resources.py looks for them. The lists must match."""
    from make_my_figure_core.resources import BUNDLED_DIRS

    setup_py = _read("setup.py")
    for name in BUNDLED_DIRS:
        assert f'"{name}"' in setup_py, (
            f"{name!r} is resolved by resources.py but setup.py does not stage it")
    # and the folders actually exist in the checkout
    for name in BUNDLED_DIRS:
        assert os.path.isdir(os.path.join(_ROOT, name)), f"{name}/ is missing from the checkout"


def test_manifest_grafts_every_bundled_dir():
    """Without this the sdist has no resources, so a build from the sdist stages nothing."""
    from make_my_figure_core.resources import BUNDLED_DIRS

    manifest = _read("MANIFEST.in")
    for name in BUNDLED_DIRS:
        assert f"graft {name}" in manifest, f"MANIFEST.in must graft {name}"


def test_pyproject_declares_the_staged_package_data():
    pyproject = _read("pyproject.toml")
    assert "_bundled" in pyproject, "package-data must include the staged _bundled tree"
    assert "[tool.setuptools.package-data]" in pyproject


# --------------------------------------------------------------------------------------
# resolution order
# --------------------------------------------------------------------------------------

def test_checkout_resolves_to_the_project_root():
    """A checkout must keep using the root copies, and must not grow a staged copy."""
    from make_my_figure_core.resources import missing_bundled_dirs, project_base

    assert os.path.abspath(project_base()) == _ROOT
    assert missing_bundled_dirs() == []
    assert not os.path.isdir(os.path.join(_ROOT, "make_my_figure_core", "_bundled")), (
        "the build must stage into build_lib, never into the source tree")


def test_environment_override_still_wins(tmp_path, monkeypatch):
    (tmp_path / "schemas").mkdir()
    monkeypatch.setenv("MAKE_MY_FIGURE_RESOURCES", str(tmp_path))
    from make_my_figure_core import resources

    assert os.path.abspath(resources.project_base()) == os.path.abspath(str(tmp_path))


def test_staged_package_dir_is_preferred_over_the_root(tmp_path, monkeypatch):
    """Simulates the installed layout: resources sit inside the package."""
    from make_my_figure_core import resources

    staged = tmp_path / "_bundled"
    (staged / "schemas").mkdir(parents=True)
    monkeypatch.delenv("MAKE_MY_FIGURE_RESOURCES", raising=False)
    monkeypatch.setattr(resources, "_STAGED_BASE", str(staged))
    assert os.path.abspath(resources.project_base()) == os.path.abspath(str(staged))


def test_frozen_bundle_still_wins_over_everything(tmp_path, monkeypatch):
    from make_my_figure_core import resources

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    try:
        assert os.path.abspath(resources.project_base()) == os.path.abspath(str(tmp_path))
    finally:
        for attr in ("frozen", "_MEIPASS"):
            if hasattr(sys, attr):
                monkeypatch.delattr(sys, attr, raising=False)


def test_missing_bundled_dirs_names_what_is_absent(tmp_path, monkeypatch):
    """A caller should be able to say which folder is missing, not just hit a stray path."""
    from make_my_figure_core import resources

    monkeypatch.delenv("MAKE_MY_FIGURE_RESOURCES", raising=False)
    staged = tmp_path / "_bundled"
    (staged / "schemas").mkdir(parents=True)          # only one of the four
    monkeypatch.setattr(resources, "_STAGED_BASE", str(staged))
    missing = resources.missing_bundled_dirs()
    assert "schemas" not in missing
    assert {"style_profiles", "mock_data", "examples"} <= set(missing)


# --------------------------------------------------------------------------------------
# the real thing: build, install, render
# --------------------------------------------------------------------------------------

def _build(outdir):
    subprocess.run([sys.executable, "-m", "build", "--outdir", str(outdir)],
                   cwd=_ROOT, check=True, capture_output=True, timeout=1800)
    wheels = [f for f in os.listdir(outdir) if f.endswith(".whl")]
    assert len(wheels) == 1, f"expected one wheel, got {wheels}"
    return os.path.join(outdir, wheels[0])


@pytest.mark.skipif(not os.environ.get("RUN_PACKAGING_BUILD_TESTS"),
                    reason="set RUN_PACKAGING_BUILD_TESTS=1 to build a wheel (slow, needs network)")
def test_built_wheel_contains_every_bundled_dir(tmp_path):
    from make_my_figure_core.resources import BUNDLED_DIRS

    wheel = _build(tmp_path / "dist")
    with zipfile.ZipFile(wheel) as zf:
        names = zf.namelist()
    for name in BUNDLED_DIRS:
        prefix = f"make_my_figure_core/_bundled/{name}/"
        assert any(n.startswith(prefix) for n in names), f"wheel is missing {name}/"
    assert "make_my_figure_core/_bundled/schemas/plot_spec.schema.json" in names, (
        "the plot-spec schema is what render() needs first; it must be in the wheel")


@pytest.mark.skipif(not os.environ.get("RUN_PACKAGING_BUILD_TESTS"),
                    reason="set RUN_PACKAGING_BUILD_TESTS=1 to build and install (slow)")
def test_installed_wheel_can_render_every_plot_type(tmp_path):
    """The check that would have caught the original bug: render from an install, not a checkout."""
    wheel = _build(tmp_path / "dist")
    venv = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True, capture_output=True)
    python = str(venv / ("Scripts" if os.name == "nt" else "bin") / "python")
    subprocess.run([python, "-m", "pip", "install", "--quiet", wheel],
                   check=True, capture_output=True, timeout=1800)

    probe = tmp_path / "probe.py"
    probe.write_text(
        "import matplotlib; matplotlib.use('Agg')\n"
        "import warnings, matplotlib.pyplot as plt\n"
        "from make_my_figure_core.plots.registry import _RENDERERS, render\n"
        "from make_my_figure_core import examples as ex\n"
        "from make_my_figure_core.resources import missing_bundled_dirs\n"
        "assert missing_bundled_dirs() == [], missing_bundled_dirs()\n"
        "ok = 0\n"
        "for pt in _RENDERERS:\n"
        "    info, aux, spec = ex.load_example(pt)\n"
        "    with warnings.catch_warnings():\n"
        "        warnings.simplefilter('ignore')\n"
        "        res = (render(spec, info.dataframe,\n"
        "                      aux={k: v.dataframe for k, v in aux.items()})\n"
        "               if aux else render(spec, info.dataframe))\n"
        "    plt.close(res.figure); ok += 1\n"
        "print(f'{ok}/{len(_RENDERERS)}')\n",
        encoding="utf-8")
    out = subprocess.run([python, str(probe)], check=True, capture_output=True,
                         text=True, timeout=1800)
    rendered, total = out.stdout.strip().splitlines()[-1].split("/")
    assert rendered == total, f"only {rendered} of {total} plot types rendered from the install"
