"""Capture browser-app (Streamlit) screenshots for the manuals with headless Chromium.

Drives the running app at http://localhost:8501 through its main states using only the bundled
example datasets, and saves full-page PNGs under docs/manuals/assets/screenshots/.
"""
from __future__ import annotations

import json
import os
import sys
import time

from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "docs", "manuals", "assets", "screenshots")
URL = os.environ.get("MMF_STREAMLIT_URL", "http://localhost:8501")
captured = []


def settle(page, ms=2500):
    page.wait_for_timeout(ms)
    # wait for Streamlit's "running" indicator to disappear
    for _ in range(40):
        if page.locator('[data-testid="stStatusWidget"]').count() == 0:
            break
        page.wait_for_timeout(500)


def shot(page, name, note="", full=True):
    path = os.path.join(OUT, name)
    page.screenshot(path=path, full_page=full)
    captured.append({"screenshot": name, "note": note})
    print("  ok ", name, note)


def select_option(page, label, option):
    """Open the selectbox with aria-label/label text `label` and choose `option`."""
    box = page.get_by_label(label, exact=False).first
    box.click()
    page.get_by_role("option", name=option, exact=True).first.click()
    settle(page)


def expand(page, title):
    exp = page.get_by_text(title, exact=False).first
    try:
        exp.scroll_into_view_if_needed()
        exp.click()
        page.wait_for_timeout(600)
    except Exception as exc:  # noqa: BLE001
        print("  could not expand", title, exc)


with sync_playwright() as p:
    browser = p.chromium.launch()
    # Streamlit scrolls inside its own containers, so a full-page screenshot only shows the
    # viewport; a tall viewport makes the whole page (sidebar and main column) visible at once.
    page = browser.new_page(viewport={"width": 1500, "height": 2600}, device_scale_factor=1)
    page.goto(URL, wait_until="networkidle")
    settle(page, 4000)
    shot(page, "streamlit_01_home.png", "landing state: data source, bundled sample", full=False)

    # a bar plot from the bundled examples
    select_option(page, "Example dataset (by plot type)", "Bar plot with error bars")
    settle(page, 3000)
    shot(page, "streamlit_02_data_loaded_bar.png", "bar plot example rendered with sidebar controls")

    # publication style expanders
    for title in ("① Figure", "② Typography", "③ Axes & labels", "④ Legend"):
        expand(page, title)
    settle(page, 1500)
    shot(page, "streamlit_04_publication_controls.png", "Publication style expanders opened")

    # statistics
    expand(page, "Statistical tests & annotations")
    settle(page, 1200)
    shot(page, "streamlit_05_statistics.png", "Statistical tests & annotations expander")

    # figure preset expander
    expand(page, "Figure preset")
    settle(page, 1200)
    shot(page, "streamlit_11_figure_preset.png", "Figure preset expander: apply / save / import / export")

    # volcano with label controls
    page.goto(URL, wait_until="networkidle"); settle(page, 3000)
    select_option(page, "Example dataset (by plot type)", "Volcano plot")
    settle(page, 3000)
    expand(page, "Label points (annotate)")
    settle(page, 1200)
    shot(page, "streamlit_10_volcano_editor.png", "volcano example with the Label points expander")

    # define groups expander + recommended figures
    page.goto(URL, wait_until="networkidle"); settle(page, 3000)
    select_option(page, "Example dataset (by plot type)", "Clustered heatmap")
    settle(page, 3000)
    expand(page, "🔮 Recommended figures")
    settle(page, 1200)
    shot(page, "streamlit_09_recommended_figures.png", "Recommended figures expander for a matrix")
    expand(page, "🗂 Define groups (no metadata file needed)")
    settle(page, 1200)
    shot(page, "streamlit_07_define_groups.png", "Define groups expander (wide matrix assignment)")

    # export area (bottom of page)
    page.goto(URL, wait_until="networkidle"); settle(page, 3000)
    select_option(page, "Example dataset (by plot type)", "Scatter plot")
    settle(page, 3000)
    shot(page, "streamlit_16_export.png", "scatter example; Export section with PNG/SVG/PDF downloads at the bottom")

    # multi-sheet workbook: Upload file mode needs a file; use the bundled example workbook
    page.goto(URL, wait_until="networkidle"); settle(page, 3000)
    page.get_by_text("Upload file", exact=True).first.click(); settle(page, 1500)
    wb = os.path.join(ROOT, "examples", "Make_My_Figure_All_Example_Data.xlsx")
    page.locator('input[type="file"]').first.set_input_files(wb)
    settle(page, 5000)
    shot(page, "streamlit_17_multi_sheet_workbook.png", "workbook browser: worksheet chooser + classification")

    # matrix workflow (guided) radio if present
    page.goto(URL, wait_until="networkidle"); settle(page, 3000)
    try:
        select_option(page, "Example dataset (by plot type)", "Clustered heatmap")
        settle(page, 3000)
        page.get_by_text("Matrix workflow (guided)", exact=True).first.click(); settle(page, 4000)
        shot(page, "streamlit_06_matrix_workflow.png", "guided Matrix workflow with the heatmap example: step ① mapping")
    except Exception as exc:  # noqa: BLE001
        print("  matrix workflow entry not captured:", exc)

    browser.close()

with open(os.path.join(OUT, "streamlit_capture_log.json"), "w", encoding="utf-8") as fh:
    json.dump(captured, fh, indent=2)
print(f"captured {len(captured)} streamlit screenshots")
