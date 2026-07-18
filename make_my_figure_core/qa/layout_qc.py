"""Advisory clipping / overlap QC for a rendered figure.

Inspects a Matplotlib figure and reports likely layout problems as structured
issues (category, severity, affected artist, message, suggested fix, whether an
auto-fix is available). Detection is **approximate and honest** — it uses artist
bounding boxes, so it flags likely problems rather than guaranteeing perfect
detection. Never changes scientific values.

`check_layout(fig)` -> LayoutQCReport
`auto_fix_layout(fig, spec=None)` -> list of applied, non-destructive layout fixes
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

_MIN_FONT_PT = 6.0
_OVERLAP_FRAC = 0.35          # min IoU-ish overlap of two text boxes to flag
_CLIP_TOL_PX = 1.5           # allow a hair of overflow before flagging


@dataclass
class LayoutIssue:
    category: str            # clipping | overlap | font | density | missing_label | colorbar
    severity: str            # "warning" | "fail"
    artist: str
    message: str
    suggested_fix: str = ""
    auto_fixable: bool = False


@dataclass
class LayoutQCReport:
    status: str = "pass"     # pass | warning | fail
    issues: List[LayoutIssue] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"status": self.status, "issues": [asdict(i) for i in self.issues]}


def _renderer(fig):
    fig.canvas.draw()
    try:
        return fig.canvas.get_renderer()
    except Exception:  # noqa: BLE001 - some backends
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        return FigureCanvasAgg(fig).get_renderer()


def _bb(artist, renderer):
    try:
        b = artist.get_window_extent(renderer=renderer)
        return b if (b.width > 0 and b.height > 0) else None
    except Exception:  # noqa: BLE001
        return None


def _visible_ticklabels(ax, which: str):
    """Tick labels for ticks that are actually inside the axes view — excludes the
    phantom out-of-range ticks Matplotlib keeps (they sit past the figure edge and
    would otherwise register as false 'clipping')."""
    if which == "x":
        lim = sorted(ax.get_xlim())
        ticks, labs = ax.get_xticks(), ax.get_xticklabels()
    else:
        lim = sorted(ax.get_ylim())
        ticks, labs = ax.get_yticks(), ax.get_yticklabels()
    span = (lim[1] - lim[0]) or 1.0
    tol = span * 1e-6
    return [lb for tk, lb in zip(ticks, labs)
            if lb.get_text() and (lim[0] - tol) <= tk <= (lim[1] + tol)]


def _overlap_frac(a, b) -> float:
    ix = max(0.0, min(a.x1, b.x1) - max(a.x0, b.x0))
    iy = max(0.0, min(a.y1, b.y1) - max(a.y0, b.y0))
    inter = ix * iy
    if inter <= 0:
        return 0.0
    return inter / min(a.width * a.height, b.width * b.height)


def check_layout(fig, *, min_font_pt: float = _MIN_FONT_PT) -> LayoutQCReport:
    """Return a structured advisory report of likely clipping/overlap problems."""
    issues: List[LayoutIssue] = []
    r = _renderer(fig)
    fb = fig.bbox

    def _clipped(b):
        return (b.x0 < fb.x0 - _CLIP_TOL_PX or b.y0 < fb.y0 - _CLIP_TOL_PX
                or b.x1 > fb.x1 + _CLIP_TOL_PX or b.y1 > fb.y1 + _CLIP_TOL_PX)

    for ax in fig.axes:
        # --- clipped titles / axis labels / tick labels ---
        checks = [("title", ax.title), ("x-axis label", ax.xaxis.label),
                  ("y-axis label", ax.yaxis.label)]
        for name, art in checks:
            if art is None or not art.get_text():
                continue
            b = _bb(art, r)
            if b is not None and _clipped(b):
                issues.append(LayoutIssue(
                    "clipping", "warning", name,
                    f"The {name} extends past the figure edge (clipped in a fixed-size preview).",
                    "Increase the corresponding margin or figure size, or enable auto-fix.",
                    auto_fixable=True))
        for axis_name in ("x", "y"):
            labs = _visible_ticklabels(ax, axis_name)
            for t in labs:
                b = _bb(t, r)
                if b is not None and _clipped(b):
                    issues.append(LayoutIssue(
                        "clipping", "warning", f"{axis_name} tick label '{t.get_text()[:20]}'",
                        f"A {axis_name} tick label is clipped at the figure edge.",
                        "Rotate the tick labels, widen the figure, or enable auto-fix.",
                        auto_fixable=True))
                    break  # one per axis/side is enough
            # --- tick-label overlap (adjacent labels) ---
            boxes = [(_bb(t, r), t.get_text()) for t in labs]
            boxes = [(b, txt) for b, txt in boxes if b is not None]
            overlaps = 0
            for i in range(len(boxes) - 1):
                if _overlap_frac(boxes[i][0], boxes[i + 1][0]) > _OVERLAP_FRAC:
                    overlaps += 1
            if overlaps:
                issues.append(LayoutIssue(
                    "overlap", "warning", f"{axis_name} tick labels",
                    f"{overlaps} pair(s) of {axis_name} tick labels overlap.",
                    "Rotate the tick labels, reduce their font, or widen the figure.",
                    auto_fixable=(axis_name == "x")))
            # --- tiny tick fonts ---
            for t in labs:
                if 0 < t.get_fontsize() < min_font_pt:
                    issues.append(LayoutIssue(
                        "font", "warning", f"{axis_name} tick labels",
                        f"{axis_name} tick label font is below {min_font_pt:g} pt.",
                        "Increase the tick font size or show fewer labels.", auto_fixable=False))
                    break

        # --- annotation-text overlap (e.g. gene labels) ---
        texts = [t for t in ax.texts if t.get_text()]
        tboxes = [_bb(t, r) for t in texts]
        tboxes = [b for b in tboxes if b is not None]
        ann_ov = 0
        for i in range(len(tboxes)):
            for j in range(i + 1, len(tboxes)):
                if _overlap_frac(tboxes[i], tboxes[j]) > _OVERLAP_FRAC:
                    ann_ov += 1
        if ann_ov:
            issues.append(LayoutIssue(
                "overlap", "warning", "annotations",
                f"{ann_ov} pair(s) of annotation labels overlap.",
                "Move overlapping labels (per-label offsets) or label fewer points.",
                auto_fixable=False))

        # --- legend clipped ---
        leg = ax.get_legend()
        if leg is not None:
            b = _bb(leg, r)
            if b is not None and _clipped(b):
                issues.append(LayoutIssue(
                    "clipping", "warning", "legend",
                    "The legend extends past the figure edge.",
                    "Use an inside legend location or enable auto-fix to reserve margin.",
                    auto_fixable=True))

    if any(i.severity == "fail" for i in issues):
        status = "fail"
    elif issues:
        status = "warning"
    else:
        status = "pass"
    return LayoutQCReport(status=status, issues=issues)


def auto_fix_layout(fig, spec: Optional[Dict[str, Any]] = None) -> List[str]:
    """Apply non-destructive layout fixes so content is not clipped. Layout only —
    never changes data, colors, or statistics. Returns the list of fixes applied."""
    applied: List[str] = []
    r = _renderer(fig)
    fb = fig.bbox

    # 1) Rotate overcrowded x tick labels to 45 (before resizing).
    for ax in fig.axes:
        labs = [t for t in ax.get_xticklabels() if t.get_text()]
        boxes = [_bb(t, r) for t in labs]
        boxes = [b for b in boxes if b is not None]
        crowded = any(_overlap_frac(boxes[i], boxes[i + 1]) > _OVERLAP_FRAC
                      for i in range(len(boxes) - 1))
        if crowded and labs and abs(labs[0].get_rotation()) < 1:
            for t in labs:
                t.set_rotation(45)
                t.set_horizontalalignment("right")
                t.set_verticalalignment("top")
                t.set_rotation_mode("anchor")
            applied.append(f"rotated x tick labels 45° on axes {fig.axes.index(ax)}")

    # 2) Reserve absolute room for labels/titles/legends with tight_layout (axes are
    #    fractional, so simply growing the figure scales the overflow with it — the
    #    subplot repositioning is what actually clears clipping). Then, if content
    #    still overflows, grow the figure and re-tighten. Layout only — no data change.
    import warnings as _warnings
    with _warnings.catch_warnings():
        _warnings.simplefilter("ignore")   # tight_layout may warn on tiny figures
        try:
            fig.tight_layout()
            applied.append("applied tight layout to reserve label room")
        except Exception:  # noqa: BLE001 - tight_layout can fail on divider/colorbar figs
            pass
        try:
            r = _renderer(fig)
            tb = fig.get_tightbbox(r)   # inches
            fw, fh = fig.get_size_inches()
            if tb.width > fw + 0.02 or tb.height > fh + 0.02:
                fig.set_size_inches(max(fw, tb.width + 0.3), max(fh, tb.height + 0.3))
                try:
                    fig.tight_layout()
                except Exception:  # noqa: BLE001
                    pass
                fig.canvas.draw()
                applied.append(f"expanded figure to {fig.get_size_inches()[0]:.1f}x"
                               f"{fig.get_size_inches()[1]:.1f} in to fit content")
        except Exception:  # noqa: BLE001
            pass
    return applied
