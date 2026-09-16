"""Individual observations drawn over a summary (bar, box, violin): the shared engine.

Biological figures show the replicates. This module is the one place that decides how a group's
observations are arranged (jitter, centred column, beeswarm), how big and how transparent the
markers are for the number of points actually present, and what the renderer must know afterwards
(the highest drawn value, so a statistics bracket clears the points).

Rules that hold for every renderer using it:

* The observations come from the data - every value in ``values`` is drawn. Nothing is sampled,
  thinned or hidden; n is never a plotting parameter.
* Adaptation is bounded and declared: :func:`adaptive_marker` scales marker size, alpha and jitter
  width within fixed limits by group size, and for very dense groups it returns a *suggestion*
  (use a distribution plot) that the renderer surfaces as a warning. It never removes points.
* Everything visual is an option a preset may carry (style scope); nothing here changes values,
  groups, summaries or tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

if TYPE_CHECKING:  # pragma: no cover - ``ui_hints`` imports this module for the option list
    from make_my_figure_core.ui_hints import Option

ARRANGEMENTS = ("jitter", "centered", "beeswarm")
FILLS = ("filled", "open")
EDGES = ("dark", "same", "none")
MARKERS = ("o", "s", "^", "D", "v")

# Bounded adaptation by group size: (max n, size factor, alpha, jitter-width factor)
_ADAPT = (
    (10, 1.00, 0.90, 0.60),   # small biological n: points prominent, narrow spread
    (30, 0.85, 0.85, 0.85),
    (100, 0.65, 0.70, 1.00),
    (float("inf"), 0.45, 0.50, 1.00),
)
DENSE_N = 60   # above this a bar with points is no longer a good summary - suggest a distribution


@dataclass
class ObservationStyle:
    arrangement: str = "jitter"      # jitter | centered | beeswarm
    jitter_width: float = 0.35       # total spread as a fraction of the category spacing (1.0)
    marker: str = "o"
    fill: str = "filled"             # filled | open
    edge: str = "dark"               # dark | same | none
    edge_width: float = 0.5          # pt
    alpha: Optional[float] = None    # None -> adaptive
    size: Optional[float] = None     # scatter s (pt^2); None -> adaptive from style.marker_size
    seed: int = 42
    zorder: float = 3.0

    @classmethod
    def from_mapping(cls, mapping: Dict[str, Any], *, prefix: str = "point_") -> "ObservationStyle":
        """Read the ``point_*`` options a renderer declares (missing keys keep the defaults)."""
        g = lambda k, d: mapping.get(prefix + k, d) if mapping.get(prefix + k) not in (None, "") else d  # noqa: E731
        arr = str(g("arrangement", "jitter")).lower()
        size = mapping.get(prefix + "size")
        alpha = mapping.get(prefix + "alpha")
        return cls(
            arrangement=arr if arr in ARRANGEMENTS else "jitter",
            jitter_width=float(g("jitter_width", 0.35)),
            marker=str(g("marker", "o")),
            fill=str(g("fill", "filled")).lower(),
            edge=str(g("edge", "dark")).lower(),
            edge_width=float(g("edge_width", 0.5)),
            # 0 (the option's "adaptive" value), blank and "auto" all mean adaptive
            alpha=(float(alpha) if alpha not in (None, "", "auto") and float(alpha) > 0 else None),
            size=(float(size) if size not in (None, "", "auto") and float(size) > 0 else None),
            seed=int(g("seed", 42)),
        )


def observation_options(*, prefix: str = "point_", include_toggle: bool = True) -> List["Option"]:
    """The ``ui_hints`` options every renderer with overlaid observations declares (style scope)."""
    # Imported here: ``ui_hints`` builds its option table from this function, so a module-level
    # import in either direction would be circular.
    from make_my_figure_core.ui_hints import Option

    opts: List["Option"] = []
    if include_toggle:
        opts.append(Option(prefix.rstrip("_") + "s", "Show individual observations", "bool", True, scope="style"))
    opts += [
        Option(prefix + "arrangement", "Point arrangement", "choice", "jitter", list(ARRANGEMENTS), scope="style"),
        Option(prefix + "jitter_width", "Jitter width (fraction of spacing)", "number", 0.35,
               minimum=0.0, maximum=0.9, step=0.05, decimals=2, scope="style"),
        Option(prefix + "size", "Point size (pt²; 0 = adaptive)", "number", 0.0, minimum=0.0, maximum=120.0,
               step=1.0, decimals=1, scope="style"),
        Option(prefix + "marker", "Point marker", "choice", "o", list(MARKERS), scope="style"),
        Option(prefix + "fill", "Point fill", "choice", "filled", list(FILLS), scope="style"),
        Option(prefix + "edge", "Point edge", "choice", "dark", list(EDGES), scope="style"),
        Option(prefix + "edge_width", "Point edge width (pt)", "number", 0.5, minimum=0.0, maximum=3.0,
               step=0.1, decimals=2, scope="style"),
        Option(prefix + "alpha", "Point opacity (0 = adaptive)", "number", 0.0, minimum=0.0, maximum=1.0,
               step=0.05, decimals=2, scope="style"),
    ]
    return opts


def adaptive_marker(n: int, base_size: float, obs: ObservationStyle) -> Tuple[float, float, float, Optional[str]]:
    """``(size, alpha, jitter_width, suggestion)`` for a group of ``n`` observations.

    ``size`` and ``alpha`` honour explicit values in ``obs``; otherwise they follow the bounded
    table above. ``suggestion`` is a sentence for the renderer's warnings when the group is too
    dense for a summary-plus-points display to stay readable; nothing is dropped either way.
    """
    factor, alpha, jw = 1.0, 0.9, 1.0
    for upper, f, a, j in _ADAPT:
        if n <= upper:
            factor, alpha, jw = f, a, j
            break
    size = obs.size if obs.size is not None else max(3.0, base_size * factor)
    alpha_out = obs.alpha if obs.alpha is not None else alpha
    width = obs.jitter_width * jw
    suggestion = None
    if n > DENSE_N:
        suggestion = (f"A group has {n} observations; a bar or box with every point becomes hard to read at "
                      "this density. Consider a violin, box or raincloud plot, which shows the distribution "
                      "directly. All observations are still drawn.")
    return float(size), float(alpha_out), float(width), suggestion


def _swarm_offsets(values_px: np.ndarray, diameter_px: float) -> np.ndarray:
    """Greedy 1-D beeswarm: offsets (px) along the category axis so markers do not overlap."""
    order = np.argsort(values_px)
    placed_y: List[float] = []
    placed_x: List[float] = []
    out = np.zeros(len(values_px))
    d2 = diameter_px ** 2
    for idx in order:
        y = values_px[idx]
        # candidate offsets: 0, then symmetric steps of a quarter diameter
        cands = [0.0]
        step = diameter_px / 4.0
        for k in range(1, 400):
            cands += [k * step, -k * step]
        chosen = 0.0
        for c in cands:
            ok = True
            for px, py in zip(placed_x, placed_y):
                if abs(py - y) < diameter_px and (px - c) ** 2 + (py - y) ** 2 < d2:
                    ok = False
                    break
            if ok:
                chosen = c
                break
        placed_x.append(chosen)
        placed_y.append(y)
        out[idx] = chosen
    return out


def draw_observations(ax, position: float, values: Sequence[float], *, color, style, obs: ObservationStyle,
                      orientation: str = "vertical", rng: Optional[np.random.Generator] = None,
                      base_size: Optional[float] = None) -> Dict[str, Any]:
    """Draw one group's observations at ``position`` and return what the renderer needs.

    Returns ``{"n", "max", "min", "size", "alpha", "suggestion"}``; ``max`` is the largest drawn
    value (for bracket placement), never an inflated estimate.
    """
    vals = np.asarray([v for v in values if v is not None and np.isfinite(v)], dtype=float)
    n = int(len(vals))
    if n == 0:
        return {"n": 0, "max": float("nan"), "min": float("nan"), "size": 0.0, "alpha": 0.0, "suggestion": None}
    rng = rng or np.random.default_rng(obs.seed)
    base = float(base_size if base_size is not None else getattr(style, "marker_size", 20.0)) * 0.6
    size, alpha, width, suggestion = adaptive_marker(n, base, obs)

    if obs.arrangement == "centered":
        offsets = np.zeros(n)
    elif obs.arrangement == "beeswarm":
        # marker diameter in px from the scatter area (pt^2): d_pt = sqrt(size); px = pt * dpi/72
        fig = ax.get_figure()
        d_px = float(np.sqrt(size)) * fig.dpi / 72.0 * 1.05
        if orientation == "horizontal":
            v_px = ax.transData.transform(np.column_stack([vals, np.full(n, position)]))[:, 0]
        else:
            v_px = ax.transData.transform(np.column_stack([np.full(n, position), vals]))[:, 1]
        off_px = _swarm_offsets(v_px, d_px)
        # px -> data units along the category axis
        if orientation == "horizontal":
            p0 = ax.transData.transform([[0.0, position]])[0][1]
            per_unit = ax.transData.transform([[0.0, position + 1.0]])[0][1] - p0
        else:
            p0 = ax.transData.transform([[position, 0.0]])[0][0]
            per_unit = ax.transData.transform([[position + 1.0, 0.0]])[0][0] - p0
        offsets = off_px / per_unit if per_unit else np.zeros(n)
        # keep the swarm inside the category spacing
        lim = max(width / 2.0, 0.05)
        offsets = np.clip(offsets, -lim, lim)
    else:
        offsets = rng.uniform(-width / 2.0, width / 2.0, size=n)

    if obs.fill == "open":
        face = "white"
        edge = color if obs.edge in ("same", "none") else "black"
        lw = max(obs.edge_width, 0.4)
    else:
        face = color
        edge = {"dark": "black", "same": color, "none": "none"}.get(obs.edge, "black")
        lw = 0.0 if obs.edge == "none" else obs.edge_width
    xs = np.full(n, position) + offsets
    if orientation == "horizontal":
        ax.scatter(vals, xs, s=size, marker=obs.marker, facecolors=face, edgecolors=edge,
                   linewidths=lw, alpha=alpha, zorder=obs.zorder, clip_on=False)
    else:
        ax.scatter(xs, vals, s=size, marker=obs.marker, facecolors=face, edgecolors=edge,
                   linewidths=lw, alpha=alpha, zorder=obs.zorder, clip_on=False)
    return {"n": n, "max": float(vals.max()), "min": float(vals.min()), "size": size, "alpha": alpha,
            "suggestion": suggestion}


def n_label_positions(kind: str, groups: Sequence[str], counts: Dict[str, int]) -> List[str]:
    """Text for optional sample-size labels: ``n = 6`` per group, in group order."""
    return [f"n = {int(counts.get(str(g), 0))}" for g in groups]


def add_n_labels(ax, positions: Sequence[float], counts: Sequence[int], *, where: str, style,
                 orientation: str = "vertical", tops: Optional[Sequence[float]] = None) -> None:
    """Write ``n = k`` below or above each category (``where``: below | above). Legend/none handled by caller."""
    if where not in ("below", "above"):
        return
    fs = float(getattr(style, "annotation_pt", 8.0))
    for i, (pos, n) in enumerate(zip(positions, counts)):
        text = f"n = {int(n)}"
        if orientation == "horizontal":
            x = 0.0 if where == "below" else (tops[i] if tops is not None else 0.0)
            ax.annotate(text, xy=(x, pos), xytext=(6 if where == "above" else -6, 0), textcoords="offset points",
                        ha="left" if where == "above" else "right", va="center", fontsize=fs, clip_on=False,
                        annotation_clip=False)
        else:
            if where == "below":
                ax.annotate(text, xy=(pos, 0), xycoords=("data", "axes fraction"), xytext=(0, -2),
                            textcoords="offset points", ha="center", va="top", fontsize=fs, clip_on=False,
                            annotation_clip=False)
            else:
                top = tops[i] if tops is not None else ax.get_ylim()[1]
                ax.annotate(text, xy=(pos, top), xytext=(0, 3), textcoords="offset points", ha="center",
                            va="bottom", fontsize=fs, clip_on=False, annotation_clip=False)
