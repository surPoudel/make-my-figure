"""Static UpSet plot: intersections among many sets (a Venn alternative).

Two input modes:

* **Binary membership columns** — ``mapping['sets']`` is a list of column names
  holding 0/1 (or boolean) membership; each row is an element. If ``sets`` is
  omitted, every 0/1 column is used.
* **Long form** — ``mapping['element']`` + ``mapping['set']`` (a column of set
  names); membership is pivoted to binary internally.

The figure shows intersection-size bars (top), per-set size bars (left) and a
dot matrix (filled dots = the sets that define each intersection).

Limitation: this is a static UpSet (no interactive sorting/queries); the number
of intersections shown is capped for legibility.
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from make_my_figure_core.plots.base import (
    RenderError,
    RenderResult,
    apply_publication_layout,
    base_metadata,
    get_mapping,
    require_columns,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "upset_plot"
_MAX_INTERSECTIONS = 20


def _binary_membership(df: pd.DataFrame, spec: Dict[str, Any]) -> pd.DataFrame:
    """Return a boolean elements x sets membership frame from either input mode."""
    sets = get_mapping(spec, "sets", None)
    element = get_mapping(spec, "element", None)
    set_col = get_mapping(spec, "set", None)

    if element and set_col and element in df.columns and set_col in df.columns:
        # Long form -> pivot to binary membership.
        long = df[[element, set_col]].dropna()
        mem = pd.crosstab(long[element], long[set_col])
        return mem > 0

    if isinstance(sets, str):
        sets = [sets]
    if not sets:
        # Auto-detect binary 0/1 columns.
        sets = []
        for c in df.columns:
            vals = pd.to_numeric(df[c], errors="coerce").dropna().unique()
            if len(vals) and set(np.unique(vals)).issubset({0, 1}):
                sets.append(c)
    if not sets or len(sets) < 2:
        raise RenderError(
            f"{PLOT_TYPE}: need >=2 binary set columns (or element+set columns). "
            f"Provide mapping['sets'] as a list of 0/1 columns. Columns: {list(df.columns)}")
    require_columns(df, sets, context=PLOT_TYPE)
    mem = df[sets].apply(lambda s: pd.to_numeric(s, errors="coerce").fillna(0) > 0)
    return mem


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    mem = _binary_membership(df, spec)
    set_names = list(mem.columns)
    warnings: List[str] = []

    # Per-set sizes, ordered largest first (top row = biggest set).
    set_sizes = {s: int(mem[s].sum()) for s in set_names}
    set_order = sorted(set_names, key=lambda s: set_sizes[s], reverse=True)

    # Intersection = the exact combination of sets each element belongs to.
    combos: Dict[frozenset, int] = {}
    for _, row in mem.iterrows():
        key = frozenset(s for s in set_order if bool(row[s]))
        if key:
            combos[key] = combos.get(key, 0) + 1
    if not combos:
        raise RenderError(f"{PLOT_TYPE}: no non-empty set memberships found.")
    inter = sorted(combos.items(), key=lambda kv: kv[1], reverse=True)[:_MAX_INTERSECTIONS]
    n_inter = len(inter)
    n_sets = len(set_order)
    if len(combos) > n_inter:
        warnings.append(f"Showing top {n_inter} of {len(combos)} intersections.")

    layout = spec.get("layout", {}) or {}
    w_in, _ = style.figure_size_inches(str(layout.get("column_width", "double")).lower(), aspect=1.0)
    w_in = max(w_in, 6.0)
    h_in = max(4.0, 1.6 + 0.42 * n_sets + 2.2)

    with style.apply():
        fig = plt.figure(figsize=(w_in, h_in))
        gs = fig.add_gridspec(2, 2, width_ratios=[1.0, 3.2], height_ratios=[2.2, 1.0],
                              wspace=0.05, hspace=0.08)
        ax_bars = fig.add_subplot(gs[0, 1])
        ax_matrix = fig.add_subplot(gs[1, 1], sharex=ax_bars)
        ax_sets = fig.add_subplot(gs[1, 0], sharey=ax_matrix)

        xs = np.arange(n_inter)
        sizes = [c for _, c in inter]
        ax_bars.bar(xs, sizes, color=style.color_for(0), width=0.6,
                    edgecolor=style.text_color, linewidth=style.bar_edge_width)
        for xi, s in zip(xs, sizes):
            ax_bars.annotate(str(s), (xi, s), ha="center", va="bottom",
                             fontsize=max(7.0, style.annotation_pt - 0.5))
        ax_bars.set_ylabel("Intersection size")
        ax_bars.margins(y=0.15)
        ax_bars.tick_params(labelbottom=False, bottom=False)
        for sp in ("top", "right"):
            ax_bars.spines[sp].set_visible(False)

        # Dot matrix: rows = sets (top = biggest), cols = intersections.
        yidx = {s: i for i, s in enumerate(reversed(set_order))}  # bottom-up so row0 at bottom
        for xi, (combo, _) in enumerate(inter):
            members = [yidx[s] for s in set_order if s in combo]
            # background (all) dots
            ax_matrix.scatter([xi] * n_sets, list(range(n_sets)), s=style.marker_size * 1.1,
                              color="#D9D9D9", zorder=2)
            if members:
                ax_matrix.plot([xi, xi], [min(members), max(members)], color=style.text_color,
                               lw=style.line_width_pt, zorder=3)
                ax_matrix.scatter([xi] * len(members), members, s=style.marker_size * 1.1,
                                  color=style.text_color, zorder=4)
        ax_matrix.set_xlim(-0.6, n_inter - 0.4)
        ax_matrix.set_ylim(-0.6, n_sets - 0.4)
        ax_matrix.set_xticks([])
        ax_matrix.set_yticks([])
        for sp in ax_matrix.spines.values():
            sp.set_visible(False)
        ax_matrix._colorbar = True  # decorative panel: skip missing-label QA check

        # Per-set size bars (horizontal), aligned to matrix rows, growing left.
        rows = [yidx[s] for s in set_order]
        ax_sets.barh(rows, [set_sizes[s] for s in set_order], color=style.color_for(1),
                     height=0.6, edgecolor=style.text_color, linewidth=style.bar_edge_width)
        ax_sets.set_yticks(list(range(n_sets)))
        ax_sets.set_yticklabels([s for s in reversed(set_order)], fontsize=style.tick_label_pt)
        ax_sets.set_xlabel("Set size")
        ax_sets.invert_xaxis()
        ax_sets.margins(y=0.05)
        for sp in ("top", "left"):
            ax_sets.spines[sp].set_visible(False)

        # Reserve a left margin sized to the longest set-name label — these grow
        # leftward and were being clipped. User margin controls override this.
        longest = max((len(str(s)) for s in set_order), default=4)
        fig.subplots_adjust(left=min(0.45, 0.10 + 0.012 * longest),
                            right=0.98, bottom=0.08, top=0.90 if layout.get("title") else 0.97)

        title = layout.get("title")
        if title:
            fig.suptitle(title, fontsize=style.title_font_pt, fontweight="bold")
        apply_publication_layout(fig, ax_sets, spec, style)

    meta = base_metadata(spec, style, df, used_columns=set_names)
    meta["n_sets"] = n_sets
    meta["n_intersections"] = int(len(combos))
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
