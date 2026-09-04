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


def _render_panel_figure(panel: Panel, font_overrides: Optional[Dict[str, Any]] = None) -> Figure:
    """Return the panel's Figure, rendering from its PlotSpec if needed.

    ``font_overrides`` (figure-level font sizes) are merged into the panel's
    style overrides so the whole composite stays typographically consistent.
    A pre-rendered figure is returned as-is (fonts were fixed at render time).
    """
    if panel.figure is not None:
        return panel.figure
    if panel.plot_spec is None or panel.table is None:
        raise ValueError(f"Panel '{panel.label}' has neither a figure nor a plot_spec+table.")
    from make_my_figure_core.plots.registry import render

    spec = dict(panel.plot_spec)
    if panel.stats_spec is not None and "statistics" not in spec:
        spec["statistics"] = panel.stats_spec
    if font_overrides:
        # Figure-level fonts win over the panel's own so panels match; a panel
        # that set a token explicitly still keeps anything not overridden here.
        spec["style"] = {**(spec.get("style") or {}), **font_overrides}
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


def _external_panel_image(panel: Panel) -> Tuple[np.ndarray, List[str]]:
    """Load + process an imported external panel's asset into an RGBA array."""
    from make_my_figure_core import figure_import as fi

    if not panel.image_path:
        raise ValueError(f"Panel '{panel.label}' is external but has no image_path.")
    dpi = int(panel.image_meta.get("rasterization_dpi") or fi.DEFAULT_RASTER_DPI)
    res = fi.import_asset(panel.image_path, os.path.dirname(panel.image_path) or ".",
                          rasterize_dpi=dpi, pdf_page=int(panel.image_meta.get("page", 0)))
    if res.error:
        raise ValueError(f"Panel '{panel.label}': {res.error}")
    arr = fi.process_image(res.image, crop=panel.crop or None, rotate=panel.rotate,
                           flip_h=panel.flip_h, flip_v=panel.flip_v,
                           auto_trim=panel.auto_trim, background=panel.background)
    warns = list(res.warnings) + fi.resolution_warnings(res.metadata, panel.width_in)
    return arr, warns


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

    font_overrides = layout.font_overrides()
    from make_my_figure_core.styles.engine import load_profile

    _ann_style = load_profile("publication")   # for per-panel annotation defaults

    # Render + rasterize each panel; capture aspect (height/width). External
    # (imported) panels load their asset image directly instead of rendering a plot.
    images: List[np.ndarray] = []
    aspects: List[float] = []
    own_figs: List[Figure] = []
    panel_warnings: List[str] = []
    for panel in panels:
        if panel.is_external:
            img, warns = _external_panel_image(panel)
            panel_warnings.extend(f"[{panel.label}] {w}" for w in warns)
        else:
            fig = _render_panel_figure(panel, font_overrides)
            img = _figure_to_image(fig, layout.panel_dpi)
            if panel.figure is None:
                own_figs.append(fig)   # close figures we rendered ourselves
        images.append(img)
        h, w = img.shape[0], img.shape[1]
        aspects.append(h / w if w else 1.0)

    n = len(panels)
    nrows, ncols = _auto_grid(n, layout)

    # Effective per-panel size in inches. An unset width defaults to an even
    # share of the figure width (so old specs keep their overall width); an
    # unset height follows the panel's own aspect ratio, so by default a panel
    # exactly fills its cell (no letterboxing, no distortion).
    default_w = mm_to_inches(layout.fig_width_mm) / ncols
    panel_w = [float(p.width_in) if p.width_in else default_w for p in panels]
    panel_h = [float(p.height_in) if p.height_in else panel_w[i] * aspects[i]
               for i, p in enumerate(panels)]

    # Column width = widest panel in the column; row height = tallest in the row.
    col_w = [max((panel_w[i] for i in range(c, n, ncols)), default=default_w)
             for c in range(ncols)]
    row_h = [max((panel_h[i] for i in range(r * ncols, min((r + 1) * ncols, n))),
                 default=1.0) for r in range(nrows)]
    if layout.width_ratios and len(layout.width_ratios) == ncols:
        col_w = list(layout.width_ratios)
    if layout.height_ratios and len(layout.height_ratios) == nrows:
        row_h = list(layout.height_ratios)

    # Approximate figure size from the grid + relative gutters. Exactness isn't
    # required (sizes are "approximate"); gridspec distributes the ratios.
    fig_w_in = sum(col_w) * (1.0 + layout.wspace)
    if layout.fig_height_mm:
        fig_h_in = mm_to_inches(layout.fig_height_mm)
    else:
        fig_h_in = max(sum(row_h) * (1.0 + layout.hspace), 1.5)

    # Panel letters and titles are drawn on the composite itself, so they take the Publication
    # style's font stack rather than matplotlib's default (which would mix DejaVu Sans letters
    # with Arial panel text on systems that have Arial).
    with plt.rc_context({**_VECTOR_TEXT_RC, "font.family": list(_ann_style.font_family)}):
        comp = plt.figure(figsize=(fig_w_in, fig_h_in), facecolor=layout.background)
        gs = comp.add_gridspec(
            nrows, ncols, wspace=layout.wspace, hspace=layout.hspace,
            width_ratios=col_w, height_ratios=row_h,
        )
        for i, panel in enumerate(panels):
            r, c = divmod(i, ncols)
            ax = comp.add_subplot(gs[r, c])
            # Fit mode: imported panels may 'fill'/'stretch' the cell (aspect=auto)
            # or 'contain'/'crop' preserving aspect (default). Generated panels
            # always preserve aspect (letterboxed) so they are never distorted.
            fill = panel.is_external and panel.fit_mode in ("fill", "stretch")
            if fill:
                ax.imshow(images[i], aspect="auto", interpolation="antialiased")
                if panel.fit_mode == "stretch":
                    panel_warnings.append(
                        f"[{panel.label}] stretched non-proportionally; may distort the figure.")
            else:
                ax.imshow(images[i], interpolation="antialiased")
                ax.set_anchor("N")  # top-align within the cell so panel tops line up
            ax.set_xticks([]); ax.set_yticks([])
            show_border = bool(panel.is_external and panel.border)
            for spine in ax.spines.values():
                spine.set_visible(show_border)
                if show_border:
                    spine.set_linewidth(panel.border_width)
                    spine.set_edgecolor("#000000")
            if layout.show_titles and panel.title:
                ax.set_title(panel.title, fontsize=layout.label_size * 0.8)
            # Per-panel manual annotations (imported panels use normalized 0..1
            # coords => 'axes' transform, so they reproduce at any panel size).
            if panel.annotations:
                from make_my_figure_core.annotations import apply_annotations, parse_annotations

                anns = parse_annotations(panel.annotations)
                for a in anns:
                    if panel.is_external and a.coords == "data":
                        a.coords = "axes"
                apply_annotations(comp, ax, anns, _ann_style)
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
    # Surface imported-panel warnings (resolution/DPI/stretch/rasterization) to
    # the caller without changing the return type.
    comp._mmf_panel_warnings = panel_warnings  # type: ignore[attr-defined]
    return comp


def panel_warnings(fig: Figure) -> List[str]:
    """Imported-panel publication warnings collected during the last build."""
    return list(getattr(fig, "_mmf_panel_warnings", []))


def import_external_panel(src_path: str, assets_dir: str, *, label: str = "", title: str = "",
                          width_in: Optional[float] = None, rasterize_dpi: int = 300,
                          pdf_page: int = 0, **transform: Any):
    """Import an external figure file and return ``(Panel, ImportedAsset)``.

    The file is copied into ``assets_dir``; the Panel references the stored asset
    (relative basename in its FigureSpec). Returns the asset too so the caller can
    show a preview / any import error before adding the panel. On import error the
    Panel is ``None``.
    """
    from make_my_figure_core import figure_import as fi

    asset = fi.import_asset(src_path, assets_dir, rasterize_dpi=rasterize_dpi, pdf_page=pdf_page)
    if asset.error:
        return None, asset
    meta = dict(asset.metadata)
    meta["warnings"] = list(asset.warnings)
    allowed = {"fit_mode", "preserve_aspect", "crop", "rotate", "flip_h", "flip_v",
               "auto_trim", "background", "border", "border_width", "annotations"}
    kw = {k: v for k, v in transform.items() if k in allowed}
    panel = Panel(label=label, title=title, width_in=width_in,
                  image_path=os.path.join(assets_dir, meta["stored_asset"]),
                  image_meta=meta, source_name=meta.get("original_filename", ""), **kw)
    return panel, asset


def panel_from_dict(d: Dict[str, Any], assets_dir: Optional[str] = None) -> Panel:
    """Reconstruct a Panel from a FigureSpec panel dict (round-trip).

    For imported panels, the asset is resolved as ``assets_dir/<image_path>`` so a
    shared FigureSpec + assets folder reload without absolute paths.
    """
    kind = d.get("panel_kind")
    img_rel = d.get("image_path")
    image_path = None
    if img_rel:
        image_path = os.path.join(assets_dir, img_rel) if assets_dir else img_rel
    return Panel(
        label=d.get("label", ""), title=d.get("title", ""), caption=d.get("caption", ""),
        plot_spec=d.get("plot_spec"), stats_spec=d.get("stats_spec"),
        source_name=d.get("source_name", ""),
        source_workbook=d.get("source_workbook", ""), source_sheet=d.get("source_sheet", ""),
        width_in=d.get("width_in"), height_in=d.get("height_in"),
        image_path=image_path, image_meta=d.get("image_meta", {}) or {},
        fit_mode=d.get("fit_mode", "contain"), preserve_aspect=d.get("preserve_aspect", True),
        crop=d.get("crop", {}) or {}, rotate=int(d.get("rotate", 0)),
        flip_h=bool(d.get("flip_h", False)), flip_v=bool(d.get("flip_v", False)),
        auto_trim=bool(d.get("auto_trim", False)), background=d.get("background", "white"),
        border=bool(d.get("border", False)), border_width=float(d.get("border_width", 0.8)),
        annotations=d.get("annotations", []) or [],
    )


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
            # Pass dpi for EVERY format: the panels are embedded as raster images,
            # so vector outputs (pdf/svg/eps) also need a high dpi or the panels
            # look blurry — text stays vector via _VECTOR_TEXT_RC regardless.
            kwargs: Dict[str, Any] = {"bbox_inches": "tight", "facecolor": fig.get_facecolor(),
                                      "dpi": dpi}
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
