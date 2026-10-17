"""Model diagnostics: the four panels of R's ``plot(lm)``, for the model behind a test.

Before reporting an ANOVA (or a t-test, or a regression) the residuals are looked
at, not only tested: a Shapiro-Wilk or Levene P value says *whether* an assumption
fails, the plots say *how* - a funnel (variance growing with the mean), a curve, one
influential point. The four panels are R's defaults, computed the way R computes
them so the two can be compared point by point:

1. **Residuals vs Fitted** - residuals against fitted values, with R's smoother
   ``lowess(f = 2/3, iter = 3)``: linearity, and a spread that should not change.
2. **Normal Q-Q** - standardized residuals against normal quantiles (R's
   ``qqnorm`` positions ``ppoints``) with the line through the quartiles
   (``qqline``): normality.
3. **Scale-Location** - √|standardized residuals| against fitted values, with the
   smoother: homogeneity of variance (a rising line is variance growing with the
   mean).
4. **Residuals vs Leverage** - standardized residuals against leverage (hat
   values) with Cook's distance contours at 0.5 and 1: influential observations.
   When every leverage is the same (every balanced ANOVA) R draws **Constant
   Leverage: Residuals vs Factor Levels** instead, and so does this.

Standardized residuals are R's ``rstandard``: r / (s √(1 - h)). The three most
extreme observations are labelled with their row number in the table (1-based, as
R does), by |residual| (panel 1), |standardized residual| (2, 3) and Cook's
distance (4). Nothing here changes a value or a test result.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

ID_N = 3
COOK_LEVELS = (0.5, 1.0)
SMOOTH_COLOR = "#d62728"      # a single artist: the smoother (named colour, as R's red)


class DiagnosticsError(ValueError):
    """The model cannot be built for diagnostics."""


@dataclass
class ModelDiagnostics:
    """Per-observation quantities of one fitted linear model."""

    formula: str
    response: str
    factors: List[str]
    covariates: List[str]
    rows: np.ndarray                  # 1-based row numbers in the table given
    fitted: np.ndarray
    residuals: np.ndarray
    standardized: np.ndarray          # rstandard
    leverage: np.ndarray              # hatvalues
    cooks: np.ndarray                 # cooks.distance
    n_parameters: int
    residual_df: int
    first_factor_levels: Optional[np.ndarray] = None
    constant_leverage: bool = False
    title: str = ""
    notes: List[str] = field(default_factory=list)
    checks: List[Dict[str, Any]] = field(default_factory=list)   # Shapiro-Wilk / Levene, as reported

    @property
    def n(self) -> int:
        return int(self.fitted.size)

    def table(self) -> pd.DataFrame:
        """One row per observation - the values behind every panel."""
        out = pd.DataFrame({"row": self.rows, "fitted": self.fitted, "residual": self.residuals,
                            "standardized_residual": self.standardized,
                            "sqrt_abs_standardized_residual": np.sqrt(np.abs(self.standardized)),
                            "leverage": self.leverage, "cooks_distance": self.cooks})
        if self.first_factor_levels is not None:
            out.insert(1, self.factors[0], self.first_factor_levels)
        return out

    def summary(self) -> Dict[str, Any]:
        k = int(np.argmax(self.cooks)) if self.n else 0
        return {"formula": self.formula, "n": self.n, "parameters": self.n_parameters,
                "residual_df": self.residual_df, "constant_leverage": self.constant_leverage,
                "max_cooks_distance": float(self.cooks[k]) if self.n else None,
                "max_cooks_row": int(self.rows[k]) if self.n else None,
                "n_cooks_above_4_over_n": int(np.sum(self.cooks > 4.0 / max(self.n, 1))),
                "checks": self.checks, "notes": list(self.notes)}


# --- R's building blocks ----------------------------------------------------------------------

def lowess(x: np.ndarray, y: np.ndarray, *, f: float = 2.0 / 3.0, it: int = 3) -> Tuple[np.ndarray, np.ndarray]:
    """R's ``lowess(x, y, f = 2/3, iter = 3)`` (``delta = 0.01 * diff(range(x))``)."""
    from statsmodels.nonparametric.smoothers_lowess import lowess as _lowess

    x = np.asarray(x, float)
    y = np.asarray(y, float)
    delta = 0.01 * float(np.ptp(x)) if x.size else 0.0
    fit = _lowess(y, x, frac=f, it=it, delta=delta, return_sorted=True)
    return fit[:, 0], fit[:, 1]


def ppoints(n: int) -> np.ndarray:
    """R's ``ppoints(n)``: a = 3/8 for n <= 10, else 1/2."""
    a = 3.0 / 8.0 if n <= 10 else 0.5
    return (np.arange(1, n + 1) - a) / (n + 1 - 2 * a)


def _top(values: np.ndarray, k: int = ID_N) -> np.ndarray:
    """Indices of the k largest values, largest first (ties: first occurrence, as R's order)."""
    return np.argsort(-values, kind="stable")[:k]


# --- the model ----------------------------------------------------------------------------------

def fit_diagnostics(df: pd.DataFrame, response: str, factors: Sequence[str] = (),
                    covariates: Sequence[str] = (), *, interactions: str = "full",
                    title: str = "") -> ModelDiagnostics:
    """Fit ``response ~ factors (* or +) + covariates`` by least squares and return its diagnostics.

    Rows with a missing response, factor or covariate are left out (and counted).
    Row numbers are ``df``'s integer index + 1, so a subset (a facet panel) keeps the
    row numbers of the full table, as R's row names do.
    """
    import statsmodels.formula.api as smf

    factors, covariates = list(factors), list(covariates)
    if not factors and not covariates:
        raise DiagnosticsError("A model needs at least one factor or covariate.")
    used = [response, *factors, *covariates]
    missing = [c for c in used if c not in df.columns]
    if missing:
        raise DiagnosticsError(f"Column(s) not in the table: {', '.join(map(repr, missing))}.")
    work = df[used].copy()
    work[response] = pd.to_numeric(work[response], errors="coerce")
    for c in covariates:
        work[c] = pd.to_numeric(work[c], errors="coerce")
    # Row numbers of the full table (a facet panel is a subset that keeps its index), as R's row names.
    work["_row"] = (np.asarray(df.index, dtype=np.int64) + 1 if pd.api.types.is_integer_dtype(df.index)
                    else np.arange(1, len(df) + 1))
    n_before = len(work)
    work = work.dropna(subset=used)
    notes: List[str] = []
    if len(work) < n_before:
        notes.append(f"{n_before - len(work)} row(s) with a missing value left out.")
    fmap = {f: f"_f{i}" for i, f in enumerate(factors)}
    cmap = {c: f"_c{i}" for i, c in enumerate(covariates)}
    frame = work.rename(columns={response: "_y", **fmap, **cmap})
    for f in fmap.values():
        frame[f] = frame[f].astype(str)
    fac = [f"C({v}, Sum)" for v in fmap.values()]
    rhs = (" * " if interactions == "full" else " + ").join(fac)
    if cmap:
        rhs = " + ".join(([f"({rhs})"] if rhs else []) + list(cmap.values()))
    model = smf.ols(f"_y ~ {rhs}", data=frame).fit()
    p = int(np.linalg.matrix_rank(model.model.exog))
    if model.df_resid <= 0:
        raise DiagnosticsError(f"No residual degrees of freedom ({len(work)} observations, {p} parameters).")
    infl = model.get_influence()
    h = np.asarray(infl.hat_matrix_diag, float)
    resid = np.asarray(model.resid, float)
    s = float(np.sqrt(model.ssr / model.df_resid))
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = resid / (s * np.sqrt(1.0 - h))
        cooks = rs ** 2 * h / (p * (1.0 - h))
    if np.any(h >= 1.0 - 1e-10):
        notes.append(f"{int(np.sum(h >= 1.0 - 1e-10))} observation(s) with leverage 1 (fitted exactly); "
                     "their standardized residuals are undefined and not drawn.")
    disp = " * " if interactions == "full" else " + "
    formula = f"{response} ~ " + " + ".join([x for x in [disp.join(factors), *covariates] if x])
    lev_range = float(np.nanmax(h) - np.nanmin(h)) if h.size else 0.0
    return ModelDiagnostics(
        formula=formula, response=response, factors=factors, covariates=covariates,
        rows=work["_row"].to_numpy(int), fitted=np.asarray(model.fittedvalues, float), residuals=resid,
        standardized=rs, leverage=h, cooks=cooks, n_parameters=p, residual_df=int(model.df_resid),
        first_factor_levels=(work[factors[0]].astype(str).to_numpy() if factors else None),
        constant_leverage=bool(lev_range < 1e-10 * max(1.0, float(np.nanmax(h)) if h.size else 1.0)),
        title=title, notes=notes)


def model_for_statistics(df: pd.DataFrame, stats_spec: Dict[str, Any], *, plot_type: Optional[str] = None,
                         mapping: Optional[Dict[str, Any]] = None,
                         response: Optional[str] = None) -> ModelDiagnostics:
    """Diagnostics of the linear model behind the configured statistics.

    ANOVA / ANCOVA: its factors and covariates. Group comparisons (t-tests,
    Mann-Whitney, Kruskal-Wallis): the group means (both grouping columns on a
    grouped plot), i.e. the one- or two-way model the comparison rests on.
    Correlation / regression: ``y ~ x``. ``response`` replaces the value column
    (to compare, say, ``Growth_cm`` with ``log10(Growth_cm)``).
    """
    from make_my_figure_core.statistics.runner import resolve_columns

    mapping = mapping or {}
    cols = resolve_columns(plot_type, mapping, stats_spec or {})
    test = str((stats_spec or {}).get("test", "auto"))
    y = response or cols.get("value_column") or cols.get("y_column")
    if test in ("pearson", "spearman", "linear_regression"):
        x = cols.get("x_column")
        return fit_diagnostics(df, y, covariates=[x] if x else [], title="")
    factors = [f for f in ((stats_spec or {}).get("factors") or [cols.get("group_column"), cols.get("subgroup_column")])
               if f]
    factors = list(dict.fromkeys(factors))
    covariates = list((stats_spec or {}).get("covariates") or []) if test == "factorial_anova" else []
    interactions = (stats_spec or {}).get("interactions", "full") if test == "factorial_anova" else "full"
    if not y:
        raise DiagnosticsError("No response (y) column is mapped.")
    diag = fit_diagnostics(df, y, factors, covariates, interactions=interactions)
    try:
        from make_my_figure_core.statistics.assumptions import levene, shapiro

        groups = {k: g[y].to_numpy(float) for k, g in df.assign(**{y: pd.to_numeric(df[y], errors="coerce")})
                  .dropna(subset=[y, *factors]).groupby(factors, observed=True)} if factors else {}
        checks = [shapiro(diag.residuals, "residuals", 0.05)]
        if len(groups) >= 2:
            checks.append(levene(groups, "groups", 0.05))
        diag.checks = [c.to_dict() for c in checks]
    except Exception:  # noqa: BLE001 - the plots do not depend on the tests
        pass
    return diag


# --- the figure -------------------------------------------------------------------------------

def diagnostic_figure(diag: ModelDiagnostics, style=None, *, width_in: float = 7.0, height_in: float = 6.4):
    """The four-panel figure (matplotlib), styled with ``style`` (a StyleProfile) when given."""
    import matplotlib.pyplot as plt
    from scipy import stats as sps

    fs = float(getattr(style, "tick_pt", 8.0) or 8.0)
    lab = float(getattr(style, "axis_label_pt", 9.0) or 9.0)
    tit = float(getattr(style, "title_pt", 10.0) or 10.0)
    point = getattr(style, "text_color", "#222222") or "#222222"
    fig, axes = plt.subplots(2, 2, figsize=(width_in, height_in))
    fig._mmf_diagnostics = diag
    ok = np.isfinite(diag.standardized)
    x_f, r, rs = diag.fitted, diag.residuals, diag.standardized
    marker = dict(s=14, facecolors="none", edgecolors=point, linewidths=0.7)

    def smooth(ax, x, y):
        m = np.isfinite(x) & np.isfinite(y)
        if m.sum() >= 3 and np.ptp(x[m]) > 0:
            sx, sy = lowess(x[m], y[m])
            ax.plot(sx, sy, color=SMOOTH_COLOR, lw=1.1, zorder=4)

    def label(ax, idx, xs, ys):
        for i in idx:
            if np.isfinite(xs[i]) and np.isfinite(ys[i]):
                ax.annotate(str(diag.rows[i]), (xs[i], ys[i]), xytext=(3, 1), textcoords="offset points",
                            fontsize=fs * 0.85, color=point)

    def finish(ax, title, xl, yl):
        ax.set_title(title, fontsize=tit)
        ax.set_xlabel(xl, fontsize=lab)
        ax.set_ylabel(yl, fontsize=lab)
        ax.tick_params(labelsize=fs)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)

    # 1 Residuals vs Fitted
    ax = axes[0, 0]
    ax.scatter(x_f, r, **marker)
    ax.axhline(0, color="0.5", lw=0.8, ls=":")
    smooth(ax, x_f, r)
    label(ax, _top(np.abs(r)), x_f, r)
    finish(ax, "Residuals vs Fitted", "Fitted values", "Residuals")

    # 2 Normal Q-Q (standardized residuals)
    ax = axes[0, 1]
    rsk = rs[ok]
    order = np.argsort(rsk, kind="stable")
    theo = np.empty_like(rsk)
    theo[order] = sps.norm.ppf(ppoints(rsk.size))
    ax.scatter(theo, rsk, **marker)
    if rsk.size >= 2:
        q_y = np.quantile(rsk, [0.25, 0.75])     # R's qqline: type 7 quantiles
        q_x = sps.norm.ppf([0.25, 0.75])
        slope = (q_y[1] - q_y[0]) / (q_x[1] - q_x[0])
        icpt = q_y[0] - slope * q_x[0]
        xs = np.array([theo.min(), theo.max()])
        ax.plot(xs, icpt + slope * xs, color="0.45", lw=0.8, ls=":")
    idx_ok = np.flatnonzero(ok)
    top = _top(np.abs(rsk))
    for i in top:
        ax.annotate(str(diag.rows[idx_ok[i]]), (theo[i], rsk[i]), xytext=(3, 1), textcoords="offset points",
                    fontsize=fs * 0.85, color=point)
    finish(ax, "Normal Q-Q", "Theoretical Quantiles", "Standardized residuals")

    # 3 Scale-Location
    ax = axes[1, 0]
    sl = np.sqrt(np.abs(rs))
    ax.scatter(x_f, sl, **marker)
    smooth(ax, x_f, sl)
    label(ax, _top(np.where(ok, np.abs(rs), -np.inf)), x_f, sl)
    finish(ax, "Scale-Location", "Fitted values", r"$\sqrt{|\mathrm{Standardized\ residuals}|}$")
    ax.set_ylim(bottom=0)

    # 4 Residuals vs Leverage, or vs factor levels when the leverage is constant
    ax = axes[1, 1]
    if diag.constant_leverage and diag.first_factor_levels is not None:
        levels = list(dict.fromkeys(diag.first_factor_levels))
        # R orders the levels by their fitted value (mean of the fitted values per level)
        means = {lv: float(np.mean(x_f[diag.first_factor_levels == lv])) for lv in levels}
        levels.sort(key=lambda lv: means[lv])
        pos = np.array([levels.index(v) + 1 for v in diag.first_factor_levels], float)
        ax.scatter(pos, rs, **marker)
        ax.axhline(0, color="0.5", lw=0.8, ls=":")
        ax.set_xticks(range(1, len(levels) + 1))
        ax.set_xticklabels([str(v) for v in levels], fontsize=fs)
        label(ax, _top(np.where(ok, np.abs(rs), -np.inf)), pos, rs)
        finish(ax, "Constant Leverage:\nResiduals vs Factor Levels", f"{diag.factors[0]} :", "Standardized residuals")
    else:
        h = diag.leverage
        ax.scatter(h, rs, **marker)
        ax.axhline(0, color="0.5", lw=0.8, ls=":")
        ax.axvline(0, color="0.5", lw=0.8, ls=":")
        smooth(ax, h, np.where(ok, rs, np.nan))
        hh = np.linspace(max(1e-6, 0.01 * float(np.nanmax(h))), float(np.nanmax(h)) * 1.05, 200)
        ylim = ax.get_ylim()
        for lvl in COOK_LEVELS:
            curve = np.sqrt(lvl * diag.n_parameters * (1 - hh) / hh)
            for sgn in (1, -1):
                ax.plot(hh, sgn * curve, color=SMOOTH_COLOR, lw=0.8, ls="--")
            ax.annotate(f"{lvl:g}", (hh[-1], curve[-1]), xytext=(2, 0), textcoords="offset points",
                        fontsize=fs * 0.8, color=SMOOTH_COLOR)
        ax.set_ylim(ylim)
        ax.plot([], [], color=SMOOTH_COLOR, lw=0.8, ls="--", label="Cook's distance")
        ax.legend(loc="best", fontsize=fs * 0.85, frameon=True, framealpha=0.85, edgecolor="none")
        label(ax, _top(np.where(np.isfinite(diag.cooks), diag.cooks, -np.inf)), h, rs)
        finish(ax, "Residuals vs Leverage", "Leverage", "Standardized residuals")

    head = diag.title or diag.formula
    fig.suptitle(head, fontsize=tit, y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    return fig


# --- which model, for a plot ------------------------------------------------------------------

WHOLE_TABLE = "whole table"
WHOLE_GRID = "whole grid (facet variables as factors)"


def facet_columns_of(spec: Dict[str, Any]) -> List[str]:
    mapping = (spec or {}).get("mapping", {}) or {}
    return [c for c in (mapping.get("facet_row"), mapping.get("facet_col")) if c and c != "(none)"]


def panel_choices(df: pd.DataFrame, spec: Dict[str, Any]) -> List[str]:
    """``["whole table"]``, or the facet panels then the whole grid, for a faceted plot."""
    facets = facet_columns_of(spec)
    if not facets:
        return [WHOLE_TABLE]
    combos = df[facets].dropna().drop_duplicates()
    labels = [", ".join(f"{c} = {v}" for c, v in zip(facets, row)) for row in combos.itertuples(index=False)]
    return labels + [WHOLE_GRID]


def diagnostics_for_plot(df: pd.DataFrame, spec: Dict[str, Any], *, panel: Optional[str] = None,
                         response: Optional[str] = None) -> ModelDiagnostics:
    """Diagnostics of the model behind a plot's statistics, for one facet panel or the whole grid."""
    stats_spec = dict((spec or {}).get("statistics") or {})
    mapping = (spec or {}).get("mapping", {}) or {}
    plot_type = (spec or {}).get("plot_type")
    facets = facet_columns_of(spec)
    panel = panel or (panel_choices(df, spec)[0])
    sub = df
    title = ""
    if facets and panel == WHOLE_GRID:
        from make_my_figure_core.statistics.runner import resolve_columns

        cols = resolve_columns(plot_type, mapping, stats_spec)
        base = stats_spec.get("factors") or [cols.get("group_column"), cols.get("subgroup_column")]
        stats_spec["factors"] = list(dict.fromkeys([f for f in base if f] + facets))
        title = "whole grid"
    elif facets and panel not in (WHOLE_TABLE, WHOLE_GRID):
        mask = pd.Series(True, index=df.index)
        for part in panel.split(", "):
            col, _, val = part.partition(" = ")
            mask &= df[col].astype(str) == val
        sub = df[mask]
        title = panel
    diag = model_for_statistics(sub, stats_spec, plot_type=plot_type, mapping=mapping, response=response)
    diag.title = f"{diag.formula}" + (f"   [{title}]" if title else "")
    return diag


def summary_text(diag: ModelDiagnostics) -> str:
    """One paragraph: the model, the checks, the most influential observation."""
    s = diag.summary()
    parts = [f"<b>{s['formula']}</b> - n = {s['n']}, {s['parameters']} parameters, residual df {s['residual_df']}."]
    for c in s["checks"]:
        if c.get("p_value") is None:
            parts.append(f"{c['method']}: {c.get('note') or 'not tested'}.")
            continue
        p = "P < 0.001" if c["p_value"] < 0.001 else f"P = {c['p_value']:.3f}"
        verdict = "met" if c.get("passed") else "<span style='color:#b00'><b>NOT met</b></span>"
        parts.append(f"{c['method']} ({c['assumption']}): {c['statistic_name']} = {c['statistic']:.3g}, {p} - {verdict}.")
    if s["max_cooks_distance"] is not None:
        flag = " - above 0.5, check this observation" if s["max_cooks_distance"] > 0.5 else ""
        parts.append(f"Largest Cook's distance {s['max_cooks_distance']:.3g} (row {s['max_cooks_row']}){flag}; "
                     f"{s['n_cooks_above_4_over_n']} observation(s) above 4/n.")
    if s["constant_leverage"]:
        parts.append("Every observation has the same leverage (a balanced design), so the last panel shows "
                     "residuals by factor level, as R does.")
    parts += s["notes"]
    return " ".join(parts)
