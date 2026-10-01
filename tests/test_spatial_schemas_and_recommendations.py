"""Spatial schema detection and recommendations.

The risk this file guards is not that spatial tables go undetected — it is that
ordinary tables get *mis*detected. ``x`` and ``y`` are the two most common
headers in any scatter-plot table, so most of these tests are negative controls.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from make_my_figure_core.recommendations.data_profiler import profile_table
from make_my_figure_core.recommendations.plot_recommender import recommend_plots
from make_my_figure_core.recommendations.schema_detector import detect_schema


def _schema(df: pd.DataFrame) -> str:
    return detect_schema(profile_table(df, "t"), df)


def _recs(df: pd.DataFrame):
    prof = profile_table(df, "t")
    return recommend_plots(prof, detect_schema(prof, df), df, "t")


# --- negative controls: ordinary tables must not become spatial --------------

def test_a_plain_xy_scatter_is_not_spatial():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"x": rng.normal(size=60), "y": rng.normal(size=60)})
    assert not _schema(df).startswith("spatial")


def test_xy_with_only_a_group_column_is_not_spatial():
    """A dose-response or grouped scatter must not be read as tissue."""
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"x": rng.normal(size=60), "y": rng.normal(size=60),
                       "group": rng.choice(["ctrl", "drug"], 60)})
    assert not _schema(df).startswith("spatial")


def test_a_differential_table_is_unaffected():
    rng = np.random.default_rng(2)
    df = pd.DataFrame({"log2_fold_change": rng.normal(size=40),
                       "adjusted_p_value": rng.random(40)})
    assert _schema(df) == "precomputed_differential"


# --- positive detection ------------------------------------------------------

def test_bare_xy_becomes_spatial_when_a_cell_type_corroborates_it():
    rng = np.random.default_rng(3)
    df = pd.DataFrame({"x": rng.uniform(0, 100, 60), "y": rng.uniform(0, 100, 60),
                       "cell_type": rng.choice(["Tumor", "Stroma"], 60)})
    assert _schema(df) == "spatial_cells"


@pytest.mark.parametrize("xcol,ycol", [
    ("x_centroid", "y_centroid"),
    ("pxl_col_in_fullres", "pxl_row_in_fullres"),
    ("imagecol", "imagerow"),
])
def test_platform_coordinate_names_are_spatial_without_corroboration(xcol, ycol):
    """These names mean a tissue coordinate and nothing else."""
    rng = np.random.default_rng(4)
    df = pd.DataFrame({xcol: rng.uniform(0, 100, 40), ycol: rng.uniform(0, 100, 40),
                       "measurement": rng.normal(size=40)})
    assert _schema(df).startswith("spatial")


def test_transcript_table_is_detected():
    rng = np.random.default_rng(5)
    df = pd.DataFrame({"transcript_id": [f"t{i}" for i in range(50)],
                       "x": rng.uniform(0, 100, 50), "y": rng.uniform(0, 100, 50),
                       "gene": rng.choice(["EPCAM", "CD8A"], 50),
                       "qv": rng.uniform(20, 40, 50)})
    assert _schema(df) == "spatial_transcripts"


def test_roi_polygon_table_is_detected():
    rows = [{"roi_id": r, "vertex_order": i, "x": float(i), "y": float(i)}
            for r in ("A", "B") for i in range(6)]
    assert _schema(pd.DataFrame(rows)) == "spatial_roi_polygons"


def test_composition_is_told_apart_from_a_per_cell_table():
    """Both have spot + cell_type; only one repeats the spot across categories."""
    comp = pd.DataFrame([{"spot_id": f"s{s}", "x": s, "y": s, "cell_type": ct,
                          "cell_count": 3 + s}
                         for s in range(8) for ct in ("Tumor", "Stroma", "T cell")])
    assert _schema(comp) == "spatial_composition"

    per_cell = pd.DataFrame([{"spot_id": f"s{i}", "x": i % 10, "y": i // 10,
                              "cell_type": "Tumor" if i % 2 else "Stroma"}
                             for i in range(40)])
    assert _schema(per_cell) == "spatial_cells"


# --- recommendations ---------------------------------------------------------

def test_cells_recommend_a_categorical_map_first():
    rng = np.random.default_rng(6)
    df = pd.DataFrame({"x": rng.uniform(0, 100, 80), "y": rng.uniform(0, 100, 80),
                       "cell_type": rng.choice(["Tumor", "Stroma", "T cell"], 80),
                       "CD8": rng.gamma(2, 1, 80)})
    recs = _recs(df)
    assert recs[0].plot_type == "spatial_categorical_map"
    assert recs[0].required_mappings["category"] == "cell_type"


def test_an_identifier_is_never_suggested_as_a_measurement():
    """Colouring tissue by 'patient' is meaningless even though it is numeric."""
    rng = np.random.default_rng(7)
    df = pd.DataFrame({"x": rng.uniform(0, 100, 80), "y": rng.uniform(0, 100, 80),
                       "cell_type": rng.choice(["Tumor", "Stroma"], 80),
                       "patient": rng.integers(1, 4, 80),
                       "CD8": rng.gamma(2, 1, 80)})
    values = [r.required_mappings.get("value") for r in _recs(df)
              if r.plot_type == "spatial_feature_map"]
    assert values, "expected a feature-map recommendation"
    assert "patient" not in values
    assert "CD8" in values


def test_neighbourhood_analysis_is_advisory_and_suggests_no_parameters():
    """The number of neighbourhoods and the graph are the user's decisions."""
    rng = np.random.default_rng(8)
    df = pd.DataFrame({"x": rng.uniform(0, 100, 80), "y": rng.uniform(0, 100, 80),
                       "cell_type": rng.choice(["Tumor", "Stroma"], 80),
                       "image": rng.choice(["img1", "img2"], 80)})
    rec = next(r for r in _recs(df) if r.plot_type == "cellular_neighborhood_analysis")
    assert rec.plot_spec_draft is None          # advisory, not directly renderable
    assert rec.requires_confirmation
    blob = (rec.why + " " + " ".join(rec.warnings)).lower()
    for token in ("k=", "radius=", "n_neighborhoods=", "use k of", "we suggest"):
        assert token not in blob, f"recommendation should not propose {token!r}"


def test_missing_sample_column_is_called_out_for_neighbourhood_analysis():
    rng = np.random.default_rng(9)
    df = pd.DataFrame({"x": rng.uniform(0, 100, 60), "y": rng.uniform(0, 100, 60),
                       "cell_type": rng.choice(["Tumor", "Stroma"], 60)})
    rec = next(r for r in _recs(df) if r.plot_type == "cellular_neighborhood_analysis")
    assert "single tissue" in rec.why or "image/sample" in rec.why


def test_coordinate_units_are_never_inferred():
    rng = np.random.default_rng(10)
    df = pd.DataFrame({"x": rng.uniform(0, 100, 60), "y": rng.uniform(0, 100, 60),
                       "cell_type": rng.choice(["Tumor", "Stroma"], 60)})
    rec = next(r for r in _recs(df) if r.plot_type == "spatial_categorical_map")
    assert any("unit" in w.lower() for w in rec.warnings)
