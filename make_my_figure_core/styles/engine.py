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

# A polished, high-contrast, colorblind-aware categorical palette used as the
# publication default (not Matplotlib's default cycle).
_PUBLICATION = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9",
                "#4B0092", "#000000"]
_HIGH_CONTRAST = ["#000000", "#E41A1C", "#377EB8", "#4DAF4A", "#984EA3", "#FF7F00",
                  "#A65628", "#F781BF"]
_GRAYSCALE = ["#111111", "#555555", "#888888", "#AAAAAA", "#333333", "#666666"]

_PALETTES: Dict[str, List[str]] = {
    "publication": _PUBLICATION,
    "nature_like": _OKABE_ITO,
    "science_like": ["#1B1B1B", "#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00"],
    "cell_like": ["#3B6FB6", "#E8743B", "#19A979", "#945ECF", "#ED4A7B", "#13A4B4"],
}

# Named palettes selectable from the GUI/PlotSpec (override "palette_name").
# The trailing journal-named entries are retained ONLY as back-compat aliases so
# old PlotSpecs with those palette_name values still resolve; they are NOT shown
# in the UI (see USER_PALETTES) and are not journal templates.
NAMED_PALETTES: Dict[str, List[str]] = {
    "publication": _PUBLICATION,
    "colorblind_safe": _OKABE_ITO,
    "high_contrast": _HIGH_CONTRAST,
    "grayscale": _GRAYSCALE,
    # --- legacy aliases (hidden) ---
    "nature_like": _OKABE_ITO,
    "science_like": _PALETTES["science_like"],
    "cell_like": _PALETTES["cell_like"],
}

# Palettes shown in the UI palette chooser (no journal names).
USER_PALETTES: List[str] = ["publication", "colorblind_safe", "high_contrast", "grayscale"]

# Palettes also drive the continuous heatmap/colormap so the WHOLE figure (not just
# categorical colours) follows the chosen palette. All picks are colourblind-aware.
#   publication      -> profile defaults (viridis / RdBu_r)
#   colorblind_safe  -> viridis + PuOr  (both colourblind-safe)
#   high_contrast    -> inferno + seismic (punchy dynamic range / saturated diverging)
#   grayscale        -> Greys + gray  (fully monochrome)
_PALETTE_CMAPS: Dict[str, Dict[str, str]] = {
    "colorblind_safe": {"sequential_cmap": "viridis", "diverging_cmap": "PuOr"},
    "high_contrast": {"sequential_cmap": "inferno", "diverging_cmap": "seismic"},
    "grayscale": {"sequential_cmap": "Greys", "diverging_cmap": "gray"},
}

# Figure width presets (mm). "default" is a comfortable medium size so the very
# first plot reads well on screen and in slides without any tweaking.
WIDTH_PRESETS_MM = {"single": 110.0, "onehalf": 140.0, "double": 180.0, "default": 130.0}

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
    """Resolved publication-style tokens for one profile.

    Defaults are tuned to be *publication-ready out of the box*: readable font
    sizes, strong axis/tick widths, visible markers, and colorblind-aware
    high-contrast colors. GUI/PlotSpec ``style`` overrides refine these.
    """

    name: str
    font_family: List[str] = field(default_factory=lambda: list(_FONT_STACK))
    # --- typography (points) ---
    base_font_pt: float = 11.0
    axis_font_pt: float = 12.0          # axis (x/y) label size
    tick_label_pt: float = 10.0
    legend_pt: float = 10.0
    legend_title_pt: float = 11.0
    title_font_pt: float = 13.0
    annotation_pt: float = 9.5          # gene/mutation/point labels
    panel_label_pt: float = 13.0
    font_weight: str = "normal"
    text_color: str = "#1a1a1a"
    # --- axes ---
    spine_width_pt: float = 1.1
    tick_width: float = 1.0
    tick_length: float = 4.5
    tick_direction: str = "out"
    show_top_spine: bool = False
    show_right_spine: bool = False
    grid: bool = False
    grid_width: float = 0.6
    grid_alpha: float = 0.35
    # --- data marks ---
    line_width_pt: float = 1.8
    marker_size: float = 45.0           # scatter s=
    marker_edge_width: float = 0.6
    marker_alpha: float = 0.9
    regression_line_width: float = 2.0
    errorbar_line_width: float = 1.1
    errorbar_capsize: float = 3.5
    bar_edge_width: float = 0.9
    # --- legend ---
    legend_frameon: bool = False
    legend_loc: str = "best"
    legend_outside: bool = False
    legend_ncol: int = 1
    # --- sizing / colors ---
    single_column_width_mm: float = 110.0
    double_column_width_mm: float = 180.0
    default_width_mm: float = 130.0
    export_dpi: int = 300
    preferred_exports: List[str] = field(default_factory=lambda: ["svg", "pdf", "png"])
    palette_role: str = "publication"
    palette: List[str] = field(default_factory=lambda: list(_PUBLICATION))
    sequential_cmap: str = "viridis"
    diverging_cmap: str = "RdBu_r"
    is_learned: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)

    def figure_size_inches(self, width: str = "default", aspect: float = 0.72) -> tuple[float, float]:
        """Return ``(width_in, height_in)`` for a width preset and aspect."""
        w_mm = WIDTH_PRESETS_MM.get(width)
        if w_mm is None:
            w_mm = {"single": self.single_column_width_mm,
                    "double": self.double_column_width_mm}.get(width, self.default_width_mm)
        w_in = mm_to_inches(w_mm)
        return (w_in, w_in * float(aspect))

    def color_for(self, index: int) -> str:
        palette = self.palette or _PUBLICATION
        return palette[index % len(palette)]

    def rc_params(self) -> Dict[str, Any]:
        """Matplotlib rcParams encoding this profile's tokens."""
        # The family list is written explicitly rather than as the generic "sans-serif":
        # text artists keep the family they were created with, and a generic family is
        # resolved through the *global* rcParams at save time (outside this profile's
        # rc_context), which silently replaced Arial with DejaVu Sans in every export.
        return {
            "font.family": list(self.font_family),
            "font.sans-serif": self.font_family,
            "font.size": self.base_font_pt,
            "font.weight": self.font_weight,
            "text.color": self.text_color,
            "axes.titlesize": self.title_font_pt,
            "axes.titleweight": "bold",
            "axes.labelsize": self.axis_font_pt,
            "axes.labelcolor": self.text_color,
            "axes.labelweight": self.font_weight,
            "axes.edgecolor": self.text_color,
            "xtick.color": self.text_color,
            "ytick.color": self.text_color,
            "xtick.labelsize": self.tick_label_pt,
            "ytick.labelsize": self.tick_label_pt,
            "legend.fontsize": self.legend_pt,
            "legend.title_fontsize": self.legend_title_pt,
            "legend.frameon": self.legend_frameon,
            "axes.linewidth": self.spine_width_pt,
            "lines.linewidth": self.line_width_pt,
            "xtick.major.width": self.tick_width,
            "ytick.major.width": self.tick_width,
            "xtick.major.size": self.tick_length,
            "ytick.major.size": self.tick_length,
            "xtick.direction": self.tick_direction,
            "ytick.direction": self.tick_direction,
            "axes.spines.top": self.show_top_spine,
            "axes.spines.right": self.show_right_spine,
            "axes.grid": self.grid,
            "grid.linewidth": self.grid_width,
            "grid.alpha": self.grid_alpha,
            "figure.dpi": 110,
            "savefig.dpi": self.export_dpi,
            "savefig.bbox": "tight",
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }

    def apply(self) -> mpl.rc_context:
        """Return an rc_context that temporarily applies this profile."""
        return mpl.rc_context(rc=self.rc_params())

    def with_overrides(self, overrides: Optional[Dict[str, Any]]) -> "StyleProfile":
        """Return a copy with GUI/PlotSpec style overrides applied."""
        import copy

        if not overrides:
            return self
        clone = copy.deepcopy(self)
        pal = overrides.get("palette_name")
        if pal and pal in NAMED_PALETTES:
            clone.palette = list(NAMED_PALETTES[pal])
            clone.palette_role = pal
            # Palettes like grayscale also drive the heatmap colormaps (an explicit
            # sequential_cmap/diverging_cmap override in the loop below still wins).
            cmaps = _PALETTE_CMAPS.get(pal)
            if cmaps:
                clone.sequential_cmap = cmaps["sequential_cmap"]
                clone.diverging_cmap = cmaps["diverging_cmap"]
        for key, val in overrides.items():
            if key in ("palette_name",):
                continue
            if hasattr(clone, key) and val is not None:
                setattr(clone, key, val)
        # A font_family override may arrive as a single family name (e.g. "Arial");
        # turn it into a proper fallback stack so matplotlib resolves it (and falls
        # back gracefully if that font isn't installed).
        if isinstance(clone.font_family, str):
            fam = clone.font_family.strip()
            clone.font_family = [f for f in (fam, "Arial", "Helvetica", "DejaVu Sans",
                                             "sans-serif") if f]
        return clone


def _parse_profile(name: str, raw: Dict[str, Any]) -> StyleProfile:
    # Journal print sizes in the starter JSON (~7pt) are too small for on-screen
    # / general export use, so we keep the publication-ready dataclass defaults
    # and only take per-profile palette, colormaps, and column widths.
    return StyleProfile(
        name=name,
        palette=_PALETTES.get(name, _PUBLICATION),
        palette_role=str(raw.get("palette_role", name)),
        sequential_cmap=_SEQUENTIAL_CMAP.get(name, "viridis"),
        diverging_cmap=_DIVERGING_CMAP.get(name, "RdBu_r"),
        single_column_width_mm=float(raw.get("single_column_width_mm", 110)) if float(raw.get("single_column_width_mm", 110)) >= 100 else 110.0,
    )


@lru_cache(maxsize=1)
def _load_raw(path: Optional[str] = None) -> Dict[str, Any]:
    profiles_path = path or _PROFILES_PATH
    with open(profiles_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


# --- learned profiles (derived from the local reference library) ------------

_LEARNED_DIR = resource_path("style_profiles", "learned")


def _learned_files() -> List[str]:
    if not os.path.isdir(_LEARNED_DIR):
        return []
    return sorted(f for f in os.listdir(_LEARNED_DIR) if f.endswith(".json"))


@lru_cache(maxsize=1)
def _load_learned_raw() -> Dict[str, Dict[str, Any]]:
    """Return {profile_name: raw_dict} for every learned profile JSON."""
    out: Dict[str, Dict[str, Any]] = {}
    for fn in _learned_files():
        try:
            with open(os.path.join(_LEARNED_DIR, fn), "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            name = raw.get("profile_name") or os.path.splitext(fn)[0]
            out[name] = raw
        except Exception:
            continue
    return out


def _parse_learned(name: str, raw: Dict[str, Any]) -> StyleProfile:
    typo = raw.get("typography", {})
    lines = raw.get("lines", {})
    color = raw.get("color", {})
    base_name = raw.get("base_profile", "nature_like")
    base_palette = _PALETTES.get(base_name, _PUBLICATION)
    d = StyleProfile(name=name)   # publication-ready defaults
    # Learned profiles refine palette/colormap; keep publication-readable type/marks
    # (clamp any stale small font sizes up to readable minimums).
    d.is_learned = True
    d.extra = raw
    d.palette = list(color.get("palette", base_palette))
    d.palette_role = color.get("policy", "learned")
    d.sequential_cmap = color.get("sequential_cmap", _SEQUENTIAL_CMAP.get(base_name, "viridis"))
    d.diverging_cmap = color.get("diverging_cmap", _DIVERGING_CMAP.get(base_name, "RdBu_r"))
    d.base_font_pt = max(float(typo.get("base_font_pt", d.base_font_pt)), 10.0)
    d.axis_font_pt = max(float(typo.get("axis_font_pt", d.axis_font_pt)), 11.0)
    d.title_font_pt = max(float(typo.get("title_font_pt", d.title_font_pt)), 12.0)
    if raw.get("export", {}).get("formats"):
        d.preferred_exports = list(raw["export"]["formats"])
    return d


def _publication_profile() -> StyleProfile:
    return StyleProfile(name="publication", palette=list(_PUBLICATION),
                        palette_role="publication", sequential_cmap="viridis",
                        diverging_cmap="RdBu_r")


# v0.6: Make My Figure exposes ONE style identity — "Publication". Older PlotSpecs
# and learned profiles used journal-named profiles; these are no longer separate
# styles. They are transparently migrated to Publication on load so saved files
# keep working. (This is a scope decision, not a claim about journal templates.)
LEGACY_STYLE_ALIASES: Dict[str, str] = {
    "nature_like": "publication",
    "science_like": "publication",
    "cell_like": "publication",
    "nature_like_learned": "publication",
    "science_like_learned": "publication",
    "cell_like_learned": "publication",
    "journal_like": "publication",
}


def is_legacy_style_name(name: Optional[str]) -> bool:
    """True if ``name`` is a removed journal-named profile (migrates to Publication)."""
    return name in LEGACY_STYLE_ALIASES


def normalize_style_name(name: Optional[str]) -> str:
    """Map any style name to a current one; removed journal names → 'publication'."""
    if not name:
        return "publication"
    return LEGACY_STYLE_ALIASES.get(name, name)


def list_profiles(path: Optional[str] = None) -> List[str]:
    """User-facing style profiles. v0.6 exposes a single 'publication' identity.

    Journal-named starter/learned profiles are intentionally NOT listed. Any
    learned profile explicitly named ``publication*`` (e.g. benchmark-derived
    aggregate defaults) is included so it can be selected/inspected.
    """
    learned_publication = [n for n in _load_learned_raw().keys() if n.startswith("publication")]
    # Defensive: never expose a journal-named profile even if a learned file is
    # polluted (e.g. a stale install). The single visible identity is Publication.
    _forbidden = ("nature", "science", "cell", "journal", "jama", "nejm", "lancet", "plos")
    learned_publication = [n for n in learned_publication
                           if not any(tok in n.lower() for tok in _forbidden)]
    return ["publication"] + learned_publication


def load_profile(name: str, path: Optional[str] = None) -> StyleProfile:
    """Load a style profile. Removed journal-named profiles migrate to Publication."""
    name = normalize_style_name(name)
    if name == "publication":
        return _publication_profile()
    profiles = _load_raw(path).get("profiles", {})
    if name in profiles:
        return _parse_profile(name, profiles[name])
    learned = _load_learned_raw()
    if name in learned:
        return _parse_learned(name, learned[name])
    raise KeyError(
        f"Unknown style profile '{name}'. Available: {sorted(['publication'] + list(learned))}"
    )


def load_all_profiles(path: Optional[str] = None) -> Dict[str, StyleProfile]:
    return {name: load_profile(name, path) for name in list_profiles(path)}
