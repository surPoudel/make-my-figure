"""Score a rendered figure for publication readiness.

`score_publication` folds in the existing advisory
`qa.publication_check.check_publication_readiness` and adds v0.6 checks:
export DPI at the intended physical size, rasterized panel resolution, text
contrast, label crowding (heatmap rows, volcano labels, generic tick density),
a missing statistical-method report when stats were used, and missing axis
labels / units. It is defensive: it never raises and always returns a valid
`PublicationScore`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Thresholds.
MIN_EXPORT_DPI_WARN = 300      # below this at target size → warn
MIN_EXPORT_DPI_FAIL = 150      # below this → fail (clearly too low to print)
MIN_PANEL_DPI = 200            # rasterized multi-panel content
HEATMAP_ROW_LABEL_WARN = 60    # y tick labels on a heatmap
VOLCANO_LABEL_WARN = 40        # text annotations on a volcano
GENERIC_TICK_WARN = 30         # tick labels on a normal axis

# Penalties applied to the 0-100 score.
_WARN_PENALTY = 12
_FAIL_PENALTY = 30

# Axis-label keywords that usually carry a unit; used only for a low-confidence
# "missing units" advisory (never a fail).
_UNIT_KEYWORDS = ("time", "concentration", "dose", "distance", "length", "mass",
                  "weight", "volume", "temperature", "voltage", "current",
                  "wavelength", "frequency", "pressure", "duration", "age")
_UNIT_MARKERS = ("(", "[", "/", "%")


@dataclass
class Check:
    """One publication-readiness finding."""

    id: str
    level: str            # 'pass' | 'warn' | 'fail'
    message: str
    suggestion: str = ""
    element: str = ""     # affected figure element (axis, legend, export, ...)


@dataclass
class PublicationScore:
    level: str            # 'pass' | 'warn' | 'fail'
    score: int            # 0-100
    checks: List[Check] = field(default_factory=list)
    summary: str = ""

    def issues(self) -> List[Check]:
        """Only the warn/fail checks (the actionable ones)."""
        return [c for c in self.checks if c.level in ("warn", "fail")]

    @property
    def passed(self) -> bool:
        return self.level == "pass"


# --- helpers ---------------------------------------------------------------

def _target_dpi(spec: Optional[Dict[str, Any]], figure) -> Optional[int]:
    """Effective export DPI at the intended physical size.

    Export writes ``output.dpi`` at ``output.width_mm``; the on-paper resolution
    is just that DPI (pixels = width_in * dpi ⇒ ppi = dpi). If no output block is
    given we cannot judge, so return None.
    """
    if not spec:
        return None
    out = spec.get("output") or {}
    dpi = out.get("dpi")
    try:
        return int(dpi) if dpi is not None else None
    except (TypeError, ValueError):
        return None


def _luminance(color) -> Optional[float]:
    try:
        from matplotlib.colors import to_rgb

        r, g, b = to_rgb(color)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    except Exception:
        return None


def _plot_type(spec: Optional[Dict[str, Any]], metadata: Dict[str, Any]) -> str:
    if spec and spec.get("plot_type"):
        return str(spec["plot_type"])
    inner = metadata.get("spec") if isinstance(metadata, dict) else None
    if isinstance(inner, dict):
        return str(inner.get("plot_type", ""))
    return ""


def _stats_were_used(spec: Optional[Dict[str, Any]], metadata: Dict[str, Any],
                     stats_report) -> bool:
    if stats_report is not None and getattr(stats_report, "results", None):
        return True
    if spec and isinstance(spec.get("statistics"), dict) and spec["statistics"].get("enabled"):
        return True
    if isinstance(metadata, dict) and metadata.get("statistics", {}):
        stats = metadata.get("statistics")
        if isinstance(stats, dict) and stats.get("enabled"):
            return True
    return False


def _has_method_report(metadata: Dict[str, Any], stats_report) -> bool:
    if stats_report is not None:
        if getattr(stats_report, "method_paragraph", "") or getattr(stats_report, "results", None):
            return True
    if isinstance(metadata, dict) and metadata.get("statistics_report"):
        return True
    return False


# --- main entry point ------------------------------------------------------

def score_publication(*, result=None, figure=None, spec: Optional[Dict[str, Any]] = None,
                      stats_report=None) -> PublicationScore:
    """Inspect a rendered figure and return a `PublicationScore`.

    Pass a ``RenderResult`` (``result=``) or a bare matplotlib ``figure=``.
    ``spec`` (the PlotSpec) and ``stats_report`` enable extra checks.
    """
    checks: List[Check] = []
    metadata: Dict[str, Any] = {}
    fig = figure
    try:
        if result is not None:
            fig = getattr(result, "figure", None) or figure
            metadata = getattr(result, "metadata", {}) or {}
            if stats_report is None:
                stats_report = getattr(result, "stats_report", None)
            if spec is None and isinstance(metadata.get("spec"), dict):
                spec = metadata["spec"]
    except Exception:
        pass

    # 1) Fold in the existing advisory figure check.
    if fig is not None:
        try:
            from make_my_figure_core.qa.publication_check import check_publication_readiness

            base = check_publication_readiness(fig)
            for w in base.warnings:
                if "missing x/y labels" in w:
                    checks.append(Check("missing_axis_labels", "warn", w,
                                        "Add x and y axis labels (with units where relevant).",
                                        "axes"))
                elif "too small" in w or "clipped" in w:
                    checks.append(Check("readability", "warn", w,
                                        "Enlarge the figure or increase font sizes.", "text"))
                elif "Legend may overlap" in w:
                    checks.append(Check("legend_overlap", "warn", w,
                                        "Move the legend outside the axes.", "legend"))
                elif "dense" in w:
                    checks.append(Check("tick_density", "warn", w,
                                        "Rotate tick labels or widen the figure.", "xticks"))
                else:
                    checks.append(Check("readability", "warn", w, "", "figure"))
        except Exception:
            pass

    # 2) Export DPI at the target physical size.
    dpi = _target_dpi(spec, fig)
    if dpi is not None:
        if dpi < MIN_EXPORT_DPI_FAIL:
            checks.append(Check("export_dpi", "fail",
                                f"Export DPI is {dpi}, far below print quality.",
                                "Increase export DPI to at least 300 (600 for line art).",
                                "export"))
        elif dpi < MIN_EXPORT_DPI_WARN:
            checks.append(Check("export_dpi", "warn",
                                f"Export DPI is {dpi}; many journals require ≥300 at final size.",
                                "Increase export DPI to at least 300.", "export"))

    # 3) Rasterized multi-panel content resolution.
    panel_dpi = None
    if isinstance(metadata, dict):
        panel_dpi = metadata.get("panel_dpi")
    if panel_dpi is None and spec:
        panel_dpi = (spec.get("layout") or {}).get("panel_dpi")
    try:
        if panel_dpi is not None and int(panel_dpi) < MIN_PANEL_DPI:
            checks.append(Check("panel_resolution", "warn",
                                f"Multi-panel content is rasterized at {panel_dpi} DPI.",
                                f"Raise panel DPI to ≥{MIN_PANEL_DPI} for crisp panels.",
                                "panels"))
    except (TypeError, ValueError):
        pass

    ptype = _plot_type(spec, metadata)

    # 4) Contrast + 5) label crowding (need the figure).
    if fig is not None:
        try:
            _contrast_and_crowding_checks(fig, ptype, checks)
        except Exception:
            pass

    # 6) Missing statistical method report when stats were used.
    if _stats_were_used(spec, metadata, stats_report) and not _has_method_report(metadata, stats_report):
        checks.append(Check("missing_method_report", "warn",
                            "Statistics are shown but no method report was recorded.",
                            "Include the statistical method sentence with the figure.",
                            "statistics"))

    # 7) Missing units (low-confidence advisory).
    if fig is not None:
        try:
            _units_advisory(fig, checks)
        except Exception:
            pass

    return _finalize(checks)


def _contrast_and_crowding_checks(fig, ptype: str, checks: List[Check]) -> None:
    fig_lum = _luminance(fig.get_facecolor())
    flagged_contrast = False
    max_yticks = 0
    max_xticks = 0
    total_texts = 0
    for ax in fig.axes:
        if getattr(ax, "_colorbar", None):
            continue
        yt = [t for t in ax.get_yticklabels() if t.get_text().strip()]
        xt = [t for t in ax.get_xticklabels() if t.get_text().strip()]
        max_yticks = max(max_yticks, len(yt))
        max_xticks = max(max_xticks, len(xt))
        total_texts += len([t for t in ax.texts if t.get_text().strip()])
        # Contrast: axis-label text vs figure/axes background.
        if not flagged_contrast and fig_lum is not None:
            ax_lum = _luminance(ax.get_facecolor())
            bg_lum = ax_lum if ax_lum is not None else fig_lum
            for lab in (ax.xaxis.label, ax.yaxis.label):
                if lab.get_text().strip():
                    tl = _luminance(lab.get_color())
                    if tl is not None and abs(tl - bg_lum) < 0.25:
                        checks.append(Check("low_contrast", "warn",
                                            "Text and background have low contrast.",
                                            "Use dark text on a light background.", "text"))
                        flagged_contrast = True
                        break

    if ptype == "heatmap_clustered_matrix" and max_yticks > HEATMAP_ROW_LABEL_WARN:
        checks.append(Check("heatmap_row_density", "warn",
                            f"Heatmap shows {max_yticks} row labels; they will be unreadable.",
                            "Show top-N rows or hide row labels.", "yticks"))
    if ptype == "volcano_plot" and total_texts > VOLCANO_LABEL_WARN:
        checks.append(Check("label_crowding", "warn",
                            f"Volcano has {total_texts} gene labels; they will overlap.",
                            "Label only the top hits.", "annotations"))
    if ptype not in ("heatmap_clustered_matrix", "oncoprint_mutation_heatmap") and \
            max(max_xticks, max_yticks) > GENERIC_TICK_WARN:
        checks.append(Check("tick_density", "warn",
                            f"{max(max_xticks, max_yticks)} tick labels may crowd the axis.",
                            "Reduce categories, bin the data, or widen the figure.", "ticks"))


def _units_advisory(fig, checks: List[Check]) -> None:
    for ax in fig.axes:
        if getattr(ax, "_colorbar", None):
            continue
        for lab in (ax.xaxis.label, ax.yaxis.label):
            text = lab.get_text().strip().lower()
            if not text:
                continue
            if any(k in text for k in _UNIT_KEYWORDS) and not any(m in text for m in _UNIT_MARKERS):
                checks.append(Check("missing_units", "warn",
                                    f"Axis label '{lab.get_text().strip()}' may be missing units.",
                                    "Add units, e.g. 'Time (h)'.", "axes"))
                return  # one advisory is enough


def _finalize(checks: List[Check]) -> PublicationScore:
    warns = [c for c in checks if c.level == "warn"]
    fails = [c for c in checks if c.level == "fail"]
    score = max(0, 100 - _WARN_PENALTY * len(warns) - _FAIL_PENALTY * len(fails))
    if fails:
        level = "fail"
    elif warns:
        level = "warn"
    else:
        level = "pass"
    if level == "pass":
        summary = "Publication QC: passed (100)"
        checks = checks or [Check("ok", "pass", "No publication issues detected.", "", "figure")]
    else:
        summary = (f"Publication QC: {level} ({score}) — "
                   + "; ".join(c.message for c in (fails + warns)[:4]))
    return PublicationScore(level=level, score=score, checks=checks, summary=summary)
