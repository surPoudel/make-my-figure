"""Factorial ANOVA / ANCOVA for ordinary experimental tables — only when estimable.

A table with three categorical columns does not license a three-way ANOVA. The
model ``response ~ A * B * C`` can be fitted only if every combination of levels
was observed, no factor is a relabelling of another, the design matrix has full
rank, and observations remain to estimate the error variance. With four rows,
two of which share one treatment/time combination, none of that holds — and a
naive fit returns ``NaN`` or, worse, a confident-looking number.

:func:`check_design` therefore inspects the design first and says, in plain
words, why a model is not estimable. :func:`factorial_anova` refuses to run
unless the check passes.

Conventions (see ``docs/STATISTICS_FACTORIAL.md``):

* Ordinary least squares via statsmodels; factors as categorical terms.
* Type II sums of squares by default (each term adjusted for every term that
  does not contain it; the default of ``car::Anova``). Type I (sequential, R's
  ``anova(lm)``: each term adjusted only for the terms before it, so the factor
  order matters when cell sizes differ) and Type III on request; Type III is
  always with sum-to-zero contrasts — Type III with treatment contrasts tests
  hypotheses that depend on the reference level and is not offered.
* Covariates enter as main effects (ANCOVA with parallel slopes).
* Effect size: partial eta-squared, SS_term / (SS_term + SS_residual).
* Repeated rows from one subject/colony are not independent; a mixed-effects
  model would be needed and is not fitted here — the design is refused.
"""
from __future__ import annotations

import itertools
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from make_my_figure_core.statistics._versions import software_versions
from make_my_figure_core.statistics.models import StatResult, StatsError

MAX_FACTORS = 3


@dataclass
class DesignReport:
    """What the design can and cannot support."""

    response: str
    factors: List[str]
    covariates: List[str]
    subject: Optional[str]
    interactions: str
    estimable: bool = False
    problems: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    n_rows: int = 0
    n_used: int = 0
    n_dropped_missing: int = 0
    n_parameters: int = 0
    rank: int = 0
    residual_df: int = 0
    n_cells: int = 0
    n_empty_cells: int = 0
    balanced: bool = False
    cells: List[Dict[str, Any]] = field(default_factory=list)
    confounded: List[List[str]] = field(default_factory=list)
    formula: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def explanation(self) -> str:
        if self.estimable:
            head = (f"The design is estimable: {self.n_used} observations, {self.n_parameters} model "
                    f"parameters, {self.residual_df} residual degrees of freedom.")
        else:
            head = "This analysis cannot be estimated from these data:"
        lines = [head] + [f"• {p}" for p in self.problems] + [f"Note: {w}" for w in self.warnings]
        return "\n".join(lines)


def _internal(names: Sequence[str], prefix: str) -> Dict[str, str]:
    return {n: f"{prefix}{i}" for i, n in enumerate(names)}


def _formula(fmap: Dict[str, str], cmap: Dict[str, str], interactions: str, contrast: str) -> str:
    fac = [f"C({v}, {contrast})" for v in fmap.values()]
    joiner = " * " if interactions == "full" else " + "
    rhs = joiner.join(fac) if fac else "1"
    if cmap:
        rhs = " + ".join([f"({rhs})" if interactions == "full" and len(fac) > 1 else rhs] + list(cmap.values()))
    return f"_y ~ {rhs}"


def display_formula(response: str, factors: Sequence[str], covariates: Sequence[str], interactions: str) -> str:
    """``total quantity ~ treatment * time + body size`` (names as the user wrote them)."""
    rhs = (" * " if interactions == "full" else " + ").join(factors) or "1"
    if covariates:
        rhs = " + ".join([rhs, *covariates])
    return f"{response} ~ {rhs}"


def _prepare(df: pd.DataFrame, response: str, factors: Sequence[str], covariates: Sequence[str],
             subject: Optional[str], report: DesignReport) -> Optional[pd.DataFrame]:
    used = [response, *factors, *covariates] + ([subject] if subject else [])
    missing_cols = [c for c in used if c not in df.columns]
    if missing_cols:
        report.problems.append(f"Column(s) not in the table: {', '.join(map(repr, missing_cols))}.")
        return None
    if len(set(used)) != len(used):
        report.problems.append("A column was given more than one role (response, factor, covariate, subject).")
        return None
    work = df[used].copy()
    for c in [response, *covariates]:
        coerced = pd.to_numeric(work[c], errors="coerce")
        text = int((coerced.isna() & work[c].notna()).sum())
        if text:
            report.problems.append(f"{c!r} must be numeric but {text} value(s) are text.")
        work[c] = coerced
    report.n_rows = int(len(work))
    before = len(work)
    analysed = [response, *factors, *covariates]
    work = work.dropna(subset=analysed)
    if subject and work[subject].isna().any():
        report.warnings.append(f"{int(work[subject].isna().sum())} row(s) have no {subject!r}; their "
                               "independence from other rows cannot be checked.")
    report.n_dropped_missing = int(before - len(work))
    report.n_used = int(len(work))
    if report.n_dropped_missing:
        report.warnings.append(f"{report.n_dropped_missing} row(s) with a missing value in a used column "
                               "were left out (listwise deletion).")
    for f in factors:
        work[f] = work[f].astype(str)
    return work


def check_design(df: pd.DataFrame, response: str, factors: Sequence[str], *,
                 covariates: Sequence[str] = (), subject: Optional[str] = None,
                 interactions: str = "full") -> DesignReport:
    """Inspect whether ``response ~ factors (+ covariates)`` can be estimated."""
    factors, covariates = list(factors), list(covariates or [])
    rep = DesignReport(response=response, factors=factors, covariates=covariates, subject=subject,
                       interactions=interactions)
    if interactions not in ("full", "main"):
        rep.problems.append("interactions must be 'full' or 'main'.")
        return rep
    if not factors:
        rep.problems.append("Choose at least one factor.")
        return rep
    if len(factors) > MAX_FACTORS:
        rep.problems.append(f"At most {MAX_FACTORS} factors are supported.")
        return rep
    work = _prepare(df, response, factors, covariates, subject, rep)
    if work is None or rep.problems:
        return rep
    if rep.n_used == 0:
        rep.problems.append("No complete rows remain after leaving out missing values.")
        return rep

    y = work[response].to_numpy(float)
    if np.nanmax(y) == np.nanmin(y):     # exact: a 5e-9 M response is not "constant"
        rep.problems.append(f"{response!r} has the same value ({y[0]:g}) in every row; there is no variation "
                            "to analyse.")
    for f in factors:
        k = work[f].nunique()
        if k < 2:
            rep.problems.append(f"Factor {f!r} has only {k} level in the analysed rows; a factor needs at least 2.")
    for c in covariates:
        if work[c].max() == work[c].min():
            rep.problems.append(f"Covariate {c!r} is constant.")

    # Independence: rows sharing a subject/colony are repeated measurements.
    if subject:
        per = work.groupby(subject).size()
        if (per > 1).any():
            rep.problems.append(
                f"{int(per.sum())} rows come from {int(per.size)} distinct {subject!r} values; "
                f"{int((per > 1).sum())} {subject!r} value(s) contribute more than one row. Repeated "
                "observations of the same unit are not independent replicates. That needs a "
                "mixed-effects model with the unit as a random effect, which MakeMyFigure does not "
                "fit. Average to one value per unit and condition, or analyse the full data in "
                "dedicated software (e.g. R lme4).")

    # Cells of the full factorial.
    levels = [sorted(work[f].unique()) for f in factors]
    counts = work.groupby(factors).size()
    cells = []
    for combo in itertools.product(*levels):
        key = combo if len(factors) > 1 else combo[0]
        n = int(counts.get(key, 0))
        cells.append({**dict(zip(factors, combo)), "n": n})
    rep.cells = cells
    rep.n_cells = len(cells)
    rep.n_empty_cells = sum(1 for c in cells if c["n"] == 0)
    ns = {c["n"] for c in cells}
    rep.balanced = len(ns) == 1 and 0 not in ns

    # Complete confounding between two factors (each level of one occurs with one level of the other).
    for a, b in itertools.combinations(factors, 2):
        tab = pd.crosstab(work[a], work[b])
        if ((tab > 0).sum(axis=1) == 1).all() and ((tab > 0).sum(axis=0) == 1).all():
            rep.confounded.append([a, b])
            rep.problems.append(f"{a!r} and {b!r} are completely confounded: each level of {a!r} occurs "
                                f"with exactly one level of {b!r}, so their effects cannot be separated.")
    if rep.n_empty_cells and interactions == "full" and len(factors) > 1:
        rep.problems.append(f"{rep.n_empty_cells} of {rep.n_cells} factor combinations have no observations, "
                            "so the interaction terms cannot be estimated. Collect data for the empty "
                            "combinations, or fit main effects only (no interactions).")

    # Rank and residual degrees of freedom of the requested model.
    try:
        import patsy

        fmap = _internal(factors, "_f")
        cmap = _internal(covariates, "_c")
        frame = work.rename(columns={response: "_y", **fmap, **cmap})
        formula = _formula(fmap, cmap, interactions, "Sum")
        rep.formula = display_formula(response, factors, covariates, interactions)
        X = patsy.dmatrix(formula.split("~", 1)[1], frame, return_type="dataframe")
        rep.n_parameters = int(X.shape[1])
        rep.rank = int(np.linalg.matrix_rank(X.to_numpy(float)))
        rep.residual_df = int(rep.n_used - rep.rank)
        explained = bool(rep.confounded) or (rep.n_empty_cells and interactions == "full" and len(factors) > 1)
        if rep.rank < rep.n_parameters and not explained:
            # e.g. a factor nested in another under a main-effects model, or a
            # covariate collinear with a factor: fitting would silently drop
            # parameters and report wrong F and P for the aliased terms.
            rep.problems.append(f"The design matrix is rank-deficient ({rep.rank} of {rep.n_parameters} "
                                "parameters identifiable): some effects are aliased with others.")
        if rep.residual_df <= 0:
            rep.problems.append(f"No residual degrees of freedom: {rep.n_used} observations for "
                                f"{rep.rank} identifiable parameters. The error variance cannot be "
                                "estimated, so F statistics and P values do not exist.")
        elif rep.residual_df < 5:
            rep.warnings.append(f"Only {rep.residual_df} residual degrees of freedom; the error variance is "
                                "poorly estimated and the test has little power.")
    except Exception as exc:  # noqa: BLE001
        rep.problems.append(f"The model could not be built: {exc}")

    singles = sum(1 for c in cells if c["n"] == 1)
    if singles and not rep.n_empty_cells:
        rep.warnings.append(f"{singles} factor combination(s) have a single observation (no replication).")
    if not rep.balanced and not rep.n_empty_cells:
        rep.warnings.append("Unequal numbers per combination: Type II and Type III sums of squares differ; "
                            "report which was used.")
    if covariates:
        rep.warnings.append("Covariates are assumed to have the same slope in every group (no "
                            "factor x covariate interaction).")
    rep.estimable = not rep.problems
    return rep


def _term_label(term: str, fmap: Dict[str, str], cmap: Dict[str, str]) -> str:
    inv = {v: k for k, v in {**fmap, **cmap}.items()}
    parts = []
    for p in term.split(":"):
        p = p.strip()
        if p.startswith("C("):
            p = p[2:].split(",")[0].strip()
        parts.append(inv.get(p, p))
    return " × ".join(parts)


def _fit(work: pd.DataFrame, response: str, factors, covariates, interactions):
    import statsmodels.formula.api as smf

    fmap = _internal(factors, "_f")
    cmap = _internal(covariates, "_c")
    frame = work.rename(columns={response: "_y", **fmap, **cmap})
    formula = _formula(fmap, cmap, interactions, "Sum")
    return smf.ols(formula, data=frame).fit(), fmap, cmap, formula


def _sequential_table(model) -> pd.DataFrame:
    """Type I (sequential) ANOVA table in R's term order.

    Each term's SS is the drop in residual SS when it joins the terms before it.
    R orders terms main effects first (factors, then covariates), then
    interactions by degree. Patsy groups a covariate after every categorical
    interaction, and sequential SS depend on the order: ``anova_lm(typ=1)`` gave
    the covariate of validation case F6 SS = 0.0463 where R's ``anova(lm)``
    gives 0.0975, so the table is built here from nested least-squares fits.
    """
    from scipy import stats as sps

    info = model.model.data.design_info
    X = np.asarray(model.model.exog, float)
    y = np.asarray(model.model.endog, float)
    terms = [t for t in info.terms if t.factors]
    terms.sort(key=lambda t: len(t.factors))          # stable: keeps main-effect order
    intercept = [info.slice(t) for t in info.terms if not t.factors]

    def rss(cols):
        if not cols:
            return float(np.sum((y - y.mean()) ** 2)) if intercept else float(np.sum(y ** 2))
        A = X[:, cols]
        beta, *_ = np.linalg.lstsq(A, y, rcond=None)
        return float(np.sum((y - A @ beta) ** 2))

    used = [i for sl in intercept for i in range(X.shape[1])[sl]]
    prev = rss(used) if used else rss([])
    df_res = float(model.df_resid)
    rss_full = float(model.ssr)
    rows, names = [], []
    for t in terms:
        cols = list(range(X.shape[1])[info.slice(t)])
        used += cols
        cur = rss(used)
        ss = prev - cur
        df = float(len(cols))
        F = (ss / df) / (rss_full / df_res)
        rows.append({"df": df, "sum_sq": ss, "F": F, "PR(>F)": float(sps.f.sf(F, df, df_res))})
        names.append(info.term_names[info.terms.index(t)])
        prev = cur
    rows.append({"df": df_res, "sum_sq": rss_full, "F": np.nan, "PR(>F)": np.nan})
    names.append("Residual")
    return pd.DataFrame(rows, index=names)


def factorial_anova(df: pd.DataFrame, response: str, factors: Sequence[str], *,
                    covariates: Sequence[str] = (), subject: Optional[str] = None,
                    interactions: str = "full", ss_type: int = 2) -> List[StatResult]:
    """ANOVA table (one :class:`StatResult` per term). Raises :class:`StatsError`
    with the design explanation when the model is not estimable."""
    try:
        import statsmodels.api as sm
    except Exception as exc:  # pragma: no cover
        raise StatsError(f"Factorial ANOVA requires statsmodels ({exc}).")
    if ss_type not in (1, 2, 3):
        raise StatsError("ss_type must be 1, 2 or 3.")
    rep = check_design(df, response, factors, covariates=covariates, subject=subject, interactions=interactions)
    if not rep.estimable:
        raise StatsError(rep.explanation())
    work = _prepare(df, response, list(factors), list(covariates), subject, DesignReport(
        response, list(factors), list(covariates), subject, interactions))
    model, fmap, cmap, formula = _fit(work, response, list(factors), list(covariates), interactions)
    table = _sequential_table(model) if ss_type == 1 else sm.stats.anova_lm(model, typ=ss_type)
    ss_res = float(table.loc["Residual", "sum_sq"])
    df_res = float(table.loc["Residual", "df"])
    k = len(factors)
    name = {1: "One-way", 2: "Two-way", 3: "Three-way"}[k] if not covariates else f"{k}-factor ANCOVA"
    name = f"{name} ANOVA" if not covariates else name
    roman = {1: "I", 2: "II", 3: "III"}[ss_type]
    results: List[StatResult] = []
    for term in table.index:
        if term in ("Residual", "Intercept"):
            continue
        row = table.loc[term]
        r = StatResult(test_id="factorial_anova", test_name=f"{name} (Type {roman} SS)",
                       comparison_type="omnibus", value_column=response,
                       grouping_columns=list(factors), n_total=rep.n_used,
                       software_versions=software_versions())
        label = _term_label(term, fmap, cmap)
        r.group_a = label
        r.statistic = float(row["F"]); r.statistic_name = "F"
        r.df = float(row["df"]); r.df2 = df_res
        r.p_value = float(row["PR(>F)"])
        ss = float(row["sum_sq"])
        r.effect_size_name = "partial eta-squared"
        r.effect_size = ss / (ss + ss_res) if (ss + ss_res) > 0 else float("nan")
        r.extra = {"term": label, "sum_sq": ss, "mean_sq": ss / float(row["df"]),
                   "residual_sum_sq": ss_res, "residual_df": df_res, "ss_type": roman,
                   "contrasts": "sum-to-zero", "formula": rep.formula,
                   "covariates": list(covariates), "design": {"balanced": rep.balanced,
                                                              "cells": rep.cells}}
        r.warnings = list(rep.warnings)
        r.assumptions_checked = ["independent observations", "approximately normal residuals",
                                 "equal variances across groups"] + (["parallel covariate slopes"]
                                                                     if covariates else [])
        results.append(r)
    return results


def _coefficient_label(term: str, fmap: Dict[str, str], cmap: Dict[str, str]) -> Tuple[str, str]:
    """``("treatment = control × time = 2", meaning)`` for a patsy term name."""
    if term == "Intercept":
        return "Intercept", ("mean of the cell means (factors); with covariates, at covariate = 0"
                             if cmap else "mean of the cell means")
    inv = {v: k for k, v in {**fmap, **cmap}.items()}
    parts, is_covariate = [], False
    for piece in term.split(":"):
        if piece.startswith("C("):
            inner = piece[2:].split(",")[0].strip()
            level = piece.split("[S.", 1)[1].rstrip("]") if "[S." in piece else "?"
            parts.append(f"{inv.get(inner, inner)} = {level}")
        else:
            parts.append(inv.get(piece, piece))
            is_covariate = True
    label = " × ".join(parts)
    if is_covariate and len(parts) == 1:
        return f"{label} (slope)", "change in the response per unit of the covariate"
    if len(parts) == 1:
        return label, "deviation of this level from the mean of all levels (sum-to-zero)"
    return label, "interaction deviation for this combination of levels (sum-to-zero)"


def model_coefficients(df: pd.DataFrame, response: str, factors: Sequence[str], *,
                       covariates: Sequence[str] = (), subject: Optional[str] = None,
                       interactions: str = "full", alpha: float = 0.05) -> pd.DataFrame:
    """Coefficient table of the sum-to-zero OLS fit - R's ``summary(lm)`` under ``contr.sum``.

    Columns: ``label`` (readable, e.g. ``treatment = control``), ``estimate``,
    ``std_error``, ``t``, ``p_value``, ``ci_low``/``ci_high`` (``1 - alpha``),
    ``residual_df``, ``meaning`` and ``term`` (the model's own name). With
    sum-to-zero coding each factor's last level has no row: its deviation is minus
    the sum of the others. Refuses, like :func:`factorial_anova`, a design that is
    not estimable.
    """
    rep = check_design(df, response, factors, covariates=covariates, subject=subject,
                       interactions=interactions)
    if not rep.estimable:
        raise StatsError(rep.explanation())
    work = _prepare(df, response, list(factors), list(covariates), subject, DesignReport(
        response, list(factors), list(covariates), subject, interactions))
    model, fmap, cmap, _ = _fit(work, response, list(factors), list(covariates), interactions)
    ci = model.conf_int(alpha)
    labels = [_coefficient_label(str(t), fmap, cmap) for t in model.params.index]
    return pd.DataFrame({"label": [lab for lab, _ in labels], "estimate": model.params.values,
                         "std_error": model.bse.values, "t": model.tvalues.values,
                         "p_value": model.pvalues.values, "ci_low": ci[0].values,
                         "ci_high": ci[1].values, "residual_df": float(model.df_resid),
                         "meaning": [m for _, m in labels], "term": model.params.index})
