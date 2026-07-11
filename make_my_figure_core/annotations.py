"""Universal manual annotation layer for Make My Figure (v0.5).

A frontend-agnostic model + renderer for manual annotations that work across all
plot types: free text, arrows, callouts, highlight boxes / regions of interest,
and brackets. Annotations are stored in the PlotSpec (``spec['annotations']``)
so exported figures are fully reproducible, and are drawn as **vector** artists
so SVG/PDF export keeps them editable.

Feature-targeted highlighting that needs data lookup (e.g. "highlight these
genes" in a volcano/heatmap) is resolved inside those renderers, which can also
emit coordinate annotations through this layer. This module handles the
coordinate-based, renderer-independent annotations applied after any render.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Coordinate systems an annotation can be anchored in.
_COORDS = {"data", "axes", "figure"}
# Supported annotation kinds.
_KINDS = {"text", "arrow", "callout", "box", "region", "bracket", "hline", "vline"}


@dataclass
class Annotation:
    """One manual annotation. See ``AnnotationSpec`` docs for field meanings."""

    kind: str = "text"                      # text|arrow|callout|box|region|bracket|hline|vline
    annotation_id: str = ""
    text: str = ""
    # Anchor point(s). ``xy`` is the primary point; ``xytext``/``xy2`` a second
    # point (arrow tail / opposite box corner / bracket end).
    xy: Optional[Tuple[float, float]] = None
    xy2: Optional[Tuple[float, float]] = None
    coords: str = "data"                    # data|axes|figure
    # Styling (None -> inherit sensible publication defaults from the profile).
    color: Optional[str] = None
    font_size: Optional[float] = None
    font_weight: str = "normal"
    box: bool = False                       # draw a background box behind text
    arrow: bool = False                     # draw a connector arrow (text/callout)
    arrow_style: str = "->"
    line_width: Optional[float] = None
    alpha: float = 1.0
    layer: int = 10                         # z-order
    visible: bool = True
    created_by: str = "user"                # user|statistics|volcano|heatmap|clustering
    target: Dict[str, Any] = field(default_factory=dict)  # optional semantic target record

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "kind": self.kind, "annotation_id": self.annotation_id, "text": self.text,
            "xy": list(self.xy) if self.xy else None,
            "xy2": list(self.xy2) if self.xy2 else None,
            "coords": self.coords, "color": self.color, "font_size": self.font_size,
            "font_weight": self.font_weight, "box": self.box, "arrow": self.arrow,
            "arrow_style": self.arrow_style, "line_width": self.line_width,
            "alpha": self.alpha, "layer": self.layer, "visible": self.visible,
            "created_by": self.created_by, "target": self.target or {},
        }
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Annotation":
        def _pt(v):
            return tuple(v) if isinstance(v, (list, tuple)) and len(v) == 2 else None
        kind = str(d.get("kind", "text")).lower()
        if kind not in _KINDS:
            kind = "text"
        coords = str(d.get("coords", "data")).lower()
        if coords not in _COORDS:
            coords = "data"
        return cls(
            kind=kind, annotation_id=str(d.get("annotation_id", "")),
            text=str(d.get("text", "")), xy=_pt(d.get("xy")), xy2=_pt(d.get("xy2")),
            coords=coords, color=d.get("color"), font_size=d.get("font_size"),
            font_weight=str(d.get("font_weight", "normal")), box=bool(d.get("box", False)),
            arrow=bool(d.get("arrow", False)), arrow_style=str(d.get("arrow_style", "->")),
            line_width=d.get("line_width"), alpha=float(d.get("alpha", 1.0)),
            layer=int(d.get("layer", 10)), visible=bool(d.get("visible", True)),
            created_by=str(d.get("created_by", "user")), target=dict(d.get("target", {}) or {}),
        )


def parse_annotations(raw: Any) -> List[Annotation]:
    """Coerce a spec's ``annotations`` (list of dicts) into Annotation objects."""
    if not raw:
        return []
    out: List[Annotation] = []
    for item in raw:
        if isinstance(item, Annotation):
            out.append(item)
        elif isinstance(item, dict):
            out.append(Annotation.from_dict(item))
    return out


def _transform(ax, coords: str):
    if coords == "axes":
        return ax.transAxes
    if coords == "figure":
        return ax.figure.transFigure
    return ax.transData


def apply_annotations(fig, ax, annotations: List[Annotation], style) -> int:
    """Draw coordinate-based annotations on ``ax`` (vector artists). Returns count drawn.

    Never raises: a malformed annotation is skipped with the rest still drawn.
    """
    drawn = 0
    default_color = getattr(style, "text_color", "#1a1a1a")
    default_fs = getattr(style, "annotation_pt", 9.5)
    default_lw = getattr(style, "line_width_pt", 1.5)
    for ann in sorted(annotations, key=lambda a: a.layer):
        if not ann.visible:
            continue
        color = ann.color or default_color
        fs = ann.font_size or default_fs
        lw = ann.line_width or default_lw
        tr = _transform(ax, ann.coords)
        bbox = dict(boxstyle="round,pad=0.25", fc="white", ec=color, lw=0.6,
                    alpha=0.85) if ann.box else None
        try:
            if ann.kind in ("text", "callout"):
                if ann.xy is None:
                    continue
                if (ann.arrow or ann.kind == "callout") and ann.xy2 is not None:
                    # callout: text at xy2 pointing to xy
                    ax.annotate(ann.text, xy=ann.xy, xytext=ann.xy2, xycoords=tr,
                                textcoords=tr, fontsize=fs, fontweight=ann.font_weight,
                                color=color, alpha=ann.alpha, zorder=ann.layer, bbox=bbox,
                                arrowprops=dict(arrowstyle=ann.arrow_style, color=color, lw=lw))
                else:
                    ax.text(ann.xy[0], ann.xy[1], ann.text, transform=tr, fontsize=fs,
                            fontweight=ann.font_weight, color=color, alpha=ann.alpha,
                            zorder=ann.layer, bbox=bbox)
            elif ann.kind == "arrow":
                if ann.xy is None or ann.xy2 is None:
                    continue
                ax.annotate("", xy=ann.xy, xytext=ann.xy2, xycoords=tr, textcoords=tr,
                            zorder=ann.layer,
                            arrowprops=dict(arrowstyle=ann.arrow_style, color=color,
                                            lw=lw, alpha=ann.alpha))
                if ann.text:
                    mx = (ann.xy[0] + ann.xy2[0]) / 2.0
                    my = (ann.xy[1] + ann.xy2[1]) / 2.0
                    ax.text(mx, my, ann.text, transform=tr, fontsize=fs, color=color,
                            zorder=ann.layer, bbox=bbox)
            elif ann.kind in ("box", "region"):
                if ann.xy is None or ann.xy2 is None:
                    continue
                from matplotlib.patches import Rectangle

                x0, y0 = ann.xy
                x1, y1 = ann.xy2
                rect = Rectangle((min(x0, x1), min(y0, y1)), abs(x1 - x0), abs(y1 - y0),
                                 transform=tr, fill=(ann.kind == "region"),
                                 facecolor=(color if ann.kind == "region" else "none"),
                                 edgecolor=color, lw=lw,
                                 alpha=(ann.alpha * (0.18 if ann.kind == "region" else 1.0)),
                                 zorder=ann.layer)
                ax.add_patch(rect)
                if ann.text:
                    ax.text(min(x0, x1), max(y0, y1), ann.text, transform=tr, fontsize=fs,
                            color=color, va="bottom", zorder=ann.layer, bbox=bbox)
            elif ann.kind == "bracket":
                if ann.xy is None or ann.xy2 is None:
                    continue
                (x0, y0), (x1, y1) = ann.xy, ann.xy2
                tick = 0.02 * (abs(y1 - y0) + abs(x1 - x0) + 1)
                ax.plot([x0, x0, x1, x1], [y0 - tick, y0, y0, y0 - tick], transform=tr,
                        color=color, lw=lw, zorder=ann.layer, clip_on=False)
                if ann.text:
                    ax.text((x0 + x1) / 2.0, y0, ann.text, transform=tr, fontsize=fs,
                            color=color, ha="center", va="bottom", zorder=ann.layer)
            elif ann.kind == "hline":
                if ann.xy is None:
                    continue
                ax.axhline(ann.xy[1], color=color, lw=lw, alpha=ann.alpha, ls="--",
                           zorder=ann.layer)
            elif ann.kind == "vline":
                if ann.xy is None:
                    continue
                ax.axvline(ann.xy[0], color=color, lw=lw, alpha=ann.alpha, ls="--",
                           zorder=ann.layer)
            else:
                continue
            drawn += 1
        except Exception:
            # Never let a single bad annotation break the render/export.
            continue
    return drawn
