"""Tests for the on-demand R environment bootstrap + DESeq2 method wiring.

Network-free: we exercise path resolution, command construction, resolver
preference order, and the missing-R error paths. The actual ~1 GB install and
the live DESeq2 run are only exercised when R is present.
"""

import os
import sys

import numpy as np
import pandas as pd
import pytest

from make_my_figure_core.rnaseq import r_setup as rs
from make_my_figure_core.rnaseq.rscript import DE_SCRIPTS, DESEQ2_DE_R
from make_my_figure_core.rnaseq.runner import (
    METHOD_PACKAGES, RDependencyError, check_r_environment, find_rscript, run_de_pipeline,
)


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("MAKE_MY_FIGURE_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("MAKE_MY_FIGURE_RSCRIPT", raising=False)
    return tmp_path


def test_app_data_and_prefix(data_dir):
    assert rs.app_data_dir() == str(data_dir)
    assert rs.r_env_prefix() == os.path.join(str(data_dir), "r_env")
    assert rs.managed_rscript_path() is None  # nothing installed yet


def test_platform_key_is_known():
    assert rs._platform_key() in {"linux-64", "linux-aarch64", "osx-64", "osx-arm64", "win-64"}


def test_install_command_has_all_packages(data_dir):
    cmd = rs.install_command("/x/micromamba", rs.r_env_prefix())
    assert cmd[:3] == ["/x/micromamba", "create", "-y"]
    assert "-c" in cmd and "conda-forge" in cmd and "bioconda" in cmd
    for pkg in ("r-base>=4.2", "bioconductor-edger", "bioconductor-limma",
                "bioconductor-deseq2", "r-jsonlite"):
        assert pkg in cmd


def test_rscript_preference_order(data_dir, monkeypatch):
    # 1) managed env detected when a fake Rscript exists
    binp = os.path.join(rs.r_env_prefix(), "bin")
    os.makedirs(binp, exist_ok=True)
    fake = os.path.join(binp, "Rscript")
    open(fake, "w").close()
    assert rs.managed_rscript_path() == fake
    assert find_rscript() == fake
    # 2) explicit override beats the managed env
    override = os.path.join(str(data_dir), "custom_Rscript")
    open(override, "w").close()
    monkeypatch.setenv("MAKE_MY_FIGURE_RSCRIPT", override)
    assert find_rscript() == override


def test_bundled_rscript_detected_via_meipass(data_dir, monkeypatch, tmp_path):
    # Simulate a frozen build with R bundled under sys._MEIPASS/r_env.
    meipass = tmp_path / "meipass"
    binp = meipass / "r_env" / "bin"
    binp.mkdir(parents=True)
    fake = binp / "Rscript"
    fake.write_text("")
    monkeypatch.setattr(sys, "_MEIPASS", str(meipass), raising=False)
    assert rs.bundled_rscript_path() == str(fake)
    # find_rscript prefers the bundled R over PATH / managed env
    monkeypatch.delenv("MAKE_MY_FIGURE_RSCRIPT", raising=False)
    assert find_rscript() == str(fake)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    assert rs.bundled_rscript_path() is None


def test_check_environment_method_packages(data_dir):
    assert METHOD_PACKAGES["deseq2"] == ["DESeq2", "jsonlite"]
    assert set(METHOD_PACKAGES["edger_limma_voom"]) == {"edgeR", "limma", "jsonlite"}
    env = check_r_environment(method="deseq2")
    assert isinstance(env.ready, bool)
    if not env.ready:
        assert "DESeq2" in env.message or "Set up R" in env.message


def test_deseq2_script_present_and_shaped():
    assert "deseq2" in DE_SCRIPTS and "edger_limma_voom" in DE_SCRIPTS
    assert "DESeqDataSetFromMatrix" in DESEQ2_DE_R
    assert "results(dds" in DESEQ2_DE_R
    # maps DESeq2 columns to the app's schema
    assert "log2FoldChange" in DESEQ2_DE_R and "adj.P.Val" in DESEQ2_DE_R


def test_unknown_method_rejected(data_dir):
    with pytest.raises(ValueError):
        run_de_pipeline(pd.DataFrame({"S1": [1]}), pd.DataFrame(),
                        sample_id_col="s", group_col="g", reference_group="a",
                        comparisons=[], method="bogus")


def test_deseq2_without_r_raises(data_dir):
    if check_r_environment(method="deseq2").ready:
        pytest.skip("R with DESeq2 is installed")
    rng = np.random.default_rng(0)
    counts = pd.DataFrame(rng.integers(0, 500, size=(50, 6)),
                          columns=[f"S{i}" for i in range(6)], index=[f"G{i}" for i in range(50)])
    meta = pd.DataFrame({"SampleID": [f"S{i}" for i in range(6)], "Group": ["A"] * 3 + ["B"] * 3})
    with pytest.raises(RDependencyError):
        run_de_pipeline(counts, meta, sample_id_col="SampleID", group_col="Group",
                        reference_group="A", comparisons=[{"group1": "B", "group2": "A"}],
                        method="deseq2")


@pytest.mark.skipif(not check_r_environment(method="deseq2").ready,
                    reason="R + DESeq2 not installed")
def test_deseq2_with_r():
    rng = np.random.default_rng(1)
    n_per = 4
    samples = [f"C{i}" for i in range(n_per)] + [f"T{i}" for i in range(n_per)]
    base = rng.integers(50, 500, size=300)
    mat = np.vstack([rng.poisson(base) for _ in samples]).T
    mat[:30, n_per:] *= 4
    counts = pd.DataFrame(mat, columns=samples, index=[f"G{i:05d}" for i in range(300)])
    meta = pd.DataFrame({"SampleID": samples, "Group": ["Ctrl"] * n_per + ["Trt"] * n_per})
    res = run_de_pipeline(counts, meta, sample_id_col="SampleID", group_col="Group",
                          reference_group="Ctrl", comparisons=[{"group1": "Trt", "group2": "Ctrl"}],
                          method="deseq2")
    assert res["rnaseq_spec"].de_method_id == "deseq2"
    de = pd.read_csv(next(iter(res["de_tables"].values())), sep="\t", index_col=0)
    for col in ("logFC", "P.Value", "adj.P.Val"):
        assert col in de.columns


def test_windows_install_uses_biocmanager_not_bioconda(data_dir, monkeypatch):
    # On Windows, Bioconda has no builds -> create with conda-forge + r-biocmanager,
    # then a separate BiocManager step installs edgeR/limma/DESeq2.
    monkeypatch.setattr(rs, "_is_windows", lambda: True)
    channels, packages = rs.conda_packages_for_platform()
    assert channels == ["conda-forge"]
    assert "r-biocmanager" in packages
    assert not any(p.startswith("bioconductor-") for p in packages)
    bcmd = rs._biocmanager_command("/x/Rscript")
    joined = " ".join(bcmd)
    assert "BiocManager::install" in joined
    for p in ("edgeR", "limma", "DESeq2"):
        assert p in joined


def test_unix_install_uses_bioconda(data_dir, monkeypatch):
    monkeypatch.setattr(rs, "_is_windows", lambda: False)
    channels, packages = rs.conda_packages_for_platform()
    assert channels == ["conda-forge", "bioconda"]
    assert "bioconductor-edger" in packages and "bioconductor-deseq2" in packages


def test_conda_prefix_and_windows_dll_path(data_dir, monkeypatch, tmp_path):
    # prefix detection from a conda-style Rscript path
    prefix = tmp_path / "r_env"
    (prefix / "bin").mkdir(parents=True)
    rscript = prefix / "bin" / "Rscript"
    rscript.write_text("")
    assert rs.conda_prefix_of(str(rscript)) == str(prefix)
    # On non-Windows, env is unchanged (rpath handles DLLs)
    monkeypatch.setattr(rs, "_is_windows", lambda: False)
    assert rs.rscript_subprocess_env(str(rscript))["PATH"] == os.environ.get("PATH", "")
    # On Windows, the conda library dirs are prepended to PATH
    for sub in ("Library/bin", "Library/mingw-w64/bin", "Scripts"):
        (prefix / sub).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(rs, "_is_windows", lambda: True)
    win_path = rs.rscript_subprocess_env(str(rscript))["PATH"]
    assert str(prefix / "Library" / "bin") in win_path
    assert str(prefix / "Scripts") in win_path
    assert win_path.startswith(str(prefix))  # env dirs come first
