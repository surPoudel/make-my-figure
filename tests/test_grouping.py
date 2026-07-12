"""Tests for in-app group definition (no metadata file needed)."""

import numpy as np
import pandas as pd
import pytest

from make_my_figure_core.grouping import (
    add_group_column, guess_groups_from_names, melt_matrix_to_long,
    metadata_from_assignment, numeric_sample_columns, wide_grouped_matrix,
)


def _rsem_matrix():
    """A wide matrix with RNA-seq-style annotation columns before the samples."""
    return pd.DataFrame({
        "geneID": ["G1", "G2", "G3", "G4"],
        "geneSymbol": ["A", "B", "C", "D"],        # non-numeric annotation
        "bioType": ["pc", "pc", "lnc", "pc"],       # non-numeric annotation
        "annotationLevel": [1, 2, 1, 3],            # NUMERIC annotation (looks like a sample)
        "S1": [10.0, 5, 1, 3], "S2": [12, 6, 2, 4],
        "S3": [20, 15, 1, 8], "S4": [22, 16, 2, 9],
    })


def test_numeric_sample_columns_drops_text_annotation():
    df = _rsem_matrix()
    cols = numeric_sample_columns(df, "geneID")
    assert "geneSymbol" not in cols and "bioType" not in cols   # text annotation dropped
    assert {"S1", "S2", "S3", "S4"} <= set(cols)
    # annotationLevel is numeric so it can't be auto-excluded by dtype — it's left
    # for the user to leave unassigned (and is then dropped from the output).
    assert "annotationLevel" in cols


def test_wide_grouped_matrix_keeps_only_assigned_samples_and_builds_strip():
    df = _rsem_matrix()
    s2g = {"S1": "Ctrl", "S2": "Ctrl", "S3": "Trt", "S4": "Trt"}  # annotationLevel unassigned
    wide, ann = wide_grouped_matrix(
        df, feature_col="geneID", sample_columns=numeric_sample_columns(df, "geneID"),
        sample_to_group=s2g)
    # matrix shape preserved (features x assigned samples), annotation cols excluded
    assert list(wide.columns) == ["geneID", "S1", "S2", "S3", "S4"]
    assert "annotationLevel" not in wide.columns
    assert wide.shape == (4, 5)
    # group color strip spec
    assert ann[0]["values"] == s2g and set(ann[0]["values"].values()) == {"Ctrl", "Trt"}


def test_wide_grouped_matrix_renders_a_nonblank_heatmap():
    import matplotlib
    matplotlib.use("Agg")
    from make_my_figure_core.plots.registry import make_spec, render

    df = _rsem_matrix()
    s2g = {"S1": "Ctrl", "S2": "Ctrl", "S3": "Trt", "S4": "Trt"}
    wide, ann = wide_grouped_matrix(df, feature_col="geneID",
                                    sample_columns=numeric_sample_columns(df, "geneID"),
                                    sample_to_group=s2g)
    spec = make_spec("heatmap_clustered_matrix", "w.csv", "publication")
    spec["mapping"] = dict(spec["mapping"], row_id="geneID")
    spec["column_annotations"] = ann
    r = render(spec, wide)
    assert r.metadata["matrix_shape"] == [4, 4]   # 4 genes x 4 assigned samples (not 1)


def _matrix():
    return pd.DataFrame({
        "gene": ["G1", "G2", "G3"],
        "Ctrl_1": [10.0, 5, 1], "Ctrl_2": [12, 6, 2],
        "Trt_1": [20, 15, 1], "Trt_2": [22, 16, 2],
    })


def test_metadata_from_assignment():
    meta = metadata_from_assignment({"S1": "A", "S2": "B", "S3": ""})
    assert list(meta.columns) == ["SampleID", "Group"]
    assert set(meta["SampleID"]) == {"S1", "S2"}  # blank group dropped


def test_melt_matrix_to_long_by_group():
    df = _matrix()
    s2g = {"Ctrl_1": "Ctrl", "Ctrl_2": "Ctrl", "Trt_1": "Trt", "Trt_2": "Trt"}
    long = melt_matrix_to_long(df, sample_columns=["Ctrl_1", "Ctrl_2", "Trt_1", "Trt_2"],
                               sample_to_group=s2g, feature_col="gene", features=["G1"])
    assert set(long.columns) == {"feature", "sample", "group", "value"}
    assert set(long["group"]) == {"Ctrl", "Trt"}
    assert len(long) == 4  # 1 feature x 4 samples
    # values line up
    assert long.loc[long["sample"] == "Trt_1", "value"].iloc[0] == 20


def test_melt_requires_assignment():
    df = _matrix()
    with pytest.raises(ValueError):
        melt_matrix_to_long(df, sample_columns=["Ctrl_1"], sample_to_group={},
                            feature_col="gene")


def test_melt_feeds_barplot_grouped_stats():
    # The long frame should drive a grouped bar plot with stats end-to-end.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from make_my_figure_core.plots.registry import make_spec, render

    df = _matrix()
    s2g = {"Ctrl_1": "Ctrl", "Ctrl_2": "Ctrl", "Trt_1": "Trt", "Trt_2": "Trt"}
    long = melt_matrix_to_long(df, sample_columns=list(s2g), sample_to_group=s2g,
                               feature_col="gene", features=["G1", "G2"])
    spec = make_spec("boxplot_or_violin_with_points", "grp", "publication")
    spec["mapping"] = {"x": "group", "y": "value", "kind": "box"}
    spec["statistics"] = {"enabled": True, "test": "welch_t", "comparison_mode": "all_pairs"}
    res = render(spec, long)
    assert res.figure is not None
    assert res.stats_report is not None and len(res.stats_report.results) == 1
    plt.close(res.figure)


def test_add_group_column_from_existing():
    df = pd.DataFrame({"sample": ["s1", "s2", "s3"], "cond": ["wt", "wt", "ko"], "v": [1, 2, 3]})
    out = add_group_column(df, source_col="cond", value_to_group={"wt": "Control", "ko": "Knockout"},
                           new_col="group")
    assert list(out["group"]) == ["Control", "Control", "Knockout"]
    # unmapped -> default
    out2 = add_group_column(df, source_col="cond", value_to_group={"wt": "Control"},
                            new_col="group", default="Other")
    assert list(out2["group"]) == ["Control", "Control", "Other"]


def test_controller_group_from_matrix_roundtrip():
    from apps.desktop_app.controller import DesktopController

    ctrl = DesktopController()
    base = ctrl.loaded_from_dataframe(_matrix(), "matrix.csv")
    s2g = {"Ctrl_1": "Ctrl", "Ctrl_2": "Ctrl", "Trt_1": "Trt", "Trt_2": "Trt"}
    grouped = ctrl.group_from_matrix(base, sample_columns=list(s2g), sample_to_group=s2g,
                                     feature_col="gene", features=["G1"])
    df = grouped.info.dataframe
    assert set(df.columns) == {"feature", "sample", "group", "value"}
    assert "group" in grouped.info.categorical_columns
    assert "value" in grouped.info.numeric_columns
    assert grouped.table_name.endswith("(grouped)")


def test_controller_add_group_column():
    from apps.desktop_app.controller import DesktopController

    ctrl = DesktopController()
    df = pd.DataFrame({"sample": ["s1", "s2", "s3"], "cond": ["wt", "wt", "ko"], "v": [1, 2, 3]})
    base = ctrl.loaded_from_dataframe(df, "obs.csv")
    out = ctrl.add_group_column(base, source_col="cond",
                                value_to_group={"wt": "Control", "ko": "Knockout"})
    assert list(out.info.dataframe["group"]) == ["Control", "Control", "Knockout"]


def test_guess_groups_from_names():
    g = guess_groups_from_names(["Ctrl_1", "Ctrl_2", "Trt_1", "Trt_2"])
    assert g["Ctrl_1"] == g["Ctrl_2"] and g["Trt_1"] == g["Trt_2"]
    assert g["Ctrl_1"] != g["Trt_1"]
    # names that collapse to one token -> single group
    g2 = guess_groups_from_names(["x1", "x2"])
    assert set(g2.values()) == {"Group1"}
