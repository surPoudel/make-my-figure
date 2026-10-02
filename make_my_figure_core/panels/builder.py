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


def _render_panel_figure(panel: Panel, font_overrides: Optional[Dict[str, Any]] = None,
                         size_in: Optional[Tuple[float, float]] = None) -> Figure:
    """Return the panel's Figure, rendering from its PlotSpec if needed.

    ``font_overrides`` (figure-level font sizes) are merged into the panel's
    style overrides so the whole composite stays typographically consistent.
    A pre-rendered figure is returned as-is (fonts were fixed at render time).

    ``size_in`` is ``(width, height)`` in inches for the panel's own canvas. It
    is the mechanism behind the per-panel size controls: a panel asked to be
    taller is *drawn* taller (pinned ``layout.width_mm``/``height_mm``, which
    every renderer already honours) rather than having its finished image
    stretched, so the axes grow and nothing in the plot is distorted. Render
    warnings from a size the plot type had to correct are stashed on the figure
    for the caller to surface; they are the user's only clue that a request was
    adjusted.
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
    if size_in is not None:
        w_in, h_in = float(size_in[0]), float(size_in[1])
        if w_in > 0 and h_in > 0:
            spec["layout"] = {**(spec.get("layout") or {}),
                              "width_mm": w_in * 25.4, "height_mm": h_in * 25.4}
    aux = panel.aux or None
    result = render(spec, panel.table, aux=aux)
    fig = result.figure
    fig._mmf_render_warnings = list(result.warnings)  # type: ignore[attr-defined]
    return fig


def _can_resize(panel: Panel) -> bool:
    """True when the panel can be *re-drawn* at a requested size.

    Only a panel that still carries its PlotSpec + table can honour a size by
    rendering at it. A pre-rendered figure or an imported image has a fixed
    aspect, so for those a requested height can only scale the finished picture.
    """
    return (not panel.is_external and panel.figure is None
            and panel.plot_spec is not None and panel.table is not None)


def _figure_to_image(fig: Figure, dpi: int, *, keep_canvas: bool = False) -> np.ndarray:
    """Rasterize a figure to an RGBA image array.

    Trims to the content by default, which is what keeps a panel from carrying a
    band of its own margin into the composite.

    ``keep_canvas`` turns the trim off, and is used when the panel was rendered
    at a size the user explicitly asked for. Trimming there defeats the request:
    a panel rendered on a 3.2 x 4.5 in canvas came back as an image of aspect
    0.77 rather than 1.41, so "make it 4.5 inches tall" drew 2.46 inches. The
    whitespace kept here is the plot's own margin, at the size that was asked
    for, which is exactly what the user is buying.
    """
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi,
                bbox_inches=None if keep_canvas else "tight",
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

    n = len(panels)
    nrows, ncols = _auto_grid(n, layout)

    # Effective per-panel WIDTH in inches. An unset width defaults to an even
    # share of the figure width, so old specs keep their overall width.
    default_w = mm_to_inches(layout.fig_width_mm) / ncols
    panel_w = [float(p.width_in) if p.width_in else default_w for p in panels]

    # Render + rasterize each panel; capture aspect (height/width). External
    # (imported) panels load their asset image directly instead of rendering a plot.
    images: List[np.ndarray] = []
    aspects: List[float] = []
    own_figs: List[Figure] = []
    panel_warnings: List[str] = []
    for i, panel in enumerate(panels):
        if panel.is_external:
            img, warns = _external_panel_image(panel)
            panel_warnings.extend(f"[{panel.label}] {w}" for w in warns)
        else:
            # A requested height is honoured where it can actually be honoured:
            # at render time. Scaling a finished panel can only ever give it its
            # own proportions back, which is why setting a height used to do
            # nothing visible - it moved the grid row and left the picture the
            # same shape, floating in a taller cell. Rendering the panel at the
            # requested canvas makes it genuinely that tall with no distortion.
            size_in = ((panel_w[i], float(panel.height_in))
                       if (panel.height_in and _can_resize(panel)) else None)
            fig = _render_panel_figure(panel, font_overrides, size_in=size_in)
            # Keep the full canvas when the size was requested, or the trim gives
            # the panel its own proportions straight back and the control looks
            # dead again - which is the bug this was meant to fix.
            img = _figure_to_image(fig, layout.panel_dpi,
                                   keep_canvas=size_in is not None)
            if panel.figure is None:
                own_figs.append(fig)   # close figures we rendered ourselves
                if size_in is not None:
                    panel_warnings.extend(
                        f"[{panel.label}] {w}" for w in getattr(fig, "_mmf_render_warnings", []))
        images.append(img)
        h, w = img.shape[0], img.shape[1]
        aspects.append(h / w if w else 1.0)

    # Effective per-panel HEIGHT in inches = the height the panel is really
    # DRAWN at, which is its width times its own aspect. For a panel we could
    # re-render that already *is* the requested height (it was rendered at it),
    # and using the drawn value rather than the raw request keeps the grid row
    # the same size as the picture instead of a hair taller.
    panel_h: List[float] = []
    for i, p in enumerate(panels):
        natural = panel_w[i] * aspects[i]
        requested = float(p.height_in) if p.height_in else 0.0
        if requested and not _can_resize(p):
            # A pre-rendered figure or an imported image has one fixed shape, so
            # at this width it has one possible height. Honour a request to make
            # it SHORTER (scale the whole picture down), but cap a request to make
            # it taller: growing the row to a height the picture cannot fill only
            # manufactures the white space the user was trying to get rid of.
            panel_h.append(min(requested, natural))
            if requested > natural * 1.01:
                panel_warnings.append(
                    f"[{p.label}] keeps its own proportions, so at {panel_w[i]:.2f} in wide it is "
                    f"{natural:.2f} in tall and cannot be made {requested:.2f} in tall. Make it "
                    f"wider, or set it to fill its cell to use the whole space.")
        else:
            panel_h.append(natural)

    # Column width = widest panel in the column; row height = tallest in the row.
    col_w = [max((panel_w[i] for i in range(c, n, ncols)), default=default_w)
             for c in range(ncols)]
    row_h = [max((panel_h[i] for i in range(r * ncols, min((r + 1) * ncols, n))),
                 default=1.0) for r in range(nrows)]
    # The tallest DRAWN panel per row: the yardstick each panel's own height is
    # measured against when it is placed in its cell. Kept separately from row_h
    # because row_h is about to be replaced by any explicit height_ratios.
    content_h = list(row_h)
    if layout.width_ratios and len(layout.width_ratios) == ncols:
        col_w = list(layout.width_ratios)
    if layout.height_ratios and len(layout.height_ratios) == nrows:
        row_h = list(layout.height_ratios)
        # Explicit ratios decouple a row's cell height from the inches its panels
        # asked for, so there is nothing left to measure a panel against: every
        # panel simply fits its cell, exactly as it did before per-panel heights
        # were honoured. Only the ratios the user gave decide the proportions.
        content_h = [0.0] * nrows

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
            cell = gs[r, c].get_position(comp)
            cell_w_in, cell_h_in = cell.width * fig_w_in, cell.height * fig_h_in
            # Fit mode: a panel may FILL its cell edge to edge instead of keeping
            # its own proportions. Imported panels say so with 'fill'/'stretch';
            # any panel can say so with fill_cell. Preserving the proportions is
            # and stays the default - a stretched scientific figure is a wrong one.
            fill = panel.fill_cell or (panel.is_external
                                       and panel.fit_mode in ("fill", "stretch"))
            if fill and _can_resize(panel):
                # The honest way to fill a cell: re-draw the plot ON a canvas that
                # size. The axes grow, the data keeps its shape and the fonts keep
                # their points - nothing is stretched. Only a panel that has lost
                # its PlotSpec has to fall back to scaling the finished picture.
                f2 = _render_panel_figure(panel, font_overrides,
                                          size_in=(cell_w_in, cell_h_in))
                own_figs.append(f2)
                images[i] = _figure_to_image(f2, layout.panel_dpi)
                aspects[i] = (images[i].shape[0] / images[i].shape[1]
                              if images[i].shape[1] else aspects[i])
                # Keep panel_h on the same (requested-inch) basis as every other
                # entry - the grid is laid out in those units, not in cell inches.
                # content_h is deliberately NOT raised with it: the row's cells
                # are already fixed, and nudging the yardstick here would shrink
                # whichever sibling happens to be placed after this one.
                panel_h[i] = panel_w[i] * aspects[i]
                panel_warnings.extend(
                    f"[{panel.label}] {w}" for w in getattr(f2, "_mmf_render_warnings", []))
                fill = False     # it now fits by construction; keep square pixels
            if fill:
                ax.set_position([cell.x0, cell.y0, cell.width, cell.height])
                ax.imshow(images[i], aspect="auto", interpolation="antialiased")
                if panel.fit_mode == "stretch" or panel.fill_cell:
                    panel_warnings.append(
                        f"[{panel.label}] stretched non-proportionally; may distort the figure.")
            else:
                # The largest box with the panel's own proportions that fits in
                # the height this panel asked for, inside its cell. Pinned to the
                # TOP of the cell: a short panel beside a tall one belongs level
                # with its neighbour, with the dead space below it, not floating
                # in the middle of an empty cell. Horizontally it stays centred,
                # which is where matplotlib's 'N' anchor already put it - nothing
                # moves sideways in a figure that was laid out before this.
                avail_h = cell_h_in * (min(1.0, panel_h[i] / content_h[r])
                                       if content_h[r] > 0 else 1.0)
                draw_w = min(cell_w_in, avail_h / aspects[i] if aspects[i] else cell_w_in)
                draw_h = draw_w * aspects[i]
                ax.set_position([cell.x0 + (cell_w_in - draw_w) / 2.0 / fig_w_in,
                                 cell.y1 - draw_h / fig_h_in,
                                 draw_w / fig_w_in, draw_h / fig_h_in])
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
               "auto_trim", "background", "border", "border_width", "annotations",
               "fill_cell"}
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
        # Missing in layouts saved before fill_cell existed -> keep proportions.
        fill_cell=bool(d.get("fill_cell", False)),
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
