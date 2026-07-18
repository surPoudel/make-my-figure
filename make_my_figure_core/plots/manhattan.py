"""Manhattan plot for genome-wide association studies (GWAS).

Plots -log10(p) against genomic position, laying chromosomes end to end with
alternating colors, a genome-wide significance line (5e-8) and a suggestive
line (1e-5).
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from make_my_figure_core.plots._v04_shared import (
    GENOME_WIDE_SIG,
    SUGGESTIVE_SIG,
    neg_log10,
)
from make_my_figure_core.plots.base import (
    RenderError,
    RenderResult,
    apply_publication_layout,
    base_metadata,
    coerce_numeric,
    figure_size,
    get_mapping,
    place_legend,
    require_columns,
    resolve_legend_location,
    style_axes,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "manhattan_plot"

# Natural chromosome ordering: 1..22, X, Y, MT/M.
_CHROM_ORDER = {str(i): i for i in range(1, 23)}
_CHROM_ORDER.update({"X": 23, "Y": 24, "MT": 25, "M": 25})


def _chrom_key(label: str):
    s = str(label).upper().replace("CHR", "").strip()
    if s in _CHROM_ORDER:
        return (_CHROM_ORDER[s], s)
    # Unknown labels sort last but stably.
    return (999, s)


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    chrom = get_mapping(spec, "chrom", required=True, context=PLOT_TYPE)
    pos = get_mapping(spec, "pos", required=True, context=PLOT_TYPE)
    p = get_mapping(spec, "p", required=True, context=PLOT_TYPE)
    snp = get_mapping(spec, "snp", None)

    require_columns(df, [chrom, pos, p], context=PLOT_TYPE)
    work = df.copy()
    work[pos] = coerce_numeric(work, pos, context=PLOT_TYPE)
    pvals = coerce_numeric(work, p, context=PLOT_TYPE)
    work["__p"] = pvals
    warnings: List[str] = []
    bad = ~np.isfinite(work["__p"].to_numpy(float)) | (work["__p"] <= 0) | (work["__p"] > 1)
    if bad.any():
        warnings.append(f"{int(bad.sum())} variant(s) had out-of-range/non-numeric p-values; "
                        "clipped into (0, 1].")

    # Chromosome ordering + cumulative x layout.
    chrom_labels = sorted(work[chrom].astype(str).unique().tolist(), key=_chrom_key)
    work["__chrom"] = work[chrom].astype(str)

    offset = 0.0
    tick_pos: List[float] = []
    tick_lab: List[str] = []
    xs_all: List[np.ndarray] = []
    ys_all: List[np.ndarray] = []
    colors: List[str] = []
    n_gw = 0
    gap = 0.0

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.5))
        for ci, clab in enumerate(chrom_labels):
            sub = work[work["__chrom"] == clab].sort_values(pos)
            positions = sub[pos].to_numpy(float)
            if positions.size == 0:
                continue
            pmin = np.nanmin(positions)
            xcoord = offset + (positions - pmin)
            y = neg_log10(sub["__p"].to_numpy(float))
            col = style.color_for(0) if ci % 2 == 0 else style.color_for(1)
            ax.scatter(xcoord, y, s=max(6.0, style.marker_size * 0.35), color=col,
                       edgecolors="none", alpha=style.marker_alpha, zorder=2)
            span = float(np.nanmax(positions) - pmin) or 1.0
            tick_pos.append(offset + span / 2.0)
            tick_lab.append(clab)
            n_gw += int(np.sum(sub["__p"].to_numpy(float) <= GENOME_WIDE_SIG))
            offset += span
            gap = max(gap, span * 0.02)
            offset += gap
            xs_all.append(xcoord)
            ys_all.append(y)
            colors.append(col)

        # Genome-wide cutoff line — fully user-controllable (optional, editable
        # threshold / color / width / style / label). Default threshold 5e-8.
        show_cutoff = bool(get_mapping(spec, "show_cutoff_line", True))
        if show_cutoff:
            gw_thresh = float(get_mapping(spec, "genome_wide_threshold", GENOME_WIDE_SIG))
            gw = float(neg_log10([gw_thresh])[0])
            gw_color = str(get_mapping(spec, "cutoff_line_color", "#C0392B"))
            gw_ls = str(get_mapping(spec, "cutoff_line_style", "--"))
            gw_lw = float(get_mapping(spec, "cutoff_line_width", style.line_width_pt))
            gw_label = get_mapping(spec, "cutoff_line_label", f"Genome-wide ({gw_thresh:g})")
            ax.axhline(gw, color=gw_color, ls=gw_ls, lw=gw_lw, label=str(gw_label))
        # Suggestive line is optional too (off by default keeps the plot clean unless asked).
        if bool(get_mapping(spec, "show_suggestive_line", True)):
            sug_thresh = float(get_mapping(spec, "suggestive_threshold", SUGGESTIVE_SIG))
            sug = float(neg_log10([sug_thresh])[0])
            ax.axhline(sug, color="#7F8C8D", ls=":", lw=style.line_width_pt,
                       label=f"Suggestive ({sug_thresh:g})")

        # X tick rotation: layout control (0/45/90/custom), else auto by chromosome count.
        _xr = get_mapping(spec, "x_tick_rotation", spec.get("layout", {}).get("x_tick_rotation"))
        if _xr is None or str(_xr) == "auto":
            rot = 90 if len(tick_lab) > 12 else 0
        else:
            rot = {"horizontal": 0, "vertical": 90}.get(str(_xr).lower(), int(_xr))
        ax.set_xticks(tick_pos)
        ax.set_xticklabels(tick_lab, fontsize=max(style.tick_label_pt - 1, 9.0),
                           rotation=rot, ha=("right" if 0 < rot < 90 else "center"))
        ax.set_xlabel(spec.get("layout", {}).get("x_label", "Chromosome"))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", "-log10(p)"))
        ax.margins(x=0.01)
        ax.set_ylim(bottom=0)
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        style_axes(ax, style)
        if ax.get_legend_handles_labels()[0]:
            place_legend(ax, style, location=resolve_legend_location(spec, style)
                         if spec.get("layout", {}).get("legend_location") else ("upper right", None, None))
        fig.tight_layout()
        apply_publication_layout(fig, ax, spec, style)

    meta = base_metadata(spec, style, work, used_columns=[chrom, pos, p, snp])
    meta["n_variants"] = int(len(work))
    meta["n_chromosomes"] = len(tick_lab)
    meta["n_genome_wide"] = int(n_gw)
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
