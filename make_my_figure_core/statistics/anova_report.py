"""An R-style statistics report: ``summary(aov(...))`` and ``TukeyHSD(...)``, as text.

Researchers check an analysis against the console output they know::

    > model <- aov(Growth_cm ~ Species * Treatment, data = plant)
    > summary(model)
    > TukeyHSD(model)

:func:`anova_report` reproduces both for the model behind a figure - the same
rows, columns, level order, significance codes and number formatting - plus the
assumption checks (Shapiro-Wilk on the residuals, Levene) and the software
versions, so the report can go into a lab notebook or a supplement as it stands.

Conventions, matching R:

* ``summary(aov)`` is a **Type I (sequential)** table: each term is adjusted for the
  terms above it. With unequal group sizes the order of the factors changes the
  sums of squares; the report says so. Other sums-of-squares types are available in
  the app's statistics (Type II by default) and are named when used.
* Factor levels in R's default order (sorted; numbers numerically).
* ``TukeyHSD`` compares the means of every term (main effects and interactions).
  The means are those of the fitted sequential model (R's ``model.tables(x,
  "means")``): with equal group sizes they are the plain group means; with unequal
  sizes they are adjusted, exactly as R's are. Intervals and adjusted P values from
  the studentized range distribution with the model's residual df and mean square,
  computed with a port of R's own ``ptukey`` / ``qtukey`` (``_tukey_dist``).
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

SIGNIF_LEGEND = "Signif. codes:  0 '***' 0.001 '**' 0.01 '*' 0.05 '.' 0.1 ' ' 1"
_EPS = 2.220446e-16


class ReportError(ValueError):
    """The model cannot be fitted for the report."""


@dataclass
class AovRow:
    term: str
    df: int
    sum_sq: float
    mean_sq: float
    f: Optional[float] = None
    p: Optional[float] = None


@dataclass
class TukeyRow:
    comparison: str
    diff: float
    lwr: float
    upr: float
    p_adj: float


@dataclass
class AnovaReport:
    formula: str
    data_name: str
    n: int
    balanced: bool
    rows: List[AovRow]
    tukey: Dict[str, List[TukeyRow]]
    conf_level: float = 0.95
    checks: List[Dict[str, Any]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    versions: Dict[str, str] = field(default_factory=dict)
    title: str = ""

    def text(self) -> str:
        return format_report(self)


# --- factors in R's order -----------------------------------------------------------------------

def _levels(series: pd.Series) -> List[str]:
    vals = series.dropna().unique()
    try:
        nums = sorted(vals, key=lambda v: float(v))
        return [_lvl(v) for v in nums]
    except (TypeError, ValueError):
        return sorted(_lvl(v) for v in vals)


def _lvl(v) -> str:
    if isinstance(v, (float, np.floating)) and float(v).is_integer():
        return str(int(v))
    return str(v)


def _prepare(df: pd.DataFrame, response: str, factors: Sequence[str]) -> Tuple[pd.DataFrame, Dict[str, List[str]]]:
    missing = [c for c in [response, *factors] if c not in df.columns]
    if missing:
        raise ReportError(f"Column(s) not in the table: {', '.join(map(repr, missing))}.")
    work = df[[response, *factors]].copy()
    work[response] = pd.to_numeric(work[response], errors="coerce")
    work = work.dropna()
    levels = {f: _levels(work[f]) for f in factors}
    for f in factors:
        work[f] = pd.Categorical(work[f].map(_lvl), categories=levels[f])
    return work.reset_index(drop=True), levels


def _terms(factors: Sequence[str], interactions: str) -> List[Tuple[str, ...]]:
    """R's term order: main effects, then interactions by degree."""
    out = [(f,) for f in factors]
    if interactions == "full":
        for k in range(2, len(factors) + 1):
            out += list(itertools.combinations(factors, k))
    return out


def _design(work: pd.DataFrame, term: Tuple[str, ...]) -> np.ndarray:
    """Columns spanning a term's effect (sum-to-zero coding), as R's model matrix."""
    blocks = []
    for f in term:
        cats = work[f].cat.categories
        codes = work[f].cat.codes.to_numpy()
        k = len(cats)
        m = np.zeros((len(work), k - 1))
        for j in range(k - 1):
            m[codes == j, j] = 1.0
        m[codes == k - 1, :] = -1.0
        blocks.append(m)
    out = blocks[0]
    for b in blocks[1:]:
        out = np.einsum("ni,nj->nij", out, b).reshape(len(work), -1)
    return out


def _fit(X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, int]:
    beta, _, rank, _ = np.linalg.lstsq(X, y, rcond=None)
    return X @ beta, int(rank)


# --- summary(aov) -------------------------------------------------------------------------------

def aov_table(work: pd.DataFrame, response: str, factors: Sequence[str], interactions: str = "full"
              ) -> Tuple[List[AovRow], Dict[Tuple[str, ...], np.ndarray], float, int]:
    """Type I table, the per-term projections, the residual mean square and df."""
    from scipy import stats

    y = work[response].to_numpy(float)
    X = np.ones((len(work), 1))
    fitted, rank = _fit(X, y)
    rows: List[AovRow] = []
    proj: Dict[Tuple[str, ...], np.ndarray] = {}
    for term in _terms(factors, interactions):
        X = np.hstack([X, _design(work, term)])
        new, new_rank = _fit(X, y)
        df = new_rank - rank
        if df <= 0:
            continue
        ss = float(np.sum((y - fitted) ** 2) - np.sum((y - new) ** 2))
        rows.append(AovRow(":".join(term), df, ss, ss / df))
        proj[term] = new - fitted
        fitted, rank = new, new_rank
    resid = y - fitted
    df_res = len(y) - rank
    if df_res <= 0:
        raise ReportError(f"No residual degrees of freedom ({len(y)} observations, {rank} parameters).")
    ms_res = float(np.sum(resid ** 2) / df_res)
    for r in rows:
        r.f = r.mean_sq / ms_res
        r.p = float(stats.f.sf(r.f, r.df, df_res))
    rows.append(AovRow("Residuals", df_res, float(np.sum(resid ** 2)), ms_res))
    return rows, proj, ms_res, df_res


# --- TukeyHSD -----------------------------------------------------------------------------------

def tukey_hsd(work: pd.DataFrame, response: str, factors: Sequence[str], interactions: str = "full",
              conf_level: float = 0.95) -> Dict[str, List[TukeyRow]]:
    """R's ``TukeyHSD(aov(...))`` for every term."""
    from make_my_figure_core.statistics._tukey_dist import ptukey, qtukey

    _, proj, ms_res, df_res = aov_table(work, response, factors, interactions)
    grand = float(work[response].mean())
    out: Dict[str, List[TukeyRow]] = {}
    for term in proj:
        # R's cell order: the first factor varies fastest (Basil:Control, Fern:Control, ...).
        cells = [tuple(reversed(c)) for c in
                 itertools.product(*[list(work[f].cat.categories) for f in reversed(term)])]
        keys = list(zip(*[work[f].astype(str) for f in term]))
        index = pd.MultiIndex.from_tuples(keys) if len(term) > 1 else pd.Index([k[0] for k in keys])
        counts = pd.Series(1, index=index).groupby(level=list(range(len(term)))).sum()
        # model.tables(type = "means"): grand mean + the effects of every term contained in this one,
        # each effect the mean of that term's projection within its cells.
        # Every contained term's projection is averaged within this term's cells (R's
        # make.tables.aovproj): with unequal group sizes a later main effect's projection is not
        # constant within its own levels, and averaging it there gave 1.5023 where R has 1.5111.
        contained = sum(p for sub, p in proj.items() if set(sub) <= set(term))
        means: Dict[Tuple[str, ...], float] = {}
        for cell in cells:
            mask = np.ones(len(work), bool)
            for f, lv in zip(term, cell):
                mask &= (work[f].astype(str) == lv).to_numpy()
            if mask.any():
                means[cell] = grand + float(np.asarray(contained)[mask].mean())
        present = [c for c in cells if (c if len(term) > 1 else c[0]) in counts.index]
        k = len(present)
        pairs = list(itertools.combinations(range(k), 2))
        diffs, ses = [], []
        for i, j in pairs:
            a, b = present[i], present[j]
            na = int(counts[a if len(term) > 1 else a[0]])
            nb = int(counts[b if len(term) > 1 else b[0]])
            diffs.append(means[b] - means[a])
            ses.append(math.sqrt(ms_res / 2.0 * (1.0 / na + 1.0 / nb)))
        diffs_a, ses_a = np.asarray(diffs, float), np.asarray(ses, float)
        # R's own ptukey / qtukey (ported): one quantile per term, one vectorised tail call.
        q = qtukey(conf_level, k, df_res) if pairs else float("nan")
        p = np.minimum(1.0, ptukey(np.abs(diffs_a) / ses_a, k, df_res, lower_tail=False)) if pairs else []
        out[":".join(term)] = [
            TukeyRow(f"{':'.join(present[j])}-{':'.join(present[i])}", float(d), float(d - q * se),
                     float(d + q * se), float(pv))
            for (i, j), d, se, pv in zip(pairs, diffs_a, ses_a, p)]
    return out


# --- report -------------------------------------------------------------------------------------

def anova_report(df: pd.DataFrame, response: str, factors: Sequence[str], *, interactions: str = "full",
                 data_name: str = "data", conf_level: float = 0.95, title: str = "") -> AnovaReport:
    """``summary(aov)`` + ``TukeyHSD`` + the assumption checks, for ``response ~ factors``."""
    factors = list(dict.fromkeys(f for f in factors if f))
    if not factors:
        raise ReportError("The report needs at least one factor (x, hue or a grouping column).")
    work, _levels_ = _prepare(df, response, factors)
    rows, _, _, _ = aov_table(work, response, factors, interactions)
    counts = work.groupby(factors, observed=True).size()
    full = int(np.prod([len(work[f].cat.categories) for f in factors]))
    balanced = bool(len(counts) == full and counts.nunique() == 1)
    joiner = " * " if interactions == "full" else " + "
    rep = AnovaReport(formula=f"{response} ~ {joiner.join(factors)}", data_name=data_name, n=len(work),
                      balanced=balanced, rows=rows,
                      tukey=tukey_hsd(work, response, factors, interactions, conf_level),
                      conf_level=conf_level, title=title)
    dropped = len(df) - len(work)
    if dropped:
        rep.notes.append(f"{dropped} row(s) with a missing value were left out.")
    if not balanced:
        rep.notes.append("Unequal group sizes: these Type I (sequential) sums of squares depend on the order of "
                         "the factors, and the Tukey means are the model's adjusted means (as in R).")
    try:
        from make_my_figure_core.statistics.assumptions import levene, shapiro
        from make_my_figure_core.statistics.diagnostics import fit_diagnostics

        diag = fit_diagnostics(df, response, factors, interactions=interactions)
        groups = {k: g[response].to_numpy(float) for k, g in work.groupby(factors, observed=True)}
        rep.checks = [shapiro(diag.residuals, "residuals(model)", 0.05).to_dict(),
                      levene(groups, "groups", 0.05).to_dict()]
    except Exception:  # noqa: BLE001 - the tables do not depend on the checks
        pass
    from make_my_figure_core.statistics._versions import software_versions

    rep.versions = software_versions()
    return rep


# --- R's number formatting ----------------------------------------------------------------------
# A port of the parts of R's formatReal / format.pval / printCoefmat / print.TukeyHSD that these
# two tables use, so the text reads digit for digit as R's console output.

def _sci_parts(x: float, digits: int) -> Tuple[int, int, bool]:
    """(kpower, nsig, negative): x = alpha * 10^kpower with alpha rounded to ``digits`` significant."""
    if x == 0:
        return 0, 1, False
    neg = x < 0
    ax = abs(x)
    kp = int(math.floor(math.log10(ax)))
    alpha = round(ax / 10 ** kp, digits - 1)
    if alpha >= 10:
        kp += 1
        alpha = round(ax / 10 ** kp, digits - 1)
    mant = f"{alpha:.{digits - 1}f}".rstrip("0").rstrip(".")
    nsig = len(mant.replace(".", "").lstrip("0")) or 1
    return kp, nsig, neg


def format_real(values: Sequence[Optional[float]], digits: int) -> List[str]:
    """R's ``format(x, digits = digits)`` for a numeric vector (common fixed or scientific form)."""
    finite = [v for v in values if v is not None and math.isfinite(v)]
    if not finite:
        return ["" for _ in values]
    parts = [_sci_parts(v, digits) for v in finite]
    neg = int(any(p[2] for p in parts))
    left = max(max(p[0] + 1, 1) for p in parts)
    rgt = max(max(0, p[1] - p[0] - 1) for p in parts)
    w_fixed = neg + left + (rgt + 1 if rgt else 0)
    mxns = max(p[1] for p in parts)
    big_e = any(abs(p[0]) >= 100 for p in parts)
    w_sci = neg + (mxns + 1 if mxns > 1 else mxns) + (5 if big_e else 4)
    if w_fixed <= w_sci:
        txt = [f"{v:.{rgt}f}" for v in finite]
    else:
        txt = [f"{v:.{mxns - 1}e}" for v in finite]
    it = iter(txt)
    out = [next(it) if (v is not None and math.isfinite(v)) else "" for v in values]
    width = max(len(t) for t in out)
    return [t.rjust(width) if t else "" for t in out]


def _zapsmall(values: Sequence[Optional[float]], digits: int) -> List[Optional[float]]:
    finite = [abs(v) for v in values if v is not None and math.isfinite(v)]
    mx = max(finite) if finite else 0.0
    # R >= 4.4: digits - log10(mx), no ceiling; round() then takes the nearest whole number of
    # digits (4 - log10(279.97) = 1.55 -> 2 decimals: 279.97, as R prints).
    d = max(0, int(math.floor(digits - math.log10(mx) + 0.5))) if mx > 0 else digits
    return [None if v is None else round(v, d) for v in values]


def format_pval(pv: Sequence[float], digits: int, eps: float = _EPS) -> List[str]:
    """R's ``format.pval``: fixed for P >= 1e-3, scientific below, ``< 2e-16`` under eps."""
    out = [""] * len(pv)
    idx = [i for i, p in enumerate(pv) if p >= eps]
    fix = [i for i in idx if (math.floor(math.log10(pv[i])) if pv[i] > 0 else -50) >= -3]
    sci = [i for i in idx if i not in fix]
    for group in (fix, sci):
        if group:
            for i, t in zip(group, format_real([pv[i] for i in group], digits)):
                out[i] = t.strip()
    tiny = [i for i, p in enumerate(pv) if p < eps]
    if tiny:
        d = max(1, digits - 2)
        nc = max((len(out[i]) for i in idx), default=0)
        if idx and d > 1 and d + 6 > nc:
            d = max(1, nc - 7)
        sep = "" if (d == 1 and idx and nc <= 6) or (not idx and d == 1) else " "
        label = "<" + sep + f"{_signif(eps, d):.{d - 1}e}".replace("e-16", "e-16")
        for i in tiny:
            out[i] = label
    return out


def _signif(x: float, digits: int) -> float:
    if x == 0 or not math.isfinite(x):
        return x
    return round(x, digits - 1 - int(math.floor(math.log10(abs(x)))))


def _stars(p: Optional[float]) -> str:
    if p is None:
        return ""
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "." if p < 0.1 else " "


def _table(header: List[str], columns: List[List[str]], names: List[str]) -> List[str]:
    """print.default of a character matrix: row names left-aligned, columns right-aligned."""
    nw = max(len(n) for n in names)
    widths = [max(len(h), *(len(v) for v in col)) for h, col in zip(header, columns)]
    lines = [" " * nw + "".join(" " + h.rjust(w) for h, w in zip(header, widths))]
    for i, n in enumerate(names):
        lines.append(n.ljust(nw) + "".join(" " + col[i].rjust(w) for col, w in zip(columns, widths)))
    return [ln.rstrip() for ln in lines]


def format_aov(rows: List[AovRow], digits: int = 4) -> str:
    """``print(summary(aov(...)))`` (print.anova -> printCoefmat, digits = 4)."""
    dig_tst = max(1, min(5, digits - 1))
    df = format_real([float(r.df) for r in rows], digits)
    ss = format_real(_zapsmall([r.sum_sq for r in rows], digits), digits)
    ms = format_real(_zapsmall([r.mean_sq for r in rows], digits), digits)
    fv = format_real([None if r.f is None else round(r.f, dig_tst) for r in rows], digits)
    ps = [r.p for r in rows if r.p is not None]
    pf = iter(format_pval(ps, dig_tst))
    pcol = [next(pf) if r.p is not None else "" for r in rows]
    stars = [_stars(r.p) for r in rows]
    sw = max(len(x) for x in stars)
    stars = [x.ljust(sw) for x in stars]
    header = ["Df", "Sum Sq", "Mean Sq", "F value", "Pr(>F)", ""]
    lines = _table(header, [df, ss, ms, fv, pcol, stars], [r.term for r in rows])
    if any(r.p is not None and r.p < 0.1 for r in rows):
        lines += ["---", SIGNIF_LEGEND]
    return "\n".join(lines)


def format_tukey(rep: AnovaReport, digits: int = 7) -> str:
    """``print(TukeyHSD(...))``: p adj rounded to 7 decimals, each column in R's format."""
    lines = ["  Tukey multiple comparisons of means",
             f"    {rep.conf_level * 100:g}% family-wise confidence level", "",
             f"Fit: aov(formula = {rep.formula}, data = {rep.data_name})", ""]
    for term, rows in rep.tukey.items():
        lines.append(f"${term}" if ":" not in term else f"$`{term}`")
        cols = [format_real([getattr(r, a) for r in rows], digits) for a in ("diff", "lwr", "upr")]
        cols.append(format_real([round(r.p_adj, digits) for r in rows], digits))
        lines += _table(["diff", "lwr", "upr", "p adj"], cols, [r.comparison for r in rows])
        lines.append("")
    return "\n".join(lines).rstrip()


def format_report(rep: AnovaReport) -> str:
    head = [f"Statistics report{(' - ' + rep.title) if rep.title else ''}",
            f"Model: aov({rep.formula})   n = {rep.n}   "
            + ("balanced design" if rep.balanced else "unequal group sizes"),
            ""]
    parts = ["\n".join(head), "> summary(model)   # Type I (sequential) sums of squares, as in R",
             format_aov(rep.rows), "", "> TukeyHSD(model)", format_tukey(rep)]
    if rep.checks:
        parts += ["", "Assumption checks (alpha = 0.05)"]
        for c in rep.checks:
            if c.get("p_value") is None:
                parts.append(f"  {c['method']} on {c['target']}: {c.get('note') or 'not tested'}")
                continue
            dfs = f"({c['df']:g}, {c['df2']:g})" if c.get("df") is not None else ""
            verdict = "met" if c.get("passed") else "NOT met"
            parts.append(f"  {c['method']} ({c['assumption']}) on {c['target']}: "
                         f"{c['statistic_name']}{dfs} = {c['statistic']:.4g}, p = {c['p_value']:.4g}  -> {verdict}")
    if rep.notes:
        parts += ["", "Notes"] + [f"  {n}" for n in rep.notes]
    if rep.versions:
        parts += ["", "Software: " + ", ".join(f"{k} {v}" for k, v in rep.versions.items())]
    return "\n".join(parts)


def report_for_plot(df: pd.DataFrame, spec: Dict[str, Any], *, panel: Optional[str] = None,
                    response: Optional[str] = None, data_name: Optional[str] = None) -> AnovaReport:
    """The R-style report for the model behind a plot (one facet panel, the whole grid or table)."""
    import re

    from make_my_figure_core.statistics.diagnostics import panel_subset
    from make_my_figure_core.statistics.runner import resolve_columns

    sub, stats_spec, title = panel_subset(df, spec, panel)
    mapping = (spec or {}).get("mapping", {}) or {}
    plot_type = (spec or {}).get("plot_type")
    cols = resolve_columns(plot_type, mapping, stats_spec)
    test = str(stats_spec.get("test", "auto"))
    if test in ("pearson", "spearman", "linear_regression", "logrank", "cox_ph", "chi_square", "fishers_exact"):
        raise ReportError("The summary(aov) / TukeyHSD report is for comparisons of group means; the "
                          f"chosen test ({test}) is not one.")
    if test == "factorial_anova" and stats_spec.get("covariates"):
        raise ReportError("The report covers factors only; this model has covariates (ANCOVA) - see the "
                          "Factorial analysis tab of Prepare table for its table.")
    y = response or cols.get("value_column")
    if not y:
        raise ReportError("No response (y) column is mapped.")
    factors = [f for f in (stats_spec.get("factors") or [cols.get("group_column"), cols.get("subgroup_column")])
               if f]
    interactions = stats_spec.get("interactions", "full") if test == "factorial_anova" else "full"
    name = data_name or str((spec or {}).get("input_table") or "data")
    name = re.sub(r"\W+", "_", name.rsplit(".", 1)[0]).strip("_") or "data"
    rep = anova_report(sub, y, factors, interactions=interactions, data_name=name, title=title)
    ss = int(stats_spec.get("ss_type", 2) or 2)
    if test in ("factorial_anova", "two_way_anova") and ss != 1 and not rep.balanced:
        rep.notes.append(f"The figure's ANOVA uses Type {'II' if ss == 2 else 'III'} sums of squares; with unequal "
                         "group sizes its F and P differ from this sequential table (choose Type I to match R's "
                         "summary(aov)).")
    return rep
