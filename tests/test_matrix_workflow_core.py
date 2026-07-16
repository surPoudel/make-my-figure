"""Matrix-workflow core: suggestion, confirmation gate, validation, round-trips.

No silent guessing: annotation columns are never treated as values, and the user
must confirm the mapping/groups before validation passes or statistics run.
"""

import json

import numpy as np
import pandas as pd
import pytest

import make_my_figure_core.matrix_workflow as mw
from make_my_figure_core.matrix_workflow.examples import (
    CTRL,
    SAMPLES,
    TREAT,
    build_example_matrix,
    build_example_metadata,
)


@pytest.fixture
def matrix():
    return build_example_matrix()


@pytest.fixture
def confirmed_spec():
    return mw.MatrixSpec(feature_id_column="feature_id", feature_display_column="feature_name",
                         annotation_columns=["bioType", "annotationLevel"],
                         value_columns=list(SAMPLES), value_type="log_normalized",
                         confirmed_by_user=True)


@pytest.fixture
def groups():
    return mw.metadata_from_assignment({**{c: "Ctrl" for c in CTRL},
                                        **{t: "Treatment" for t in TREAT}})


def test_suggestion_separates_value_and_annotation(matrix):
    spec = mw.suggest_matrix_spec(matrix)
    assert "annotationLevel" in spec.annotation_columns
    assert "annotationLevel" not in spec.value_columns
    assert set(SAMPLES).issubset(set(spec.value_columns))
    assert spec.confirmed_by_user is False           # suggestions are never confirmed
    assert spec.value_type == "unknown_user_confirmed"  # scale never inferred


def test_suggestion_on_generic_names_uses_only_numeric_measurements():
    df = pd.DataFrame({"id": ["a", "b", "c"], "flag": [1, 2, 1],
                       "x1": [1.5, 2.5, 3.5], "x2": [2.1, 0.4, 5.9]})
    spec = mw.suggest_matrix_spec(df)
    assert spec.feature_id_column == "id"
    assert "flag" in spec.annotation_columns and "flag" not in spec.value_columns
    assert set(spec.value_columns) == {"x1", "x2"}


def test_matrix_spec_json_round_trip(confirmed_spec):
    d = json.loads(json.dumps(confirmed_spec.to_dict()))
    back = mw.MatrixSpec.from_dict(d)
    assert back.value_columns == confirmed_spec.value_columns
    assert back.value_type == "log_normalized"
    assert back.confirmed_by_user is True


def test_metadata_spec_json_round_trip(groups):
    back = mw.SampleMetadataSpec.from_dict(json.loads(json.dumps(groups.to_dict())))
    assert back.groups() == ["Ctrl", "Treatment"]
    assert back.group_sizes() == {"Ctrl": 6, "Treatment": 6}


def test_validation_passes_for_confirmed_mapping(matrix, confirmed_spec, groups):
    r = mw.validate_matrix(matrix, confirmed_spec, groups)
    assert r.ok, r.errors
    assert r.summary["n_samples"] == 12
    assert r.summary["n_groups"] == 2
    assert r.summary["group_sizes"] == {"Ctrl": 6, "Treatment": 6}


def test_validation_fails_when_unconfirmed(matrix, confirmed_spec):
    spec = mw.MatrixSpec.from_dict(confirmed_spec.to_dict())
    spec.confirmed_by_user = False
    r = mw.validate_matrix(matrix, spec)
    assert not r.ok
    assert any("not confirmed" in e.lower() for e in r.errors)


def test_validation_rejects_annotation_as_value(matrix, confirmed_spec):
    spec = mw.MatrixSpec.from_dict(confirmed_spec.to_dict())
    spec.value_columns = spec.value_columns + ["annotationLevel"]
    spec.annotation_columns = ["annotationLevel"]
    r = mw.validate_matrix(matrix, spec)
    assert not r.ok
    assert any("both annotation and value" in e for e in r.errors)


def test_statistics_gate_requires_two_confirmed_groups(confirmed_spec):
    one = mw.metadata_from_assignment({c: "Ctrl" for c in CTRL})
    r = mw.require_for_statistics(confirmed_spec, one)
    assert not r.ok
    unconfirmed = mw.SampleMetadataSpec(sample_to_group={"a": "X"}, confirmed_by_user=False)
    assert not mw.require_for_statistics(confirmed_spec, unconfirmed).ok


def test_metadata_sample_match_reports_mismatches():
    meta = mw.metadata_from_assignment({"SAMPLE_01": "Ctrl", "ZZZ": "Treatment"})
    m = mw.metadata_sample_match(meta, ["SAMPLE_01", "SAMPLE_02"])
    assert "SAMPLE_01" in m["matched"]
    assert "ZZZ" in m["in_metadata_not_matrix"]
    assert "SAMPLE_02" in m["in_matrix_not_metadata"]


def test_no_rnaseq_or_journal_names_in_package():
    import pathlib
    root = pathlib.Path(mw.__file__).parent
    banned = ("rnaseqspec", "edger", "voom analysis pipeline", "limma",
              "nature-like", "science-like", "cell-like", "journal-like")
    for path in root.glob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        for bad in banned:
            assert bad not in text, f"{path.name} contains banned term {bad!r}"
