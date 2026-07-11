"""Plot-type registry, default mappings, render entrypoint, and export.

This module wires together the loaders, style engine, schema validation, and
individual renderers. It is the single import surface the dashboard and tests
use.
"""

from __future__ import annotations

import inspect
import json
import os
from typing import Any, Callable, Dict, List, Optional

import pandas as pd
from matplotlib.figure import Figure

from make_my_figure_core.plots import (
    barplot,
    beeswarm,
    bland_altman,
    box_violin,
    calibration,
    confusion_matrix,
    dendrogram,
    dose_response,
    dot_strip,
    embedding_scatter,
    enrichment,
    forest,
    grouped_barplot,
    heatmap,
    lineplot,
    lollipop,
    ma_plot,
    manhattan,
    oncoprint,
    paired_slope,
    pca,
    precision_recall,
    qq_plot,
    raincloud,
    ridge,
    roc,
    sankey,
    scatter,
    spider,
    stacked,
    survival,
    swimmer,
    upset,
    volcano,
    waterfall,
)
from make_my_figure_core.plots.base import RenderError, RenderResult
from make_my_figure_core.spec.validate import (
    SpecValidationError,
    default_output_block,
    validate_plot_spec,
)
from make_my_figure_core.styles.engine import StyleProfile, list_profiles, load_profile

# plot_type -> renderer function(spec, df, style) -> RenderResult
_RENDERERS: Dict[str, Callable[..., RenderResult]] = {
    barplot.PLOT_TYPE: barplot.render,
    grouped_barplot.PLOT_TYPE: grouped_barplot.render,
    heatmap.PLOT_TYPE: heatmap.render,
    volcano.PLOT_TYPE: volcano.render,
    scatter.PLOT_TYPE: scatter.render,
    box_violin.PLOT_TYPE: box_violin.render,
    lineplot.PLOT_TYPE: lineplot.render,
    ridge.PLOT_TYPE: ridge.render,
    enrichment.PLOT_TYPE: enrichment.render,
    survival.PLOT_TYPE: survival.render,
    stacked.PLOT_TYPE: stacked.render,
    waterfall.PLOT_TYPE: waterfall.render,
    pca.PLOT_TYPE: pca.render,
    oncoprint.PLOT_TYPE: oncoprint.render,
    lollipop.PLOT_TYPE: lollipop.render,
    roc.PLOT_TYPE: roc.render,
    forest.PLOT_TYPE: forest.render,
    # --- v0.4 manuscript plot types ---
    dot_strip.PLOT_TYPE: dot_strip.render,
    beeswarm.PLOT_TYPE: beeswarm.render,
    paired_slope.PLOT_TYPE: paired_slope.render,
    raincloud.PLOT_TYPE: raincloud.render,
    dendrogram.PLOT_TYPE: dendrogram.render,
    ma_plot.PLOT_TYPE: ma_plot.render,
    manhattan.PLOT_TYPE: manhattan.render,
    qq_plot.PLOT_TYPE: qq_plot.render,
    bland_altman.PLOT_TYPE: bland_altman.render,
    precision_recall.PLOT_TYPE: precision_recall.render,
    confusion_matrix.PLOT_TYPE: confusion_matrix.render,
    calibration.PLOT_TYPE: calibration.render,
    dose_response.PLOT_TYPE: dose_response.render,
    upset.PLOT_TYPE: upset.render,
    swimmer.PLOT_TYPE: swimmer.render,
    spider.PLOT_TYPE: spider.render,
    sankey.PLOT_TYPE: sankey.render,
    embedding_scatter.PLOT_TYPE: embedding_scatter.render,
}

# Default column mappings per plot type (mirrors the mock-data manifest).
_DEFAULT_MAPPINGS: Dict[str, Dict[str, Any]] = {
    barplot.PLOT_TYPE: {"x": "condition", "y": "measurement", "error": "sem", "color": "condition"},
    grouped_barplot.PLOT_TYPE: {"x": "genotype", "group": "treatment", "y": "expression", "error": "sem"},
    heatmap.PLOT_TYPE: {"row_id": "gene", "cluster_rows": True, "cluster_columns": True, "color_scale": "diverging"},
    volcano.PLOT_TYPE: {"x": "log2_fold_change", "p": "adjusted_p_value", "label": "label",
                        "lfc_cutoff": 1.0, "p_cutoff": 0.05},
    scatter.PLOT_TYPE: {"x": "x_marker", "y": "y_response", "color": "group", "fit_line": True},
    box_violin.PLOT_TYPE: {"x": "group", "y": "value", "kind": "box", "points": True},
    lineplot.PLOT_TYPE: {"x": "time_hours", "y": "signal", "color": "treatment", "error": "sem"},
    ridge.PLOT_TYPE: {"x": "pseudotime", "group": "condition", "overlap": 0.7},
    enrichment.PLOT_TYPE: {"y": "term", "x": "gene_ratio", "size": "gene_count",
                           "color": "neg_log10_fdr", "fdr": "fdr"},
    survival.PLOT_TYPE: {"time": "time_months", "event": "event", "group": "group"},
    stacked.PLOT_TYPE: {"x": "sample_id", "stack": "cell_type", "y": "fraction",
                        "facet_or_sort_by": "group"},
    waterfall.PLOT_TYPE: {"x": "patient_id", "y": "best_percent_change",
                          "color": "response_category", "sort": "ascending"},
    pca.PLOT_TYPE: {"matrix_row_id": "gene", "metadata_key": "sample_id",
                    "color": "group", "shape": "batch"},
    oncoprint.PLOT_TYPE: {"sample": "patient_id", "row": "gene", "fill": "alteration_type"},
    lollipop.PLOT_TYPE: {"x": "protein_position", "y": "sample_count",
                         "color": "mutation_type", "label": "amino_acid_change"},
    roc.PLOT_TYPE: {"label": "true_label", "score": "score_model_a", "score2": "score_model_b"},
    forest.PLOT_TYPE: {"label": "subgroup", "estimate": "hazard_ratio",
                       "lower": "ci_low", "upper": "ci_high", "reference": 1.0},
    # --- v0.4 manuscript plot types ---
    dot_strip.PLOT_TYPE: {"x": "group", "y": "value", "summary": "mean", "jitter": True},
    beeswarm.PLOT_TYPE: {"x": "group", "y": "value", "summary": "mean"},
    paired_slope.PLOT_TYPE: {"subject": "subject", "condition": "condition", "value": "value"},
    raincloud.PLOT_TYPE: {"x": "group", "y": "value"},
    dendrogram.PLOT_TYPE: {"row_id": "gene", "method": "average", "metric": "euclidean",
                           "cluster": "rows", "orientation": "top"},
    ma_plot.PLOT_TYPE: {"x": "AveExpr", "y": "logFC", "p": "adj.P.Val", "label": "gene",
                        "p_cutoff": 0.05, "label_top_n": 8},
    manhattan.PLOT_TYPE: {"chrom": "chromosome", "pos": "position", "p": "p_value", "snp": "snp"},
    qq_plot.PLOT_TYPE: {"mode": "pvalue", "p": "p_value"},
    bland_altman.PLOT_TYPE: {"method_a": "device_A", "method_b": "device_B"},
    precision_recall.PLOT_TYPE: {"label": "true_label", "score": "score_model_a",
                                 "score2": "score_model_b"},
    confusion_matrix.PLOT_TYPE: {"true": "true_label", "predicted": "predicted_label",
                                 "normalize": "none"},
    calibration.PLOT_TYPE: {"label": "true_label", "prob": "predicted_prob", "n_bins": 10},
    dose_response.PLOT_TYPE: {"dose": "concentration_uM", "response": "viability_pct",
                              "group": "drug", "fit": True},
    upset.PLOT_TYPE: {"sets": ["DEG_up", "DEG_down", "Promoter_peak", "Conserved"]},
    swimmer.PLOT_TYPE: {"subject": "patient_id", "start": "start_month", "end": "end_month",
                        "event": "event_type", "group": "response"},
    spider.PLOT_TYPE: {"subject": "patient_id", "time": "week", "value": "pct_change",
                       "group": "arm", "reference": 0},
    sankey.PLOT_TYPE: {"source": "baseline_response", "target": "outcome", "value": "n_patients"},
    embedding_scatter.PLOT_TYPE: {"x": "UMAP_1", "y": "UMAP_2", "color": "cell_type"},
}

# Human-friendly labels for the UI.
_DISPLAY_NAMES: Dict[str, str] = {
    barplot.PLOT_TYPE: "Bar plot with error bars",
    grouped_barplot.PLOT_TYPE: "Grouped bar plot with error bars",
    heatmap.PLOT_TYPE: "Clustered heatmap",
    volcano.PLOT_TYPE: "Volcano plot",
    scatter.PLOT_TYPE: "Scatter plot",
    box_violin.PLOT_TYPE: "Box / violin plot with points",
    lineplot.PLOT_TYPE: "Line / time-course with error band",
    ridge.PLOT_TYPE: "Ridge / density plot",
    enrichment.PLOT_TYPE: "Enrichment dot plot",
    survival.PLOT_TYPE: "Kaplan-Meier survival curve",
    stacked.PLOT_TYPE: "Stacked composition bar plot",
    waterfall.PLOT_TYPE: "Waterfall plot",
    pca.PLOT_TYPE: "PCA scatter (matrix + metadata)",
    oncoprint.PLOT_TYPE: "Oncoprint mutation heatmap",
    lollipop.PLOT_TYPE: "Lollipop mutation plot",
    roc.PLOT_TYPE: "ROC curve",
    forest.PLOT_TYPE: "Forest plot",
    # --- v0.4 manuscript plot types ---
    dot_strip.PLOT_TYPE: "Dot / strip plot",
    beeswarm.PLOT_TYPE: "Beeswarm plot",
    paired_slope.PLOT_TYPE: "Paired dot plot / slopegraph",
    raincloud.PLOT_TYPE: "Raincloud plot",
    dendrogram.PLOT_TYPE: "Hierarchical clustering dendrogram",
    ma_plot.PLOT_TYPE: "MA plot (differential expression)",
    manhattan.PLOT_TYPE: "Manhattan plot (GWAS)",
    qq_plot.PLOT_TYPE: "Q-Q plot (p-value / quantile)",
    bland_altman.PLOT_TYPE: "Bland-Altman (method agreement)",
    precision_recall.PLOT_TYPE: "Precision-recall curve",
    confusion_matrix.PLOT_TYPE: "Confusion matrix",
    calibration.PLOT_TYPE: "Calibration plot",
    dose_response.PLOT_TYPE: "Dose-response curve",
    upset.PLOT_TYPE: "UpSet plot (set intersections)",
    swimmer.PLOT_TYPE: "Swimmer plot",
    spider.PLOT_TYPE: "Spider plot (longitudinal change)",
    sankey.PLOT_TYPE: "Sankey / alluvial flow (two-stage)",
    embedding_scatter.PLOT_TYPE: "UMAP / t-SNE embedding scatter",
}

_EXPORT_FORMATS = ("svg", "png", "pdf", "tiff", "eps")

# rcParams that keep exported vector text EDITABLE (not converted to paths).
# These must be applied at savefig time, which can happen outside a style's
# rc_context, so we set them explicitly around every export.
_VECTOR_TEXT_RC = {"svg.fonttype": "none", "pdf.fonttype": 42, "ps.fonttype": 42}


def available_plot_types() -> List[str]:
    return list(_RENDERERS.keys())


def display_name(plot_type: str) -> str:
    return _DISPLAY_NAMES.get(plot_type, plot_type)


def default_mapping(plot_type: str) -> Dict[str, Any]:
    return dict(_DEFAULT_MAPPINGS.get(plot_type, {}))


def make_spec(
    plot_type: str,
    input_table: str,
    journal_style: str,
    *,
    mapping: Optional[Dict[str, Any]] = None,
    layout: Optional[Dict[str, Any]] = None,
    statistics: Optional[Dict[str, Any]] = None,
    output: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a PlotSpec dict with sensible defaults filled in."""
    spec: Dict[str, Any] = {
        "plot_type": plot_type,
        "input_table": input_table,
        "mapping": mapping if mapping is not None else default_mapping(plot_type),
        "journal_style": journal_style,
        "output": output or default_output_block(),
    }
    if layout:
        spec["layout"] = layout
    if statistics:
        spec["statistics"] = statistics
    return spec


def render(
    spec: Dict[str, Any],
    df: pd.DataFrame,
    *,
    style: Optional[StyleProfile] = None,
    validate: bool = True,
    aux: Optional[Dict[str, pd.DataFrame]] = None,
) -> RenderResult:
    """Validate ``spec`` then dispatch to the matching renderer.

    Parameters
    ----------
    spec: PlotSpec dict.
    df: the loaded DataFrame for ``spec['input_table']``.
    style: optional pre-loaded profile; loaded from ``journal_style`` otherwise.
    validate: run schema + app-level validation first.
    aux: optional auxiliary tables (e.g. PCA sample metadata) keyed by name.
        Only passed to renderers that declare an ``aux`` parameter.
    """
    if validate:
        validate_plot_spec(
            spec,
            known_plot_types=available_plot_types(),
            known_styles=list_profiles(),
        )

    plot_type = spec["plot_type"]
    renderer = _RENDERERS.get(plot_type)
    if renderer is None:
        raise RenderError(f"No renderer registered for plot_type '{plot_type}'.")

    if style is None:
        style = load_profile(spec["journal_style"])
    # Apply GUI/PlotSpec style refinements (fonts, widths, markers, palette, ...).
    style = style.with_overrides(spec.get("style"))

    if "aux" in inspect.signature(renderer).parameters:
        result = renderer(spec, df, style, aux=aux or {})
    else:
        result = renderer(spec, df, style)
    # Stamp the spec into metadata for a reproducibility sidecar.
    result.metadata.setdefault("spec", spec)
    # Publication-readiness check (advisory; never blocks rendering/export).
    try:
        from make_my_figure_core.qa.publication_check import check_publication_readiness

        check = check_publication_readiness(result.figure)
        result.metadata["publication_check"] = {
            "passed": check.passed, "warnings": check.warnings, "summary": check.summary}
    except Exception as exc:  # QA must never break rendering
        result.metadata["publication_check"] = {
            "passed": True, "warnings": [], "summary": f"Publication check skipped: {exc}"}
    return result


def export_figure(fig: Figure, base_path: str, formats: List[str], dpi: int = 300) -> List[str]:
    """Save ``fig`` to ``base_path.<ext>`` for each requested format.

    Returns the list of written file paths.
    """
    import matplotlib as mpl

    written: List[str] = []
    os.makedirs(os.path.dirname(os.path.abspath(base_path)) or ".", exist_ok=True)
    with mpl.rc_context(_VECTOR_TEXT_RC):
        for fmt in formats:
            fmt = fmt.lower()
            if fmt not in _EXPORT_FORMATS:
                continue
            out = f"{base_path}.{fmt}"
            save_kwargs: Dict[str, Any] = {"bbox_inches": "tight"}
            if fmt in ("png", "tiff"):
                save_kwargs["dpi"] = dpi
            if fmt == "tiff":
                save_kwargs["pil_kwargs"] = {"compression": "tiff_lzw"}
            fig.savefig(out, format=fmt, **save_kwargs)
            written.append(out)
    return written


def write_sidecar(spec: Dict[str, Any], metadata: Dict[str, Any], base_path: str) -> str:
    """Write the reproducibility sidecar ``base_path.plot_spec.json``."""
    out = f"{base_path}.plot_spec.json"
    payload = {"plot_spec": spec, "render_metadata": {k: v for k, v in metadata.items() if k != "spec"}}
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return out


def write_stats_sidecar(spec: Dict[str, Any], result: RenderResult, base_path: str) -> Optional[str]:
    """Write ``base_path.stats_spec.json`` when the render produced statistics.

    Returns the written path, or ``None`` when no statistics were computed.
    """
    report = getattr(result, "stats_report", None)
    if report is None:
        return None
    from make_my_figure_core.statistics.schemas import stats_sidecar_payload

    out = f"{base_path}.stats_spec.json"
    payload = stats_sidecar_payload(spec.get("statistics") or {}, report)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return out


def figure_to_bytes(fig: Figure, fmt: str, dpi: int = 300) -> bytes:
    """Serialize a figure to bytes in the requested format (in-memory)."""
    import io as _io

    import matplotlib as mpl

    buf = _io.BytesIO()
    save_kwargs: Dict[str, Any] = {"format": fmt.lower(), "bbox_inches": "tight"}
    if fmt.lower() in ("png", "tiff"):
        save_kwargs["dpi"] = dpi
    if fmt.lower() == "tiff":
        save_kwargs["pil_kwargs"] = {"compression": "tiff_lzw"}
    with mpl.rc_context(_VECTOR_TEXT_RC):
        fig.savefig(buf, **save_kwargs)
    return buf.getvalue()


def export_bundle_bytes(
    spec: Dict[str, Any],
    result: RenderResult,
    *,
    formats: Optional[List[str]] = None,
    dpi: int = 300,
    basename: str = "figure",
) -> bytes:
    """Build a ZIP (in memory) containing the figure in each format + sidecar JSON."""
    import io as _io
    import zipfile as _zip

    fmts = formats or ["svg", "png", "pdf"]
    buf = _io.BytesIO()
    with _zip.ZipFile(buf, "w", _zip.ZIP_DEFLATED) as zf:
        for fmt in fmts:
            if fmt.lower() in _EXPORT_FORMATS:
                zf.writestr(f"{basename}.{fmt.lower()}",
                            figure_to_bytes(result.figure, fmt, dpi=dpi))
        sidecar = {
            "plot_spec": spec,
            "render_metadata": {k: v for k, v in result.metadata.items() if k != "spec"},
        }
        zf.writestr(f"{basename}.plot_spec.json", json.dumps(sidecar, indent=2))
        report = getattr(result, "stats_report", None)
        if report is not None:
            from make_my_figure_core.statistics.schemas import stats_sidecar_payload

            payload = stats_sidecar_payload(spec.get("statistics") or {}, report)
            zf.writestr(f"{basename}.stats_spec.json", json.dumps(payload, indent=2))
    return buf.getvalue()


def render_to_files(
    spec: Dict[str, Any],
    df: pd.DataFrame,
    base_path: str,
    *,
    formats: Optional[List[str]] = None,
    style: Optional[StyleProfile] = None,
    aux: Optional[Dict[str, pd.DataFrame]] = None,
) -> Dict[str, Any]:
    """Render and write figure files plus the PlotSpec sidecar.

    Returns a dict with ``files``, ``sidecar``, ``metadata``, ``warnings``.
    """
    result = render(spec, df, style=style, aux=aux)
    output = spec.get("output", {}) or {}
    fmts = formats or output.get("formats") or ["svg", "png", "pdf"]
    dpi = int(output.get("dpi", 300))
    files = export_figure(result.figure, base_path, fmts, dpi=dpi)
    sidecar = write_sidecar(spec, result.metadata, base_path)
    stats_sidecar = write_stats_sidecar(spec, result, base_path)
    return {
        "files": files,
        "sidecar": sidecar,
        "stats_sidecar": stats_sidecar,
        "metadata": result.metadata,
        "warnings": result.warnings,
    }
