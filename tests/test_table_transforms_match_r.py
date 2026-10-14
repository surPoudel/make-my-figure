"""Table transformations agree with base R, and never invent values R leaves undefined.

Reference: tests/fixtures/r_transform_reference.csv, written by
quality_audit/general_tabular_workflow/r_validation/transforms.R (R 4.5.3, 17
significant digits) for log2 / log10 / ln / sqrt at offsets 0, 0.5 and 1 over values
from 1e-300 to 1e300 plus 0, -1 and NA, and z-scores (sample SD).

Prespecified tolerance: relative 1e-14 where R's result is finite and non-zero. Where
R returns -Inf, NaN or NA, ours must refuse by default and give a missing value when
told to record invalid values as missing.
"""
import numpy as np
import pandas as pd
import pytest

from make_my_figure_core.tabular import TableTransform, preview_transform

REF = pd.read_csv("tests/fixtures/r_transform_reference.csv", na_values=["NA"], float_precision="round_trip")
GROUPS = [(m, o) for (m, o), _ in REF.groupby(["method", "offset"], sort=False) if m != "zscore_extreme"]


@pytest.mark.parametrize("method,offset", GROUPS)
def test_values_match_r_and_undefined_values_are_not_invented(method, offset):
    grp = REF[(REF.method == method) & (REF.offset == offset)]
    df = pd.DataFrame({"x": grp["x"].to_numpy(float)})
    lenient = preview_transform(df, TableTransform("x", method, float(offset), "missing"))
    strict = preview_transform(df, TableTransform("x", method, float(offset), "refuse"))
    r_vals = grp["r_value"].to_numpy(float)
    xs = df["x"].to_numpy(float)
    undefined = np.isfinite(xs) & ~np.isfinite(r_vals)
    for x, rv, ov in zip(xs, r_vals, lenient.transformed):
        if not np.isfinite(x) or not np.isfinite(rv):
            assert ov is None, (method, offset, x, ov)
        elif rv == 0:
            assert ov == 0.0
        else:
            assert abs(ov - rv) <= 1e-14 * abs(rv), (method, offset, x, ov, rv)
    assert strict.n_invalid == int(undefined.sum())
    assert strict.can_apply == (not undefined.any())


def test_z_score_refuses_where_r_returns_a_column_of_zeros():
    grp = REF[REF.method == "zscore_extreme"]
    assert (grp["r_value"] == 0).all()          # R: SD overflows to Inf, every z is 0
    pv = preview_transform(pd.DataFrame({"x": grp["x"].to_numpy(float)}), TableTransform("x", "zscore"))
    assert not pv.can_apply and "double precision" in " ".join(pv.problems)
