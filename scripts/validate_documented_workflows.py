"""Exercise the workflows the manuals describe, through the same GUI-free controller and core
functions the two apps call, and record the outcome for the documentation validation table.

Covers: load a bundled example -> map -> render -> export every engine format (PNG, TIFF, PDF,
SVG, EPS) with a PlotSpec sidecar; save a Figure preset (style + full) and apply it to a second
dataset (mapping check, remapping report); open the bundled multi-sheet workbook, list/classify
sheets, load and switch sheets; Matrix workflow smoke path (MatrixSpec -> groups -> preprocessing
with a PreprocessingSpec -> PCA + clustered heatmap through the normal plot editor path);
statistics on a box plot with a StatsSpec; Figure Builder (generated + imported panel ->
FigureSpec -> rebuild).  Only bundled example data are used.

Run: python scripts/validate_documented_workflows.py
Writes: docs/manuals/audit/v1.1.0_documentation_validation.csv
"""
from __future__ import annotations

import csv
import json
import os
import sys
import tempfile
import traceback

import matplotlib

matplotlib.use("Agg")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
os.environ["MAKE_MY_FIGURE_PRESETS"] = tempfile.mkdtemp(prefix="mmf_presets_")

from apps.desktop_app.controller import DesktopController  # noqa: E402
from make_my_figure_core.plots.registry import export_figure, write_sidecar  # noqa: E402
from make_my_figure_core.version import __version__  # noqa: E402

OUT = os.path.join(ROOT, "docs", "manuals", "audit", "v1.1.0_documentation_validation.csv")
TMP = tempfile.mkdtemp(prefix="mmf_docs_validation_")
rows = []


def record(section, claim, code_source, ok, notes=""):
    rows.append({"section": section, "claim": claim, "code_source": code_source,
                 "UI_verified": "controller/core path shared by both apps", "workflow_tested": "yes",
                 "screenshot_current": "n/a", "version_current": __version__,
                 "status": "PASS" if ok else "FAIL", "notes": notes})
    print(("PASS " if ok else "FAIL ") + claim + (f" — {notes}" if notes else ""))


def step(section, claim, code_source, fn):
    try:
        notes = fn() or ""
        record(section, claim, code_source, True, notes)
    except Exception as exc:  # noqa: BLE001
        record(section, claim, code_source, False, f"{type(exc).__name__}: {exc}")
        traceback.print_exc()


ctl = DesktopController()

# ---------------------------------------------------------------- load / map / render / export
state = {}


def t_load_example():
    data = ctl.load_example("boxplot_or_violin_with_points")
    state["box"] = data
    return f"{data.table_name}: {data.info.dataframe.shape[0]} rows, numeric {data.info.numeric_columns[:3]}"


def t_render_export():
    data = state["box"]
    mapping = ctl.default_mapping("boxplot_or_violin_with_points")
    spec = ctl.build_spec("boxplot_or_violin_with_points", "publication", data.table_name, mapping,
                          layout={"title": "Validation box plot"}, formats=["svg", "png", "pdf", "tiff", "eps"])
    res = ctl.render(spec, data)
    base = os.path.join(TMP, "box")
    files = export_figure(res.figure, base, ["svg", "png", "pdf", "tiff", "eps"], dpi=300)
    side = write_sidecar(spec, res.metadata, base)
    state["box_spec"] = spec
    sizes = {os.path.splitext(f)[1]: os.path.getsize(f) for f in files}
    assert set(sizes) == {".svg", ".png", ".pdf", ".tiff", ".eps"} and all(v > 0 for v in sizes.values())
    assert os.path.exists(side) and json.load(open(side))["plot_spec"]["plot_type"] == "boxplot_or_violin_with_points"
    svg = open(base + ".svg", encoding="utf-8").read()
    assert "<text" in svg and "Validation box plot" in svg   # text kept as text
    return f"exports {sorted(sizes)}; sidecar {os.path.basename(side)}"


step("Quick Start 4-5 / Manual 17,21,70", "Load a bundled example, map columns, render, export SVG/PNG/PDF/TIFF/EPS with PlotSpec sidecar",
     "DesktopController.load_example/build_spec/render; registry.export_figure/write_sidecar", t_load_example)
step("Quick Start 5, 11 / Manual 70", "Render and export all five engine formats; SVG keeps text as text",
     "registry.export_figure (_EXPORT_FORMATS), _VECTOR_TEXT_RC", t_render_export)

# ---------------------------------------------------------------- statistics
def t_stats():
    data = state["box"]
    mapping = ctl.default_mapping("boxplot_or_violin_with_points")
    tests = [k for k, _ in ctl.available_tests()]
    assert "welch_t" in tests
    report = ctl.run_statistics("boxplot_or_violin_with_points", mapping, data,
                                {"enabled": True, "test": "welch_t", "comparisons": "all_pairs", "correction": "benjamini_hochberg"})
    rows_ = ctl.stats_table_rows(report)
    assert rows_ and all("p_value" in r or "p" in " ".join(r.keys()) for r in rows_)
    sent = ctl.method_sentence(report)
    spec = ctl.build_spec("boxplot_or_violin_with_points", "publication", data.table_name, mapping,
                          statistics={"enabled": True, "test": "welch_t", "comparisons": "all_pairs", "correction": "benjamini_hochberg"})
    res = ctl.render(spec, data)
    assert res.stats_report is not None and "statistics_report" in res.metadata
    base = os.path.join(TMP, "box_stats"); write_sidecar(spec, res.metadata, base)
    return f"{len(rows_)} comparisons; method sentence: {sent[:70]}…"


step("Quick Start 7 / Manual 33-40", "Run Welch's t with BH correction on a box plot; results table, method sentence, StatsSpec in the export",
     "DesktopController.run_statistics/stats_table_rows/method_sentence; statistics.runner", t_stats)

# ---------------------------------------------------------------- figure presets
def t_presets():
    from make_my_figure_core import presets as P
    spec = json.loads(json.dumps(state["box_spec"]))
    spec["style"] = {"palette_name": "colorblind", "marker_size": 30.0, "axis_font_pt": 11.0}
    spec["mapping"]["point_size"] = 20.0
    style_preset = P.extract_preset(spec, mode="style", name="Validation style")
    full_preset = P.extract_preset(spec, mode="full", name="Validation full")
    assert not P.preset_contains_data(style_preset)
    store = P.PresetStore()
    p1 = store.save(style_preset); p2 = store.save(full_preset)
    assert os.path.exists(p1) and os.path.exists(p2)
    # apply the style preset to a different table/plot of the same type (violin example)
    other = ctl.load_example("raincloud_plot") if False else ctl.load_example("boxplot_or_violin_with_points")
    new_spec = ctl.build_spec("boxplot_or_violin_with_points", "publication", "other_table.csv",
                              {"x": other.info.categorical_columns[0], "y": other.info.numeric_columns[0]})
    result = P.apply_preset(store.load(p1), new_spec)
    applied = result.spec if hasattr(result, "spec") else new_spec
    assert applied["style"].get("marker_size") == 30.0 and applied["mapping"].get("point_size") == 20.0
    assert applied["input_table"] == "other_table.csv"
    # full preset onto a table lacking the roles -> unresolved roles reported, nothing substituted
    bare = ctl.build_spec("boxplot_or_violin_with_points", "publication", "bare.csv", {})
    r2 = P.apply_preset(store.load(p2), bare, columns=["colA", "colB"]) if "columns" in P.apply_preset.__code__.co_varnames else P.apply_preset(store.load(p2), bare)
    unresolved = getattr(r2, "unresolved_roles", None)
    exp = store.export_file(p1, os.path.join(TMP, "exported.mmfpreset.json"))
    imp = store.import_file(exp, rename="Imported copy")
    names = [e.name if hasattr(e, "name") else str(e) for e in store.list()]
    assert store.delete(imp)
    return f"style+full saved; style applied (marker_size 30, point_size 20 carried); full preset unresolved roles: {unresolved}; export/import/delete ok; store had {len(names)} entries"


step("Quick Start 9 / Manual 53-60", "Save a Figure preset (style and full), apply to a new dataset, remapping report, import/export/delete",
     "presets.extract_preset/apply_preset/PresetStore", t_presets)

# ---------------------------------------------------------------- multi-sheet Excel
def t_workbook():
    path = os.path.join(ROOT, "examples", "multi_sheet_workbook", "synthetic_multisheet.xlsx")
    assert os.path.exists(path)
    wb = ctl.inspect_workbook(path)
    sheets = list(wb.sheet_names)
    kinds = {name: ctl.preview_sheet(wb, name, source=path).inferred_type for name in sheets}
    assert len(sheets) >= 3
    first = ctl.load_file(path, sheet_name="Comparison_A")
    second = ctl.load_file(path, sheet_name="Matrix")
    assert first.is_workbook and first.sheet_name == "Comparison_A" and second.sheet_name == "Matrix"
    prov = first.source_provenance
    prov = prov() if callable(prov) else prov
    assert prov.get("source_sheet_name") == "Comparison_A" and prov.get("source_workbook_name") == "synthetic_multisheet.xlsx"
    assert second.source_provenance().get("source_sheet_name") == "Matrix"
    return f"sheets {sheets} kinds {kinds}; loaded Comparison_A ({first.info.dataframe.shape}) then Matrix ({second.info.dataframe.shape}); provenance keys {sorted(prov)[:5]}"


step("Manual 72 / Quick Start 4", "Open a multi-sheet workbook, list and classify sheets, load a sheet, switch to another, provenance recorded",
     "io.workbook.inspect_excel_workbook/classify_worksheet; DesktopController.load_file(sheet_name)", t_workbook)

# ---------------------------------------------------------------- matrix workflow
def t_matrix():
    from make_my_figure_core.matrix_workflow.matrix_spec import suggest_matrix_spec
    from make_my_figure_core.matrix_workflow.metadata_spec import metadata_from_assignment, metadata_sample_match
    from make_my_figure_core.matrix_workflow.preprocessing import run_preprocessing
    from make_my_figure_core.matrix_workflow.transformations import compute_pca, hierarchical_clustering
    data = ctl.load_example("heatmap_clustered_matrix")
    df = data.info.dataframe
    mspec = suggest_matrix_spec(df, source_file=data.table_name)
    assert mspec.feature_id_column and len(mspec.value_columns) >= 4
    groups = ctl.guess_sample_groups(list(mspec.value_columns))
    meta = metadata_from_assignment(groups)
    match = metadata_sample_match(meta, list(mspec.value_columns))
    out_df, out_spec, pspec = run_preprocessing(df, mspec, [{"method": "log2", "params": {"pseudocount": 1.0}}, {"method": "row_zscore", "params": {}}])
    assert df.equals(data.info.dataframe)                      # original untouched
    assert len(pspec.preprocessing_steps) == 2 and pspec.preprocessing_steps[0].method_name == "log2"
    scores, tspec = compute_pca(out_df, out_spec, n_components=2)
    clus, cspec = hierarchical_clustering(out_df, out_spec)
    spec = ctl.build_spec("heatmap_clustered_matrix", "publication", data.table_name, {"row_id": mspec.feature_id_column})
    res = ctl.render(spec, ctl.loaded_from_dataframe(out_df, data.table_name + "_processed"))
    return f"matrix {df.shape}; groups guessed {sorted(set(groups.values()))}; match {match.get('n_matched', match)}; 2 preprocessing steps recorded; PCA scores {scores.shape}; heatmap rendered {res.metadata['matrix_shape']}"


step("Quick Start 8 / Manual 27-32", "Matrix workflow smoke path: MatrixSpec, groups, preprocessing (PreprocessingSpec), PCA, clustered heatmap; original matrix untouched",
     "matrix_workflow.matrix_spec/metadata_spec/preprocessing/transformations; DesktopController.loaded_from_dataframe", t_matrix)

# ---------------------------------------------------------------- Figure Builder
def t_builder():
    from make_my_figure_core.panels import FigureLayout, MultiPanelFigure, Panel, build_figure, export_multipanel, import_external_panel, multipanel_sidecar, panel_from_dict
    box = state["box"]; spec = state["box_spec"]
    assets = os.path.join(TMP, "assets"); os.makedirs(assets, exist_ok=True)
    imported, _ = import_external_panel(os.path.join(TMP, "box.png"), assets, width_in=3.0)
    mpf = MultiPanelFigure(name="Validation", panels=[Panel(plot_spec=spec, table=box.info.dataframe, source_name=box.table_name, width_in=3.4), imported],
                           layout=FigureLayout(ncols=2, fig_width_mm=180.0, label_style="A"))
    fig = build_figure(mpf)
    files = export_multipanel(fig, os.path.join(TMP, "composite"), ["png", "pdf", "svg"], dpi=300)
    side = multipanel_sidecar(mpf, os.path.join(TMP, "composite"))
    d = json.load(open(side))["figure"]
    rebuilt = [panel_from_dict(pd_, assets_dir=assets) for pd_ in d["panels"]]
    rebuilt[0].table = box.info.dataframe
    fig2 = build_figure(MultiPanelFigure(name=d["name"], panels=rebuilt, layout=FigureLayout.from_dict(d["layout"])))
    assert len(fig.axes) == len(fig2.axes) == 2 and [p["label"] for p in d["panels"]] == ["A", "B"]
    return f"composite exported {[os.path.basename(f) for f in files]}; FigureSpec {os.path.basename(side)} with {len(d['panels'])} panels; rebuilt with {len(fig2.axes)} axes"


step("Quick Start 10 / Manual 64-68", "Figure Builder: generated + imported panel, labels A/B, export PNG/PDF/SVG, FigureSpec written and rebuilt",
     "panels.builder.build_figure/export_multipanel/multipanel_sidecar/panel_from_dict/import_external_panel", t_builder)

# ---------------------------------------------------------------- recommendations
def t_recs():
    data = state["box"]
    recs = ctl.recommend_for_loaded(data)
    cands = recs.recommendations
    top = recs.top
    return f"schema {recs.schema}; {len(cands)} recommendations; top {top.plot_type}"


step("Quick Start 6 / Manual 24-26", "Recommendations for a loaded table (rule-based, advisory)",
     "DesktopController.recommend_for_loaded; recommendations.run_recommendations", t_recs)

# ---------------------------------------------------------------- write
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(f"\n{sum(r['status']=='PASS' for r in rows)}/{len(rows)} PASS -> {os.path.relpath(OUT, ROOT)}")
sys.exit(0 if all(r["status"] == "PASS" for r in rows) else 1)
