"""GUI-free application logic for the desktop app.

Everything here is testable without a running Qt event loop: loading files,
listing plot types/styles, building a PlotSpec, rendering, and exporting. The
Qt layer (``main.py``) calls into this controller and never touches plotting
internals directly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from make_my_figure_core import data as mock_data
from make_my_figure_core import examples as examples_lib
from make_my_figure_core import ui_hints
from make_my_figure_core.io.loaders import (
    LoaderError,
    TableInfo,
    load_table,
    table_info_from_dataframe,
)
from make_my_figure_core.plots.base import RenderError
from make_my_figure_core.plots.registry import (
    available_plot_types,
    default_mapping,
    display_name,
    export_bundle_bytes,
    export_figure,
    render,
    write_sidecar,
)
from make_my_figure_core.spec.validate import (
    SpecValidationError,
    default_output_block,
)
from make_my_figure_core.styles.engine import list_profiles, load_profile
from make_my_figure_core.version import __version__

# Friendly labels for style profiles (starter + learned).
STYLE_LABELS = {
    "nature_like": "Nature-like",
    "science_like": "Science-like",
    "cell_like": "Cell-like",
    "nature_like_learned": "Nature-like (learned)",
    "science_like_learned": "Science-like (learned)",
    "cell_like_learned": "Cell-like (learned)",
}


@dataclass
class LoadedData:
    info: TableInfo
    table_name: str
    aux: Dict[str, TableInfo] = field(default_factory=dict)
    source_path: Optional[str] = None
    is_example: bool = False   # True for bundled examples, False for user uploads


class DesktopController:
    """Bridges the desktop GUI and the figure core."""

    version = __version__

    # --- catalog ---------------------------------------------------------
    def plot_types(self) -> List[Tuple[str, str]]:
        return [(pt, display_name(pt)) for pt in available_plot_types()]

    def styles(self) -> List[Tuple[str, str]]:
        return [(s, STYLE_LABELS.get(s, s)) for s in list_profiles()]

    def column_fields(self, plot_type: str) -> List[str]:
        return ui_hints.column_fields(plot_type)

    def options(self, plot_type: str) -> List[ui_hints.Option]:
        return ui_hints.options(plot_type)

    def default_mapping(self, plot_type: str) -> Dict[str, Any]:
        return default_mapping(plot_type)

    def needs_metadata(self, plot_type: str) -> bool:
        return plot_type == mock_data.PCA_PLOT_TYPE

    def pca_metadata_fields(self) -> List[str]:
        return list(ui_hints.PCA_METADATA_FIELDS)

    # --- data loading ----------------------------------------------------
    def load_file(self, path: str) -> LoadedData:
        """Load a user file with friendly errors raised as ``LoaderError``."""
        info = load_table(path)
        return LoadedData(info=info, table_name=os.path.basename(path), source_path=path)

    def load_example(self, plot_type: str) -> LoadedData:
        """Load the bundled example for ``plot_type``.

        Prefers the rich ``examples/`` system; falls back to the simpler
        ``mock_data`` bundle if the example manifest is unavailable.
        """
        if examples_lib.has_manifest() and examples_lib.has_example(plot_type):
            info, aux, _spec = examples_lib.load_example(plot_type)
            return LoadedData(info=info, table_name=f"{plot_type} (example)", aux=aux,
                              is_example=True)
        info, aux = mock_data.load_sample(plot_type)
        name = mock_data.sample_filename(plot_type) or f"{plot_type}.csv"
        return LoadedData(info=info, table_name=name, aux=aux, is_example=True)

    def loaded_from_dataframe(self, df, table_name: str,
                              *, aux: Optional[Dict[str, TableInfo]] = None) -> LoadedData:
        """Wrap an in-memory DataFrame as a :class:`LoadedData` (a derived table).

        Used after in-app transforms such as reshaping a wide matrix to long or
        adding a grouping column, so the result flows through the normal
        map → render → export path.
        """
        info = table_info_from_dataframe(df, table_name)
        return LoadedData(info=info, table_name=table_name, aux=aux or {}, is_example=False)

    # --- in-app grouping (no metadata file) ------------------------------
    def group_from_matrix(self, data: LoadedData, *, sample_columns, sample_to_group,
                          feature_col=None, features=None) -> LoadedData:
        """Reshape a wide features x samples matrix to a long, group-tagged table."""
        from make_my_figure_core.grouping import melt_matrix_to_long

        long = melt_matrix_to_long(data.info.dataframe, sample_columns=sample_columns,
                                   sample_to_group=sample_to_group, feature_col=feature_col,
                                   features=features)
        name = f"{data.table_name} (grouped)"
        return self.loaded_from_dataframe(long, name)

    def add_group_column(self, data: LoadedData, *, source_col, value_to_group,
                         new_col="group", default=None) -> LoadedData:
        """Add a derived grouping column mapped from an existing column's values."""
        from make_my_figure_core.grouping import add_group_column

        out = add_group_column(data.info.dataframe, source_col=source_col,
                               value_to_group=value_to_group, new_col=new_col, default=default)
        return self.loaded_from_dataframe(out, data.table_name, aux=data.aux)

    def guess_sample_groups(self, sample_columns) -> Dict[str, str]:
        from make_my_figure_core.grouping import guess_groups_from_names

        return guess_groups_from_names(list(sample_columns))

    def example_description(self, plot_type: str) -> str:
        if examples_lib.has_manifest():
            e = examples_lib.entry(plot_type)
            if e:
                return e.get("use_case", "")
        return ""

    def example_source_path(self, plot_type: str) -> Optional[str]:
        if examples_lib.has_manifest():
            p = examples_lib.template_path(plot_type, "csv")
            if p:
                return p
        return mock_data.sample_path(plot_type)

    # --- spec + render ---------------------------------------------------
    def build_spec(
        self,
        plot_type: str,
        style_name: str,
        table_name: str,
        mapping: Dict[str, Any],
        *,
        layout: Optional[Dict[str, Any]] = None,
        width: str = "single",
        dpi: int = 300,
        formats: Optional[List[str]] = None,
        statistics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        style = load_profile(style_name)
        w_mm = style.double_column_width_mm if width == "double" else style.single_column_width_mm
        spec: Dict[str, Any] = {
            "plot_type": plot_type,
            "input_table": table_name,
            "mapping": {k: v for k, v in mapping.items() if v not in (None, "")},
            "journal_style": style_name,
            "output": default_output_block(formats or ["svg", "png", "pdf"], width_mm=w_mm, dpi=dpi),
        }
        merged_layout = dict(layout or {})
        merged_layout["column_width"] = width
        spec["layout"] = merged_layout
        if statistics and statistics.get("enabled"):
            from make_my_figure_core.statistics import normalize_stats_spec

            spec["statistics"] = normalize_stats_spec(statistics)
        return spec

    # --- statistics ------------------------------------------------------
    def available_tests(self) -> List[Tuple[str, str]]:
        """(test_id, label) for every implemented statistical test."""
        from make_my_figure_core.statistics import TESTS

        return [(tid, info.label) for tid, info in TESTS.items()]

    def recommend_tests(self, plot_type: str, mapping: Dict[str, Any],
                        data: Optional[LoadedData] = None,
                        stats_mapping: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        from make_my_figure_core.statistics import recommend_tests

        df = data.info.dataframe if data else None
        return recommend_tests(plot_type, mapping, df=df, stats_mapping=stats_mapping)

    def run_statistics(self, plot_type: str, mapping: Dict[str, Any], data: LoadedData,
                       stats_spec: Dict[str, Any]):
        """Run statistics for the current plot; returns a StatsReport."""
        from make_my_figure_core.statistics import normalize_stats_spec, run_statistics

        spec = normalize_stats_spec({**stats_spec, "enabled": True})
        return run_statistics(data.info.dataframe, spec, plot_type=plot_type, mapping=mapping)

    def stats_table_rows(self, report) -> List[Dict[str, Any]]:
        """Flatten a StatsReport into rows for a results table widget."""
        rows: List[Dict[str, Any]] = []
        for r in report.results:
            ci = ""
            if r.confidence_interval_low is not None and r.confidence_interval_low == r.confidence_interval_low:
                ci = f"[{r.confidence_interval_low:.3g}, {r.confidence_interval_high:.3g}]"
            rows.append({
                "comparison": r.comparison_label,
                "test": r.test_name,
                "statistic": "" if r.statistic is None else f"{r.statistic:.3g}",
                "p_value": "" if r.p_value is None else f"{r.p_value:.4g}",
                "adjusted_p": "" if r.adjusted_p_value is None else f"{r.adjusted_p_value:.4g}",
                "effect_size": ("" if r.effect_size is None or r.effect_size != r.effect_size
                                else f"{r.effect_size_name}={r.effect_size:.3g}"),
                "ci": ci,
                "n": "" if r.n_total is None else str(r.n_total),
                "warning": "; ".join(r.warnings),
            })
        return rows

    def export_stats_table(self, report, path: str, *, sep: str = ",") -> str:
        """Write the results table as CSV/TSV."""
        import csv

        rows = self.stats_table_rows(report)
        fields = ["comparison", "test", "statistic", "p_value", "adjusted_p",
                  "effect_size", "ci", "n", "warning"]
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, delimiter=sep)
            w.writeheader()
            for row in rows:
                w.writerow(row)
        return path

    def export_method_report(self, report, path: str, *, fmt: str = "markdown") -> str:
        """Write the method report as markdown/json/txt."""
        import json as _json

        if fmt == "json":
            from make_my_figure_core.statistics.schemas import stats_sidecar_payload

            payload = stats_sidecar_payload(report.config, report)
            with open(path, "w", encoding="utf-8") as fh:
                _json.dump(payload, fh, indent=2)
            return path
        lines = [f"# Statistical methods\n", report.method_paragraph, "",
                 "## Per-comparison results", ""]
        for r in report.results:
            lines.append(f"- {r.method_sentence}")
        if report.warnings:
            lines += ["", "## Warnings", ""] + [f"- {w}" for w in report.warnings]
        lines += ["", "## Figure legend (draft)", "", report.legend_sentence]
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        return path

    def method_sentence(self, report) -> str:
        return report.method_paragraph

    def render(self, spec: Dict[str, Any], data: LoadedData):
        """Render a figure. Raises RenderError / SpecValidationError on failure."""
        aux = {k: v.dataframe for k, v in data.aux.items()} if data.aux else None
        return render(spec, data.info.dataframe, aux=aux)

    # --- export ----------------------------------------------------------
    def export_files(self, spec, result, base_path: str, formats: List[str], dpi: int = 300) -> Dict[str, Any]:
        files = export_figure(result.figure, base_path, formats, dpi=dpi)
        sidecar = None
        if "json" in [f.lower() for f in formats] or True:
            sidecar = write_sidecar(spec, result.metadata, base_path)
        return {"files": files, "sidecar": sidecar}

    def export_bundle(self, spec, result, formats: List[str], dpi: int = 300, basename: str = "figure") -> bytes:
        return export_bundle_bytes(spec, result, formats=formats, dpi=dpi, basename=basename)

    def save_template(self, plot_type: str, dest_path: str) -> str:
        """Copy the bundled example table for ``plot_type`` to ``dest_path``.

        Picks the format (csv/tsv/xlsx) from the destination extension when an
        example file in that format exists; otherwise copies the CSV.
        """
        import shutil

        ext = os.path.splitext(dest_path)[1].lower().lstrip(".") or "csv"
        src = None
        if examples_lib.has_manifest() and examples_lib.has_example(plot_type):
            src = examples_lib.template_path(plot_type, ext) or examples_lib.template_path(plot_type, "csv")
        if not src or not os.path.exists(src):
            src = mock_data.sample_path(plot_type)
        if not src or not os.path.exists(src):
            raise FileNotFoundError(f"No bundled template for '{plot_type}'.")
        shutil.copyfile(src, dest_path)
        return dest_path
