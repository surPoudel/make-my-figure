"""DE-result column auto-detection (for volcano-mapping confirmation)."""

import pandas as pd

from make_my_figure_core.de_detect import detect_de_columns


def test_detect_edger_limma_headers():
    df = pd.DataFrame(columns=["geneSymbol", "logFC", "AveExpr", "t", "P.Value", "adj.P.Val"])
    det = detect_de_columns(df)
    assert det["logFC"] == "logFC"
    assert det["p_value"] == "P.Value"
    assert det["adj_p"] == "adj.P.Val"
    assert det["gene_symbol"] == "geneSymbol"
    assert det["statistic"] == "t"


def test_detect_deseq2_headers():
    df = pd.DataFrame(columns=["gene_name", "baseMean", "log2FoldChange", "stat", "pvalue", "padj"])
    det = detect_de_columns(df)
    assert det["logFC"] == "log2FoldChange"
    assert det["p_value"] == "pvalue"
    assert det["adj_p"] == "padj"
    assert det["ave_expr"] == "baseMean"


def test_unresolved_roles_are_none_not_fabricated():
    df = pd.DataFrame(columns=["foo", "bar"])
    det = detect_de_columns(df)
    assert det["logFC"] is None and det["p_value"] is None
    # every value is either an existing column or None
    assert all(v is None or v in df.columns for v in det.values())
