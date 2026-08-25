"""Kaplan-Meier / lifespan survival curves (per group), implemented without lifelines.

Two input forms are supported, because survival data reaches a figure in two quite different
shapes and confusing them silently produces a meaningless curve:

``subject_level`` (default)
    One row per subject: a time column and an event indicator (1 = event, 0 = censored), with an
    optional group column. The Kaplan-Meier estimator is computed here.

``precomputed``
    One row per time point and one column per group, each holding the survival function S(t)
    itself - the shape you get from a published or digitised lifespan curve. Nothing is estimated;
    the supplied curve is drawn as a step function. A log-rank test cannot be computed from this
    form (it needs per-subject event times or at-risk counts), and asking for one is refused
    explicitly rather than answered with a number that would not mean anything.

The y axis can be a fraction (0-1, the default) or a percentage (0-100), because lifespan figures
are conventionally drawn as "% survival".
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from make_my_figure_core.plots.base import (
    RenderError,
    apply_axis_overrides,
    RenderResult,
    base_metadata,
    coerce_numeric,
    figure_size,
    get_mapping,
    require_columns,
    style_axes,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "kaplan_meier_survival_curve"

INPUT_FORMS = ("subject_level", "precomputed")
Y_SCALES = ("fraction", "percent")

# Y-axis label used when the spec does not set one, per scale.
_DEFAULT_Y_LABEL = {"fraction": "Survival probability", "percent": "% survival"}


def _km_estimate(times: np.ndarray, events: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Return step coordinates (t, S(t)) for the Kaplan-Meier estimator.

    ``events`` is 1 for an event and 0 for censored. Curve starts at (0, 1).
    """
    order = np.argsort(times)
    times, events = times[order], events[order]
    n = len(times)
    unique_t = np.unique(times)
    surv = 1.0
    ts, ss = [0.0], [1.0]
    at_risk = n
    for t in unique_t:
        d = int(np.sum((times == t) & (events == 1)))  # events at t
        c = int(np.sum(times == t))                     # total leaving risk set at t
        if at_risk > 0 and d > 0:
            surv *= (1.0 - d / at_risk)
        ts.append(float(t))
        ss.append(surv)
        at_risk -= c
    return np.asarray(ts), np.asarray(ss)


def _resolve_event_indicator(values: np.ndarray, event_col: str) -> Tuple[np.ndarray, List[str]]:
    """Coerce an event column to a strict 0/1 indicator, or explain why it cannot be one.

    An event column must be binary. Three cases are distinguished rather than lumped together,
    because they need different answers:

    * already 0/1 (or a single one of them) - used as is;
    * exactly two distinct values, e.g. the 1/2 coding common in R, or 0/2 - the larger value is
      taken as the event and the choice is reported, since guessing silently is what causes
      unnoticed errors;
    * more than two distinct values - this is not an indicator at all. Rather than counting only
      the rows that happen to equal 1 and drawing a curve that means nothing, this raises. When the
      values look like a survival function already, the message says so and names the input form
      that plots it.
    """
    notes: List[str] = []
    finite = values[~np.isnan(values)]
    if finite.size == 0:
        raise RenderError(
            f"{PLOT_TYPE}: event column '{event_col}' has no numeric values. It must be 1 for an "
            f"event and 0 for a censored observation."
        )

    uniq = np.unique(finite)
    if np.all(np.isin(uniq, (0.0, 1.0))):
        return (values == 1.0).astype(float), notes

    if uniq.size == 2:
        lo, hi = float(uniq[0]), float(uniq[1])
        notes.append(
            f"Event column '{event_col}' is coded {lo:g}/{hi:g} rather than 0/1; {hi:g} was taken "
            f"as the event and {lo:g} as censored. Recode to 0/1 to remove the ambiguity."
        )
        return (values == hi).astype(float), notes

    # More than two levels: not an event indicator.
    monotone_non_increasing = bool(
        finite.size > 2 and np.all(np.diff(finite) <= 1e-12)
    )
    within_unit = bool(np.nanmin(finite) >= 0.0 and np.nanmax(finite) <= 1.0)
    if within_unit and monotone_non_increasing:
        raise RenderError(
            f"{PLOT_TYPE}: event column '{event_col}' holds {uniq.size} distinct values between 0 "
            f"and 1 that never increase, so it looks like an already-computed survival curve S(t) "
            f"rather than an event indicator. Set mapping 'input_form' to 'precomputed' and map "
            f"this column with 'survival' (or several such columns with 'survival_columns', one per "
            f"group) to plot it directly. An event indicator must be 1 for an event and 0 for a "
            f"censored observation."
        )
    if within_unit:
        raise RenderError(
            f"{PLOT_TYPE}: event column '{event_col}' holds {uniq.size} distinct values between 0 "
            f"and 1, so it cannot be an event indicator (which must be 0 or 1). If these are "
            f"survival probabilities, set mapping 'input_form' to 'precomputed' and map the column "
            f"with 'survival'."
        )
    raise RenderError(
        f"{PLOT_TYPE}: event column '{event_col}' has {uniq.size} distinct values "
        f"({', '.join(f'{v:g}' for v in uniq[:6])}{', ...' if uniq.size > 6 else ''}), so it is not "
        f"an event indicator. Map a column that is 1 for an event and 0 for a censored observation."
    )


def _resolve_survival_columns(spec: Dict[str, Any], df: pd.DataFrame) -> List[str]:
    """Columns holding S(t) in precomputed mode, one per group."""
    cols = get_mapping(spec, "survival_columns", None)
    if isinstance(cols, str):
        cols = [cols]
    if not cols:
        single = get_mapping(spec, "survival", None)
        if single:
            cols = [single]
    if not cols:
        raise RenderError(
            f"{PLOT_TYPE}: input_form='precomputed' needs the column(s) holding the survival "
            f"function. Map one with 'survival', or several (one per group) with "
            f"'survival_columns'. Available columns: {list(df.columns)}"
        )
    cols = [str(c) for c in cols]
    require_columns(df, cols, context=PLOT_TYPE)
    return cols


def _group_labels(spec: Dict[str, Any], keys: Sequence[Any]) -> List[str]:
    """Curve labels, so the display name never has to be the spreadsheet header.

    A workbook exported from another tool often repeats one header for every group, which pandas
    then disambiguates to ``event``, ``event.1``, ``event.2``. Those are accurate but useless on a
    legend, so ``group_labels`` lets the caller name the curves without renaming the data.
    """
    labels = get_mapping(spec, "group_labels", None)
    if isinstance(labels, str):
        labels = [labels]
    if not labels:
        return [str(k) for k in keys]
    out = [str(x) for x in labels][: len(keys)]
    if len(out) < len(keys):
        out += [str(k) for k in keys[len(out):]]
    return out


def _y_scale(spec: Dict[str, Any]) -> str:
    scale = str(get_mapping(spec, "y_scale", "fraction") or "fraction").lower()
    if scale in ("percent", "percentage", "%"):
        return "percent"
    if scale in ("fraction", "proportion", "probability"):
        return "fraction"
    raise RenderError(
        f"{PLOT_TYPE}: y_scale must be one of {Y_SCALES}, got {scale!r}."
    )


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    input_form = str(get_mapping(spec, "input_form", "subject_level") or "subject_level").lower()
    if input_form not in INPUT_FORMS:
        raise RenderError(
            f"{PLOT_TYPE}: input_form must be one of {INPUT_FORMS}, got {input_form!r}."
        )
    scale = _y_scale(spec)
    factor = 100.0 if scale == "percent" else 1.0

    time_col = get_mapping(spec, "time", "time_months")
    warnings: List[str] = []
    summaries: Dict[str, Any] = {}
    used: List[str] = [time_col]

    work = df.copy()
    require_columns(work, [time_col], context=PLOT_TYPE)
    work[time_col] = coerce_numeric(work, time_col, context=PLOT_TYPE)

    # ---- assemble the curves to draw, per input form -------------------------------------
    curves: List[Tuple[str, np.ndarray, np.ndarray]] = []   # (label, t, S)
    censor_marks: List[Tuple[str, np.ndarray, np.ndarray]] = []
    group_col = None
    event_col = None

    if input_form == "precomputed":
        surv_cols = _resolve_survival_columns(spec, work)
        used += surv_cols
        labels = _group_labels(spec, surv_cols)
        for col, label in zip(surv_cols, labels):
            s = pd.to_numeric(work[col], errors="coerce").to_numpy(dtype=float)
            t = work[time_col].to_numpy(dtype=float)
            mask = ~(np.isnan(t) | np.isnan(s))
            t, s = t[mask], s[mask]
            if t.size == 0:
                warnings.append(f"Curve '{label}' has no complete (time, survival) rows.")
                continue
            order = np.argsort(t, kind="stable")
            t, s = t[order], s[order]
            if s.max() > 1.0 + 1e-9:
                warnings.append(
                    f"Curve '{label}' has values above 1 ({s.max():g}); read as already being on a "
                    f"0-100 scale and plotted as supplied."
                )
                curves.append((label, t, s if scale == "percent" else s / 100.0))
            else:
                curves.append((label, t, s * factor))
            if np.any(np.diff(s) > 1e-9):
                warnings.append(
                    f"Curve '{label}' increases at one or more time points; a survival function "
                    f"should never rise. Check the column and the row order."
                )
            summaries[label] = {
                "n_time_points": int(t.size),
                "source_column": col,
                "survival_start": float(s[0]),
                "survival_end": float(s[-1]),
            }
    else:
        event_col = get_mapping(spec, "event", "event")
        require_columns(work, [event_col], context=PLOT_TYPE)
        used.append(event_col)
        work[event_col] = coerce_numeric(work, event_col, context=PLOT_TYPE)
        indicator, notes = _resolve_event_indicator(
            work[event_col].to_numpy(dtype=float), str(event_col)
        )
        warnings.extend(notes)
        # Write the resolved 0/1 indicator back into the mapped column. ``work`` is already a copy,
        # so the caller's frame is untouched, and the statistics runner reads this same column by
        # name - if the indicator lived somewhere else, a 1/2-coded input would draw one curve and
        # test another.
        work[event_col] = indicator

        group_col = get_mapping(spec, "group", None)
        if group_col and group_col in work.columns:
            keys = list(dict.fromkeys(work[group_col].tolist()))
            used.append(group_col)
        else:
            keys = ["all"]
            group_col = None
        labels = _group_labels(spec, keys)

        for key, label in zip(keys, labels):
            sub = work if group_col is None else work[work[group_col] == key]
            t = sub[time_col].to_numpy(dtype=float)
            e = sub[event_col].to_numpy(dtype=float)
            mask = ~(np.isnan(t) | np.isnan(e))
            t, e = t[mask], e[mask]
            if t.size == 0:
                warnings.append(f"Group '{label}' has no valid rows.")
                continue
            ts, ss = _km_estimate(t, e)
            curves.append((label, ts, ss * factor))
            cens_t = t[e == 0]
            if cens_t.size:
                cens_s = np.array(
                    [ss[np.searchsorted(ts, ct, side="right") - 1] for ct in cens_t]
                ) * factor
                censor_marks.append((label, cens_t, cens_s))
            summaries[label] = {"n": int(t.size), "events": int(np.sum(e == 1))}

    show_legend = len(curves) > 1 or (group_col is not None)

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.8))
        # A survival function is a step function, so "step" is the default and the only correct
        # choice for an estimated curve. "line" exists for the precomputed form only, where the
        # curve was digitised from an existing figure at coarse resolution and joining the points
        # reproduces how that figure was drawn; it interpolates between supplied points.
        curve_style = str(get_mapping(spec, "curve_style", "step") or "step").lower()
        if curve_style not in ("step", "line"):
            raise RenderError(
                f"{PLOT_TYPE}: curve_style must be 'step' or 'line', got {curve_style!r}."
            )
        if curve_style == "line" and input_form != "precomputed":
            warnings.append(
                "curve_style='line' joins successive estimates with straight segments, which "
                "misrepresents an estimated Kaplan-Meier curve; 'step' was used instead."
            )
            curve_style = "step"
        for ci, (label, t, s) in enumerate(curves):
            col = style.color_for(ci)
            draw = ax.step if curve_style == "step" else ax.plot
            kw = {"where": "post"} if curve_style == "step" else {}
            draw(t, s, color=col, lw=style.line_width_pt,
                 label=label if show_legend else None, **kw)
        for ci, (label, ct, cs) in enumerate(censor_marks):
            col = style.color_for([c[0] for c in curves].index(label))
            ax.plot(ct, cs, "|", color=col, markersize=5,
                    markeredgewidth=style.line_width_pt)

        top = 100.0 if scale == "percent" else 1.0
        ax.set_ylim(0, top * 1.02)

        ref = get_mapping(spec, "reference_line", None)
        if ref is not None and ref != "":
            try:
                ref_v = float(ref)
            except (TypeError, ValueError):
                raise RenderError(
                    f"{PLOT_TYPE}: reference_line must be a number in the units of the y axis "
                    f"({'0-100' if scale == 'percent' else '0-1'}), got {ref!r}."
                )
            ax.axhline(ref_v, ls=":", lw=max(0.6, style.line_width_pt * 0.7),
                       color="#555555", zorder=1)

        layout = spec.get("layout", {}) or {}
        ax.set_xlabel(layout.get("x_label", time_col))
        ax.set_ylabel(layout.get("y_label", _DEFAULT_Y_LABEL[scale]))
        title = layout.get("title")
        if title:
            ax.set_title(title)
        if show_legend:
            legend_title = str(group_col) if group_col is not None else None
            ax.legend(title=legend_title, frameon=False, loc="best")
        style_axes(ax, style)
        # Axis frame overrides, applied after the cosmetics so they are not overwritten.
        # "ends_and_midpoint" means 0/50/100 on a percent axis and 0/0.5/1 on a fraction one,
        # which is how survival curves are usually labelled.
        axis_applied = apply_axis_overrides(
            ax, spec, tick_values=[0.0, top / 2.0, top])

        from make_my_figure_core.plots.stats_integration import run_and_annotate

        stats_report = None
        if input_form == "precomputed":
            if (spec.get("statistics") or {}).get("enabled"):
                warnings.append(
                    "Statistics were requested but cannot be computed from a precomputed survival "
                    "curve: a log-rank test needs per-subject event times or the number at risk at "
                    "each time, and neither can be recovered from the curve alone. Supply "
                    "subject-level rows (time, event, group) to obtain a log-rank test."
                )
        elif group_col is not None:
            stats_report = run_and_annotate(spec, work, style, PLOT_TYPE, ax=ax, mode="survival")
        fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=[c for c in used if c])
    meta["groups"] = summaries
    meta["survival_input_form"] = input_form
    meta["y_scale"] = scale
    meta["n_curves"] = len(curves)
    if axis_applied:
        meta["axis_overrides"] = axis_applied
    if stats_report is not None:
        meta["statistics_report"] = stats_report.to_dict()
    return RenderResult(figure=fig, metadata=meta, warnings=warnings,
                        stats_report=stats_report)
