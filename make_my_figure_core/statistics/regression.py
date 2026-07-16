"""Generalized linear model (GLM) regression — pure Python (statsmodels).

Fits ``response ~ predictors`` for a user-chosen family and returns a
:class:`StatsReport` with one :class:`StatResult` per model coefficient (Wald test)
plus model-level fit statistics. Numeric predictors are used as-is; categorical
predictors are one-hot encoded (first level dropped as the reference). No R, no rpy2
— statsmodels only. Every reported value comes straight from the fitted model, so it
is exact by construction (validated against statsmodels in the tests).

Families: ``gaussian`` (identity), ``binomial`` (logit), ``poisson`` (log),
``negativebinomial`` (log), ``gamma`` (log). This is a generic regression tool, not
tied to any domain workflow.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from make_my_figure_core.statistics._versions import software_versions
from make_my_figure_core.statistics.models import StatResult, StatsReport

_FAMILIES = ("gaussian", "binomial", "poisson", "negativebinomial", "gamma")


class RegressionError(ValueError):
    """Raised for actionable GLM configuration/data problems."""


def _family(name: str):
    import statsmodels.api as sm

    fam = {
        "gaussian": lambda: sm.families.Gaussian(),
        "binomial": lambda: sm.families.Binomial(),
        "poisson": lambda: sm.families.Poisson(),
        "negativebinomial": lambda: sm.families.NegativeBinomial(),
        "gamma": lambda: sm.families.Gamma(link=sm.families.links.Log()),
    }
    key = str(name).lower().replace(" ", "").replace("_", "")
    key = {"negbin": "negativebinomial", "nb": "negativebinomial",
           "logistic": "binomial"}.get(key, key)
    if key not in fam:
        raise RegressionError(
            f"Unknown GLM family '{name}'. Choose one of: {', '.join(_FAMILIES)}.")
    return key, fam[key]()


def _design(df: pd.DataFrame, predictors: Sequence[str]) -> pd.DataFrame:
    """Build a numeric design matrix: numeric columns as-is, categoricals one-hot
    (drop-first as reference). Returns the design (no constant yet)."""
    parts: List[pd.DataFrame] = []
    for col in predictors:
        s = df[col]
        if pd.api.types.is_numeric_dtype(s):
            parts.append(pd.to_numeric(s, errors="coerce").rename(col).to_frame())
        else:
            dummies = pd.get_dummies(s.astype("category"), prefix=col, drop_first=True,
                                     dtype=float)
            parts.append(dummies)
    if not parts:
        raise RegressionError("At least one predictor is required.")
    return pd.concat(parts, axis=1)


def glm_regression(df: pd.DataFrame, *, response: str, predictors: Sequence[str],
                   family: str = "gaussian", alpha: float = 0.05,
                   plot_type: Optional[str] = None,
                   preprocessing_note: str = "") -> StatsReport:
    """Fit a GLM and return a StatsReport (one StatResult per coefficient).

    ``response`` is the outcome column; ``predictors`` the explanatory columns. For
    ``binomial`` the response may be 0/1 or two-level categorical."""
    import statsmodels.api as sm

    if response not in df.columns:
        raise RegressionError(f"Response column '{response}' not found.")
    predictors = [c for c in predictors if c and c != response]
    missing = [c for c in predictors if c not in df.columns]
    if missing:
        raise RegressionError(f"Predictor column(s) not found: {', '.join(missing)}.")
    fam_key, fam = _family(family)

    X = _design(df, predictors)
    y_raw = df[response]
    if fam_key == "binomial" and not pd.api.types.is_numeric_dtype(y_raw):
        levels = list(pd.Series(y_raw.astype("category")).cat.categories)
        if len(levels) != 2:
            raise RegressionError(
                "Binomial (logistic) response must have exactly two levels; "
                f"got {len(levels)}.")
        y = y_raw.astype("category").cat.codes.astype(float)
        y_note = f"{levels[1]} vs {levels[0]}"
    else:
        y = pd.to_numeric(y_raw, errors="coerce")
        y_note = ""

    data = pd.concat([y.rename("_y"), X], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(data) <= X.shape[1] + 1:
        raise RegressionError(
            f"Not enough complete rows ({len(data)}) for {X.shape[1] + 1} parameters.")
    yv = data["_y"].to_numpy(float)
    Xv = sm.add_constant(data.drop(columns=["_y"]), has_constant="add")

    model = sm.GLM(yv, Xv.to_numpy(float), family=fam)
    fit = model.fit()

    names = list(Xv.columns)
    coefs = np.asarray(fit.params, float)
    ses = np.asarray(fit.bse, float)
    zvals = np.asarray(fit.tvalues, float)
    pvals = np.asarray(fit.pvalues, float)
    try:
        ci = np.asarray(fit.conf_int(alpha=alpha), float)
    except Exception:  # noqa: BLE001
        ci = np.full((len(names), 2), np.nan)

    # Model-fit summary: R2 for Gaussian, McFadden pseudo-R2 otherwise.
    if fam_key == "gaussian":
        ss_res = float(np.sum(fit.resid_response ** 2))
        ss_tot = float(np.sum((yv - yv.mean()) ** 2))
        fit_stat = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
        fit_stat_name = "R-squared"
    else:
        try:
            fit_stat = float(1.0 - fit.llf / fit.llnull)
        except Exception:  # noqa: BLE001
            fit_stat = np.nan
        fit_stat_name = "McFadden pseudo-R-squared"

    model_summary = {
        "family": fam_key, "link": fit.family.link.__class__.__name__,
        "n_observations": int(len(data)), "n_parameters": int(len(names)),
        "df_residual": float(getattr(fit, "df_resid", np.nan)),
        "deviance": float(getattr(fit, "deviance", np.nan)),
        "null_deviance": float(getattr(fit, "null_deviance", np.nan)),
        "log_likelihood": float(getattr(fit, "llf", np.nan)),
        "aic": float(getattr(fit, "aic", np.nan)),
        "bic": float(getattr(fit, "bic_llf", np.nan)),
        fit_stat_name: float(fit_stat) if fit_stat == fit_stat else np.nan,
        "response": response, "response_coding": y_note,
    }

    versions = software_versions()
    results: List[StatResult] = []
    for i, name in enumerate(names):
        r = StatResult(
            test_id="glm", test_name=f"GLM ({fam_key})", plot_type=plot_type,
            comparison_type="regression", value_column=response,
            grouping_columns=list(predictors), group_a=name,
            n_total=int(len(data)), statistic=float(zvals[i]), statistic_name="z",
            p_value=float(pvals[i]), alpha=alpha, alternative="two-sided",
            estimate=float(coefs[i]), estimate_name=("intercept" if name == "const"
                                                     else f"coefficient ({name})"),
            confidence_interval_low=float(ci[i, 0]), confidence_interval_high=float(ci[i, 1]),
            ci_level=1 - alpha, software_versions=versions)
        r.extra = {"std_error": float(ses[i]), "term": name, **model_summary}
        r.reject_null = bool(r.p_value is not None and r.p_value < alpha)
        r.method_sentence = _method_sentence(fam_key, response, predictors, alpha,
                                             preprocessing_note)
        results.append(r)

    report = StatsReport(results=results)
    report.config = {"analysis": "glm", **model_summary,
                     "predictors": list(predictors), "alpha": alpha}
    report.method_paragraph = _method_sentence(fam_key, response, predictors, alpha,
                                               preprocessing_note)
    return report


def _method_sentence(fam_key: str, response: str, predictors: Sequence[str],
                     alpha: float, preprocessing_note: str = "") -> str:
    fam_label = {"gaussian": "Gaussian (identity link)",
                 "binomial": "binomial/logistic (logit link)",
                 "poisson": "Poisson (log link)",
                 "negativebinomial": "negative-binomial (log link)",
                 "gamma": "Gamma (log link)"}.get(fam_key, fam_key)
    pre = (preprocessing_note.rstrip(". ") + ". ") if preprocessing_note else ""
    return (f"{pre}A generalized linear model ({fam_label}) was fit with {response} as the "
            f"response and {', '.join(predictors)} as predictor(s); coefficients were tested "
            f"with Wald z-tests (statsmodels), reporting {int((1 - alpha) * 100)}% confidence "
            f"intervals.")
