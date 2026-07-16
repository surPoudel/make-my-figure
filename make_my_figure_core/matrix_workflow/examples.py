"""Deterministic synthetic fixtures for the matrix workflow (no private data).

Builds a small normalized feature matrix (feature id + label + annotation columns
+ 12 samples: 6 Ctrl, 6 Treatment), matching sample metadata, a precomputed
differential table, and a feature list. Used by tests and the examples/ folder.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Tuple

import numpy as np
import pandas as pd

N_FEATURES = 300
CTRL = [f"SAMPLE_{i:02d}" for i in range(1, 7)]
TREAT = [f"SAMPLE_{i:02d}" for i in range(7, 13)]
SAMPLES = CTRL + TREAT
_BIOTYPES = ["protein_coding", "lncRNA", "miRNA", "pseudogene"]


def build_example_matrix(seed: int = 7) -> pd.DataFrame:
    """A log-normalized feature x sample matrix with annotation columns."""
    rng = np.random.default_rng(seed)
    base = rng.normal(6.0, 2.0, size=N_FEATURES)          # per-feature mean (log scale)
    mat = base[:, None] + rng.normal(0, 0.6, size=(N_FEATURES, len(SAMPLES)))
    # make the first 40 features differential (up in Treatment)
    effect = np.zeros(N_FEATURES)
    effect[:20] = rng.uniform(1.5, 3.0, 20)               # up in treatment
    effect[20:40] = -rng.uniform(1.5, 3.0, 20)            # down in treatment
    for j, s in enumerate(SAMPLES):
        if s in TREAT:
            mat[:, j] += effect
    data: Dict[str, object] = {
        "feature_id": [f"FEAT{i:05d}" for i in range(N_FEATURES)],
        "feature_name": [f"Feature{i}" for i in range(N_FEATURES)],
        "bioType": [_BIOTYPES[i % len(_BIOTYPES)] for i in range(N_FEATURES)],
        "annotationLevel": rng.integers(1, 4, N_FEATURES),   # numeric ANNOTATION (1/2/3)
    }
    for j, s in enumerate(SAMPLES):
        data[s] = mat[:, j]
    return pd.DataFrame(data)


def build_example_metadata() -> pd.DataFrame:
    return pd.DataFrame({
        "sample_id": SAMPLES,
        "group": ["Ctrl"] * len(CTRL) + ["Treatment"] * len(TREAT),
        "batch": [("A" if i % 2 == 0 else "B") for i in range(len(SAMPLES))],
    })


def build_precomputed_differential(seed: int = 11) -> pd.DataFrame:
    df = build_example_matrix(seed=7)
    from make_my_figure_core.matrix_workflow.matrix_spec import MatrixSpec
    from make_my_figure_core.matrix_workflow.metadata_spec import metadata_from_assignment
    from make_my_figure_core.matrix_workflow.differential_summary import (
        feature_differential_summary,
    )
    spec = MatrixSpec(feature_id_column="feature_id", feature_display_column="feature_name",
                      annotation_columns=["bioType", "annotationLevel"], value_columns=SAMPLES,
                      value_type="log_normalized", confirmed_by_user=True)
    meta = metadata_from_assignment({**{s: "Ctrl" for s in CTRL},
                                     **{s: "Treatment" for s in TREAT}})
    res = feature_differential_summary(df, spec, meta, group_a="Treatment", group_b="Ctrl",
                                       test="welch_t")
    out = res.table.rename(columns={"feature_label": "feature_name",
                                    "log2_fold_change": "logFC", "p_value": "P.Value",
                                    "adjusted_p_value": "adj.P.Val"})
    out["AveExpr"] = (df[SAMPLES].mean(axis=1)).values
    return out[["feature_id", "feature_name", "logFC", "AveExpr", "P.Value", "adj.P.Val"]]


def write_examples(out_dir: str) -> Dict[str, str]:
    """Write the fixtures + README + expected recommendations to ``out_dir``."""
    os.makedirs(out_dir, exist_ok=True)
    paths: Dict[str, str] = {}
    mat = build_example_matrix()
    meta = build_example_metadata()
    diff = build_precomputed_differential()

    paths["matrix"] = os.path.join(out_dir, "normalized_feature_matrix.tsv")
    mat.to_csv(paths["matrix"], sep="\t", index=False)
    paths["metadata"] = os.path.join(out_dir, "sample_metadata.csv")
    meta.to_csv(paths["metadata"], index=False)
    paths["differential"] = os.path.join(out_dir, "precomputed_differential_table.tsv")
    diff.to_csv(paths["differential"], sep="\t", index=False)
    paths["feature_list"] = os.path.join(out_dir, "feature_list.txt")
    with open(paths["feature_list"], "w", encoding="utf-8") as fh:
        fh.write("\n".join(f"FEAT{i:05d}" for i in range(10)) + "\n")

    from make_my_figure_core.matrix_workflow.matrix_spec import MatrixSpec
    from make_my_figure_core.matrix_workflow.metadata_spec import metadata_from_assignment
    from make_my_figure_core.matrix_workflow.recommendations import recommend_plots
    spec = MatrixSpec(feature_id_column="feature_id", feature_display_column="feature_name",
                      annotation_columns=["bioType", "annotationLevel"], value_columns=SAMPLES,
                      value_type="log_normalized", confirmed_by_user=True)
    grp = metadata_from_assignment({**{s: "Ctrl" for s in CTRL},
                                    **{s: "Treatment" for s in TREAT}})
    recs = recommend_plots(spec, grp, has_differential_summary=False, n_features=N_FEATURES)
    paths["expected"] = os.path.join(out_dir, "expected_recommendations.json")
    with open(paths["expected"], "w", encoding="utf-8") as fh:
        json.dump([r.to_dict() for r in recs], fh, indent=2)

    paths["readme"] = os.path.join(out_dir, "README.md")
    with open(paths["readme"], "w", encoding="utf-8") as fh:
        fh.write(_README)
    return paths


_README = """# Matrix workflow examples (synthetic)

Deterministic, synthetic fixtures — no private or sensitive data.

- `normalized_feature_matrix.tsv` — 300 features x (2 annotation + 12 sample) columns.
  Columns: `feature_id`, `feature_name`, `bioType`, `annotationLevel` (a numeric
  ANNOTATION coded 1/2/3, **not** a measurement), then 12 sample value columns
  (`SAMPLE_01`..`SAMPLE_12`). Values are log-normalized (may be negative).
- `sample_metadata.csv` — `sample_id`, `group` (6 Ctrl + 6 Treatment), `batch`.
- `precomputed_differential_table.tsv` — a supplied differential table
  (`feature_id`, `feature_name`, `logFC`, `AveExpr`, `P.Value`, `adj.P.Val`).
- `feature_list.txt` — feature ids to highlight.
- `expected_recommendations.json` — plots recommended for the confirmed mapping.

The app never guesses silently: you confirm the feature id / annotation / value
columns and the sample->group assignment before anything is plotted or tested.
This is a generic feature matrix (not an RNA-seq pipeline); statistics are generic
feature-level comparisons on normalized values, and precomputed tables are supported.
"""
