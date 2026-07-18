"""Generate the synthetic multi-sheet Excel fixture used by tests and demos.

The workbook is small, fully synthetic, and license-safe (no real data). It
exercises every worksheet shape the app must handle: documentation/notes, a
column legend, two differential-result tables with *different* header
conventions, a numeric matrix, sample metadata, an empty sheet, a sheet whose
headers start below the first row, a hidden sheet, and a Unicode-named sheet.

Run:
    python scripts/generate_multi_sheet_fixture.py

Output:
    examples/multi_sheet_workbook/synthetic_multisheet.xlsx
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                       "examples", "multi_sheet_workbook")
OUT_PATH = os.path.join(OUT_DIR, "synthetic_multisheet.xlsx")

# Deterministic synthetic values (seeded; no randomness at import elsewhere).
_RNG = np.random.default_rng(20260717)


def _de_table_deseq(n: int = 40) -> pd.DataFrame:
    genes = [f"ENSG{100000 + i:06d}" for i in range(n)]
    lfc = _RNG.normal(0, 1.5, n)
    p = np.clip(np.abs(_RNG.normal(0, 0.1, n)), 1e-6, 1.0)
    return pd.DataFrame({
        "feature_id": genes,
        "log2FoldChange": np.round(lfc, 4),
        "pvalue": np.round(p, 6),
        "padj": np.round(np.clip(p * 1.5, 0, 1), 6),
        "baseMean": np.round(np.abs(_RNG.normal(500, 200, n)), 2),
    })


def _de_table_limma(n: int = 35) -> pd.DataFrame:
    genes = [f"Gene{i:03d}" for i in range(n)]
    lfc = _RNG.normal(0, 1.2, n)
    p = np.clip(np.abs(_RNG.normal(0, 0.1, n)), 1e-6, 1.0)
    return pd.DataFrame({
        "gene": genes,
        "logFC": np.round(lfc, 4),
        "P.Value": np.round(p, 6),
        "adj.P.Val": np.round(np.clip(p * 1.3, 0, 1), 6),
        "AveExpr": np.round(_RNG.normal(6, 1.5, n), 3),
    })


def _matrix(n_features: int = 30, n_samples: int = 8) -> pd.DataFrame:
    feats = [f"PROT_{i:03d}" for i in range(n_features)]
    data = {"feature_id": feats,
            "annotation": [f"pathway_{i % 4}" for i in range(n_features)]}
    for s in range(n_samples):
        grp = "ctrl" if s < n_samples // 2 else "treat"
        data[f"{grp}_{s + 1}"] = np.round(_RNG.normal(10, 2, n_features), 3)
    return pd.DataFrame(data)


def _metadata(n_samples: int = 8) -> pd.DataFrame:
    ids, groups = [], []
    for s in range(n_samples):
        grp = "ctrl" if s < n_samples // 2 else "treat"
        ids.append(f"{grp}_{s + 1}")
        groups.append(grp)
    return pd.DataFrame({"sample_id": ids, "group": groups,
                         "batch": [(s % 2) + 1 for s in range(n_samples)]})


def build_workbook(path: str = OUT_PATH) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)

    readme = pd.DataFrame({
        "Make My Figure — synthetic example workbook": [
            "This workbook is fully synthetic test data (no real samples).",
            "Comparison_A and Comparison_B are precomputed differential results.",
            "Matrix is a numeric feature x sample matrix.",
            "Metadata maps samples to groups.",
            "EmptySheet, DE_sheet_legend, and OddHeaders test edge cases.",
        ]
    })
    legend = pd.DataFrame({
        "column": ["feature_id", "log2FoldChange", "pvalue", "padj", "baseMean"],
        "definition": [
            "gene/feature identifier",
            "log2 fold-change (effect size)",
            "raw p-value",
            "Benjamini-Hochberg adjusted p-value / FDR",
            "mean normalized abundance",
        ],
    })
    # OddHeaders: two junk rows, then the real header on row 3 (0-indexed row 2).
    odd = pd.DataFrame([
        ["Experiment notes: ignore first rows", None, None],
        [None, None, None],
        ["sample", "value", "group"],
        ["s1", 1.1, "a"],
        ["s2", 2.2, "b"],
        ["s3", 3.3, "a"],
    ])

    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        readme.to_excel(xw, index=False, sheet_name="README")
        legend.to_excel(xw, index=False, sheet_name="DE_sheet_legend")
        _de_table_deseq().to_excel(xw, index=False, sheet_name="Comparison_A")
        _de_table_limma().to_excel(xw, index=False, sheet_name="Comparison_B")
        _matrix().to_excel(xw, index=False, sheet_name="Matrix")
        _metadata().to_excel(xw, index=False, sheet_name="Metadata")
        # Truly empty sheet.
        pd.DataFrame().to_excel(xw, index=False, sheet_name="EmptySheet", header=False)
        odd.to_excel(xw, index=False, header=False, sheet_name="OddHeaders")
        # A Unicode-named sheet with a differential table (tests name handling).
        _de_table_limma(10).to_excel(xw, index=False, sheet_name="Résumé_βγ")

        # Mark one sheet hidden via openpyxl so hidden-state handling is exercised.
        wbk = xw.book
        if "DE_sheet_legend" in wbk.sheetnames:
            wbk["DE_sheet_legend"].sheet_state = "hidden"

    return path


if __name__ == "__main__":
    out = build_workbook()
    print(f"Wrote {out}")
