"""Publication style engine — the single manuscript-ready visual identity.

Make My Figure ships ONE user-facing style: **Publication**. This module is the
documented source of truth for that style and its accessibility variants, plus a
small set of *aggregate* refinements derived from the benchmark-recreation work
(see ``docs/V0_6_PUBLICATION_STYLE_LESSONS.md``). These are general publication
design defaults — NOT an official journal template and not a compliance claim.

The variants are palette swaps over the same readable Publication tokens:
- ``publication``      — the default polished palette,
- ``publication_accessible`` — a colorblind-safe palette (Okabe–Ito),
- ``publication_grayscale``  — a print/grayscale-friendly palette.

``recommended_overrides()`` returns *advisory* style overrides that encode the
aggregate lessons (e.g. move the legend outside once a plot has many series).
Callers apply them through the normal ``StyleProfile.with_overrides`` path, so
nothing here changes rendering unless a caller opts in.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from make_my_figure_core.styles.engine import (
    NAMED_PALETTES,
    StyleProfile,
    load_profile,
)

# Palette variants offered under the single Publication style (no journal names).
PUBLICATION_PALETTES: Dict[str, str] = {
    "publication": "publication",
    "publication_accessible": "colorblind_safe",
    "publication_grayscale": "grayscale",
}

# Aggregate lessons distilled from the benchmark recreations (general defaults).
STYLE_LESSONS = (
    "Keep a clear title > axis > tick > annotation font hierarchy with readable "
    "minimums; move the legend outside the axes once a plot has many series; use "
    "slim, few-tick colorbars on heatmaps; cap on-figure point labels and use light "
    "threshold guide lines on volcano plots; leave generous outer and inter-panel "
    "margins; prefer editable vector text on export.")

# Series count at/above which a legend reads better placed outside the axes.
LEGEND_OUTSIDE_SERIES_THRESHOLD = 4


def publication_profile() -> StyleProfile:
    """The canonical Publication style profile."""
    return load_profile("publication")


def publication_variant(name: str = "publication") -> StyleProfile:
    """A Publication profile with an accessibility palette applied.

    ``name`` is one of :data:`PUBLICATION_PALETTES` keys. Unknown names fall back
    to the default Publication palette.
    """
    profile = load_profile("publication")
    palette_name = PUBLICATION_PALETTES.get(name, "publication")
    if palette_name != "publication":
        profile = profile.with_overrides({"palette_name": palette_name})
    return profile


def recommended_overrides(plot_type: Optional[str] = None, *,
                          n_series: Optional[int] = None) -> Dict[str, Any]:
    """Advisory Publication style overrides encoding the aggregate lessons.

    Returns a (possibly empty) dict of ``StyleProfile.with_overrides`` keys.
    Purely advisory: callers choose whether to apply them.
    """
    overrides: Dict[str, Any] = {}
    if n_series is not None and n_series >= LEGEND_OUTSIDE_SERIES_THRESHOLD:
        overrides["legend_outside"] = True
    return overrides


def available_palette_names() -> list[str]:
    """User-facing palette names for the Publication style (no journal names)."""
    return [p for p in ("publication", "colorblind_safe", "high_contrast", "grayscale")
            if p in NAMED_PALETTES]
