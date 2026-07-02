"""Data models for the multi-panel figure builder."""

from __future__ import annotations

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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "title": self.title,
            "caption": self.caption,
            "plot_spec": self.plot_spec,
            "stats_spec": self.stats_spec or (self.plot_spec or {}).get("statistics"),
            "source_name": self.source_name,
            "has_prerendered_figure": self.figure is not None,
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
    show_titles: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ncols": self.ncols, "nrows": self.nrows,
            "width_ratios": self.width_ratios, "height_ratios": self.height_ratios,
            "fig_width_mm": self.fig_width_mm, "fig_height_mm": self.fig_height_mm,
            "wspace": self.wspace, "hspace": self.hspace,
            "label_style": self.label_style, "label_prefix": self.label_prefix,
            "label_size": self.label_size, "label_weight": self.label_weight,
            "panel_dpi": self.panel_dpi, "background": self.background,
            "show_titles": self.show_titles,
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
