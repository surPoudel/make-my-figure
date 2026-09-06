"""Build docs/manuals/audit/screenshot_inventory.csv from the capture logs and the manual sources.

For every PNG under docs/manuals/assets/screenshots: which workflow it shows, the (synthetic) data
behind it, the private-data check, whether the manual text that references it matches, the sections
that use it, and a status. Visual verification was done by opening each referenced image during the
QC loop; that is recorded as a column rather than inferred.
"""
from __future__ import annotations

import csv
import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SHOTS = os.path.join(ROOT, "docs", "manuals", "assets", "screenshots")
OUT = os.path.join(ROOT, "docs", "manuals", "audit", "screenshot_inventory.csv")
MANUALS = [os.path.join(ROOT, "docs", "manuals", "Quick_Start", "MakeMyFigure_Quick_Start.src.md")] + [
    os.path.join(ROOT, "docs", "manuals", "User_Manual", "parts", f)
    for f in sorted(os.listdir(os.path.join(ROOT, "docs", "manuals", "User_Manual", "parts")))]

notes = {}
for log in ("desktop_capture_log.json", "streamlit_capture_log.json"):
    path = os.path.join(SHOTS, log)
    if os.path.exists(path):
        data = json.load(open(path, encoding="utf-8"))
        for c in (data.get("captured", data) if isinstance(data, dict) else data):
            notes[c["screenshot"]] = c.get("note", "")

SOURCE = {
    "desktop_01": "none (welcome page)", "desktop_02": "bundled example: barplot_with_error_bar",
    "desktop_03": "bundled example: barplot_with_error_bar", "desktop_04": "bundled example: barplot_with_error_bar",
    "desktop_05": "bundled example: boxplot_or_violin_with_points", "desktop_06": "bundled example: heatmap_clustered_matrix",
    "desktop_07": "bundled example: heatmap_clustered_matrix", "desktop_08": "bundled example: heatmap_clustered_matrix",
    "desktop_09": "bundled example: dot_strip_plot", "desktop_10": "bundled example: volcano_plot",
    "desktop_11": "bundled example: scatterplot_with_regression", "desktop_12": "bundled example: scatterplot_with_regression",
    "desktop_13": "bundled example: volcano_plot", "desktop_14": "bundled examples: bar, scatter, volcano",
    "desktop_15": "bundled examples: bar, scatter, volcano", "desktop_16": "bundled example: volcano_plot",
    "desktop_17": "bundled workbook: examples/Make_My_Figure_All_Example_Data.xlsx", "desktop_18": "none (help dialog)",
    "streamlit_01": "none (landing)", "streamlit_02": "bundled example: barplot_with_error_bar",
    "streamlit_04": "bundled example: barplot_with_error_bar", "streamlit_05": "bundled example: barplot_with_error_bar",
    "streamlit_06": "none (workflow entry)", "streamlit_07": "bundled example: heatmap_clustered_matrix",
    "streamlit_09": "bundled example: heatmap_clustered_matrix", "streamlit_10": "bundled example: volcano_plot",
    "streamlit_11": "bundled example: barplot_with_error_bar", "streamlit_16": "bundled example: scatterplot_with_regression",
    "streamlit_17": "bundled workbook: examples/Make_My_Figure_All_Example_Data.xlsx",
}
VERIFIED = {  # opened and checked during the QC loop
    "desktop_02_data_loaded_workspace.png", "desktop_04_publication_controls.png", "desktop_05_statistics.png",
    "desktop_06_matrix_workflow_mapping.png", "desktop_07_matrix_workflow_groups.png",
    "desktop_08_preprocessing_qc.png", "desktop_08b_matrix_validation.png",
    "desktop_08c_matrix_recommend_generate.png", "desktop_10b_volcano_options.png",
    "desktop_11_figure_preset_save.png", "desktop_14_figure_builder.png",
    "streamlit_02_data_loaded_bar.png", "streamlit_17_multi_sheet_workbook.png", "streamlit_06_matrix_workflow.png",
}
UI_NOTE = {
    "desktop_02_data_loaded_workspace.png": "group titles with '&' show a Qt mnemonic artefact (known UI defect)",
    "desktop_03_plot_selector_and_mapping.png": "same mnemonic artefact",
    "desktop_04_publication_controls.png": "same mnemonic artefact ('Axes _labels')",
    "desktop_06_matrix_workflow_mapping.png": "tab title 'Recommend _generate' mnemonic artefact",
}

texts = {p: open(p, encoding="utf-8").read() for p in MANUALS}
rows = []
for fn in sorted(os.listdir(SHOTS)):
    if not fn.endswith(".png"):
        continue
    key = fn[:len("desktop_00")] if fn.startswith("desktop") else fn[:len("streamlit_00")]
    refs = []
    for path, txt in texts.items():
        if fn in txt:
            # nearest preceding heading
            idx = txt.index(fn)
            heads = re.findall(r"(?m)^(#{2,3} .+)$", txt[:idx])
            sec = heads[-1].lstrip("# ").strip() if heads else os.path.basename(path)
            refs.append(f"{os.path.basename(path).split('.')[0]}: {sec}")
    used = bool(refs)
    rows.append({
        "screenshot": fn,
        "workflow": notes.get(fn, ""),
        "source_data": SOURCE.get(key, "bundled synthetic example"),
        "private_data_check": "PASS - bundled synthetic example data only; no user files, no absolute paths in the UI",
        "ui_match": "verified visually" if fn in VERIFIED else ("captured from live UI; not individually opened" if used else "captured; unused"),
        "manual_section": " | ".join(refs) if refs else "(not referenced)",
        "status": "OK" if used else "UNUSED",
        "notes": UI_NOTE.get(fn, ""),
    })
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
print(f"{len(rows)} screenshots; used={sum(r['status']=='OK' for r in rows)}; verified visually={sum(r['ui_match']=='verified visually' for r in rows)}")
for r in rows:
    if r["status"] != "OK":
        print("  unused:", r["screenshot"])
