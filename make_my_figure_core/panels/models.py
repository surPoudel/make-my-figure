"""Data models for the multi-panel figure builder."""

from __future__ import annotations

import os
import string
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def default_labels(n: int, *, style: str = "A") -> List[str]:
    """Return n panel labels: 'A','B',... or 'a','b',... or '1','2',..."""
    if style == "1":
        return [str(i + 1) for i in range(n)]
    letters = string.ascii_uppercase if style == "A" else string.ascii_lowercase
    out = []
    for i in range(n):
        if i < 26:
            out.append(letters[i])
        else:  # AA, AB, ...
            out.append(letters[i // 26 - 1] + letters[i % 26])
    return out


@dataclass
class Panel:
    """One panel in a composite figure.

    A panel provides either a pre-rendered matplotlib ``figure`` or a
    ``plot_spec`` + ``table`` to render on demand (so the composite is
    reproducible from specs alone).
    """

    label: str = ""
    title: str = ""
    caption: str = ""
    figure: Any = None                       # matplotlib Figure (optional)
    plot_spec: Optional[Dict[str, Any]] = None
    table: Any = None                        # pandas DataFrame (optional)
    aux: Dict[str, Any] = field(default_factory=dict)
    stats_spec: Optional[Dict[str, Any]] = None
    source_name: str = ""                    # provenance label (file / example name)
    source_workbook: str = ""                # workbook filename (multi-sheet Excel)
    source_sheet: str = ""                   # worksheet name (multi-sheet Excel)
    # Approximate rendered size in inches (width x height). ``None`` means
    # "auto": the width falls back to an even share of the figure width and the
    # height follows the panel's own aspect ratio. The panel is always drawn
    # WITHOUT distortion (scaled to fit its cell, letterboxed if needed), so a
    # bigger/smaller number just yields a bigger/smaller version of the same
    # figure rather than a stretched one.
    width_in: Optional[float] = None
    height_in: Optional[float] = None
    # --- imported external-figure panel (v0.5) -----------------------------
    # When ``image_path`` is set, this is an *imported* panel backed by an
    # external file (PNG/JPG/TIFF/SVG/PDF) copied into the assets folder, rather
    # than a Make My Figure plot. ``image_meta`` holds the import record
    # (original filename, dims, DPI, checksum, page, rasterization DPI). The
    # transform fields control how the image is placed in its cell.
    image_path: Optional[str] = None         # relative path within the assets folder
    image_meta: Dict[str, Any] = field(default_factory=dict)
    fit_mode: str = "contain"                # contain | fill | crop | stretch
    preserve_aspect: bool = True
    crop: Dict[str, float] = field(default_factory=dict)   # top/bottom/left/right fractions
    rotate: int = 0                          # 0 | 90 | 180 | 270
    flip_h: bool = False
    flip_v: bool = False
    auto_trim: bool = False
    background: str = "white"                # white | transparent
    border: bool = False
    border_width: float = 0.8
    # Per-panel manual annotations (normalized axes coords 0..1) — AnnotationSpec dicts.
    annotations: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def is_external(self) -> bool:
        return bool(self.image_path)

    def assets_base(self) -> Optional[str]:
        return os.path.dirname(self.image_path) if self.image_path else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "title": self.title,
            "caption": self.caption,
            "panel_kind": "external_figure_panel" if self.is_external else "make_my_figure_panel",
            "plot_spec": self.plot_spec,
            "stats_spec": self.stats_spec or (self.plot_spec or {}).get("statistics"),
            "source_name": self.source_name,
            "source_workbook": self.source_workbook or (self.plot_spec or {}).get("source", {}).get("source_workbook_name", ""),
            "source_sheet": self.source_sheet or (self.plot_spec or {}).get("source", {}).get("source_sheet_name", ""),
            "width_in": self.width_in,
            "height_in": self.height_in,
            "has_prerendered_figure": self.figure is not None,
            # imported-panel record (asset basename only — no private absolute paths)
            "image_path": os.path.basename(self.image_path) if self.image_path else None,
            "image_meta": self.image_meta or {},
            "fit_mode": self.fit_mode,
            "preserve_aspect": self.preserve_aspect,
            "crop": self.crop or {},
            "rotate": self.rotate, "flip_h": self.flip_h, "flip_v": self.flip_v,
            "auto_trim": self.auto_trim, "background": self.background,
            "border": self.border, "border_width": self.border_width,
            "annotations": self.annotations or [],
        }


@dataclass
class FigureLayout:
    """Layout + styling for a composite figure."""

    ncols: Optional[int] = None              # None/0 -> automatic grid
    nrows: Optional[int] = None
    width_ratios: Optional[List[float]] = None
    height_ratios: Optional[List[float]] = None
    fig_width_mm: float = 180.0              # double-column default
    fig_height_mm: Optional[float] = None    # None -> derived from grid
    wspace: float = 0.18
    hspace: float = 0.22
    label_style: str = "A"                   # A | a | 1
    label_prefix: str = ""                   # e.g. "" or "1" for "1A"
    label_size: float = 14.0
    label_weight: str = "bold"
    label_dx: float = -0.02                  # axes-fraction offset for the label
    label_dy: float = 1.04
    panel_dpi: int = 300                     # raster DPI for embedded panel content
    background: str = "white"
    # Per-panel titles are OFF by default: the panel letter (A, B, ...) plus the
    # figure legend already identify each panel, and a centered title collides
    # with the top-left label. The title stays populated on the Panel for use in
    # the auto-drafted legend; set True only if you explicitly want it drawn.
    show_titles: bool = False
    # Figure-level font sizes (points) applied to EVERY panel at render time so
    # the whole composite is typographically consistent. ``None`` keeps each
    # panel's own style-profile value. These are user-facing knobs with sensible
    # publication defaults baked into the style profiles.
    base_font_pt: Optional[float] = None     # general text size
    axis_font_pt: Optional[float] = None     # x/y axis label size
    tick_label_pt: Optional[float] = None    # tick number size
    legend_pt: Optional[float] = None        # legend text size

    def font_overrides(self) -> Dict[str, float]:
        """Return the non-None font tokens as a style-override dict."""
        keys = ("base_font_pt", "axis_font_pt", "tick_label_pt", "legend_pt")
        return {k: getattr(self, k) for k in keys if getattr(self, k) is not None}

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]) -> "FigureLayout":
        """Rebuild a layout from ``to_dict`` output; unknown keys are ignored, missing keep defaults."""
        import dataclasses

        known = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in (d or {}).items() if k in known})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ncols": self.ncols, "nrows": self.nrows,
            "width_ratios": self.width_ratios, "height_ratios": self.height_ratios,
            "fig_width_mm": self.fig_width_mm, "fig_height_mm": self.fig_height_mm,
            "wspace": self.wspace, "hspace": self.hspace,
            "label_style": self.label_style, "label_prefix": self.label_prefix,
            "label_size": self.label_size, "label_weight": self.label_weight,
            "label_dx": self.label_dx, "label_dy": self.label_dy,
            "panel_dpi": self.panel_dpi, "background": self.background,
            "show_titles": self.show_titles,
            "base_font_pt": self.base_font_pt, "axis_font_pt": self.axis_font_pt,
            "tick_label_pt": self.tick_label_pt, "legend_pt": self.legend_pt,
        }


@dataclass
class MultiPanelFigure:
    """A named composite figure definition (figure name + panels + layout)."""

    name: str = "Figure 1"
    panels: List[Panel] = field(default_factory=list)
    layout: FigureLayout = field(default_factory=FigureLayout)
    legend_text: str = ""

    # --- panel management ---------------------------------------------------
    def add_panel(self, panel: Panel) -> Panel:
        self.panels.append(panel)
        self.autolabel()
        return panel

    def remove_panel(self, index: int) -> None:
        if 0 <= index < len(self.panels):
            self.panels.pop(index)
            self.autolabel()

    def move_panel(self, index: int, new_index: int) -> None:
        if 0 <= index < len(self.panels) and 0 <= new_index < len(self.panels):
            p = self.panels.pop(index)
            self.panels.insert(new_index, p)
            self.autolabel()

    def duplicate_panel(self, index: int) -> None:
        if 0 <= index < len(self.panels):
            src = self.panels[index]
            import copy

            clone = copy.copy(src)
            self.panels.insert(index + 1, clone)
            self.autolabel()

    def autolabel(self) -> None:
        """(Re)assign sequential labels to any panel without an explicit one."""
        labels = default_labels(len(self.panels), style=self.layout.label_style)
        for i, panel in enumerate(self.panels):
            panel.label = f"{self.layout.label_prefix}{labels[i]}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "panels": [p.to_dict() for p in self.panels],
            "layout": self.layout.to_dict(),
            "legend_text": self.legend_text,
        }
