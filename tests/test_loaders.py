import os

import pytest

from make_my_figure_core.io.loaders import LoaderError, load_table


def test_load_csv(mock_dir):
    info = load_table(os.path.join(mock_dir, "barplot_error_raw.csv"))
    assert info.delimiter == ","
    assert info.n_rows > 0
    assert "measurement" in info.numeric_columns
    # 'replicate' looks like an id hint -> kept categorical (string)
    assert "replicate" in info.categorical_columns


def test_load_tsv_infers_tab(mock_dir):
    info = load_table(os.path.join(mock_dir, "line_timecourse.tsv"))
    assert info.delimiter == "\t"
    assert "signal" in info.numeric_columns


def test_heatmap_tsv_matrix(mock_dir):
    info = load_table(os.path.join(mock_dir, "heatmap_expression_matrix.tsv"))
    assert info.columns[0] == "gene"
    # all sample columns numeric
    assert len(info.numeric_columns) == len(info.columns) - 1


def test_sample_ids_preserved_as_strings(mock_dir):
    info = load_table(os.path.join(mock_dir, "scatter_regression.csv"))
    assert "sample_id" in info.categorical_columns
    assert info.dataframe["sample_id"].dtype == object or str(
        info.dataframe["sample_id"].dtype
    ).startswith("string")


def test_load_from_bytes_requires_or_infers_type(mock_dir):
    with open(os.path.join(mock_dir, "volcano_plot.csv"), "rb") as fh:
        data = fh.read()
    info = load_table(data, source_name="volcano_plot.csv")
    assert "log2_fold_change" in info.numeric_columns


def test_load_xlsx(repo_root):
    path = os.path.join(repo_root, "make_my_figure_mock_data.xlsx")
    info = load_table(path, sheet_name=0)
    assert info.n_rows > 0
    assert len(info.columns) > 0


def test_empty_bytes_raises():
    with pytest.raises(LoaderError):
        load_table(b"", source_name="empty.csv")


def test_missing_values_reported(tmp_path):
    p = tmp_path / "missing.csv"
    p.write_text("a,b\n1,\n2,5\n")
    info = load_table(str(p))
    assert info.missing_value_counts.get("b") == 1
    assert any("Missing values" in w for w in info.warnings)
