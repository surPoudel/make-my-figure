"""Shared machinery for the two bar renderers (``barplot`` and ``grouped_barplot``).

A publication bar chart has to say what the bar is (mean or median), what the whisker is (SEM, SD,
a confidence interval, the IQR), and - increasingly a reviewer requirement - show the individual
observations behind the summary. Both bar renderers read the same options, compute the same
summaries and record the same metadata, so those decisions live here rather than twice.

Backward compatibility: every default reproduces the pre-existing render (mean, SEM, no points,
width 0.68 / cluster 0.8, filled bars, caps from the profile, vertical). ``ci95`` keeps its
historical normal-approximation half-width (1.96 x SEM) because changing it would silently alter
existing figures; the t-based interval is the new ``ci95_t`` choice.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from make_my_figure_core.plots.base import RenderError, get_mapping, summarize_error
from make_my_figure_core.plots.observations import ObservationStyle

SUMMARIES = ("mean", "median")
ERRORS = ("sem", "sd", "ci95", "ci95_t", "iqr", "none")
FILLS = ("filled", "outline")
SHOW_N = ("none", "below", "above", "legend")
ORIENTATIONS = ("vertical", "horizontal")

ERROR_DEFINITIONS = {
    "sem": "standard error of the mean (SD / sqrt(n), SD with ddof=1)",
    "sd": "standard deviation (ddof=1)",
    "ci95": "95% confidence interval of the mean, normal approximation (1.96 x SEM)",
    "ci95_t": "95% confidence interval of the mean, t-based (scipy.stats.t, df = n - 1)",
    "iqr": "interquartile range (25th to 75th percentile) around the median",
    "none": "no error bars",
}

# Reference width for scaling the observation jitter: the historical single-bar width.
_REFERENCE_BAR_WIDTH = 0.68


@dataclass
class BarOptions:
    """Everything a bar renderer reads from ``spec['mapping']`` apart from its column roles."""

    summary: str = "mean"
    error: str = "sem"
    error_requested: str = "sem"
    points: bool = False
    obs: ObservationStyle = None  # type: ignore[assignment]
    bar_width: float = _REFERENCE_BAR_WIDTH
    bar_fill: str = "filled"
    bar_edge_width: float = 0.0          # 0 -> style.bar_edge_width
    bar_alpha: float = 1.0
    error_cap: bool = True
    show_n: str = "none"
    orientation: str = "vertical"
    warnings: List[str] = None  # type: ignore[assignment]

    @classmethod
    def from_spec(cls, spec: Dict[str, Any], *, default_width: float, context: str) -> "BarOptions":
        mapping = spec.get("mapping", {}) or {}
        warnings: List[str] = []

        summary = str(get_mapping(spec, "summary", "mean") or "mean").lower()
        if summary not in SUMMARIES:
            raise RenderError(f"{context}: summary must be one of {SUMMARIES}, got {summary!r}.")
        requested = str(get_mapping(spec, "error", "sem") or "sem").lower()
        error = requested
        if error in ("std",):
            error = "sd"
        if error in ("ci", "ci_95"):
            error = "ci95"
        if error not in ERRORS:
            warnings.append(f"Unknown error choice {requested!r}; SEM was used. "
                            f"Choose one of {', '.join(ERRORS)}.")
            error = "sem"
        # The whisker has to describe the bar: SEM/SD/CI are statements about a mean, the IQR about a
        # median. A mismatch is corrected and reported rather than drawn as if it were meaningful.
        if summary == "median" and error in ("sem", "sd", "ci95", "ci95_t"):
            warnings.append(f"Error bars '{requested}' describe a mean; with summary=median the "
                            "error bars are drawn as the interquartile range (iqr) instead. "
                            "Choose error='none' to draw median bars without whiskers.")
            error = "iqr"
        elif summary == "mean" and error == "iqr":
            warnings.append("The interquartile range describes a median; with summary=mean the "
                            "error bars are drawn as the standard deviation (sd) instead. Choose "
                            "summary=median for IQR whiskers.")
            error = "sd"

        def _num(key: str, default: float, lo: float, hi: float) -> float:
            raw = mapping.get(key)
            if raw in (None, "", "auto"):
                return float(default)
            try:
                val = float(raw)
            except (TypeError, ValueError):
                raise RenderError(f"{context}: {key} must be a number, got {raw!r}.")
            if not (lo <= val <= hi):
                raise RenderError(f"{context}: {key} must be between {lo:g} and {hi:g}, got {val:g}.")
            return val

        fill = str(get_mapping(spec, "bar_fill", "filled") or "filled").lower()
        if fill not in FILLS:
            raise RenderError(f"{context}: bar_fill must be one of {FILLS}, got {fill!r}.")
        show_n = str(get_mapping(spec, "show_n", "none") or "none").lower()
        if show_n not in SHOW_N:
            raise RenderError(f"{context}: show_n must be one of {SHOW_N}, got {show_n!r}.")
        orientation = str(get_mapping(spec, "orientation", "vertical") or "vertical").lower()
        if orientation not in ORIENTATIONS:
            raise RenderError(f"{context}: orientation must be one of {ORIENTATIONS}, got {orientation!r}.")

        return cls(
            summary=summary,
            error=error,
            error_requested=requested,
            points=_as_bool(mapping.get("points", False)),
            obs=ObservationStyle.from_mapping(mapping),
            bar_width=_num("bar_width", default_width, 0.3, 0.9),
            bar_fill=fill,
            bar_edge_width=_num("bar_edge_width", 0.0, 0.0, 3.0),
            bar_alpha=_num("bar_alpha", 1.0, 0.1, 1.0),
            error_cap=_as_bool(mapping.get("error_cap", True)),
            show_n=show_n,
            orientation=orientation,
            warnings=warnings,
        )

    @property
    def horizontal(self) -> bool:
        return self.orientation == "horizontal"

    def value_label_suffix(self) -> str:
        """Text appended to the value-axis label; the historical wording for historical choices."""
        if self.error == "none":
            return ""
        if self.summary == "median":
            return "(median, IQR)"
        if self.error == "ci95_t":
            return "(mean ± 95% CI, t)"
        return f"(mean ± {self.error.upper()})"

    def observation_style_for_width(self, bar_width: float) -> ObservationStyle:
        """Jitter scaled so points stay inside a bar narrower than the reference width."""
        factor = min(1.0, float(bar_width) / _REFERENCE_BAR_WIDTH)
        return replace(self.obs, jitter_width=self.obs.jitter_width * factor)


def _as_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


# --- summaries ---------------------------------------------------------------

@dataclass
class GroupSummary:
    center: float
    err_lo: float      # distance from the centre down to the lower whisker end (>= 0)
    err_hi: float      # distance from the centre up to the upper whisker end (>= 0)
    n: int
    values: np.ndarray

    @property
    def top(self) -> float:
        return self.center + self.err_hi if np.isfinite(self.center) else float("nan")

    @property
    def bottom(self) -> float:
        return self.center - self.err_lo if np.isfinite(self.center) else float("nan")


def summarize_group(values: Sequence[float], summary: str, error: str) -> GroupSummary:
    """Centre and whisker half-lengths for one group under an explicit ``summary`` / ``error``."""
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    n = int(arr.size)
    if n == 0:
        return GroupSummary(float("nan"), 0.0, 0.0, 0, arr)
    if summary == "median":
        med = float(np.median(arr))
        if error == "iqr" and n >= 2:
            q25, q75 = (float(q) for q in np.percentile(arr, [25, 75]))
            return GroupSummary(med, max(med - q25, 0.0), max(q75 - med, 0.0), n, arr)
        return GroupSummary(med, 0.0, 0.0, n, arr)
    if error == "ci95_t":
        mean = float(np.mean(arr))
        if n < 2:
            return GroupSummary(mean, 0.0, 0.0, n, arr)
        from scipy import stats as _st

        sem = float(np.std(arr, ddof=1)) / np.sqrt(n)
        half = float(_st.t.ppf(0.975, n - 1)) * sem
        return GroupSummary(mean, half, half, n, arr)
    # sem / sd / ci95 / none: the historical computation, unchanged.
    center, err = summarize_error(arr, error)
    err = float(err) if err == err else 0.0
    return GroupSummary(float(center), err, err, n, arr)


# --- drawing -----------------------------------------------------------------

def draw_bars(ax, positions: Sequence[float], summaries: Sequence[GroupSummary], colors: Sequence[str],
              *, opts: BarOptions, style, width: float, label: Optional[str] = None) -> None:
    """Draw one set of bars (with whiskers) honouring the bar appearance options."""
    centers = [s.center for s in summaries]
    err = None
    if opts.error != "none":
        err = np.vstack([[s.err_lo for s in summaries], [s.err_hi for s in summaries]])
    edge_lw = opts.bar_edge_width if opts.bar_edge_width > 0 else style.bar_edge_width
    colors = list(colors)
    if opts.bar_fill == "outline":
        face: Any = ["white"] * len(colors)
        edge: Any = colors
    else:
        face, edge = colors, "#222222"
    kw: Dict[str, Any] = dict(
        color=face,
        edgecolor=edge,
        linewidth=edge_lw,
        capsize=style.errorbar_capsize if opts.error_cap else 0.0,
        error_kw={"elinewidth": style.errorbar_line_width,
                  "capthick": style.errorbar_line_width},
    )
    if label is not None:
        kw["label"] = label
    if opts.bar_alpha < 1.0:
        kw["alpha"] = opts.bar_alpha
    if opts.horizontal:
        ax.barh(list(positions), centers, height=width, xerr=err, **kw)
    else:
        ax.bar(list(positions), centers, width=width, yerr=err, **kw)


def value_extent(summaries: Sequence[GroupSummary], obs_extents: Sequence[Tuple[float, float]]
                 ) -> Tuple[float, float]:
    """``(lowest, highest)`` drawn value across whisker ends and observations (NaN-safe)."""
    lows = [s.bottom for s in summaries] + [lo for lo, _ in obs_extents]
    highs = [s.top for s in summaries] + [hi for _, hi in obs_extents]
    lows = [v for v in lows if v == v]
    highs = [v for v in highs if v == v]
    if not lows or not highs:
        return (float("nan"), float("nan"))
    return (float(min(lows)), float(max(highs)))


def apply_baseline_policy(ax, *, opts: BarOptions, low: float, high: float) -> bool:
    """Bars keep a zero baseline when nothing drawn is negative. Returns whether it was applied.

    Also guarantees the value axis reaches every whisker end and observation, so a point drawn
    with ``clip_on=False`` is never left outside the frame.
    """
    lim_get = ax.get_xlim if opts.horizontal else ax.get_ylim
    lim_set = ax.set_xlim if opts.horizontal else ax.set_ylim
    lo, hi = lim_get()
    if high == high and hi < high:
        hi = high + 0.08 * max(high - min(lo, 0.0), 1e-12)
    if low == low and lo > low:
        lo = low - 0.08 * max(hi - low, 1e-12)
    baseline = bool(low == low and low >= 0.0)
    if baseline:
        lo = 0.0
    lim_set(lo, hi)
    return baseline


def n_legend_labels(names: Sequence[Any], counts: Sequence[Sequence[int]]) -> List[str]:
    """``"Control (n = 6)"`` or, for several cells per legend entry, ``"Drug (n = 6, 5, 6)"``."""
    out = []
    for name, ns in zip(names, counts):
        ns = list(ns)
        text = ", ".join(str(int(k)) for k in ns)
        out.append(f"{name} (n = {text})")
    return out


def fold_n_into_labels(labels: Sequence[str], counts: Sequence[int]) -> List[str]:
    """``show_n="below"``: the n goes under the category name, so it can never collide with it."""
    return [f"{lab}\n(n = {int(n)})" for lab, n in zip(labels, counts)]


def annotate_statistics(spec: Dict[str, Any], work, style, plot_type: str, ax, *, positions: Dict[Any, float],
                        tops: Dict[Any, float], opts: BarOptions, warnings: List[str]):
    """Run the configured statistics and draw them, honouring the bar orientation.

    Horizontal brackets go through the shared bridge when it supports an ``orientation``; if it
    does not (older bridge), the pairwise results are listed in a corner text panel instead and a
    warning says so, so a comparison is never silently dropped.
    """
    import inspect

    from make_my_figure_core.plots import stats_overlay
    from make_my_figure_core.plots.stats_integration import run_and_annotate
    from make_my_figure_core.statistics.annotations import build_pairwise_annotations

    if not opts.horizontal:
        return run_and_annotate(spec, work, style, plot_type, ax=ax, positions=positions, tops=tops,
                                mode="bracket")
    if "orientation" in inspect.signature(run_and_annotate).parameters:
        return run_and_annotate(spec, work, style, plot_type, ax=ax, positions=positions, tops=tops,
                                mode="bracket", orientation="horizontal")
    stats_cfg = spec.get("statistics") or {}
    report = run_and_annotate(spec, work, style, plot_type, ax=None)
    if report is None:
        return None
    ann_cfg = stats_cfg.get("annotation", {}) or {}
    items = build_pairwise_annotations(report.results, ann_cfg)
    lines = [f"{it.group_a} vs {it.group_b}: {it.text}" for it in items]
    if lines and stats_cfg.get("annotate", True):
        stats_overlay.annotate_corner(ax, lines, style=style, loc="upper right")
    warnings.append("Significance brackets could not be drawn for horizontal bars; the pairwise "
                    "results are listed in a corner text panel instead.")
    return report


def record_metadata(meta: Dict[str, Any], opts: BarOptions, *, group_n: Dict[str, int],
                    baseline_zero: bool, n_observations_drawn: int,
                    axis_overrides: Optional[Dict[str, Any]] = None) -> None:
    """Write the explicit summary/error record every bar figure carries."""
    meta["summary"] = opts.summary
    meta["error"] = opts.error
    meta["error_method"] = opts.error                     # historical key, kept
    meta["error_definition"] = ERROR_DEFINITIONS[opts.error]
    if opts.error_requested != opts.error:
        meta["error_requested"] = opts.error_requested
    meta["group_n"] = dict(group_n)
    meta["baseline_zero"] = bool(baseline_zero)
    meta["orientation"] = opts.orientation
    meta["points"] = bool(opts.points)
    meta["n_observations_drawn"] = int(n_observations_drawn)
    meta["bar_fill"] = opts.bar_fill
    meta["show_n"] = opts.show_n
    if axis_overrides:
        meta["axis_overrides"] = dict(axis_overrides)
