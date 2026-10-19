"""Assumption checks run before a parametric test: normality and equal variances.

A parametric test is valid only when its assumptions hold, and the usual
workflow (ecology, physiology, ...) checks them first. What is checked is what
each test actually assumes:

* t-tests: Shapiro-Wilk on each group compared (on the paired differences for a
  paired t-test); Levene's test for Student's t, which assumes equal variances
  (Welch's does not).
* one-way, two-way and factorial ANOVA / ANCOVA: Shapiro-Wilk on the **model
  residuals** (the model assumes normal errors, not normal raw data: a factor
  with a large effect makes the pooled raw values bimodal however normal each
  group is), and Levene's test across the groups / factor combinations.
* Pearson correlation: Shapiro-Wilk on each variable.

Levene's test is median-centred (Brown-Forsythe), the robust form and the
default of ``car::leveneTest``. Both tests run at ``assumption_alpha`` (0.05).

The checks are reported (table, method sentence, warnings). Acting on them is
the user's choice (``assumption_action``): ``"report"`` keeps the requested test;
``"switch"`` uses the non-parametric alternative when normality fails (Welch's
t-test when only equal variances fail for Student's t). Nothing is switched
silently, and a design with no rank-based equivalent (two-way / factorial
ANOVA) is reported with a recommendation, not replaced.
"""
from __future__ import annotations

import itertools
import warnings as _warnings
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

SW_MIN_N = 3
SW_MAX_N = 5000

PARAMETRIC = {"students_t", "welch_t", "paired_t", "one_way_anova", "two_way_anova", "factorial_anova",
              "pearson"}
# requested test -> alternative when normality fails
NONPARAMETRIC_ALTERNATIVE = {"students_t": "mann_whitney", "welch_t": "mann_whitney", "paired_t": "wilcoxon",
                             "one_way_anova": "kruskal_wallis", "pearson": "spearman"}
LABELS = {"students_t": "Student's t-test", "welch_t": "Welch's t-test", "paired_t": "paired t-test",
          "one_way_anova": "one-way ANOVA", "two_way_anova": "two-way ANOVA", "factorial_anova": "factorial ANOVA",
          "pearson": "Pearson correlation", "mann_whitney": "Mann-Whitney U test",
          "wilcoxon": "Wilcoxon signed-rank test", "kruskal_wallis": "Kruskal-Wallis test",
          "spearman": "Spearman correlation"}


@dataclass
class AssumptionCheck:
    assumption: str                 # "normality" | "equal variances"
    method: str                     # "Shapiro-Wilk" | "Levene (median-centred)"
    target: str                     # what was tested: "residuals", "group 'Low N'", ...
    n: int = 0
    statistic: Optional[float] = None
    statistic_name: str = ""
    df: Optional[float] = None
    df2: Optional[float] = None
    p_value: Optional[float] = None
    passed: Optional[bool] = None   # None: not run (too few observations)
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AssumptionReport:
    test: str
    alpha: float = 0.05
    checks: List[AssumptionCheck] = field(default_factory=list)
    action: str = "report"
    used_test: Optional[str] = None
    sentence: str = ""
    warnings: List[str] = field(default_factory=list)

    @property
    def normality_failed(self) -> bool:
        return any(c.passed is False for c in self.checks if c.assumption == "normality")

    @property
    def variances_failed(self) -> bool:
        return any(c.passed is False for c in self.checks if c.assumption == "equal variances")

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["normality_failed"] = self.normality_failed
        d["variances_failed"] = self.variances_failed
        return d


# --- the two tests ----------------------------------------------------------------------------

def shapiro(values, target: str, alpha: float) -> AssumptionCheck:
    from scipy import stats

    x = np.asarray(pd.to_numeric(pd.Series(values), errors="coerce"), float)
    x = x[np.isfinite(x)]
    c = AssumptionCheck("normality", "Shapiro-Wilk", target, n=int(x.size), statistic_name="W")
    if x.size < SW_MIN_N:
        c.note = f"not tested: {x.size} observation(s); Shapiro-Wilk needs at least {SW_MIN_N}"
        return c
    if np.ptp(x) == 0:
        c.note = "not tested: every value is the same"
        return c
    with _warnings.catch_warnings():
        _warnings.simplefilter("ignore")
        w, p = stats.shapiro(x)
    c.statistic, c.p_value = float(w), float(p)
    c.passed = bool(p >= alpha)
    if x.size > SW_MAX_N:
        c.note = (f"n = {x.size}: the P value is approximate above {SW_MAX_N}, and with this many observations "
                  "even negligible departures are significant; judge from a Q-Q plot")
    return c


def levene(groups: Dict[str, Sequence[float]], target: str, alpha: float) -> AssumptionCheck:
    from scipy import stats

    arrays = {k: np.asarray(pd.to_numeric(pd.Series(v), errors="coerce"), float) for k, v in groups.items()}
    arrays = {k: a[np.isfinite(a)] for k, a in arrays.items()}
    usable = {k: a for k, a in arrays.items() if a.size >= 2}
    n = int(sum(a.size for a in usable.values()))
    c = AssumptionCheck("equal variances", "Levene (median-centred)", target, n=n, statistic_name="F")
    if len(usable) < 2:
        c.note = "not tested: fewer than two groups with two or more observations"
        return c
    if all(np.ptp(a) == 0 for a in usable.values()):
        c.note = "not tested: no variation within any group"
        return c
    f, p = stats.levene(*usable.values(), center="median")
    c.statistic, c.p_value = float(f), float(p)
    c.df, c.df2 = float(len(usable) - 1), float(n - len(usable))
    c.passed = bool(p >= alpha)
    if len(usable) < len(arrays):
        c.note = f"{len(arrays) - len(usable)} group(s) with fewer than two observations left out"
    return c


# --- which data each test assumes things about -----------------------------------------------

def _values(df, col):
    return pd.to_numeric(df[col], errors="coerce")


def _groups(df, value_col, by: Sequence[str]) -> Dict[str, np.ndarray]:
    work = df[[value_col, *by]].copy()
    work[value_col] = _values(work, value_col)
    work = work.dropna()
    out: Dict[str, np.ndarray] = {}
    for key, sub in work.groupby(list(by), sort=False, observed=True):
        key = key if isinstance(key, tuple) else (key,)
        out[" / ".join(map(str, key))] = sub[value_col].to_numpy(float)
    return out


def _model_residuals(df, value_col, factors, covariates, interactions) -> np.ndarray:
    from make_my_figure_core.statistics.factorial import _fit

    used = [value_col, *factors, *covariates]
    work = df[used].copy()
    work[value_col] = _values(work, value_col)
    for c in covariates:
        work[c] = _values(work, c)
    work = work.dropna()
    for f in factors:
        work[f] = work[f].astype(str)
    model, *_ = _fit(work, value_col, list(factors), list(covariates), interactions)
    return np.asarray(model.resid, float)


def check_assumptions(test: str, df: pd.DataFrame, cols: Dict[str, Any], stats_spec: Dict[str, Any],
                      *, mode: str = "auto") -> Optional[AssumptionReport]:
    """Run the checks ``test`` needs on ``df``; ``None`` for a test that assumes neither."""
    if test not in PARAMETRIC:
        return None
    alpha = float(stats_spec.get("assumption_alpha", 0.05))
    rep = AssumptionReport(test=test, alpha=alpha, action=str(stats_spec.get("assumption_action", "report")))
    value_col = cols.get("value_column")
    group_col = cols.get("group_column")
    subgroup_col = cols.get("subgroup_column")
    try:
        if test in ("students_t", "welch_t"):
            within = bool(subgroup_col) and subgroup_col != group_col and mode in ("within_x", "auto", "omnibus")
            by = [group_col, subgroup_col] if within else [group_col]
            groups = _groups(df, value_col, by)
            for name, vals in groups.items():
                rep.checks.append(shapiro(vals, f"group {name}", alpha))
            if test == "students_t":
                rep.checks.append(levene(groups, "groups compared", alpha))
        elif test == "paired_t":
            from make_my_figure_core.statistics import validators as val

            subject = cols.get("subject_column")
            levels = val.group_levels(df, group_col)
            ref = stats_spec.get("reference_group")
            pairs = ([(ref, lv) for lv in levels if lv != ref] if (mode == "vs_control" and ref is not None)
                     else list(itertools.combinations(levels, 2)))
            for a, b in pairs:
                try:
                    xa, xb, _ = val.paired_arrays(df, value_col, group_col, a, b, subject, context="paired t-test")
                except Exception:  # noqa: BLE001 - the test itself reports the pairing problem
                    continue
                rep.checks.append(shapiro(np.asarray(xb, float) - np.asarray(xa, float),
                                          f"differences {b} - {a}", alpha))
        elif test == "one_way_anova":
            groups = _groups(df, value_col, [group_col])
            resid = np.concatenate([g - g.mean() for g in groups.values() if g.size]) if groups else []
            rep.checks.append(shapiro(resid, "residuals (value - group mean)", alpha))
            rep.checks.append(levene(groups, f"groups of {group_col}", alpha))
        elif test in ("two_way_anova", "factorial_anova"):
            factors = [f for f in (stats_spec.get("factors") or [group_col, subgroup_col]) if f]
            covariates = list(stats_spec.get("covariates") or []) if test == "factorial_anova" else []
            interactions = stats_spec.get("interactions", "full") if test == "factorial_anova" else "full"
            resid = _model_residuals(df, value_col, factors, covariates, interactions)
            rep.checks.append(shapiro(resid, f"residuals of the {' × '.join(factors)} model", alpha))
            rep.checks.append(levene(_groups(df, value_col, factors),
                                     f"combinations of {' × '.join(factors)}", alpha))
        elif test == "pearson":
            for c in (cols.get("x_column"), cols.get("y_column")):
                if c:
                    rep.checks.append(shapiro(_values(df, c), f"{c}", alpha))
    except Exception as exc:  # noqa: BLE001 - a failed check must not stop the requested test
        rep.warnings.append(f"Assumption checks could not be run: {exc}")
    _decide(rep)
    return rep


def _fmt_p(p: Optional[float]) -> str:
    if p is None:
        return "n/a"
    return "P < 0.001" if p < 0.001 else f"P = {p:.3f}"


def _summary(checks: List[AssumptionCheck], assumption: str) -> str:
    run = [c for c in checks if c.assumption == assumption and c.passed is not None]
    if not run:
        return ""
    if len(run) == 1:
        c = run[0]
        stat = (f"{c.statistic_name}({c.df:g}, {c.df2:g}) = {c.statistic:.3g}" if c.df is not None
                else f"{c.statistic_name} = {c.statistic:.3f}")
        return f"{c.method} on {c.target}: {stat}, {_fmt_p(c.p_value)}, n = {c.n}"
    failed = [c for c in run if not c.passed]
    worst = min(run, key=lambda c: c.p_value)
    noun = run[0].target.split(" ")[0]
    noun = noun if noun.endswith("s") else noun + "s"
    return (f"{run[0].method} on each of {len(run)} {noun}: {len(failed)} below "
            f"α (smallest {_fmt_p(worst.p_value)}, {worst.target})")


def _decide(rep: AssumptionReport) -> None:
    """Choose the test to run and write the sentence and warnings."""
    rep.used_test = rep.test
    norm = _summary(rep.checks, "normality")
    var = _summary(rep.checks, "equal variances")
    parts = [p for p in (norm, var) if p]
    alpha = f"α = {rep.alpha:g}"
    not_run = [c for c in rep.checks if c.passed is None and c.note]
    if not parts:
        if not_run:
            rep.sentence = ("Assumptions could not be tested (" + "; ".join(sorted({c.note for c in not_run}))
                            + ").")
            rep.warnings.append(rep.sentence)
        return
    rep.sentence = "Assumptions were checked before the test: " + "; ".join(parts) + f" ({alpha})."
    nf, vf = rep.normality_failed, rep.variances_failed
    if not nf and not vf:
        rep.sentence += " Both were met." if norm and var else " The assumption was met."
        return
    what = " and ".join(w for w, bad in (("normality", nf), ("equal variances", vf)) if bad)
    label = LABELS.get(rep.test, rep.test)
    alt = NONPARAMETRIC_ALTERNATIVE.get(rep.test) if nf else ("welch_t" if rep.test == "students_t" else None)
    if rep.action == "switch" and alt:
        rep.used_test = alt
        rep.sentence += (f" The assumption of {what} was not met, so the {LABELS[alt]} was used instead of the "
                         f"{label}.")
        rep.warnings.append(f"The assumption of {what} was not met; the {LABELS[alt]} was used instead of the "
                            f"{label}.")
        return
    if alt:
        advice = f"consider the {LABELS[alt]} (set 'If assumptions fail' to use it)"
    elif rep.test in ("two_way_anova", "factorial_anova"):
        advice = ("there is no rank-based equivalent here; consider a log or square-root transformation of the "
                  "response (Prepare table) and check again")
    else:
        advice = "interpret the result with care"
    rep.sentence += f" The assumption of {what} was not met; the {label} was run as requested."
    rep.warnings.append(f"The assumption of {what} was not met for the {label} ({'; '.join(parts)}): {advice}.")
