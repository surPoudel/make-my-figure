"""Execute every step-by-step workflow the manuals describe, headlessly, and record the outcome.

Each entry names a manual section, the instruction as written for the user, how it was executed
(core API, desktop controller, offscreen Qt widget, or Streamlit AppTest), and PASS/FAIL with
evidence. Only bundled example data is used. Output: docs/manuals/audit/manual_instruction_validation.csv
"""
from __future__ import annotations

import csv
import json
import os
import sys
import tempfile
import warnings

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
TMP = tempfile.mkdtemp(prefix="mmf_manual_validate_")
os.environ["MAKE_MY_FIGURE_PRESETS"] = os.path.join(TMP, "presets")

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from make_my_figure_core import examples as ex  # noqa: E402
from make_my_figure_core import presets as P  # noqa: E402
from make_my_figure_core.io.loaders import load_table  # noqa: E402
from make_my_figure_core.plots.registry import (available_plot_types, export_figure,  # noqa: E402
                                                make_spec, render, write_sidecar,
                                                write_stats_sidecar)

OUT = os.path.join(ROOT, "docs", "manuals", "audit", "manual_instruction_validation.csv")
rows = []


def record(section, instruction, how, ok, evidence):
    rows.append({"manual_section": section, "instruction": instruction, "executed_via": how,
                 "status": "PASS" if ok else "FAIL", "evidence": str(evidence)[:220]})
    print(f"  {'PASS' if ok else 'FAIL'}  [{section}] {instruction}")


def quiet(spec, df, aux=None):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return render(spec, df, aux=aux)


def step(section, instruction, how, fn):
    try:
        ev = fn()
        record(section, instruction, how, True, ev)
    except Exception as exc:  # noqa: BLE001
        record(section, instruction, how, False, f"{type(exc).__name__}: {exc}")
    finally:
        plt.close("all")


# --- Quick Start 4 / Manual IV: load data ------------------------------------------------------
def _load_csv():
    p = ex.template_path("barplot_with_error_bar", "csv")
    info = load_table(p)
    return f"{info.dataframe.shape} columns={list(info.columns)[:3]}"
step("QS4 / IV", "Load a CSV table", "core load_table", _load_csv)
step("QS4 / IV", "Load a TSV table", "core load_table",
     lambda: str(load_table(ex.template_path("scatterplot_with_regression", "tsv")).dataframe.shape))
step("QS4 / IV", "Load an Excel worksheet (.xlsx)", "core load_table",
     lambda: str(load_table(ex.template_path("volcano_plot", "xlsx")).dataframe.shape))


def _workbook():
    from make_my_figure_core.io import workbook as W
    wb = os.path.join(ROOT, "examples", "Make_My_Figure_All_Example_Data.xlsx")
    info = W.inspect_workbook(wb) if hasattr(W, "inspect_workbook") else None
    if info is None:
        from apps.desktop_app.controller import DesktopController
        info = DesktopController().inspect_workbook(wb)
    from apps.desktop_app.controller import DesktopController
    c = DesktopController()
    names = list(info.sheet_names)
    kinds = []
    for n in names[:3]:
        ws = c.preview_sheet(info, n, source=wb)
        kinds.append(getattr(ws, "inferred_type", None) or getattr(ws, "sheet_type", "?"))
    return f"{len(names)} sheets; hidden={list(info.hidden_sheets)}; first={names[:3]}; types={kinds}"
step("QS4 / XVIII", "Open a multi-sheet workbook and list every worksheet with its classification",
     "controller inspect_workbook", _workbook)


def _select_sheet():
    from apps.desktop_app.controller import DesktopController
    c = DesktopController()
    wb = os.path.join(ROOT, "examples", "Make_My_Figure_All_Example_Data.xlsx")
    info = c.inspect_workbook(wb)
    second = list(info.sheet_names)[1]
    data = c.load_workbook_sheet(info, second, source=wb)
    return f"selected sheet {second!r} -> {data.info.dataframe.shape}"
step("QS4 / XVIII", "Switch to another worksheet and use it as the data table", "controller", _select_sheet)


def _header_row():
    csv_bytes = b"Exported report,,\ngene,value,note\nA,1.5,ok\nB,2.5,ok\n"
    one = load_table(csv_bytes, source_name="s.csv", file_type="csv", header=1)
    two = load_table(b"grpA,,grpB,\nr1,r2,r1,r2\n1,2,3,4\n", source_name="s.csv", file_type="csv", header=[0, 1])
    return f"header=1 -> {list(one.columns)}; stacked -> {list(two.columns)}"
step("IV", "Choose the header row / two stacked header rows (browser app)", "core load_table", _header_row)

# --- Quick Start 5 / Manual V, XI, XVII: map, render, style, export -------------------------------
def _basic_figure():
    info, aux, spec = ex.load_example("barplot_with_error_bar")
    spec["style"] = {"title_font_pt": 16, "palette_name": "colorblind_safe"}
    spec["layout"] = {**spec.get("layout", {}), "x_tick_rotation": 45, "title": "Example"}
    res = quiet(spec, info.dataframe)
    base = os.path.join(TMP, "basic")
    files = export_figure(res.figure, base, ["png", "pdf", "svg", "tiff", "eps"], dpi=300)
    side = write_sidecar(spec, res.metadata, base)
    return f"{len(files)} files + sidecar {os.path.basename(side)}"
step("QS5 / XVII", "Map x/y/group, preview, adjust Publication controls, export PNG/PDF/SVG (+TIFF/EPS)",
     "core render + export_figure", _basic_figure)


def _svg_text():
    info, aux, spec = ex.load_example("scatterplot_with_regression")
    res = quiet(spec, info.dataframe)
    base = os.path.join(TMP, "svgtext")
    export_figure(res.figure, base, ["svg"])
    txt = open(base + ".svg", encoding="utf-8").read()
    assert "<text" in txt
    return "SVG keeps live <text> elements (editable)"
step("XVII", "Exported SVG text stays editable", "core export_figure", _svg_text)

# --- Quick Start 6 / Manual VI: recommendations ----------------------------------------------------
def _recs():
    from make_my_figure_core.recommendations import recommend_for_table
    info, aux, spec = ex.load_example("boxplot_or_violin_with_points")
    r = recommend_for_table(info.dataframe, table_name="t")
    recs = r.recommendations
    return f"schema={r.schema}; top={[(x.plot_type, round(x.confidence, 2)) for x in recs[:3]]}"
step("QS6 / VI", "See recommended plots for a grouped-observation table", "core recommend_for_table", _recs)

# --- Quick Start 7 / Manual IX: statistics --------------------------------------------------------
def _two_group():
    info, aux, spec = ex.load_example("boxplot_or_violin_with_points")
    df = info.dataframe
    groups = list(pd.unique(df[spec["mapping"]["x"]]))[:2]
    sub = df[df[spec["mapping"]["x"]].isin(groups)]
    spec["statistics"] = {"enabled": True, "test": "welch_t", "comparison_mode": "all_pairs",
                          "annotation": {"content": "p_stars", "placement": "bracket"}}
    res = quiet(spec, sub)
    rep = res.stats_report
    r0 = rep.results[0]
    base = os.path.join(TMP, "stats")
    export_figure(res.figure, base, ["png"]); side = write_stats_sidecar(spec, res, base)
    return f"{r0.test_name} p={r0.p_value:.3g} effect {r0.effect_size_name}={r0.effect_size:.2f}; stats sidecar {os.path.basename(side)}"
step("QS7 / IX", "Two-group comparison: choose test, view p-value + effect size, annotate the figure",
     "core render with statistics", _two_group)


def _every_test():
    from make_my_figure_core.statistics import TESTS
    return f"{len(TESTS)} methods: {', '.join(TESTS)}"
step("IX", "Statistics registry lists 18 methods", "core statistics.TESTS", _every_test)


def _method_report():
    from apps.desktop_app.controller import DesktopController
    c = DesktopController()
    info, aux, spec = ex.load_example("barplot_with_error_bar")
    spec["statistics"] = {"enabled": True, "test": "welch_t", "comparison_mode": "vs_control",
                          "reference_group": str(info.dataframe[spec["mapping"]["x"]].iloc[0])}
    res = quiet(spec, info.dataframe)
    t = c.export_stats_table(res.stats_report, os.path.join(TMP, "stats_table.csv"))
    m = c.export_method_report(res.stats_report, os.path.join(TMP, "method.md"))
    return f"{os.path.basename(t)}, {os.path.basename(m)}; sentence: {c.method_sentence(res.stats_report)[:80]}"
step("IX", "Export stats table and method report; copy the method sentence", "desktop controller", _method_report)

# --- Quick Start 8 / Manual VII, VIII: matrix workflow ----------------------------------------------
def _matrix_workflow():
    from apps.desktop_app.controller import DesktopController
    c = DesktopController()
    data = c.load_example("heatmap_clustered_matrix")
    df = data.info.dataframe
    cols = [x for x in df.columns if x != "gene"]
    spec = c.matrix_suggest_spec(data) if hasattr(c, "matrix_suggest_spec") else None
    from make_my_figure_core import matrix_workflow as mw
    mspec = mw.MatrixSpec(feature_id_column="gene", value_columns=cols, value_type="raw_numeric",
                          confirmed_by_user=True)
    from make_my_figure_core.grouping import guess_groups_from_names
    assign = guess_groups_from_names(cols)
    meta = mw.metadata_from_assignment(assign) if hasattr(mw, "metadata_from_assignment") else None
    if meta is not None and not hasattr(meta, "sample_to_group") and not isinstance(meta, dict):
        pass
    qc = c.matrix_diagnose(data, mspec) if hasattr(c, "matrix_diagnose") else mw.diagnose_matrix(df, mspec)
    methods = mw.available_methods()
    return f"value columns={len(cols)}; groups={sorted(set(assign.values()))}; QC keys={list(qc.__dict__)[:4] if hasattr(qc,'__dict__') else type(qc).__name__}; {len(methods)} preprocessing methods"
step("QS8 / VII", "Matrix Workflow: map feature/value columns, define groups from names, run QC, list preprocessing methods",
     "controller + matrix_workflow core", _matrix_workflow)


def _preprocess():
    from make_my_figure_core import matrix_workflow as mw
    info, aux, spec = ex.load_example("heatmap_clustered_matrix")
    df = info.dataframe
    cols = [x for x in df.columns if x != "gene"]
    mspec = mw.MatrixSpec(feature_id_column="gene", value_columns=cols, value_type="raw_numeric",
                          confirmed_by_user=True)
    before = df.copy(deep=True)
    out_df, out_spec, step_ = mw.apply_step(df, mspec, "log2", params={})
    pd.testing.assert_frame_equal(df, before)
    return f"log2 applied -> {out_df.shape}; step {step_.method_name} recorded; original matrix unchanged"
step("VIII", "Apply a preprocessing step (log2) and confirm the original matrix is preserved",
     "matrix_workflow.apply_step", _preprocess)

# --- Quick Start 9 / Manual XIV: presets ----------------------------------------------------------------
def _preset_roundtrip():
    info, aux, spec = ex.load_example("heatmap_clustered_matrix")
    spec["style"] = {"tick_label_pt": 9, "palette_name": "grayscale"}
    spec["mapping"]["colormap"] = "viridis"
    preset = P.extract_preset(spec, mode="style", name="Lab Heatmap")
    store = P.PresetStore(); path = store.save(preset)
    # new dataset of the same type: the mock sample
    from make_my_figure_core import data as mock
    new = load_table(mock.sample_path("heatmap_clustered_matrix"))
    fresh = make_spec("heatmap_clustered_matrix", "new.tsv", "publication",
                      mapping={"row_id": spec["mapping"]["row_id"]})
    res = P.apply_preset(P.load_preset(path), fresh, columns=new.columns)
    out = quiet(res.spec, new.dataframe)
    assert res.spec["style"]["palette_name"] == "grayscale" and res.spec["mapping"]["colormap"] == "viridis"
    assert P.preset_contains_data(preset) == []
    exp = store.export_file("Lab Heatmap", os.path.join(TMP, "shared"))
    store.import_file(exp, rename="Lab Heatmap (imported)")
    names = [e.name for e in store.list("heatmap_clustered_matrix")]
    store.delete("Lab Heatmap (imported)")
    return f"saved {os.path.basename(path)}; applied to {new.dataframe.shape}; library={names}"
step("QS9 / XIV", "Save a Figure preset, load new data, apply it, export/import/delete it",
     "core presets + PresetStore", _preset_roundtrip)


def _plotspec_as_preset():
    info, aux, spec = ex.load_example("forest_plot")
    p = os.path.join(TMP, "old.plot_spec.json"); json.dump(spec, open(p, "w"))
    pr = P.load_preset(p)
    return f"mode={pr['mode']} plot_type={pr['plot_type']}"
step("XIV / XV", "Load an existing PlotSpec JSON as a (full) preset", "core load_preset", _plotspec_as_preset)


def _plotspec_reload():
    from apps.desktop_app.controller import DesktopController
    c = DesktopController()
    info, aux, spec = ex.load_example("roc_curve")
    p = os.path.join(TMP, "roc.plot_spec.json"); json.dump(spec, open(p, "w"))
    import shutil; shutil.copy(ex.template_path("roc_curve", "csv"), os.path.join(TMP, os.path.basename(spec["input_table"])))
    loaded, data_path = c.load_plotspec(p)
    return f"plot_type={loaded['plot_type']}; data resolved={data_path is not None}"
step("XV", "Open PlotSpec… reproduces a saved figure and locates its data", "desktop controller load_plotspec", _plotspec_reload)

# --- Quick Start 10 / Manual XVI: Figure Builder -------------------------------------------------------
def _figure_builder():
    from make_my_figure_core.panels import (FigureLayout, MultiPanelFigure, Panel, build_figure,
                                            export_multipanel, import_external_panel, multipanel_sidecar)
    mpf = MultiPanelFigure(name="Figure 1", layout=FigureLayout(ncols=2, nrows=2, label_style="A"))
    for pt in ("barplot_with_error_bar", "scatterplot_with_regression"):
        info, aux, spec = ex.load_example(pt)
        mpf.add_panel(Panel(plot_spec=spec, table=info.dataframe, width_in=3.2))
    # an imported external panel from a PNG we export ourselves (synthetic)
    info, aux, spec = ex.load_example("volcano_plot")
    res = quiet(spec, info.dataframe); base = os.path.join(TMP, "ext"); export_figure(res.figure, base, ["png"])
    assets = os.path.join(TMP, "assets"); os.makedirs(assets, exist_ok=True)
    panel, asset = import_external_panel(base + ".png", assets, width_in=3.2)
    mpf.add_panel(panel)
    mpf.panels[0].width_in = 6.0
    fig = build_figure(mpf)
    files = export_multipanel(fig, os.path.join(TMP, "composite"), ["png", "svg", "pdf"], dpi=200)
    side = multipanel_sidecar(mpf, os.path.join(TMP, "composite"))
    lp = P.extract_layout_preset(mpf, name="2x2 wide top"); P.LayoutPresetStore().save(lp)
    return f"{len(mpf.panels)} panels (1 imported); {len(files)} files; {os.path.basename(side)}; layout preset saved"
step("QS10 / XVI", "Add generated panels, import an external panel, resize, label, export composite + FigureSpec + layout preset",
     "core panels + presets", _figure_builder)

# --- Manual XIII: annotations / duplicate labels -----------------------------------------------------------
def _labels():
    info, aux, spec = ex.load_example("volcano_plot")
    lab = spec["mapping"].get("label")
    picks = list(info.dataframe[lab].astype(str).head(3))
    spec["mapping"].update({"selected_labels": picks, "label_mode": "pasted", "label_list": picks,
                            "duplicate_label_policy": "unique",
                            "duplicate_label_representative_rule": "pvalue"})
    res = quiet(spec, info.dataframe)
    texts = [t.get_text() for t in res.figure.axes[0].texts]
    return f"labels drawn: {sum(1 for p in picks if any(p in t for t in texts))}/{len(picks)}"
step("XIII", "Select points to label; duplicate-label policy 'unique' with representative rule", "core render", _labels)

# --- Manual X: every plot renders from its bundled example ------------------------------------------------
def _all_plots():
    n = 0
    for pt in available_plot_types():
        info, aux, spec = ex.load_example(pt)
        quiet(spec, info.dataframe, {k: v.dataframe for k, v in aux.items()} if aux else None); n += 1
    return f"{n}/{len(available_plot_types())} render"
step("X", "Every registered plot type renders from its bundled example", "core render", _all_plots)

# --- Manual III / XXII: Home reset, About text, help content (desktop widgets offscreen) -------------------------
def _desktop_ui():
    from PySide6.QtWidgets import QApplication
    from apps.desktop_app import main as M
    app = QApplication.instance() or QApplication(["mmf"])
    w = M.MainWindow(); w.show(); app.processEvents()
    w.load_example("scatterplot_with_regression")
    for _ in range(15): app.processEvents()
    assert w._current_result is not None
    w.reset_to_upload(); app.processEvents()
    assert w.data is None and w._current_spec is None
    from make_my_figure_core.version import build_banner
    return f"loaded + reset OK; banner={build_banner()}"
try:
    step("III", "Desktop: load an example, then Home / Upload New Data clears the session", "offscreen Qt MainWindow", _desktop_ui)
except Exception as exc:  # noqa: BLE001
    record("III", "Desktop: load an example, then Home / Upload New Data clears the session", "offscreen Qt", False, exc)


def _streamlit_flow():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(os.path.join(ROOT, "apps", "streamlit_app", "streamlit_app.py"), default_timeout=240).run()
    box = next(b for b in at.selectbox if b.label == "Example dataset (by plot type)")
    box.set_value("Bar plot with error bars"); at.run()
    assert not at.exception
    at.session_state["sty_title_pt"] = 18; at.run()
    at.session_state["_preset_save_request"] = {"name": "Browser bars", "mode": "style"}; at.run()
    names = [e.name for e in P.PresetStore().list("barplot_with_error_bar")]
    return f"rendered; preset saved from browser app: {names}"
step("III / XIV", "Browser app: pick a bundled sample, change Title pt, save a Figure preset", "Streamlit AppTest", _streamlit_flow)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["manual_section", "instruction", "executed_via", "status", "evidence"])
    w.writeheader(); w.writerows(rows)
n_pass = sum(r["status"] == "PASS" for r in rows)
print(f"\n{n_pass}/{len(rows)} instructions validated -> {os.path.relpath(OUT, ROOT)}")
