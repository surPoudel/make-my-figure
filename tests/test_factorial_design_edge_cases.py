"""Design checks found by independent review (each reproduced before the fix)."""
import numpy as np
import pandas as pd
import pytest

from make_my_figure_core.statistics import anova
from make_my_figure_core.statistics.factorial import check_design, factorial_anova
from make_my_figure_core.statistics.models import StatsError


def test_nested_factor_under_main_effects_is_refused_not_misreported():
    # B nested in A: A1 has b1,b2; A2 has b3,b4. Rank 4 of 5 parameters. It was
    # accepted, reporting A with F = 0.037, P = 0.85 although A is aliased with B.
    rows = [{"A": a, "B": b, "y": float(i % 4) + (a == "A2")}
            for a, bs in (("A1", ("b1", "b2")), ("A2", ("b3", "b4"))) for b in bs for i in range(4)]
    df = pd.DataFrame(rows)
    rep = check_design(df, "y", ["A", "B"], interactions="main")
    assert not rep.estimable and any("rank-deficient" in p for p in rep.problems)
    with pytest.raises(StatsError):
        factorial_anova(df, "y", ["A", "B"], interactions="main")


def test_covariate_collinear_with_a_factor_is_refused():
    df = pd.DataFrame({"g": ["a", "b"] * 6, "c": [1.0, 2.0] * 6, "y": np.arange(12.0)})
    assert not check_design(df, "y", ["g"], covariates=["c"]).estimable


def test_a_nanomolar_response_is_not_called_constant():
    # np.allclose's absolute tolerance (1e-8) made 5e-9 .. 7e-9 M "the same value".
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"a": np.repeat(["x", "y"], 8), "b": np.tile(np.repeat(["p", "q"], 4), 2),
                       "conc_M": 5e-9 + 2e-9 * rng.random(16) + 1e-9 * np.repeat([0, 1], 8)})
    assert check_design(df, "conc_M", ["a", "b"]).estimable
    res = anova.two_way_anova(df, "conc_M", "a", "b")
    assert len(res) == 3 and all(np.isfinite(r.statistic) for r in res)


def test_missing_subject_ids_do_not_drop_analysed_rows():
    df = pd.DataFrame({"g": ["a", "b"] * 5, "y": np.arange(10.0),
                       "colony": ["c1", "c2", "c3", None, "c5", "c6", "c7", "c8", "c9", "c10"]})
    rep = check_design(df, "y", ["g"], subject="colony")
    assert rep.n_used == 10 and rep.n_dropped_missing == 0
    assert any("no 'colony'" in w for w in rep.warnings)
