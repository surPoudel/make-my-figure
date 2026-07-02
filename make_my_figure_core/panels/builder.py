"""Compose panels into a labelled multi-panel figure and export it.

Panels are rendered (from their PlotSpec if not pre-rendered) and embedded as
high-resolution images in a clean grid, with bold vector panel labels drawn on
the composite. Each individual panel remains independently exportable as vector
(SVG/PDF) from its own PlotSpec; the composite embeds panel *content* as
``panel_dpi`` raster while keeping labels/titles as editable vector text. This
is a deliberate, documented trade-off that always produces a correct, aligned
figure without a fragile SVG-splicing step.
"""

from __future__ import annotations

import io
import json
import math
import os
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from make_my_figure_core.panels.models import FigureLayout, MultiPanelFigure, Panel
from make_my_figure_core.styles.engine import mm_to_inches

_VECTOR_TEXT_RC = {"svg.fonttype": "none", "pdf.fonttype": 42, "ps.fonttype": 42}


def _render_panel_figure(panel: Panel) -> Figure:
    """Return the panel's Figure, rendering from its PlotSpec if needed."""
    if panel.figure is not None:
        return panel.figure
    if panel.plot_spec is None or panel.table is None:
        raise ValueError(f"Panel '{panel.label}' has neither a figure nor a plot_spec+table.")
    from make_my_figure_core.plots.registry import render

    spec = dict(panel.plot_spec)
    if panel.stats_spec is not None and "statistics" not in spec:
        spec["statistics"] = panel.stats_spec
    aux = panel.aux or None
    result = render(spec, panel.table, aux=aux)
    return result.figure


def _figure_to_image(fig: Figure, dpi: int) -> np.ndarray:
    """Rasterize a figure to an RGBA image array (tight bbox)."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    buf.seek(0)
    img = plt.imread(buf)
    buf.close()
    return img


def _auto_grid(n: int, layout: FigureLayout) -> Tuple[int, int]:
    if layout.ncols and layout.ncols > 0:
        ncols = int(layout.ncols)
    else:
        ncols = max(1, int(math.ceil(math.sqrt(n))))
    nrows = layout.nrows if (layout.nrows and layout.nrows > 0) else int(math.ceil(n / ncols))
    return nrows, ncols


def build_figure(mpf: MultiPanelFigure) -> Figure:
    """Render and compose all panels into a single labelled Figure."""
    layout = mpf.layout
    panels = list(mpf.panels)
    if not panels:
        raise ValueError("Cannot build a multi-panel figure with no panels.")
    mpf.autolabel()

    # Render + rasterize each panel; capture aspect (height/width).
    images: List[np.ndarray] = []
    aspects: List[float] = []
    own_figs: List[Figure] = []
    for panel in panels:
        fig = _render_panel_figure(panel)
        img = _figure_to_image(fig, layout.panel_dpi)
        images.append(img)
        h, w = img.shape[0], img.shape[1]
        aspects.append(h / w if w else 1.0)
        # Close figures we rendered ourselves to free memory.
        if panel.figure is None:
            own_figs.append(fig)

    n = len(panels)
    nrows, ncols = _auto_grid(n, layout)

    # Row height ratios from the median panel aspect in each row (equal columns).
    row_ratios = []
    for r in range(nrows):
        row_aspects = [aspects[i] for i in range(r * ncols, min((r + 1) * ncols, n))]
        row_ratios.append(float(np.median(row_aspects)) if row_aspects else 1.0)
    if layout.height_ratios and len(layout.height_ratios) == nrows:
        row_ratios = list(layout.height_ratios)

    fig_w_in = mm_to_inches(layout.fig_width_mm)
    col_w_in = fig_w_in / ncols
    if layout.fig_height_mm:
        fig_h_in = mm_to_inches(layout.fig_height_mm)
    else:
        fig_h_in = col_w_in * sum(row_ratios) * (1.0 + layout.hspace)
        fig_h_in = max(fig_h_in, 1.5)

    with plt.rc_context(_VECTOR_TEXT_RC):
        comp = plt.figure(figsize=(fig_w_in, fig_h_in), facecolor=layout.background)
        gs = comp.add_gridspec(
            nrows, ncols, wspace=layout.wspace, hspace=layout.hspace,
            width_ratios=layout.width_ratios if (layout.width_ratios and len(layout.width_ratios) == ncols) else None,
            height_ratios=row_ratios,
        )
        for i, panel in enumerate(panels):
            r, c = divmod(i, ncols)
            ax = comp.add_subplot(gs[r, c])
            ax.imshow(images[i], aspect="auto", interpolation="antialiased")
            ax.set_xticks([]); ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)
            if layout.show_titles and panel.title:
                ax.set_title(panel.title, fontsize=layout.label_size * 0.8)
            # Bold panel label, top-left, just outside the axes.
            ax.text(layout.label_dx, layout.label_dy, panel.label,
                    transform=ax.transAxes, ha="right", va="bottom",
                    fontsize=layout.label_size, fontweight=layout.label_weight,
                    color="#000000", clip_on=False)
        # Hide any unused trailing cells.
        for j in range(n, nrows * ncols):
            r, c = divmod(j, ncols)
            ax = comp.add_subplot(gs[r, c])
            ax.axis("off")

    for f in own_figs:
        plt.close(f)
    return comp


def export_multipanel(fig: Figure, base_path: str, formats: List[str], dpi: int = 300) -> List[str]:
    """Save the composite figure in each requested format."""
    import matplotlib as mpl

    valid = {"svg", "png", "pdf", "tiff", "eps"}
    written: List[str] = []
    os.makedirs(os.path.dirname(os.path.abspath(base_path)) or ".", exist_ok=True)
    with mpl.rc_context(_VECTOR_TEXT_RC):
        for fmt in formats:
            fmt = fmt.lower()
            if fmt not in valid:
                continue
            out = f"{base_path}.{fmt}"
            kwargs: Dict[str, Any] = {"bbox_inches": "tight", "facecolor": fig.get_facecolor()}
            if fmt in ("png", "tiff"):
                kwargs["dpi"] = dpi
            if fmt == "tiff":
                kwargs["pil_kwargs"] = {"compression": "tiff_lzw"}
            fig.savefig(out, format=fmt, **kwargs)
            written.append(out)
    return written


def draft_legend(mpf: MultiPanelFigure) -> str:
    """Generate a *draft* figure legend from panel titles, variables, and stats
    method reports. Draft only - it never fabricates biological interpretation.
    """
    parts = [f"{mpf.name}."]
    for panel in mpf.panels:
        bits = [f"({panel.label})"]
        desc = panel.title or _panel_plot_phrase(panel)
        if desc:
            bits.append(desc + ".")
        method = _panel_method_sentence(panel)
        if method:
            bits.append(method)
        parts.append(" ".join(bits))
    parts.append("[DRAFT auto-generated legend - verify all descriptions and add "
                 "biological interpretation before publication.]")
    return " ".join(parts)


def _panel_plot_phrase(panel: Panel) -> str:
    spec = panel.plot_spec or {}
    pt = spec.get("plot_type", "")
    mapping = spec.get("mapping", {}) or {}
    y = mapping.get("y"); x = mapping.get("x")
    if y and x:
        return f"{y} by {x}"
    return pt.replace("_", " ")


def _panel_method_sentence(panel: Panel) -> str:
    ss = panel.stats_spec or (panel.plot_spec or {}).get("statistics")
    if not ss or not ss.get("enabled"):
        return ""
    return "Statistics were computed as recorded in the panel StatsSpec."


def multipanel_sidecar(mpf: MultiPanelFigure, base_path: str) -> str:
    """Write ``base_path.figure_spec.json`` describing the composite."""
    out = f"{base_path}.figure_spec.json"
    payload = {
        "figure": mpf.to_dict(),
        "draft_legend": mpf.legend_text or draft_legend(mpf),
        "disclaimer": (
            "Multi-panel composite generated by Make My Figure. Panel content is embedded "
            "at the configured DPI; panel labels and titles are vector text. Auto-generated "
            "legend text is a draft and must be verified before publication."
        ),
    }
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return out
