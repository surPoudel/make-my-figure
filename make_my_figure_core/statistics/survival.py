"""Survival statistics: the log-rank test and (optional) Cox hazard ratios.

The log-rank test is implemented natively from the counting-process definition
(no lifelines dependency) and generalizes to >= 2 groups via the standard
observed-minus-expected vector and its covariance matrix. Cox proportional-
hazards estimation uses statsmodels' ``PHReg`` and reports HR + 95% CI with an
explicit warning that the proportional-hazards assumption is *not* checked.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats

from make_my_figure_core.statistics._versions import software_versions
from make_my_figure_core.statistics.models import StatResult, StatsError


def logrank_test(df: pd.DataFrame, time_col: str, event_col: str, group_col: str,
                 *, alpha: float = 0.05) -> StatResult:
    """Multi-group log-rank test comparing survival across groups.

    ``event_col`` is 1 for an event (e.g. death) and 0 for censored. Returns a
    StatResult with the chi-square statistic, df = (#groups - 1), and p-value,
    plus per-group observed/expected event counts.
    """
    for c in (time_col, event_col, group_col):
        if c not in df.columns:
            raise StatsError(f"Log-rank test: missing column '{c}'.")
    work = pd.DataFrame({
        "t": pd.to_numeric(df[time_col], errors="coerce"),
        "e": pd.to_numeric(df[event_col], errors="coerce"),
        "g": df[group_col].astype("object"),
    }).dropna(subset=["t", "e", "g"])
    if work.empty:
        raise StatsError("Log-rank test: no complete rows.")
    groups = [g for g in dict.fromkeys(work["g"].tolist())]
    if len(groups) < 2:
        raise StatsError("Log-rank test needs >= 2 groups with data.")
    gidx = {g: i for i, g in enumerate(groups)}
    k = len(groups)

    event_times = np.sort(work.loc[work["e"] == 1, "t"].unique())
    observed = np.zeros(k)
    expected = np.zeros(k)
    V = np.zeros((k, k))

    t_all = work["t"].to_numpy(float)
    e_all = work["e"].to_numpy(float)
    g_all = np.array([gidx[g] for g in work["g"].tolist()])

    for t in event_times:
        at_risk_mask = t_all >= t
        n_at_risk = at_risk_mask.sum()
        if n_at_risk == 0:
            continue
        d_total = int(((t_all == t) & (e_all == 1)).sum())
        if d_total == 0:
            continue
        n_j = np.array([(at_risk_mask & (g_all == j)).sum() for j in range(k)], float)
        o_j = np.array([((t_all == t) & (e_all == 1) & (g_all == j)).sum()
                        for j in range(k)], float)
        observed += o_j
        expected += d_total * n_j / n_at_risk
        if n_at_risk > 1:
            factor = d_total * (n_at_risk - d_total) / (n_at_risk - 1) / (n_at_risk ** 2)
            for j in range(k):
                V[j, j] += factor * n_j[j] * (n_at_risk - n_j[j])
                for l in range(j + 1, k):
                    cov = -factor * n_j[j] * n_j[l]
                    V[j, l] += cov
                    V[l, j] += cov

    z = observed - expected
    # Drop the last group for a full-rank system; chi-square with df = k-1.
    z_r = z[:-1]
    V_r = V[:-1, :-1]
    try:
        stat = float(z_r @ np.linalg.pinv(V_r) @ z_r)
    except Exception:  # pragma: no cover
        stat = float("nan")
    dof = k - 1
    p = float(stats.chi2.sf(stat, dof)) if np.isfinite(stat) else float("nan")

    r = StatResult(test_id="logrank", test_name="Log-rank test",
                   comparison_type="survival", grouping_columns=[group_col],
                   value_column=time_col, n_total=int(len(work)),
                   software_versions=software_versions())
    r.statistic = stat; r.statistic_name = "chi2"; r.df = float(dof); r.p_value = p
    r.n_by_group = {str(g): int((work["g"] == g).sum()) for g in groups}
    r.extra = {
        "observed_events": {str(g): float(observed[i]) for g, i in gidx.items()},
        "expected_events": {str(g): float(expected[i]) for g, i in gidx.items()},
        "events_by_group": {str(g): int(work.loc[(work["g"] == g) & (work["e"] == 1)].shape[0])
                            for g in groups},
    }
    r.assumptions_checked = ["independent survival times", "non-informative censoring",
                             "proportional hazards (for interpretation)"]
    return r


def cox_hazard_ratio(df: pd.DataFrame, time_col: str, event_col: str, group_col: str,
                     *, reference: Optional[Any] = None, alpha: float = 0.05) -> List[StatResult]:
    """Cox proportional-hazards HRs for a single categorical covariate.

    One StatResult per non-reference level, reporting HR = exp(coef), its 95% CI,
    and the Wald p-value. The proportional-hazards assumption is NOT tested here;
    every result carries a warning to that effect. Requires statsmodels.
    """
    try:
        import statsmodels.api as sm
        from statsmodels.duration.hazard_regression import PHReg
    except Exception as exc:  # pragma: no cover
        raise StatsError(f"Cox regression requires statsmodels ({exc}).")

    work = pd.DataFrame({
        "t": pd.to_numeric(df[time_col], errors="coerce"),
        "e": pd.to_numeric(df[event_col], errors="coerce"),
        "g": df[group_col].astype(str),
    }).dropna()
    if work.empty:
        raise StatsError("Cox regression: no complete rows.")
    levels = list(dict.fromkeys(work["g"].tolist()))
    if len(levels) < 2:
        raise StatsError("Cox regression needs >= 2 groups.")
    ref = str(reference) if reference is not None else levels[0]
    if ref not in levels:
        ref = levels[0]
    ordered = [ref] + [g for g in levels if g != ref]
    cat = pd.Categorical(work["g"], categories=ordered)
    dummies = pd.get_dummies(cat, drop_first=True).astype(float)
    exog = dummies.to_numpy()
    z = stats.norm.ppf(1 - alpha / 2)
    model = PHReg(work["t"].to_numpy(float), exog, status=work["e"].to_numpy(float))
    fit = model.fit()
    results: List[StatResult] = []
    for col_i, level in enumerate(dummies.columns):
        coef = float(fit.params[col_i]); se = float(fit.bse[col_i])
        pval = float(fit.pvalues[col_i])
        r = StatResult(test_id="cox_ph", test_name="Cox proportional-hazards model",
                       comparison_type="survival", grouping_columns=[group_col],
                       value_column=time_col, group_a=str(level), group_b=ref,
                       n_total=int(len(work)), software_versions=software_versions())
        r.statistic = float(coef / se) if se > 0 else float("nan")
        r.statistic_name = "z"; r.p_value = pval
        r.estimate = float(np.exp(coef)); r.estimate_name = "hazard ratio"
        r.effect_size_name = "hazard ratio"; r.effect_size = float(np.exp(coef))
        r.confidence_interval_low = float(np.exp(coef - z * se))
        r.confidence_interval_high = float(np.exp(coef + z * se))
        r.ci_level = 1 - alpha
        r.assumptions_checked = ["proportional hazards (NOT verified)",
                                 "non-informative censoring"]
        r.warnings.append("Proportional-hazards assumption is not checked; verify before reporting HR.")
        results.append(r)
    return results
