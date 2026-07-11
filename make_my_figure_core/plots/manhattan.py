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
    base_metadata,
    coerce_numeric,
    figure_size,
    get_mapping,
    require_columns,
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

        # Threshold lines.
        gw = float(neg_log10([GENOME_WIDE_SIG])[0])
        sug = float(neg_log10([SUGGESTIVE_SIG])[0])
        ax.axhline(gw, color="#C0392B", ls="--", lw=style.line_width_pt,
                   label="Genome-wide (5e-8)")
        ax.axhline(sug, color="#7F8C8D", ls=":", lw=style.line_width_pt,
                   label="Suggestive (1e-5)")

        ax.set_xticks(tick_pos)
        ax.set_xticklabels(tick_lab, fontsize=max(style.tick_label_pt - 1, 9.0),
                           rotation=90 if len(tick_lab) > 12 else 0)
        ax.set_xlabel(spec.get("layout", {}).get("x_label", "Chromosome"))
        ax.set_ylabel(spec.get("layout", {}).get("y_label", "-log10(p)"))
        ax.margins(x=0.01)
        ax.set_ylim(bottom=0)
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        style_axes(ax, style)
        ax.legend(loc="upper right", frameon=getattr(style, "legend_frameon", False),
                  fontsize=style.legend_pt)
        fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=[chrom, pos, p, snp])
    meta["n_variants"] = int(len(work))
    meta["n_chromosomes"] = len(tick_lab)
    meta["n_genome_wide"] = int(n_gw)
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
