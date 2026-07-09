"""End-to-end QC: the DE pipeline reproduces the user's reference files.

Runs only when R + edgeR/limma are available (set MAKE_MY_FIGURE_RSCRIPT or install
via the app). Confirms the voom-normalized matrix reproduces voom_norm_annot.txt to
machine precision and that logFC is essentially identical to Ctrl_vs_Treatment_DE.txt
(p-values are limma-version-dependent, so we assert strong rank concordance, not
bit-identity). Skips cleanly when R/inputs are absent.
"""

import os

import numpy as np
import pandas as pd
import pytest

from make_my_figure_core.rnaseq import check_r_environment, load_rnaseq_table, run_de_pipeline
from make_my_figure_core.rnaseq.detect import split_expression_matrix

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_TM = os.path.join(_ROOT, "test_matrix")
_COUNTS = os.path.join(_TM, "GREEN-853662-STRANDED_RSEM_gene_count.2025-07-18_19-34-07.txt")
_REF_DE = os.path.join(_TM, "Ctrl_vs_Treatment_DE.txt")
_REF_VOOM = os.path.join(_TM, "voom_norm_annot.txt")
_META = os.path.join(_TM, "meta_info_detail.csv")

_have_inputs = all(os.path.exists(p) for p in (_COUNTS, _REF_DE, _REF_VOOM, _META))
_have_r = check_r_environment(method="edger_limma_voom").ready


@pytest.mark.skipif(not (_have_inputs and _have_r),
                    reason="reference inputs or R+edgeR/limma unavailable")
def test_pipeline_reproduces_reference(tmp_path):
    info = load_rnaseq_table(_COUNTS)
    df = info.dataframe
    gid = df.columns[0]
    meta_cols, sample_cols = split_expression_matrix(df)
    counts = df.set_index(gid)[sample_cols]
    annot_cols = [c for c in meta_cols if c != gid]
    annotation = df.set_index(gid)[annot_cols]
    metadata = pd.read_csv(_META)

    res = run_de_pipeline(counts, metadata, sample_id_col="SampleID", group_col="Group",
                          reference_group="Ctrl",
                          comparisons=[{"group1": "Ctrl", "group2": "Treatment"}],
                          annotation=annotation, min_cpm=1.0, method="edger_limma_voom",
                          output_dir=str(tmp_path / "de"))
    mine = pd.read_csv(res["de_tables"]["Ctrl_vs_Treatment"], sep="\t", index_col=0)
    ref = pd.read_csv(_REF_DE, sep="\t", index_col=0)
    common = mine.index.intersection(ref.index)
    # identical gene set (RSEM fractional counts kept, ERCC removed)
    assert len(common) == len(ref.index) == len(mine.index)

    m, r = mine.loc[common], ref.loc[common]
    # logFC essentially identical (median abs diff tiny)
    dlfc = (m["logFC"].astype(float) - r["logFC"].astype(float)).abs()
    assert dlfc.median() < 0.01
    assert (np.sign(m["logFC"].astype(float)) == np.sign(r["logFC"].astype(float))).mean() > 0.98
    # p-value ranking strongly concordant (version-robust)
    from scipy.stats import spearmanr
    assert spearmanr(m["P.Value"].astype(float), r["P.Value"].astype(float)).statistic > 0.95

    # voom-normalized matrix reproduced to machine precision
    vm = pd.read_csv(res["voom_file"], sep="\t", index_col=0)
    vr = pd.read_csv(_REF_VOOM, sep="\t", index_col=0)
    sc = [c for c in vm.columns if c in vr.columns and c.startswith("33450")]
    cg = vm.index.intersection(vr.index)
    maxdiff = (vm.loc[cg, sc].astype(float) - vr.loc[cg, sc].astype(float)).abs().max().max()
    assert maxdiff < 1e-6, f"voom matrix differs by {maxdiff}"
    assert res["rnaseq_spec"].de_method_id == "edger_limma_voom"
