"""Regression: an ordinary experimental table must not be called an expression matrix.

The bee workbook (4 rows; treatment, social setting, time, colony; body size and
quantities) was profiled as ``expression_like_matrix`` - 7 of 11 columns numeric
- and the worksheet as "matrix", so the first suggestions were a clustered
heatmap and PCA of bee body sizes. Feature matrices must keep their
classification: an annotated count matrix and the bundled matrix examples.
"""
import numpy as np
import pandas as pd
import pytest

from make_my_figure_core import examples
from make_my_figure_core.io.workbook import classify_worksheet
from make_my_figure_core.recommendations import recommend_for_table

BEE = "tests/fixtures/bee_demo_workbook.xlsx"
SIM = "tutorial/general_tabular_data/data/simulated_bee_factorial.csv"
MATRIX_SCHEMAS = {"expression_like_matrix", "numeric_matrix", "matrix_plus_metadata"}


@pytest.mark.parametrize("path", [BEE, SIM])
def test_experimental_tables_are_generic_tables(path):
    df = pd.read_excel(path) if path.endswith(".xlsx") else pd.read_csv(path)
    rec = recommend_for_table(df, table_name=path)
    assert rec.schema not in MATRIX_SCHEMAS, rec.schema
    top = [r.plot_type for r in rec.recommendations][:3]
    assert "heatmap_clustered_matrix" not in top and "pca_scatter_from_matrix" not in top, top
    assert classify_worksheet(df)[0] == "generic"


def test_an_annotated_count_matrix_stays_a_matrix():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"gene_id": [f"ENSG{i:08d}" for i in range(200)],
                       "biotype": rng.choice(["protein_coding", "lncRNA", "miRNA"], 200)})
    for s in range(6):
        df[f"S{s + 1}"] = rng.negative_binomial(5, 0.01, 200)
    rec = recommend_for_table(df, table_name="counts.csv")
    assert rec.schema in MATRIX_SCHEMAS, rec.schema
    assert classify_worksheet(df)[0] == "matrix"


@pytest.mark.parametrize("plot_type", ["heatmap_clustered_matrix", "pca_scatter_from_matrix",
                                       "hierarchical_clustering"])
def test_bundled_matrix_examples_keep_their_classification(plot_type):
    table, _aux, _spec = examples.load_example(plot_type)
    rec = recommend_for_table(table.dataframe, table_name=plot_type)
    assert rec.schema in MATRIX_SCHEMAS | {"correlation_matrix"}, (plot_type, rec.schema)


@pytest.mark.parametrize("n_samples,lam", [(6, 3.0), (6, 0.8), (3, 3.0), (3, 50.0)])
def test_low_count_and_few_sample_annotated_matrices_stay_matrices(n_samples, lam):
    # Review finding: 500 genes x 6 Poisson(3) samples + biotype was called a
    # generic table (every low-count column looked "coarse"), and so was any
    # matrix with <= 3 sample columns beside a repeating annotation.
    rng = np.random.default_rng(3)
    df = pd.DataFrame({"gene_id": [f"G{i:05d}" for i in range(500)],
                       "biotype": rng.choice(["protein_coding", "lncRNA", "miRNA"], 500)})
    for s in range(n_samples):
        df[f"S{s + 1}"] = rng.poisson(lam, 500)
    from make_my_figure_core.recommendations.data_profiler import profile_table

    assert profile_table(df, "counts").is_matrix
    assert classify_worksheet(df)[0] == "matrix"


def test_three_unrelated_measurements_with_factors_are_a_table():
    rng = np.random.default_rng(4)
    df = pd.DataFrame({"plant_id": [f"P{i}" for i in range(40)], "treatment": np.repeat(["c", "n"], 20),
                       "height_cm": rng.normal(50, 5, 40), "dry_mass_g": rng.normal(12, 2, 40),
                       "yield_kg": rng.normal(2, 0.3, 40)})
    assert recommend_for_table(df, table_name="plants").schema not in MATRIX_SCHEMAS
