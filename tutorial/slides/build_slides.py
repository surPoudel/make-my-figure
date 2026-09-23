"""Build the Make My Figure tutorial / seminar deck from the author's PowerPoint template.

    python tutorial/slides/build_slides.py --template "<path to Suresh_Research_Progress_031826.pptx>"

Design rules (from the template): 12 x 9 in slides, Arial everywhere, titles 30 pt, body 18-20 pt,
near-black text (#111111 / #1F2937), one accent blue (#1D4E89) and the template's purple (#7030A0)
for emphasis, red only for a single warning. Real screenshots from tutorial/screenshots/ (no
mock-ups); every figure is a real render of the application or its output.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Emu, Inches, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
TUT = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(TUT, ".."))
SHOTS = os.path.join(TUT, "screenshots")
sys.path.insert(0, ROOT)

FONT = "Arial"
INK = RGBColor(0x11, 0x11, 0x11)
INK2 = RGBColor(0x1F, 0x29, 0x37)
BLUE = RGBColor(0x1D, 0x4E, 0x89)
PURPLE = RGBColor(0x70, 0x30, 0xA0)
GREY = RGBColor(0x66, 0x66, 0x66)
RED = RGBColor(0xC0, 0x00, 0x00)
LIGHT = RGBColor(0xF2, 0xF4, 0xF7)

W, H = Inches(12), Inches(9)
Y_OFF = Inches(0.3)          # content starts below the template header band
TITLE_LEFT = Inches(1.85)    # right of the template logo block


# ----------------------------------------------------------------------------- helpers
def _clear_slides(prs: Presentation) -> None:
    sldIdLst = prs.slides._sldIdLst
    for sldId in list(sldIdLst):
        prs.part.drop_rel(sldId.rId)
        sldIdLst.remove(sldId)


def _style_runs(tf, size, color=INK, bold=None):
    for p in tf.paragraphs:
        for r in p.runs:
            r.font.name = FONT
            r.font.size = Pt(size)
            r.font.color.rgb = color
            if bold is not None:
                r.font.bold = bold


def add_text(slide, left, top, width, height, text, size=18, color=INK, bold=False, align=PP_ALIGN.LEFT,
             anchor=MSO_ANCHOR.TOP, line_spacing=1.1, raw=False):
    box = slide.shapes.add_textbox(left, top if raw else top + Y_OFF, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    lines = text if isinstance(text, list) else [text]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        r = p.add_run()
        r.text = line
        r.font.name = FONT; r.font.size = Pt(size); r.font.color.rgb = color; r.font.bold = bold
    return box


def add_bullets(slide, left, top, width, height, items, size=18, color=INK, gap=6):
    """items: list of str or (str, level) or (str, level, bold)."""
    box = slide.shapes.add_textbox(left, top + Y_OFF, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.05)
    for i, it in enumerate(items):
        text, level, bold = (it, 0, False) if isinstance(it, str) else (it + (False,))[:3]
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.level = level
        p.space_after = Pt(gap)
        p.line_spacing = 1.08
        r = p.add_run()
        bullet = "• " if level == 0 else "– "
        r.text = bullet + text
        r.font.name = FONT; r.font.size = Pt(size - 2 * level); r.font.color.rgb = color if level == 0 else INK2
        r.font.bold = bold
    return box


def add_title(slide, text, size=28, color=INK2, top=Inches(0.42)):
    """Title in the template's own title area (right of the logo block, inside the header band)."""
    add_text(slide, TITLE_LEFT, top, Inches(9.7), Inches(1.1), text, size=size, color=color, bold=True,
             anchor=MSO_ANCHOR.MIDDLE, raw=True)


def add_picture_fit(slide, path, left, top, max_w, max_h, crop=None, border=True):
    """Place an image scaled to fit the box, optional crop box in pixels (l, t, r, b)."""
    img = Image.open(path)
    if crop:
        img = img.crop(crop)
        tmp = os.path.join(HERE, "_crops")
        os.makedirs(tmp, exist_ok=True)
        path = os.path.join(tmp, os.path.basename(os.path.dirname(path)) + "_" + os.path.basename(path).replace(".png", f"_{crop[0]}_{crop[1]}.png"))
        img.save(path)
    w, h = img.size
    scale = min(max_w / w, max_h / h)
    pw, ph = int(w * scale), int(h * scale)
    l = left + (max_w - pw) // 2
    t = top + (max_h - ph) // 2
    pic = slide.shapes.add_picture(path, l, t + Y_OFF, pw, ph)
    if border:
        pic.line.color.rgb = RGBColor(0xC8, 0xC8, 0xC8); pic.line.width = Pt(0.75)
    return pic


def add_caption(slide, left, top, width, text, size=13):
    add_text(slide, left, top, width, Inches(0.5), text, size=size, color=GREY)


def add_footer(slide, n, text="Make My Figure - desktop tutorial"):
    add_text(slide, Inches(0.5), Inches(8.55), Inches(8), Inches(0.3), f"{text}   |   {n}", size=10, color=GREY, raw=True)


def shot(tid, name):
    p = os.path.join(SHOTS, tid, name)
    if not os.path.exists(p):
        raise SystemExit(f"missing screenshot {p} - run the tutorial action scripts first")
    return p


# ----------------------------------------------------------------------------- content
def build(template: str, out: str) -> None:
    prs = Presentation(template)
    _clear_slides(prs)
    blank = prs.slide_layouts[2] if len(prs.slide_layouts) > 2 else prs.slide_layouts[-1]
    # Use the plain layout without gradient for content: find "Title and Content" and remove its placeholders per slide
    content_layout = next((l for l in prs.slide_layouts if l.name == "Title and Content"), prs.slide_layouts[1])
    section_layout = next((l for l in prs.slide_layouts if l.name == "Section Header"), prs.slide_layouts[0])

    manifest = json.load(open(os.path.join(TUT, "tutorial_manifest.json"), encoding="utf-8"))
    version = manifest["software_version"]; n_plots = manifest["plot_registry_count"]
    validation = manifest.get("action_scripts_validated", {})
    n = 0

    def new_slide(layout=content_layout):
        nonlocal n
        s = prs.slides.add_slide(layout)
        for ph in list(s.placeholders):  # we lay out everything ourselves
            ph._element.getparent().remove(ph._element)
        n += 1
        return s

    # 1 title -------------------------------------------------------------------------------
    s = new_slide(section_layout)
    WHITE = RGBColor(0xFF, 0xFF, 0xFF)
    add_text(s, Inches(3.0), Inches(3.15), Inches(8.6), Inches(1.1), "Make My Figure", size=40, color=WHITE, bold=True, raw=True)
    add_text(s, Inches(3.0), Inches(4.25), Inches(8.6), Inches(1.5),
             "From an ordinary data table to a publication figure, with the researcher in control",
             size=22, color=WHITE, raw=True)
    add_text(s, Inches(3.0), Inches(6.35), Inches(8.6), Inches(1.6),
             ["Desktop tutorial and demonstration", f"Version {version}  -  {n_plots} plot types", "Suresh Poudel"],
             size=18, color=INK2, raw=True)

    # 2 the problem ----------------------------------------------------------------------------
    s = new_slide(); add_title(s, "The problem this solves")
    add_bullets(s, Inches(0.6), Inches(1.7), Inches(6.2), Inches(6), [
        "Figures are made from tables whose columns were never named for a plotting program",
        "Every figure type needs its own script, style and statistics call",
        "Six months later nobody can say which file, which cut-off and which test produced the panel",
        "Journals ask for editable vector files, exact P values and a methods sentence",
        ("What a scientist actually wants", 0, True),
        ("open the table, say what each column means, pick the figure, add the test, keep the record", 1),
    ], size=19)
    add_picture_fit(s, shot("mapping_ambiguous", "01b_data_preview.png"), Inches(7.0), Inches(1.9), Inches(4.6), Inches(1.6))
    add_caption(s, Inches(7.0), Inches(3.55), Inches(4.6), "A real table: col_A, measurement_2, condition_code, thing ...")
    add_picture_fit(s, shot("mapping_ambiguous", "06_final.png"), Inches(7.0), Inches(4.2), Inches(4.6), Inches(3.4))
    add_caption(s, Inches(7.0), Inches(7.65), Inches(4.6), "... and the figure it became, without renaming a column")
    add_footer(s, n)

    # 3 what it is --------------------------------------------------------------------------------
    s = new_slide(); add_title(s, "What Make My Figure is")
    add_bullets(s, Inches(0.6), Inches(1.7), Inches(5.6), Inches(6.4), [
        f"A desktop application (and a browser version) that draws {n_plots} publication-style plot types from CSV, TSV and Excel tables",
        "Runs entirely on your computer: no upload, no account",
        "One Publication style; fonts, colours, layout, legend under your control",
        "Statistics on the figure: 19 tests, corrections, brackets, effect sizes, a methods sentence",
        "Reproducibility built in: PlotSpec, StatsSpec, Figure Package (.mmfpackage) with frozen data and checksums",
        "Multi-panel Figure Builder with panel letters and common fonts",
        "Open source, Python, Matplotlib and Qt; desktop installers for Windows, macOS and Linux",
    ], size=18)
    add_picture_fit(s, shot("getting_started", "04_workspace.png"), Inches(6.4), Inches(1.8), Inches(5.3), Inches(3.2))
    add_caption(s, Inches(6.4), Inches(5.05), Inches(5.3), "The workspace: controls left, data and live figure right")
    add_picture_fit(s, shot("getting_started", "01_start_screen.png"), Inches(6.4), Inches(5.5), Inches(5.3), Inches(2.4),
                    crop=(300, 250, 1380, 650))
    add_caption(s, Inches(6.4), Inches(7.9), Inches(5.3), "Start screen: open a file, a package, an example")
    add_footer(s, n)

    # 4 philosophy --------------------------------------------------------------------------------
    s = new_slide(); add_title(s, "Design principle: the application suggests, the researcher decides")
    left = Inches(0.6)
    for i, (head, body) in enumerate([
        ("It proposes", "Detects column types, recommends figures with a match score, proposes a column for every role, suggests a test from the design."),
        ("You decide", "Every role is a drop-down of your own columns. Change any of them; the figure follows. Choose the test; the panel runs and documents it."),
        ("It records", "PlotSpec for the specification, StatsSpec for the test, Figure Package for specification plus frozen data. Nothing hidden, nothing recomputed behind your back."),
    ]):
        x = left + i * Inches(3.75)
        box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, Inches(1.9) + Y_OFF, Inches(3.5), Inches(4.4))
        box.fill.solid(); box.fill.fore_color.rgb = LIGHT; box.line.color.rgb = RGBColor(0xD0, 0xD5, 0xDD)
        box.adjustments[0] = 0.06
        add_text(s, x + Inches(0.2), Inches(2.1), Inches(3.1), Inches(0.6), head, size=22, color=BLUE, bold=True)
        add_text(s, x + Inches(0.2), Inches(2.8), Inches(3.1), Inches(3.3), body, size=17, color=INK)
    add_text(s, Inches(0.6), Inches(6.7), Inches(11), Inches(1.0),
             "“The data do not belong to one plot.”  The same table can become a box plot, a scatter with regression and a bar plot in a minute - the user decides which question to visualise.",
             size=18, color=INK2)
    add_footer(s, n)

    # 5 mapping demo: proposal ----------------------------------------------------------------------
    s = new_slide(); add_title(s, "Demo 1 - a table with unhelpful column names")
    add_picture_fit(s, shot("mapping_ambiguous", "01_open_data.png"), Inches(0.5), Inches(1.7), Inches(7.2), Inches(4.3))
    add_bullets(s, Inches(7.9), Inches(1.8), Inches(3.8), Inches(6), [
        "Open ambiguous_columns.csv (27 rows, 6 columns)",
        "Detected types listed under the table; id_value is typed as text because it looks like an identifier",
        "Recommended figures: box / violin (72 %), ridge (62 %), bar (60 %)",
        "Nothing is drawn until a plot type is chosen",
    ], size=17)
    add_picture_fit(s, shot("mapping_ambiguous", "02_mapping_proposed.png"), Inches(0.5), Inches(6.2), Inches(5.0), Inches(1.0))
    add_caption(s, Inches(0.5), Inches(7.25), Inches(7), "The proposal for a box plot: x = condition_code, y = measurement_2")
    add_footer(s, n)

    # 6 mapping demo: correction and second plot ------------------------------------------------------
    s = new_slide(); add_title(s, "Demo 1 - correct the mapping, then ask a different question")
    add_picture_fit(s, shot("mapping_ambiguous", "03b_plot_after_correction.png"), Inches(0.5), Inches(1.7), Inches(5.5), Inches(3.6))
    add_caption(s, Inches(0.5), Inches(5.3), Inches(5.5), "y changed to score_final - the figure follows, nothing else changes")
    add_picture_fit(s, shot("mapping_ambiguous", "04_scatter_mapping.png"), Inches(6.2), Inches(1.7), Inches(5.5), Inches(1.2))
    add_picture_fit(s, shot("mapping_ambiguous", "06_final.png"), Inches(6.2), Inches(3.0), Inches(5.5), Inches(2.3))
    add_caption(s, Inches(6.2), Inches(5.3), Inches(5.5), "Same file as a scatter: x = measurement_2, y = score_final, color = condition_code")
    add_bullets(s, Inches(0.6), Inches(5.9), Inches(11), Inches(2.2), [
        "The row label is the role; the drop-down is your column - your headers, unchanged",
        "Per-group regression lines with slope, R² and P appear because a colour role was set",
        "Three figures from one table in the tutorial: box, scatter, bar with SEM",
    ], size=17)
    add_footer(s, n)

    # 7 volcano manual mapping ----------------------------------------------------------------------
    s = new_slide(); add_title(s, "Demo 2 - differential results with names the detector does not know")
    add_picture_fit(s, shot("volcano_manual_mapping", "04b_window_before.png"), Inches(0.5), Inches(1.7), Inches(5.5), Inches(3.3),
                    crop=(0, 0, 1680, 1000))
    add_caption(s, Inches(0.5), Inches(5.0), Inches(5.5), "effect_measure, p_raw, name: every role (none), Messages names the missing roles")
    add_picture_fit(s, shot("volcano_manual_mapping", "05b_plot_after_mapping.png"), Inches(6.2), Inches(1.7), Inches(5.5), Inches(3.3))
    add_caption(s, Inches(6.2), Inches(5.0), Inches(5.5), "After assigning x, p, label and id_col by hand: the volcano renders")
    add_bullets(s, Inches(0.6), Inches(5.6), Inches(11), Inches(2.4), [
        "With DESeq2 names (log2FoldChange, pvalue, gene_symbol) the same roles fill themselves",
        "P values are read from the table - the application never recomputes differential statistics",
        "Cut-offs, colours by class and the number of labelled genes are options; the header counts Up / Down / NS",
    ], size=17)
    add_footer(s, n)

    # 8 statistics --------------------------------------------------------------------------------
    s = new_slide(); add_title(s, "Statistics on the figure - chosen by you, documented by the application")
    add_picture_fit(s, shot("group_comparison_box", "05b_plot_with_brackets.png"), Inches(0.5), Inches(1.7), Inches(5.6), Inches(3.9))
    add_picture_fit(s, shot("group_comparison_box", "05_statistics.png"), Inches(6.3), Inches(1.7), Inches(5.4), Inches(5.9))
    add_bullets(s, Inches(0.6), Inches(5.8), Inches(5.6), Inches(2.4), [
        "Welch's t-test, all pairs, Holm-Bonferroni, exact P on brackets",
        "Table: test, p, adjusted p, Hedges' g, n per comparison",
        "Method sentence with library versions, ready for the manuscript",
        "Suggested test printed from the design; the choice is the researcher's",
    ], size=16)
    add_footer(s, n)

    # 9 presets ---------------------------------------------------------------------------------------
    s = new_slide(); add_title(s, "Figure presets - the style travels, the data stay")
    add_picture_fit(s, shot("figure_preset", "01_refined_plot.png"), Inches(0.5), Inches(1.7), Inches(5.5), Inches(3.3))
    add_caption(s, Inches(0.5), Inches(5.0), Inches(5.5), "Dataset 1, refined: violin, larger points, single-column width, y label - saved as a style preset")
    add_picture_fit(s, shot("figure_preset", "05_second_dataset_preset.png"), Inches(6.2), Inches(1.7), Inches(5.5), Inches(3.3))
    add_caption(s, Inches(6.2), Inches(5.0), Inches(5.5), "Dataset 2 after Apply: “Applied preset: 9 setting(s)” - groups and values are its own")
    add_bullets(s, Inches(0.6), Inches(5.6), Inches(11), Inches(2.4), [
        "Figure style only: fonts, colours, layout, legend, export - portable to any table of the plot type",
        "Full figure configuration: also roles, thresholds and statistics settings - asks for remapping on new data",
        "Neither kind contains data: checked in the validated run (no value, group name or identifier in the file)",
    ], size=17)
    add_footer(s, n)

    # 10 reproducibility ----------------------------------------------------------------------------
    s = new_slide(); add_title(s, "Reproducibility - PlotSpec versus Figure Package")
    add_picture_fit(s, shot("figure_package", "03_package_confirmation.png"), Inches(0.5), Inches(1.7), Inches(3.6), Inches(3.0))
    add_caption(s, Inches(0.5), Inches(4.7), Inches(3.6), "What the package will contain - and a privacy reminder")
    add_picture_fit(s, shot("figure_package", "05_reopened_from_package.png"), Inches(4.3), Inches(1.7), Inches(7.4), Inches(4.4))
    add_caption(s, Inches(4.3), Inches(6.1), Inches(7.4), "Reopened from the moved package: integrity verified; data, mapping and brackets restored")
    add_bullets(s, Inches(0.6), Inches(6.65), Inches(11), Inches(1.7), [
        "PlotSpec: specification with a digest of the source table; needs the data file to redraw",
        "Figure Package: ZIP with manifest and SHA-256 per member, frozen table, original file, PlotSpec, StatsSpec, previews, environment",
    ], size=17)
    add_footer(s, n)

    # 11 builder -----------------------------------------------------------------------------------------
    s = new_slide(); add_title(s, "Figure Builder - panels with their own data")
    add_picture_fit(s, shot("figure_builder", "03_figure_builder.png"), Inches(0.5), Inches(1.7), Inches(11.2), Inches(5.0))
    add_bullets(s, Inches(0.6), Inches(6.9), Inches(11), Inches(1.6), [
        "Save any plot as a panel; import external panels; order sets the letters; width in mm; fonts applied to all panels",
        "Save figure (PNG, PDF, SVG) and Save Figure Package (every panel with its table) - a draft legend is generated to be rewritten",
    ], size=17)
    add_footer(s, n)

    # 12 tutorial system ------------------------------------------------------------------------------
    s = new_slide(); add_title(s, "The tutorial system - built against the real application")
    steps = ["tutorial action script", "driver operates the real MainWindow", "screenshots (offscreen) or video (on screen)", "validation record PASS / FAIL"]
    x = Inches(0.6)
    for i, t in enumerate(steps):
        box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, Inches(1.9) + Y_OFF, Inches(2.5), Inches(1.1))
        box.fill.solid(); box.fill.fore_color.rgb = LIGHT if i % 2 == 0 else RGBColor(0xE3, 0xEB, 0xF5); box.line.color.rgb = RGBColor(0xC8, 0xD0, 0xDC)
        add_text(s, x + Inches(0.1), Inches(2.0), Inches(2.3), Inches(0.9), t, size=15, color=INK2, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        if i < len(steps) - 1:
            add_text(s, x + Inches(2.5), Inches(2.15), Inches(0.4), Inches(0.6), "→", size=24, color=BLUE, align=PP_ALIGN.CENTER)
        x += Inches(2.85)
    add_bullets(s, Inches(0.6), Inches(3.4), Inches(11), Inches(4.8), [
        "No mock-ups: every screenshot is a grab of the production PySide6 widgets; every step is performed through the widgets a user would click",
        "Same script, two modes: offscreen for deterministic screenshots (1680 x 1000, empty settings and presets), on screen for video recording - recording is separate (ffmpeg, OBS, OS recorder)",
        "Inventory read from the live plot registry: 39 plot types, tutorial and video status per plot; a new plot type appears as MISSING",
        "Facts recorded during the run (proposed roles, option names, messages) are what the written tutorial quotes - drift is caught by re-running",
        "Sixteen simulated datasets with fixed seeds support all plots; one table deliberately has bad column names, one supports nine plots",
        "Gallery, manifest, HTML copy and validation report regenerated by script; videos link through placeholders until a platform is chosen",
    ], size=16)
    add_footer(s, n)

    # 13 validation table ----------------------------------------------------------------------------------
    s = new_slide(); add_title(s, "Pilot validation - every instruction executed against the application")
    rows = [("Tutorial", "Status", "Checks")]
    for p in sorted(os.listdir(os.path.join(TUT, "audit", "validation"))):
        r = json.load(open(os.path.join(TUT, "audit", "validation", p), encoding="utf-8"))
        rows.append((r["title"], r["status"], f"{len(r['checks'])} checks, {len(r['captures'])} captures"))
    tbl = s.shapes.add_table(len(rows), 3, Inches(0.6), Inches(1.8) + Y_OFF, Inches(10.8), Inches(0.42) * len(rows)).table
    tbl.columns[0].width = Inches(6.2); tbl.columns[1].width = Inches(1.4); tbl.columns[2].width = Inches(3.2)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = tbl.cell(i, j)
            cell.text = val
            _style_runs(cell.text_frame, 14 if i else 15, INK if i else RGBColor(0xFF, 0xFF, 0xFF), bold=(i == 0))
            cell.fill.solid(); cell.fill.fore_color.rgb = BLUE if i == 0 else (RGBColor(0xFF, 0xFF, 0xFF) if i % 2 else LIGHT)
            if j == 1 and i:
                _style_runs(cell.text_frame, 14, RGBColor(0x1B, 0x7A, 0x3E) if val == "PASS" else RED, bold=True)
    add_text(s, Inches(0.6), Inches(1.8) + Inches(0.42) * len(rows) + Inches(0.2), Inches(10.8), Inches(1.2),
             "Checks are the tutorial's own steps: dataset exists, plot type exists, each column role exists, the figure rendered, options exist, statistics ran, every export was written. Report: tutorial/audit/validation_report.md",
             size=15, color=GREY)
    add_footer(s, n)

    # 14 gallery montage ------------------------------------------------------------------------------
    s = new_slide(); add_title(s, f"{n_plots} plot types, one workflow")
    gal = json.load(open(os.path.join(TUT, "audit", "gallery_index.json"), encoding="utf-8"))
    thumbs = [g for g in gal if g["thumb"]]
    cols, rows_n = 8, 5
    cw, ch = Inches(1.38), Inches(1.28)
    for i, g in enumerate(thumbs[:cols * rows_n]):
        r_, c_ = divmod(i, cols)
        add_picture_fit(s, os.path.join(TUT, g["thumb"]), Inches(0.45) + c_ * cw, Inches(1.65) + r_ * ch, cw - Inches(0.08), ch - Inches(0.08), border=False)
    add_caption(s, Inches(0.5), Inches(8.1), Inches(11), "Every thumbnail is a real render of the bundled synthetic example with the application's own renderer (tutorial/PLOT_GALLERY.md)")
    add_footer(s, n)

    # 15 roadmap / next -----------------------------------------------------------------------------------
    s = new_slide(); add_title(s, "Where this goes next")
    add_bullets(s, Inches(0.6), Inches(1.7), Inches(11), Inches(6.5), [
        ("Pilot delivered for review", 0, True),
        ("nine tutorials, getting started, mapping master tutorial, gallery, video scripts, automation, validation", 1),
        ("After review", 0, True),
        ("tutorials for the remaining plot types, generated with the same template and validated the same way", 1),
        ("matrix workflow tutorial and video: expression matrix, metadata, preprocessing you confirm, PCA, heatmap, differential summary, volcano", 1),
        ("master video (8-12 min) and 1-4 min plot videos recorded from the on-screen runs", 1),
        ("Maintenance loop", 0, True),
        ("new plot type appears as MISSING in the inventory; dataset, action script, tutorial, video script, gallery entry, validation", 1),
        ("Not yet: merged, tagged, released or published - author review first", 0, True),
    ], size=18)
    add_footer(s, n)

    # 16 summary ---------------------------------------------------------------------------------------
    s = new_slide(); add_title(s, "Summary")
    add_bullets(s, Inches(0.6), Inches(1.7), Inches(11), Inches(5), [
        "Open any table; the application detects, recommends and proposes - and you assign every role yourself",
        "One table, many figures; one workflow for all plot types",
        "Statistics run on the figure, with the table and the methods sentence a reviewer expects",
        "Presets carry the look; PlotSpec carries the recipe; a Figure Package carries recipe and ingredients, verified",
        "The tutorial is generated from the real application and checked by running it, so it stays honest as the software changes",
    ], size=19)
    add_text(s, Inches(0.6), Inches(6.6), Inches(11), Inches(1.2),
             "github.com/surPoudel/make-my-figure  -  tutorial/ in the repository (pilot branch, not yet published)", size=16, color=GREY)
    add_footer(s, n)

    prs.save(out)
    print(f"saved {out} ({n} slides)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--out", default=os.path.join(HERE, "MakeMyFigure_Tutorial_Seminar.pptx"))
    a = ap.parse_args()
    build(a.template, a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
