"""Build :class:`PackageContent` from what a frontend has on screen.

Both the desktop and the browser interface call these helpers, so the decision
"which records apply to this figure" lives in exactly one place:

* a simple plot → PlotSpec + the table + aux tables (+ StatsSpec when statistics ran);
* a plot drawn from a preprocessed matrix → additionally the ORIGINAL matrix, the
  MatrixSpec, the SampleMetadataSpec (if confirmed) and the PreprocessingSpec;
* a composite → FigureSpec + every panel's PlotSpec/StatsSpec/table + imported assets.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

from make_my_figure_core.package.tabledata import table_digest
from make_my_figure_core.package.writer import (
    AssetSource,
    PackageContent,
    PlotComponent,
    TableSource,
)


@dataclass
class MatrixContext:
    """Matrix-workflow state that applies to the plot being packaged."""

    source_dataframe: Optional[pd.DataFrame] = None     # the ORIGINAL matrix (before preprocessing)
    source_name: Optional[str] = None
    source_path: Optional[str] = None
    source_sheet: Optional[str] = None
    source_provenance: Optional[Dict[str, Any]] = None
    matrix_spec: Any = None                             # MatrixSpec or dict
    sample_metadata_spec: Any = None                    # SampleMetadataSpec or dict
    preprocessing_spec: Any = None                      # PreprocessingSpec or dict


def _to_dict(obj: Any) -> Optional[Dict[str, Any]]:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    raise TypeError(f"cannot serialise {type(obj).__name__}")


def _stats_payload(spec: Dict[str, Any], result: Any) -> Optional[Dict[str, Any]]:
    report = getattr(result, "stats_report", None)
    if report is None:
        return None
    from make_my_figure_core.statistics.schemas import stats_sidecar_payload

    return stats_sidecar_payload(spec.get("statistics") or {}, report)


def _render_metadata(result: Any) -> Dict[str, Any]:
    md = getattr(result, "metadata", None) or {}
    return {k: v for k, v in md.items() if k != "spec"}


def _same_frame(a: Optional[pd.DataFrame], b: Optional[pd.DataFrame]) -> bool:
    if a is None or b is None:
        return False
    if a is b:
        return True
    try:
        return a.shape == b.shape and table_digest(a) == table_digest(b)
    except Exception:  # noqa: BLE001
        return False


def content_for_single_plot(
    spec: Dict[str, Any],
    df: pd.DataFrame,
    result: Any,
    *,
    table_name: Optional[str] = None,
    aux: Optional[Dict[str, pd.DataFrame]] = None,
    source_path: Optional[str] = None,
    sheet_name: Optional[str] = None,
    provenance: Optional[Dict[str, Any]] = None,
    matrix: Optional[MatrixContext] = None,
    name: Optional[str] = None,
    preview_dpi: int = 300,
    record_original_paths: bool = False,
) -> PackageContent:
    """Everything needed to reproduce one plot exactly as rendered."""
    tables: List[TableSource] = []
    prov = dict(provenance or {})
    display = table_name or spec.get("input_table") or "table"
    derived = matrix is not None and matrix.source_dataframe is not None and not _same_frame(matrix.source_dataframe, df)
    if derived:
        tables.append(TableSource("source_matrix", matrix.source_dataframe, role="source_table",
                                  display_name=matrix.source_name or display,
                                  original_path=matrix.source_path or source_path, sheet_name=matrix.source_sheet or sheet_name,
                                  header_row=(matrix.source_provenance or prov).get("source_header_row"),
                                  provenance=matrix.source_provenance or prov))
        tables.append(TableSource("derived_matrix", df, role="derived_table", display_name=display,
                                  derived_from="source_matrix", include_original_file=False))
        plot_table_id = "derived_matrix"
    else:
        tables.append(TableSource("source", df, role="source_table", display_name=display,
                                  original_path=source_path, sheet_name=sheet_name,
                                  header_row=prov.get("source_header_row"), provenance=prov))
        plot_table_id = "source"
    aux_ids: Dict[str, str] = {}
    for aname, adf in (aux or {}).items():
        tid = f"aux_{aname}"
        tables.append(TableSource(tid, adf, role="aux_table", display_name=aname, include_original_file=False))
        aux_ids[aname] = tid
    comp = PlotComponent("plot", plot_spec=spec, table_id=plot_table_id, aux_tables=aux_ids,
                         stats_payload=_stats_payload(spec, result), render_metadata=_render_metadata(result),
                         title=(spec.get("layout") or {}).get("title", "") or "")
    content = PackageContent(
        kind="single_plot", name=name or _default_name(spec, display), components=[comp], tables=tables,
        preview_figure=getattr(result, "figure", None), preview_dpi=preview_dpi,
        record_original_paths=record_original_paths,
    )
    if matrix is not None:
        content.matrix_spec = _to_dict(matrix.matrix_spec)
        content.sample_metadata_spec = _to_dict(matrix.sample_metadata_spec)
        content.preprocessing_spec = _to_dict(matrix.preprocessing_spec)
        if content.preprocessing_spec and not derived:
            content.warnings.append("a preprocessing record is present but the plotted table equals the source matrix")
    return content


def _default_name(spec: Dict[str, Any], display: str) -> str:
    base = os.path.splitext(str(display).split(" [")[0])[0] if display else "figure"
    return f"{base}_{spec.get('plot_type', 'plot')}"


def content_for_composite(
    mpf: Any,
    fig: Any = None,
    *,
    name: Optional[str] = None,
    panel_results: Optional[Iterable[Any]] = None,
    panel_sources: Optional[Dict[int, Dict[str, Any]]] = None,
    preview_dpi: int = 300,
    record_original_paths: bool = False,
) -> PackageContent:
    """Package a :class:`MultiPanelFigure` with all panel data and assets.

    ``panel_results`` (optional) is an iterable of RenderResult per panel in order,
    used to store each panel's StatsSpec; ``panel_sources`` maps panel index to
    ``{"source_path", "sheet_name", "provenance", "matrix": MatrixContext}``.
    """
    from make_my_figure_core.panels import draft_legend

    results = list(panel_results or [])
    sources = panel_sources or {}
    tables: List[TableSource] = []
    assets: List[AssetSource] = []
    comps: List[PlotComponent] = []
    digests: Dict[str, str] = {}      # content digest -> table_id (deduplicate identical tables)
    fig_d = mpf.to_dict()
    panel_dicts = fig_d.get("panels", [])
    for i, panel in enumerate(mpf.panels):
        cid = f"panel_{i + 1:02d}"
        rec = panel_dicts[i] if i < len(panel_dicts) else panel.to_dict()
        if panel.is_external:
            aid = f"{cid}_image"
            assets.append(AssetSource(aid, panel.image_path, component_id=cid,
                                      original_filename=(panel.image_meta or {}).get("original_filename")))
            comps.append(PlotComponent(cid, kind="external_figure_panel", label=panel.label, title=panel.title,
                                       asset_id=aid, panel_record=rec, width_in=panel.width_in, height_in=panel.height_in))
            continue
        if panel.plot_spec is None or panel.table is None:
            raise ValueError(f"panel {panel.label or i + 1} has no plot specification or table to package")
        src = sources.get(i, {})
        tid = _dedup_table(tables, digests, panel.table, cid, panel.plot_spec.get("input_table") or panel.source_name,
                           src.get("source_path"), src.get("sheet_name"), src.get("provenance") or {})
        aux_ids: Dict[str, str] = {}
        for aname, adf in (panel.aux or {}).items():
            aux_ids[aname] = _dedup_table(tables, digests, adf, f"{cid}_aux_{aname}", aname, None, None, {}, role="aux_table")
        res = results[i] if i < len(results) else None
        payload = _stats_payload(panel.plot_spec, res) if res is not None else None
        comps.append(PlotComponent(cid, plot_spec=panel.plot_spec, table_id=tid, aux_tables=aux_ids,
                                   stats_payload=payload, render_metadata=_render_metadata(res) if res is not None else {},
                                   kind="make_my_figure_panel", label=panel.label, title=panel.title,
                                   panel_record=rec, width_in=panel.width_in, height_in=panel.height_in))
    figure_spec = {"figure": fig_d, "draft_legend": mpf.legend_text or draft_legend(mpf),
                   "disclaimer": "Auto-generated legend text is a draft and must be verified before publication."}
    return PackageContent(kind="composite", name=name or mpf.name or "figure", components=comps, tables=tables,
                          assets=assets, figure_spec=figure_spec, preview_figure=fig, preview_dpi=preview_dpi,
                          record_original_paths=record_original_paths)


def _dedup_table(tables: List[TableSource], digests: Dict[str, str], df: pd.DataFrame, tid: str, display: Any,
                 path: Optional[str], sheet: Optional[str], prov: Dict[str, Any], role: str = "source_table") -> str:
    d = table_digest(df)
    if d in digests:
        return digests[d]
    tables.append(TableSource(tid, df, role=role, display_name=str(display) if display else tid, original_path=path,
                              sheet_name=sheet, header_row=(prov or {}).get("source_header_row"), provenance=prov or {}))
    digests[d] = tid
    return tid
