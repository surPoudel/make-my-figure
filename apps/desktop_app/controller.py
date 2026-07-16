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
    make_spec,
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
# v0.6: a single user-facing style identity. Advanced appearance (fonts, widths,
# palette, legend, DPI, size) are controls under Publication, not separate profiles.
STYLE_LABELS = {
    "publication": "Publication",
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

    def load_plotspec(self, path: str):
        """Read a saved PlotSpec JSON and try to locate its data file.

        Returns ``(spec, data_path_or_None)``. Legacy journal style names in the
        spec are migrated to Publication. Data resolution: the spec's
        ``input_table`` (by basename) next to the JSON, else the sole data file in
        the same directory. The caller prompts for the data if unresolved.
        """
        import glob
        import json

        with open(path, "r", encoding="utf-8") as fh:
            spec = json.load(fh)
        if not isinstance(spec, dict) or "plot_type" not in spec:
            raise ValueError("This file is not a PlotSpec (no 'plot_type').")
        from make_my_figure_core.styles.engine import normalize_style_name
        if spec.get("journal_style"):
            spec["journal_style"] = normalize_style_name(spec["journal_style"])
        d = os.path.dirname(os.path.abspath(path))
        data_path = None
        it = spec.get("input_table")
        if it:
            cand = it if os.path.isabs(it) else os.path.join(d, os.path.basename(str(it)))
            if os.path.exists(cand):
                data_path = cand
        if not data_path:
            hits = []
            for pat in ("*.csv", "*.tsv", "*.txt", "*.xlsx", "*.xls"):
                hits += [h for h in glob.glob(os.path.join(d, pat))
                         if not h.endswith(".json")]
            if len(hits) == 1:
                data_path = hits[0]
        return spec, data_path

    def apply_transform(self, data: "LoadedData", transform: Dict[str, Any]) -> "LoadedData":
        """Apply a recommendation's transform spec to the current data and wrap the
        reshaped frame as a new LoadedData (named after the transform output)."""
        from make_my_figure_core.transforms import apply_transform

        df = apply_transform(data.info.dataframe, transform["name"], transform.get("params"))
        name = transform.get("output_filename") or f"{data.table_name}.transformed.csv"
        return self.loaded_from_dataframe(df, name)

    def save_table(self, df, path: str) -> str:
        """Write a DataFrame to CSV (used to persist a transform's output)."""
        df.to_csv(path, index=False)
        return path

    # --- in-app differential screen (normalized matrix; NOT count-based DE) ---
    def differential_test_choices(self) -> List[Tuple[str, str]]:
        """(test_id, label) for the per-feature differential-screen tests."""
        from make_my_figure_core.differential import TESTS, _TEST_LABELS

        return [(t, _TEST_LABELS.get(t, t)) for t in TESTS]

    def run_differential_screen(self, data: "LoadedData", *, feature_col: str,
                                group_labels: Dict[str, str], test: str = "welch_t",
                                log_input: bool = True,
                                reference_group: Optional[str] = None):
        """Run the differential screen on a normalized matrix and wrap the results
        table as a LoadedData. Returns ``(loaded, DifferentialResult)``."""
        from make_my_figure_core.differential import differential_screen

        result = differential_screen(
            data.info.dataframe, feature_col=feature_col, group_labels=group_labels,
            test=test, log_input=log_input, reference_group=reference_group)
        base = data.table_name.rsplit(".", 1)[0] if "." in data.table_name else data.table_name
        loaded = self.loaded_from_dataframe(result.table, f"{base}__diff.csv")
        return loaded, result

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

    def group_from_matrix_wide(self, data: LoadedData, *, sample_columns, sample_to_group,
                               feature_col=None, features=None):
        """Keep the wide matrix (assigned samples only) + a group color-strip spec.

        For heatmaps/PCA, where a long reshape would collapse the matrix and show
        nothing. Returns ``(LoadedData, column_annotations)``.
        """
        from make_my_figure_core.grouping import wide_grouped_matrix

        wide, ann = wide_grouped_matrix(
            data.info.dataframe, feature_col=feature_col, sample_columns=sample_columns,
            sample_to_group=sample_to_group, features=features)
        return self.loaded_from_dataframe(wide, f"{data.table_name} (grouped)"), ann

    def numeric_sample_columns(self, data: LoadedData, feature_col=None):
        from make_my_figure_core.grouping import numeric_sample_columns

        return numeric_sample_columns(data.info.dataframe, feature_col)

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

    # --- recommendations (intelligent figure suggestions) ----------------
    def recommend_for_loaded(self, data: LoadedData):
        """Profile the loaded table and return a RecommendationSpec (cheap; no
        expensive analysis is run — recommendations marked requires_confirmation
        must be confirmed before generating)."""
        from make_my_figure_core.recommendations import recommend_for_table

        return recommend_for_table(data.info.dataframe, table_name=data.table_name)

    def recommend_after_analysis(self, data: LoadedData, *, stats_report=None,
                                 differential: bool = False, has_matrix: bool = False):
        from make_my_figure_core.recommendations import recommend_after_analysis

        return recommend_after_analysis(
            data.info.dataframe, stats_report=stats_report,
            differential=differential, has_matrix=has_matrix, table_name=data.table_name)

    # --- publication QC --------------------------------------------------
    def publication_qc(self, result, spec: Optional[Dict[str, Any]] = None,
                       stats_report=None):
        """Score the rendered figure for publication readiness (advisory)."""
        from make_my_figure_core.qc import score_publication

        return score_publication(result=result, spec=spec, stats_report=stats_report)

    def qc_suggested_fixes(self, score, spec: Dict[str, Any]):
        from make_my_figure_core.qc import suggest_fixes

        return suggest_fixes(score, spec)

    def apply_qc_fixes(self, spec: Dict[str, Any], fix_ids: List[str]) -> Dict[str, Any]:
        from make_my_figure_core.qc import apply_fixes

        return apply_fixes(spec, fix_ids)

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

    # --- matrix workflow (GUI-free; the Qt wizard is a thin layer over these) ---
    def matrix_suggest_spec(self, data: LoadedData):
        """Suggest (unconfirmed) column roles for a feature matrix."""
        import make_my_figure_core.matrix_workflow as mw

        return mw.suggest_matrix_spec(data.info.dataframe, source_file=data.table_name)

    def matrix_value_types(self) -> Tuple[str, ...]:
        from make_my_figure_core.matrix_workflow.matrix_spec import VALUE_TYPES

        return VALUE_TYPES

    def matrix_looks_log_scale(self, data: LoadedData, value_columns) -> bool:
        import make_my_figure_core.matrix_workflow as mw

        return mw.looks_log_scale(data.info.dataframe, list(value_columns))

    def matrix_metadata_from_assignment(self, sample_to_group: Dict[str, str]):
        import make_my_figure_core.matrix_workflow as mw

        return mw.metadata_from_assignment(sample_to_group)

    def matrix_validate(self, data: LoadedData, matrix_spec, metadata=None):
        import make_my_figure_core.matrix_workflow as mw

        return mw.validate_matrix(data.info.dataframe, matrix_spec, metadata)

    def matrix_recommendations(self, data: LoadedData, matrix_spec, metadata=None, *,
                               has_differential: bool = False):
        import make_my_figure_core.matrix_workflow as mw

        return mw.recommend_plots(matrix_spec, metadata,
                                  has_differential_summary=has_differential,
                                  n_features=len(data.info.dataframe))

    def matrix_stats_choices(self):
        """Return ``(two_group_tests, multi_group_tests, corrections)`` label lists."""
        from make_my_figure_core.matrix_workflow.differential_summary import (
            CORRECTIONS,
            MULTI_GROUP_TESTS,
            TWO_GROUP_TESTS,
        )

        return TWO_GROUP_TESTS, MULTI_GROUP_TESTS, CORRECTIONS

    def matrix_can_run_statistics(self, matrix_spec, metadata):
        import make_my_figure_core.matrix_workflow as mw

        return mw.require_for_statistics(matrix_spec, metadata)

    def matrix_differential_summary(self, data: LoadedData, matrix_spec, metadata, *,
                                    group_a, group_b=None, test="welch_t",
                                    correction="benjamini_hochberg",
                                    preprocessing_note="", source_matrix_id=None,
                                    preprocessing_spec_id=None):
        """Feature-level differential summary.

        When the input is a derived (preprocessed) matrix, pass ``preprocessing_note``
        (``PreprocessingSpec.method_sentence()``), ``source_matrix_id`` and
        ``preprocessing_spec_id`` so the stored result — and its method sentence — trace
        back to the exact preprocessing chain."""
        import make_my_figure_core.matrix_workflow as mw

        return mw.feature_differential_summary(
            data.info.dataframe, matrix_spec, metadata, group_a=group_a, group_b=group_b,
            test=test, correction=correction, preprocessing_note=preprocessing_note,
            source_matrix_id=source_matrix_id, preprocessing_spec_id=preprocessing_spec_id)

    def matrix_build_plot(self, data: LoadedData, rec, matrix_spec, *, metadata=None,
                          differential_table=None, selected_features=None, params=None,
                          style_overrides=None):
        """Turn a recommendation into a rendered figure.

        ``style_overrides`` (palette_name / font_family / *_pt / marker_size / ...) is
        recorded under ``spec['style']`` so the matrix-workflow plot honours the same
        Publication style controls as the main workbench. Returns ``(spec_dict,
        RenderResult, PlotInputs)``; raises ValueError/RenderError on failure."""
        import make_my_figure_core.matrix_workflow as mw

        pi = mw.build_plot_inputs(rec, data.info.dataframe, matrix_spec, metadata=metadata,
                                  differential_table=differential_table,
                                  selected_features=selected_features, params=params)
        spec = make_spec(pi.plot_type, matrix_spec.source_file or data.table_name,
                         "publication", mapping=pi.mapping)
        for k, v in (pi.spec_extra or {}).items():   # e.g. column_annotations (group strip)
            spec[k] = v
        if style_overrides:
            spec["style"] = dict(style_overrides)
        aux = pi.aux or None
        result = render(spec, pi.dataframe, aux=aux)
        return spec, result, pi

    # --- raw-like matrix preprocessing / QC (GUI-free; the wizard is a thin layer) ---
    def matrix_diagnose(self, data: LoadedData, matrix_spec):
        import make_my_figure_core.matrix_workflow as mw

        return mw.diagnose_matrix(data.info.dataframe, matrix_spec)

    def matrix_preprocessing_recommendations(self, qc):
        import make_my_figure_core.matrix_workflow as mw

        return mw.recommend_preprocessing(qc)

    def matrix_preprocessing_methods(self):
        import make_my_figure_core.matrix_workflow as mw

        return mw.available_methods()

    def matrix_qc_plot_catalog(self):
        import make_my_figure_core.matrix_workflow as mw

        return mw.qc_plot_catalog()

    def matrix_qc_plot(self, data: LoadedData, matrix_spec, kind, *, metadata=None):
        """Render one QC plot; returns (spec, RenderResult)."""
        import make_my_figure_core.matrix_workflow as mw

        pi = mw.qc_plot_inputs(kind, data.info.dataframe, matrix_spec, metadata=metadata)
        spec = make_spec(pi.plot_type, matrix_spec.source_file or data.table_name,
                         "publication", mapping=pi.mapping)
        for k, v in (pi.spec_extra or {}).items():
            spec[k] = v
        result = render(spec, pi.dataframe, aux=pi.aux or None)
        return spec, result

    def matrix_apply_preprocessing(self, data: LoadedData, matrix_spec, steps, *,
                                   metadata=None, output_matrix_id="processed"):
        """Apply a confirmed preprocessing chain; return (derived LoadedData, derived
        MatrixSpec, PreprocessingSpec). The original data is untouched."""
        import make_my_figure_core.matrix_workflow as mw

        final_df, dspec, ps = mw.run_preprocessing(
            data.info.dataframe, matrix_spec, steps, metadata=metadata,
            output_matrix_id=output_matrix_id)
        loaded = self.loaded_from_dataframe(final_df, f"{data.table_name} [{output_matrix_id}]")
        return loaded, dspec, ps

    def matrix_before_after_report(self, data: LoadedData, matrix_spec, steps, out_dir, *,
                                   metadata=None):
        """Write a before/after QC report; returns (final_df, dspec, PreprocessingSpec, records)."""
        import make_my_figure_core.matrix_workflow as mw

        return mw.before_after_report(data.info.dataframe, matrix_spec, steps, out_dir,
                                      metadata=metadata)
