"""Journal-like style engine.

Loads the starter style tokens from
``style_profiles/starter_journal_style_profiles.json`` and exposes them as
:class:`StyleProfile` objects. Renderers consume *tokens* (font size, line
widths, palette, figure size) rather than hard-coding styling, so that all
plots share one consistent look per profile.

IMPORTANT: These are "*-like" aesthetics only. They are NOT official Nature,
Science, or Cell templates and must not be presented as guaranteeing
submission compliance.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, List, Optional

import matplotlib as mpl

from make_my_figure_core.resources import resource_path

_PROFILES_PATH = resource_path(
    "style_profiles", "starter_journal_style_profiles.json"
)

MM_PER_INCH = 25.4


def mm_to_inches(mm: float) -> float:
    return float(mm) / MM_PER_INCH


# Colorblind-aware categorical palettes (Okabe-Ito based) per profile.
# These are our own choices, not journal specifications.
_OKABE_ITO = [
    "#0072B2",  # blue
    "#D55E00",  # vermillion
    "#009E73",  # green
    "#CC79A7",  # purple/pink
    "#E69F00",  # orange
    "#56B4E9",  # sky blue
    "#F0E442",  # yellow
    "#000000",  # black
]

_PALETTES: Dict[str, List[str]] = {
    "nature_like": _OKABE_ITO,
    "science_like": ["#1B1B1B", "#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00"],
    "cell_like": ["#3B6FB6", "#E8743B", "#19A979", "#945ECF", "#ED4A7B", "#13A4B4"],
}

# Diverging / sequential colormaps used by heatmap-style renderers.
_SEQUENTIAL_CMAP = {
    "nature_like": "viridis",
    "science_like": "cividis",
    "cell_like": "magma",
}
_DIVERGING_CMAP = {
    "nature_like": "RdBu_r",
    "science_like": "RdBu_r",
    "cell_like": "PuOr_r",
}

# Preferred sans-serif stack; Arial/Helvetica fall back to DejaVu Sans which
# ships with matplotlib so rendering never crashes on a missing font.
_FONT_STACK = ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"]


@dataclass
class StyleProfile:
    """A resolved set of style tokens for one journal-like profile."""

    name: str
    font_family: List[str]
    base_font_pt: float
    axis_font_pt: float
    title_font_pt: float
    line_width_pt: float
    spine_width_pt: float
    single_column_width_mm: float
    double_column_width_mm: float
    preferred_exports: List[str]
    palette_role: str
    palette: List[str] = field(default_factory=list)
    sequential_cmap: str = "viridis"
    diverging_cmap: str = "RdBu_r"

    def figure_size_inches(self, width: str = "single", aspect: float = 0.75) -> tuple[float, float]:
        """Return ``(width_in, height_in)`` for a column width and aspect.

        ``width`` is ``"single"`` or ``"double"``; ``aspect`` is height/width.
        """
        if width == "double":
            w_mm = self.double_column_width_mm
        else:
            w_mm = self.single_column_width_mm
        w_in = mm_to_inches(w_mm)
        return (w_in, w_in * float(aspect))

    def color_for(self, index: int) -> str:
        palette = self.palette or _OKABE_ITO
        return palette[index % len(palette)]

    def rc_params(self) -> Dict[str, Any]:
        """Matplotlib rcParams encoding this profile's tokens."""
        return {
            "font.family": "sans-serif",
            "font.sans-serif": self.font_family,
            "font.size": self.base_font_pt,
            "axes.titlesize": self.title_font_pt,
            "axes.labelsize": self.axis_font_pt,
            "xtick.labelsize": self.axis_font_pt,
            "ytick.labelsize": self.axis_font_pt,
            "legend.fontsize": self.axis_font_pt,
            "axes.linewidth": self.spine_width_pt,
            "lines.linewidth": self.line_width_pt,
            "xtick.major.width": self.spine_width_pt,
            "ytick.major.width": self.spine_width_pt,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
            "figure.dpi": 100,
            "savefig.bbox": "tight",
            "svg.fonttype": "none",  # keep text editable in SVG
            "pdf.fonttype": 42,      # embed TrueType so text stays editable
            "ps.fonttype": 42,
        }

    def apply(self) -> mpl.rc_context:
        """Return an rc_context that temporarily applies this profile."""
        return mpl.rc_context(rc=self.rc_params())


def _parse_profile(name: str, raw: Dict[str, Any]) -> StyleProfile:
    return StyleProfile(
        name=name,
        font_family=list(_FONT_STACK),
        base_font_pt=float(raw.get("base_font_pt", 7)),
        axis_font_pt=float(raw.get("axis_font_pt", 7)),
        title_font_pt=float(raw.get("title_font_pt", 8)),
        line_width_pt=float(raw.get("line_width_pt", 0.75)),
        spine_width_pt=float(raw.get("spine_width_pt", 0.5)),
        single_column_width_mm=float(raw.get("single_column_width_mm", 89)),
        double_column_width_mm=float(raw.get("double_column_width_mm", 183)),
        preferred_exports=list(raw.get("preferred_exports", ["svg", "pdf", "png"])),
        palette_role=str(raw.get("palette_role", "")),
        palette=_PALETTES.get(name, _OKABE_ITO),
        sequential_cmap=_SEQUENTIAL_CMAP.get(name, "viridis"),
        diverging_cmap=_DIVERGING_CMAP.get(name, "RdBu_r"),
    )


@lru_cache(maxsize=1)
def _load_raw(path: Optional[str] = None) -> Dict[str, Any]:
    profiles_path = path or _PROFILES_PATH
    with open(profiles_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def list_profiles(path: Optional[str] = None) -> List[str]:
    return list(_load_raw(path).get("profiles", {}).keys())


def load_profile(name: str, path: Optional[str] = None) -> StyleProfile:
    profiles = _load_raw(path).get("profiles", {})
    if name not in profiles:
        raise KeyError(
            f"Unknown style profile '{name}'. Available: {sorted(profiles.keys())}"
        )
    return _parse_profile(name, profiles[name])


def load_all_profiles(path: Optional[str] = None) -> Dict[str, StyleProfile]:
    return {name: load_profile(name, path) for name in list_profiles(path)}
