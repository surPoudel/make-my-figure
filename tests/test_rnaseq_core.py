"""RNA-seq core tests: detection, DE tables, expression, config, validation, R env.

Uses the real example files in ``test_matrix/`` where present.
"""

import json
import os

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from make_my_figure_core.rnaseq import (
    build_expression_matrix, check_r_environment, classify_de, detect_de_columns,
    detect_input_mode, heatmap_spec_from_expression, load_rnaseq_table, parse_de_table,
    parse_rnaseq_config, transform_matrix, validate_counts, validate_metadata,
    volcano_spec_from_de,
)
from make_my_figure_core.rnaseq.detect import split_expression_matrix
from make_my_figure_core.rnaseq.runner import RDependencyError, run_de_pipeline
from make_my_figure_core.plots.registry import render, render_to_files

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_TM = os.path.join(_ROOT, "test_matrix")
_HAS_DE = os.path.exists(os.path.join(_TM, "Ctrl_vs_Treatment_DE.txt"))
_HAS_VOOM = os.path.exists(os.path.join(_TM, "voom_norm_annot.txt"))
_HAS_META = os.path.exists(os.path.join(_TM, "meta_info_detail.csv"))
_HAS_CFG = os.path.exists(os.path.join(_TM, "config.json"))


# --- column alias detection (synthetic, always runs) ----------------------

def test_detect_de_columns_aliases():
    df = pd.DataFrame(columns=["GeneID", "symbol", "log2FoldChange", "pvalue", "padj",
                               "baseMean", "stat", "extra"])
    det = detect_de_columns(df)
    assert det["gene_id"] == "GeneID"
    assert det["gene_symbol"] == "symbol"
    assert det["logFC"] == "log2FoldChange"
    assert det["p_value"] == "pvalue"
    assert det["adj_p"] == "padj"
    assert det["ave_expr"] == "baseMean"
    assert det["statistic"] == "stat"


# --- Mode A: precomputed DE table -----------------------------------------

@pytest.mark.skipif(not _HAS_DE, reason="DE example missing")
def test_de_table_detected_and_parsed():
    info = load_rnaseq_table(os.path.join(_TM, "Ctrl_vs_Treatment_DE.txt"))
    d = detect_input_mode(info)
    assert d["mode"] == "de_result"
    assert d["de_columns"]["logFC"] == "logFC"
    assert d["de_columns"]["p_value"] == "P.Value"
    assert d["de_columns"]["adj_p"] == "adj.P.Val"
    assert d["de_columns"]["gene_symbol"] == "geneSymbol"
    de = parse_de_table(info.dataframe)
    assert {"gene_id", "gene_symbol", "logFC", "p_value", "adj_p"} <= set(de.frame.columns)


@pytest.mark.skipif(not _HAS_DE, reason="DE example missing")
def test_de_classification_and_volcano_export(tmp_path):
    info = load_rnaseq_table(os.path.join(_TM, "Ctrl_vs_Treatment_DE.txt"))
    de = classify_de(parse_de_table(info.dataframe), lfc_cutoff=1.0, alpha=0.05, use_adjusted=False)
    # raw-p classification produces some hits on this dataset
    assert de.n_up + de.n_down >= 1
    assert set(de.frame["_class"].unique()) <= {"Up", "Down", "Not significant"}
    spec = volcano_spec_from_de(de, top_n_labels=10)
    out = render_to_files(spec, de.frame, str(tmp_path / "volcano"), formats=["svg", "pdf", "png"])
    assert len(out["files"]) == 3
    for f in out["files"]:
        assert os.path.exists(f) and os.path.getsize(f) > 200


@pytest.mark.skipif(not _HAS_DE, reason="DE example missing")
def test_volcano_subtitle_counts_match():
    info = load_rnaseq_table(os.path.join(_TM, "Ctrl_vs_Treatment_DE.txt"))
    de = classify_de(parse_de_table(info.dataframe), lfc_cutoff=1.0, alpha=0.05, use_adjusted=False)
    spec = volcano_spec_from_de(de)
    res = render(spec, de.frame)
    assert res.metadata["n_up"] == de.n_up
    assert res.metadata["n_down"] == de.n_down
    plt.close(res.figure)


# --- Mode B: normalized matrix -> heatmap ---------------------------------

@pytest.mark.skipif(not _HAS_VOOM, reason="voom example missing")
def test_voom_matrix_detected_and_split():
    info = load_rnaseq_table(os.path.join(_TM, "voom_norm_annot.txt"))
    d = detect_input_mode(info)
    assert d["mode"] == "expression_matrix"
    meta_cols, sample_cols = split_expression_matrix(info.dataframe)
    assert "geneSymbol" in meta_cols and "gene_id" in meta_cols
    assert len(sample_cols) == 12
    assert all(s.startswith("33450") for s in sample_cols)


@pytest.mark.skipif(not _HAS_VOOM, reason="voom example missing")
@pytest.mark.parametrize("selection,kw", [
    ("top_variable", {"n_genes": 40}),
    ("all", {"n_genes": 0}),
    ("selected", {"genes": ["Gnai3", "Manf", "Dnajb5"]}),
])
def test_heatmap_from_voom(selection, kw, tmp_path):
    info = load_rnaseq_table(os.path.join(_TM, "voom_norm_annot.txt"))
    meta_cols, sample_cols = split_expression_matrix(info.dataframe)
    em = build_expression_matrix(info.dataframe, metadata_columns=meta_cols, sample_columns=sample_cols)
    hm = heatmap_spec_from_expression(em, transform="zscore", selection=selection, **kw)
    out = render_to_files(hm["spec"], hm["dataframe"], str(tmp_path / f"hm_{selection}"),
                          formats=["svg", "png", "pdf"])
    assert len(out["files"]) == 3
    for f in out["files"]:
        assert os.path.exists(f) and os.path.getsize(f) > 200


def test_transforms():
    v = pd.DataFrame({"s1": [0.0, 10, 100], "s2": [0.0, 20, 200]})
    assert np.allclose(transform_matrix(v, "log2p1"), np.log2(v + 1))
    z = transform_matrix(v, "zscore")
    # z-score rows: each row mean ~0
    assert abs(float(z.mean(axis=1).abs().max())) < 1e-9
    cpm = transform_matrix(v, "cpm")
    assert np.allclose(cpm.sum(axis=0), 1e6)  # columns sum to a million


# --- config parsing --------------------------------------------------------

@pytest.mark.skipif(not _HAS_CFG, reason="config example missing")
def test_parse_config():
    cfg = parse_rnaseq_config(os.path.join(_TM, "config.json"))
    assert cfg["comparisons"] == [{"group1": "Ctrl", "group2": "Treatment"}]
    assert cfg["covariates"] == ["Age"]
    assert cfg["reference_group"] == "Ctrl"


@pytest.mark.skipif(not (_HAS_CFG and _HAS_META), reason="config/meta missing")
def test_config_validates_against_metadata():
    from make_my_figure_core.rnaseq.config import validate_config_against_metadata

    cfg = parse_rnaseq_config(os.path.join(_TM, "config.json"))
    meta = pd.read_csv(os.path.join(_TM, "meta_info_detail.csv"))
    problems = validate_config_against_metadata(cfg, meta, group_col="Group")
    assert problems == []  # Ctrl/Treatment and Age all present


# --- Mode C: validation + raw-count pipeline (R may be absent) -------------

def _synthetic_counts(n_genes=200, n_per=4, seed=0):
    rng = np.random.default_rng(seed)
    samples = [f"C{i}" for i in range(n_per)] + [f"T{i}" for i in range(n_per)]
    base = rng.integers(50, 500, size=n_genes)
    mat = np.vstack([rng.poisson(base) for _ in samples]).T
    # inject DE in first 20 genes for the Treatment group
    mat[:20, n_per:] = mat[:20, n_per:] * 4
    counts = pd.DataFrame(mat, columns=samples,
                          index=[f"ENSG{i:08d}" for i in range(n_genes)])
    meta = pd.DataFrame({"SampleID": samples,
                         "Group": ["Ctrl"] * n_per + ["Treatment"] * n_per,
                         "Age": rng.uniform(4, 6, len(samples)).round(1)})
    return counts, meta


def test_validate_counts_and_metadata():
    counts, meta = _synthetic_counts()
    rep = validate_counts(counts, list(counts.columns), min_samples=2)
    assert rep.ok and rep.summary["n_genes"] == 200 and rep.summary["n_samples"] == 8
    mrep = validate_metadata(meta, count_samples=list(counts.columns))
    assert mrep.ok
    assert mrep.summary["group_col"] == "Group"
    assert mrep.summary["matched_samples"] == 8


def test_validate_counts_flags_negative_and_missing():
    counts, _ = _synthetic_counts()
    counts.iloc[0, 0] = -5
    counts.iloc[1, 1] = np.nan
    rep = validate_counts(counts, list(counts.columns))
    assert not rep.ok  # negative -> error
    assert any("negative" in e.lower() for e in rep.errors)
    assert any("missing" in w.lower() for w in rep.warnings)


def test_validate_metadata_missing_group():
    meta = pd.DataFrame({"SampleID": ["A", "B"], "Age": [5, 6]})
    rep = validate_metadata(meta)
    assert not rep.ok and any("group" in e.lower() or "condition" in e.lower() for e in rep.errors)


def test_r_environment_report_is_graceful():
    env = check_r_environment()
    # Whether or not R is installed, this must not raise and must be informative.
    assert isinstance(env.ready, bool)
    assert env.message
    if not env.ready:
        assert "BiocManager" in env.message or "Rscript" in env.message


def test_run_de_pipeline_raises_clearly_without_r():
    env = check_r_environment()
    if env.ready:
        pytest.skip("R is installed; missing-R path not exercised here")
    counts, meta = _synthetic_counts()
    with pytest.raises(RDependencyError) as ei:
        run_de_pipeline(counts, meta, sample_id_col="SampleID", group_col="Group",
                        reference_group="Ctrl",
                        comparisons=[{"group1": "Treatment", "group2": "Ctrl"}])
    assert "edgeR" in str(ei.value) or "Rscript" in str(ei.value)


@pytest.mark.skipif(not check_r_environment().ready, reason="R + edgeR/limma not installed")
def test_run_de_pipeline_with_r():
    counts, meta = _synthetic_counts()
    res = run_de_pipeline(counts, meta, sample_id_col="SampleID", group_col="Group",
                          reference_group="Ctrl",
                          comparisons=[{"group1": "Treatment", "group2": "Ctrl"}],
                          covariates=["Age"])
    assert res["de_tables"]
    de_path = next(iter(res["de_tables"].values()))
    de = pd.read_csv(de_path, sep="\t", index_col=0)
    for col in ("logFC", "AveExpr", "t", "P.Value", "adj.P.Val"):
        assert col in de.columns
    assert res["rnaseq_spec"].de_method_id == "edger_limma_voom"
    assert "Group" in (res["method"].get("design_formula") or "")
