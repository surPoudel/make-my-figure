"""Build small, committed RNA-seq example artifacts under examples/rnaseq/.

Derives compact examples from the files in ``test_matrix/`` (or synthesizes
them if absent): a trimmed DE result table, a trimmed normalized matrix, a
synthetic raw-count matrix + metadata, and the PlotSpec/RnaSeqSpec sidecars.
Everything here is synthetic or derived and safe to commit; large source files
in test_matrix/ are not.

Usage:  python scripts/generate_rnaseq_examples.py
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from make_my_figure_core.rnaseq import (  # noqa: E402
    classify_de, heatmap_spec_from_expression, load_rnaseq_table, parse_de_table,
    volcano_spec_from_de, build_expression_matrix,
)
from make_my_figure_core.rnaseq.detect import split_expression_matrix  # noqa: E402
from make_my_figure_core.rnaseq.spec import RnaSeqSpec  # noqa: E402

TM = os.path.join(_ROOT, "test_matrix")
OUT = os.path.join(_ROOT, "examples", "rnaseq")


def _write_json(obj, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2)


def de_example(folder):
    src = os.path.join(TM, "Ctrl_vs_Treatment_DE.txt")
    if os.path.exists(src):
        info = load_rnaseq_table(src)
        df = info.dataframe
        # keep a compact, representative subset (top + random) to stay small
        top = df.reindex(df["P.Value"].astype(float).sort_values().index).head(300)
        rest = df.sample(n=min(300, len(df)), random_state=0)
        sub = pd.concat([top, rest]).iloc[~pd.concat([top, rest]).index.duplicated()]
    else:
        rng = np.random.default_rng(0)
        n = 500
        sub = pd.DataFrame({
            "geneSymbol": [f"Gene{i}" for i in range(n)],
            "logFC": rng.normal(0, 1.2, n), "AveExpr": rng.normal(5, 2, n),
            "t": rng.normal(0, 3, n), "P.Value": rng.uniform(0, 1, n),
        }, index=[f"ENSG{i:08d}" for i in range(n)])
        sub["adj.P.Val"] = np.clip(sub["P.Value"] * 5, 0, 1)
    sub.to_csv(os.path.join(folder, "de_result.tsv"), sep="\t", index_label="gene_id")
    de = classify_de(parse_de_table(load_rnaseq_table(
        os.path.join(folder, "de_result.tsv")).dataframe),
        lfc_cutoff=1.0, alpha=0.05, use_adjusted=False)
    spec = volcano_spec_from_de(de, input_table="de_result.tsv")
    _write_json(spec, os.path.join(folder, "volcano.plotspec.json"))
    _write_json(RnaSeqSpec(input_mode="de_result", volcano_thresholds=de.thresholds,
                           de_columns_used=de.mapping).to_dict(),
                os.path.join(folder, "volcano.rnaseq_spec.json"))
    return f"DE example: {sub.shape[0]} genes (up={de.n_up}, down={de.n_down})"


def matrix_example(folder):
    src = os.path.join(TM, "voom_norm_annot.txt")
    if os.path.exists(src):
        info = load_rnaseq_table(src)
        mc, sc = split_expression_matrix(info.dataframe)
        em = build_expression_matrix(info.dataframe, metadata_columns=mc, sample_columns=sc)
        # keep the 200 most variable genes to stay small
        var = em.values.var(axis=1)
        rows = var.sort_values(ascending=False).head(200).index
        sub = info.dataframe.loc[rows]
    else:
        rng = np.random.default_rng(1)
        samples = [f"S{i}" for i in range(8)]
        n = 200
        mat = rng.normal(5, 2, size=(n, len(samples)))
        sub = pd.DataFrame(mat, columns=samples, index=[f"ENSG{i:08d}" for i in range(n)])
        sub.insert(0, "geneSymbol", [f"Gene{i}" for i in range(n)])
    sub.to_csv(os.path.join(folder, "normalized_matrix.tsv"), sep="\t", index=False)
    info2 = load_rnaseq_table(os.path.join(folder, "normalized_matrix.tsv"))
    mc, sc = split_expression_matrix(info2.dataframe)
    em = build_expression_matrix(info2.dataframe, metadata_columns=mc, sample_columns=sc)
    hm = heatmap_spec_from_expression(em, transform="zscore", selection="top_variable", n_genes=40)
    _write_json(hm["spec"], os.path.join(folder, "heatmap.plotspec.json"))
    _write_json(RnaSeqSpec(input_mode="expression_matrix", heatmap_transform="zscore",
                           gene_selection_method="top_variable").to_dict(),
                os.path.join(folder, "heatmap.rnaseq_spec.json"))
    return f"Matrix example: {sub.shape[0]} genes x {len(sc)} samples"


def rawcount_example(folder):
    rng = np.random.default_rng(42)
    n_genes, n_per = 400, 4
    samples = [f"C{i}" for i in range(n_per)] + [f"T{i}" for i in range(n_per)]
    base = rng.integers(50, 800, size=n_genes)
    mat = np.vstack([rng.poisson(base) for _ in samples]).T
    mat[:40, n_per:] = (mat[:40, n_per:] * rng.uniform(2, 6, (40, n_per))).astype(int)  # DE up
    counts = pd.DataFrame(mat, columns=samples, index=[f"ENSG{i:08d}" for i in range(n_genes)])
    counts.index.name = "gene_id"
    counts.to_csv(os.path.join(folder, "raw_counts.tsv"), sep="\t")
    meta = pd.DataFrame({"SampleID": samples,
                         "Group": ["Ctrl"] * n_per + ["Treatment"] * n_per,
                         "Sex": rng.choice(["M", "F"], len(samples)),
                         "Age": rng.uniform(4, 6, len(samples)).round(1)})
    meta.to_csv(os.path.join(folder, "metadata.csv"), index=False)
    _write_json({"comparisons": [{"group1": "Treatment", "group2": "Ctrl"}],
                 "covariates": ["Age"], "reference_group": "Ctrl"},
                os.path.join(folder, "config.json"))
    return f"Raw-count example: {n_genes} genes x {len(samples)} samples (needs R to run DE)"


def main() -> int:
    lines = []
    for name, fn in [("de_result", de_example), ("normalized_matrix", matrix_example),
                     ("raw_counts", rawcount_example)]:
        folder = os.path.join(OUT, name)
        os.makedirs(folder, exist_ok=True)
        lines.append(fn(folder))
        with open(os.path.join(folder, "README.md"), "w", encoding="utf-8") as fh:
            fh.write(f"# RNA-seq example: {name}\n\n{lines[-1]}\n\n"
                     "Synthetic/derived data, safe to commit. See docs/RNASEQ_WORKFLOW.md.\n")
        print("  " + lines[-1])
    _write_json({"examples": ["de_result", "normalized_matrix", "raw_counts"],
                 "note": "Derived from test_matrix/ or synthesized; synthetic and safe to commit."},
                os.path.join(OUT, "manifest.json"))
    print(f"Wrote RNA-seq examples to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
