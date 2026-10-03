"""Oncoprint-style mutation grid: genes (rows) x samples (cols)."""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch, Rectangle

from make_my_figure_core.plots.base import (
    RenderResult,
    base_metadata,
    figure_size,
    get_mapping,
    require_columns,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "oncoprint_mutation_heatmap"

_BG = "#ECECEC"


def render(spec: Dict[str, Any], df, style: StyleProfile) -> RenderResult:
    sample_col = get_mapping(spec, "sample", "patient_id")
    gene_col = get_mapping(spec, "row", "gene")
    fill_col = get_mapping(spec, "fill", "alteration_type")

    require_columns(df, [sample_col, gene_col, fill_col], context=PLOT_TYPE)
    work = df.copy()
    work[sample_col] = work[sample_col].astype(str)
    work[gene_col] = work[gene_col].astype(str)

    # Order rows by number of altered samples (descending) - the oncoprint convention -
    # or keep the input order (``order: "input"``), which suits categorical status
    # matrices where the row/column order carries meaning.
    order_mode = str(get_mapping(spec, "order", "frequency")).lower()
    gene_freq = work.groupby(gene_col)[sample_col].nunique().sort_values(ascending=False, kind="stable")
    if order_mode == "input":
        genes: List[str] = list(dict.fromkeys(work[gene_col].tolist()))
    else:
        genes = list(gene_freq.index)
    samples: List[str] = list(dict.fromkeys(work[sample_col].tolist()))

    # Map (gene, sample) -> alteration type (last wins if multiple).
    cell: Dict[tuple, str] = {}
    for _, r in work.iterrows():
        cell[(r[gene_col], r[sample_col])] = r[fill_col]

    # Memo-style sample ordering: sort by mutation pattern across ordered genes.
    def _sample_key(s: str):
        return tuple(1 if (g, s) in cell else 0 for g in genes)

    if order_mode != "input":
        samples = sorted(samples, key=_sample_key, reverse=True)
    show_sample_labels = get_mapping(spec, "show_sample_labels", None)
    if show_sample_labels is None:
        show_sample_labels = len(samples) <= 12

    alt_types = list(dict.fromkeys(work[fill_col].astype(str).tolist()))
    color_map = {a: style.color_for(i) for i, a in enumerate(alt_types)}

    warnings: List[str] = []

    with style.apply():
        fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.7))
        n_g, n_s = len(genes), len(samples)
        for gi, g in enumerate(genes):
            yrow = n_g - 1 - gi
            for si, s in enumerate(samples):
                ax.add_patch(Rectangle((si, yrow), 0.95, 0.9, facecolor=_BG,
                                       edgecolor="white", linewidth=0.3))
                alt = cell.get((g, s))
                if alt is not None:
                    ax.add_patch(Rectangle((si, yrow + 0.2), 0.95, 0.5,
                                           facecolor=color_map[str(alt)],
                                           edgecolor="none"))
        ax.set_xlim(0, n_s)
        ax.set_ylim(0, n_g)
        ax.set_yticks([n_g - 1 - i + 0.45 for i in range(n_g)])
        ax.set_yticklabels(genes)
        if show_sample_labels:
            ax.set_xticks(range(n_s))
            ax.set_xticklabels(samples)
            ax.set_xlabel(spec.get("layout", {}).get("x_label", ""))
        else:
            ax.set_xticks([])
            ax.set_xlabel(spec.get("layout", {}).get("x_label", f"Samples (n={n_s})"))
        title = spec.get("layout", {}).get("title")
        if title:
            ax.set_title(title)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(length=0)
        handles = [Patch(facecolor=color_map[a], label=str(a)) for a in alt_types]
        ax.legend(handles=handles, title=str(fill_col), frameon=False,
                  loc="center left", bbox_to_anchor=(1.0, 0.5))
        fig.tight_layout()

    meta = base_metadata(spec, style, work, used_columns=[sample_col, gene_col, fill_col])
    meta["n_genes"] = len(genes)
    meta["n_samples"] = len(samples)
    meta["alteration_types"] = [str(a) for a in alt_types]
    meta["gene_frequency"] = {g: int(gene_freq[g]) for g in genes}
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
