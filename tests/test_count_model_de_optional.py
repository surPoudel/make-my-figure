"""Optional count-model DE: no R/rpy2 in core; graceful skip when extra absent."""

import sys

import numpy as np
import pandas as pd
import pytest

from make_my_figure_core.matrix_workflow import count_model_de as cde
import make_my_figure_core.matrix_workflow as mw


def _count_matrix(valid=True):
    rng = np.random.default_rng(0)
    samples = [f"S{i}" for i in range(6)]
    v = rng.poisson(50, size=(40, 6)).astype(float)
    if not valid:
        v[0, 0] = -1.0                       # break integer/non-negative
    d = pd.DataFrame({"feature_id": [f"F{i}" for i in range(40)]})
    for j, s in enumerate(samples):
        d[s] = v[:, j]
    spec = mw.MatrixSpec(feature_id_column="feature_id", value_columns=samples,
                         value_type="raw_numeric", source_file="counts", confirmed_by_user=True)
    meta = mw.metadata_from_assignment({s: ("A" if i < 3 else "B") for i, s in enumerate(samples)})
    return d, spec, meta


def test_no_r_or_rpy2_in_core():
    # Importing the matrix workflow must never pull in R bridges.
    import make_my_figure_core.matrix_workflow  # noqa: F401
    assert "rpy2" not in sys.modules


def test_integer_count_validation():
    d, spec, _m = _count_matrix(valid=False)
    problems = cde.validate_integer_counts(d, spec)
    assert any("non-negative" in p or "integer" in p for p in problems)
    d2, spec2, _m2 = _count_matrix(valid=True)
    assert cde.validate_integer_counts(d2, spec2) == []


def test_optional_extra_not_required_and_message_is_clear():
    if cde.count_model_available():
        pytest.skip("count-de extra installed; message path not exercised")
    d, spec, meta = _count_matrix(valid=True)
    with pytest.raises(RuntimeError) as exc:
        cde.count_model_differential(d, spec, meta, group_a="A", group_b="B")
    assert "count-de" in str(exc.value) and "PyDESeq2" in str(exc.value)


@pytest.mark.skipif(not cde.count_model_available(),
                    reason="optional 'count-de' extra (pydeseq2) not installed")
def test_count_model_runs_when_extra_present():
    d, spec, meta = _count_matrix(valid=True)
    res, cspec = cde.count_model_differential(d, spec, meta, group_a="B", group_b="A")
    for col in ("feature_id", "log2_fold_change", "p_value", "adjusted_p_value", "average_abundance"):
        assert col in res.columns
    assert cspec.method == "pydeseq2" and cspec.package_version
