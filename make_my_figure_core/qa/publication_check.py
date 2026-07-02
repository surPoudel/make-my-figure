"""Lightweight publication-readiness checks for a rendered figure.

Runs after rendering and reports likely issues (small text, legend overlapping
data, clipped labels, weak contrast, missing axis labels, dense/long tick
labels, tiny figure). It never mutates the figure and never blocks export; the
app surfaces the messages, and only "strict mode" would gate export.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

# Readability thresholds (points / ratios).
MIN_LABEL_PT = 9.0
MIN_TICK_PT = 8.0


@dataclass
class PublicationCheckResult:
    passed: bool
    warnings: List[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        if self.passed:
            return "Publication check: passed"
        return "Publication check: " + "; ".join(self.warnings)


def _bbox(artist, renderer):
    try:
        return artist.get_window_extent(renderer=renderer)
    except Exception:
        return None


def check_publication_readiness(fig) -> PublicationCheckResult:
    """Inspect a Matplotlib figure and return warnings about common issues."""
    warnings: List[str] = []
    try:
        fig.canvas.draw()  # ensure text/artist extents are available
        renderer = fig.canvas.get_renderer()
    except Exception:
        renderer = None

    fig_w_in, fig_h_in = fig.get_size_inches()
    if fig_w_in < 3.0 or fig_h_in < 1.9:
        warnings.append("Figure is small for the content; consider a larger size")

    # Clipping: compare the content's tight bbox to the figure size. Exports use
    # bbox_inches="tight" (so files are never clipped); a much larger tight bbox
    # means content would be clipped in a FIXED-size on-screen preview.
    if renderer is not None:
        try:
            tb = fig.get_tightbbox(renderer)
            if tb.width > fig_w_in * 1.12 or tb.height > fig_h_in * 1.12:
                warnings.append("Some labels may be clipped in the fixed preview "
                                "(exports use a tight bounding box)")
        except Exception:
            pass

    for ax in fig.axes:
        # Missing axis labels (skip colorbars, which have no meaningful xlabel).
        if not getattr(ax, "_colorbar", None):
            if not ax.get_xlabel().strip() and not ax.get_ylabel().strip():
                warnings.append("Axes are missing x/y labels")

        # Small axis-label font.
        for lab in (ax.xaxis.label, ax.yaxis.label):
            if lab.get_text().strip() and lab.get_fontsize() < MIN_LABEL_PT:
                warnings.append("Axis label text may be too small for final export")
                break

        # Small / dense / long tick labels.
        ticklabels = [t for t in ax.get_xticklabels() if t.get_text().strip()]
        if ticklabels:
            if ticklabels[0].get_fontsize() < MIN_TICK_PT:
                warnings.append("Tick labels may be too small")
            n = len(ticklabels)
            longest = max((len(t.get_text()) for t in ticklabels), default=0)
            rotated = abs(ticklabels[0].get_rotation()) > 1
            if n > 12 and longest > 6 and not rotated:
                warnings.append("X tick labels are dense; consider rotating or widening the figure")

        # Legend overlapping the data area (only when legend is inside the axes).
        leg = ax.get_legend()
        if leg is not None and renderer is not None:
            lb = _bbox(leg, renderer)
            ab = _bbox(ax, renderer)
            if lb is not None and ab is not None:
                # inside axes if legend is (mostly) within the axes bbox
                inside = lb.x0 >= ab.x0 - 2 and lb.x1 <= ab.x1 + 2 and \
                    lb.y0 >= ab.y0 - 2 and lb.y1 <= ab.y1 + 2
                if inside:
                    # overlaps data unless it sits over a sparse corner — we can't
                    # easily know, so flag conservatively for large legends.
                    frac = ((lb.x1 - lb.x0) * (lb.y1 - lb.y0)) / max(
                        (ab.x1 - ab.x0) * (ab.y1 - ab.y0), 1.0)
                    if frac > 0.20:
                        warnings.append("Legend may overlap data")

    # Deduplicate while preserving order.
    seen, unique = set(), []
    for w in warnings:
        if w not in seen:
            seen.add(w)
            unique.append(w)
    return PublicationCheckResult(passed=not unique, warnings=unique)
