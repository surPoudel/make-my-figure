"""Build MakeMyFigure_Seminar_Revised.pptx: a seminar plus live-demo deck restructured from the
22-slide tutorial deck (build_slides.py), keeping its assets and visual language and adding the
six manuscript figures (read from the submission package, unmodified PNGs at 300/600 dpi).

    python tutorial/slides/build_seminar.py --template "<Suresh_Research_Progress_031826.pptx>" \
        --figures "<Manuscript_reorganization_091026/02_Main_Figures>"

Main story (16 slides) then backup slides. Nothing from the original deck is deleted; slides not
in the main story move to the backup section. See tutorial/slides/SEMINAR_REVISION_NOTES.txt.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import sys

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_slides as B  # noqa: E402  (helpers, colours, paths)

TUT, ROOT, SHOTS, SHOW, OUTS = B.TUT, B.ROOT, B.SHOTS, B.SHOW, B.OUTS
INK, INK2, BLUE, GREY, GREEN, RED, LIGHT, WHITE = B.INK, B.INK2, B.BLUE, B.GREY, B.GREEN, B.RED, B.LIGHT, B.WHITE
Y_OFF, CONTENT_TOP = B.Y_OFF, B.CONTENT_TOP
add_text, add_bullets, add_title, add_message, add_picture_fit, add_caption, shot, show = (
    B.add_text, B.add_bullets, B.add_title, B.add_message, B.add_picture_fit, B.add_caption, B.shot, B.show)
L = Inches(0.5)
REPO_URL = "https://github.com/surPoudel/make-my-figure"

# Manuscript figure roles, taken from the figure legends of the submitted manuscript
# (Poudel et al. 2026, Nature Methods submission package), not from file names.
FIG_ROLE = {
    1: "Fragmented tools versus the connected six-stage workflow; each stage writes a specification",
    2: "Guided matrix workflow on a deposited count matrix: roles, groups, profiling, confirmed preprocessing, tests, plots",
    3: "Specifications support reconstruction (PlotSpec), reuse (Figure Preset) and multi-panel assembly (FigureSpec)",
    4: "Consistency across input formats, Windows / Linux, export formats, input sizes and repeated renders",
    5: "Six published panels recreated from their deposited source data and assembled with the Figure Builder",
    6: "Statistics agree with independent R calculations; published P values reproduced; imported DESeq2 results plotted",
}


def add_footer(slide, n, backup=False):
    txt = ("Backup   |   " if backup else "") + f"Make My Figure - seminar   |   {n}"
    add_text(slide, Inches(0.5), Inches(8.55), Inches(8), Inches(0.3), txt, size=10, color=GREY, raw=True)


def fig_path(figdir, n):
    p = os.path.join(figdir, f"Figure{n}.png")
    if not os.path.exists(p):
        raise SystemExit(f"manuscript figure missing: {p}")
    return p


def box(slide, x, y, w, h, fill=LIGHT, line=RGBColor(0xD0, 0xD5, 0xDD), radius=0.06):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y + Y_OFF, w, h)
    sh.fill.solid(); sh.fill.fore_color.rgb = fill; sh.line.color.rgb = line
    sh.adjustments[0] = radius
    return sh


# Panel-row boundaries (fraction of figure height) read from the figure images: each cut lies in the
# white gutter between two rows of panels, so every panel keeps its letter, axes, legend and labels.
FIG_ROWS = {
    1: {"A": (0.0, 0.322), "B": (0.322, 1.0)},
    2: {"A-F": (0.0, 0.608), "G": (0.608, 1.0)},
    3: {"A-B": (0.0, 0.627), "C": (0.627, 1.0)},
    4: {"A-B": (0.0, 0.292), "C-D": (0.292, 0.680), "E-F": (0.680, 1.0)},
    5: {"A-C": (0.0, 0.468), "D-F": (0.468, 1.0)},
    6: {"A-B": (0.0, 0.330), "C-D": (0.330, 0.658), "E-F": (0.658, 1.0)},
}


def fig_rows(figdir, n, key):
    """Return a PNG holding only the named panel row(s) of manuscript Figure n (unmodified pixels)."""
    src = fig_path(figdir, n)
    y0f, y1f = FIG_ROWS[n][key]
    img = Image.open(src)
    w, h = img.size
    crop = img.crop((0, int(y0f * h), w, int(y1f * h)))
    tmp = os.path.join(HERE, "_crops"); os.makedirs(tmp, exist_ok=True)
    out = os.path.join(tmp, f"Figure{n}_rows_{key.replace('-', '')}.png")
    crop.save(out, dpi=img.info.get("dpi", (600, 600)))
    return out


def qr_png(url):
    import segno
    tmp = os.path.join(HERE, "_crops"); os.makedirs(tmp, exist_ok=True)
    out = os.path.join(tmp, "repo_qr.png")
    segno.make(url, error="m").save(out, scale=10, border=2, dark="#1F2937")
    return out


def validation_totals():
    vals = [json.load(open(p, encoding="utf-8")) for p in glob.glob(os.path.join(TUT, "audit", "validation", "*.json"))]
    return {"workflows": len(vals), "checks": sum(len(v["checks"]) for v in vals),
            "captures": sum(len(v["captures"]) for v in vals), "all_pass": all(v["status"] == "PASS" for v in vals),
            "rows": [(v["title"], v["status"], f"{len(v['checks'])} checks, {len(v['captures'])} captures") for v in sorted(vals, key=lambda v: v["tutorial_id"])]}


def build(template, figdir, out):
    prs = Presentation(template)
    B._clear_slides(prs)
    B.placements.clear()
    content_layout = next((l for l in prs.slide_layouts if l.name == "Title and Content"), prs.slide_layouts[1])
    section_layout = next((l for l in prs.slide_layouts if l.name == "Section Header"), prs.slide_layouts[0])
    manifest = json.load(open(os.path.join(TUT, "tutorial_manifest.json"), encoding="utf-8"))
    version, n_plots = manifest["software_version"], manifest["plot_registry_count"]
    totals = validation_totals()
    n = 0
    mapping = []   # (revised slide, section, title, sources)

    def new_slide(title=None, layout=None, backup=False, sources=""):
        nonlocal n
        s = prs.slides.add_slide(layout or content_layout)
        for ph in list(s.placeholders):
            ph._element.getparent().remove(ph._element)
        n += 1
        if title:
            add_title(s, title)
        mapping.append((n, "backup" if backup else "main", title or "(title slide)", sources))
        return s

    # ================================================================== MAIN
    # 1 title
    s = new_slide(layout=section_layout, sources="new wording; template title band")
    add_text(s, Inches(3.0), Inches(2.9), Inches(8.6), Inches(1.1), "Make My Figure", size=44, color=WHITE, bold=True, raw=True)
    add_text(s, Inches(3.0), Inches(4.0), Inches(8.6), Inches(0.9), "One dataset, many controlled views", size=28, color=WHITE, bold=True, raw=True)
    add_text(s, Inches(3.0), Inches(4.85), Inches(8.6), Inches(0.8), "From research table to reproducible publication figure", size=20, color=WHITE, raw=True)
    add_text(s, Inches(3.0), Inches(6.4), Inches(8.6), Inches(1.4), ["Suresh Poudel", f"Seminar and live demonstration  -  version {version}, {n_plots} plot types"],
             size=18, color=INK2, raw=True)

    # 2 the problem (kept from tutorial deck slide 2)
    s = new_slide("A real table rarely arrives ready to plot", sources="tutorial deck 2; ambiguous_columns.csv excerpt; showcase J4")
    tbl = B.table_excerpt_image(os.path.join(TUT, "datasets", "ambiguous_columns.csv"), rows=6)
    add_picture_fit(s, tbl, L, CONTENT_TOP, Inches(5.2), Inches(5.0), border=False, kind="table")
    add_text(s, Inches(5.75), Inches(3.9), Inches(0.6), Inches(0.8), "→", size=40, color=BLUE, align=PP_ALIGN.CENTER)
    add_picture_fit(s, show("1_group_comparison", "J4_black_edged_filled_pres.png"), Inches(6.4), CONTENT_TOP, Inches(5.1), Inches(5.0), kind="plot")
    add_bullets(s, Inches(0.6), Inches(7.05), Inches(10.8), Inches(1.3), [
        "Headers like col_A and measurement_2 carry no meaning for software",
        "The researcher assigns the meaning explicitly; the table is never asked to look like a plotting specification",
    ], size=17, gap=4)
    add_footer(s, n)

    # 3 design philosophy
    s = new_slide("The application suggests. The researcher decides.", sources="tutorial deck 4, restructured into three columns")
    cols = [
        ("MMF proposes", ["column types", "possible figures", "column roles", "statistical tests"], BLUE),
        ("Researcher controls", ["role assignments", "plot choice", "observations", "statistical test", "presentation"], RGBColor(0x8A, 0x1C, 0x1C)),
        ("MMF records", ["PlotSpec", "StatsSpec", "Figure Package"], GREEN),
    ]
    for i, (head, items, col) in enumerate(cols):
        x = Inches(0.6) + i * Inches(3.75)
        box(s, x, Inches(1.85), Inches(3.5), Inches(4.2))
        add_text(s, x + Inches(0.25), Inches(2.0), Inches(3.1), Inches(0.6), head, size=20, color=col, bold=True)
        add_bullets(s, x + Inches(0.25), Inches(2.75), Inches(3.0), Inches(3.3), items, size=20, gap=10)
    add_message(s, "Nothing is silently recomputed or changed behind the researcher's back.", top=Inches(6.5), size=22)
    add_text(s, Inches(0.6), Inches(7.25), Inches(10.8), Inches(0.6), "Proposals are conveniences. Roles, tests and presentation stay explicit, and every decision is written to a record you can read.", size=16, color=GREY)
    add_footer(s, n)

    # 4 what MMF is
    s = new_slide("What Make My Figure is", sources="tutorial deck 3, condensed; claims verified against the application")
    stmts = [
        ("Code-free desktop application", "Windows, macOS, Linux; a browser version for the same core. Runs locally, no upload."),
        ("CSV, TSV and Excel in", f"{n_plots} plot types out, drawn through one Publication style."),
        ("Statistics on the figure", "19 registered tests, multiple-testing correction, brackets and effect sizes, a methods sentence."),
        ("Observations stay visible", "Size, jitter, fill, edge and arrangement of individual points under your control."),
        ("Records that travel", "PlotSpec, StatsSpec, Figure Package; a Figure Builder for multi-panel composites; presets previewed before they apply."),
    ]
    for i, (h, b) in enumerate(stmts):
        y = Inches(1.85) + i * Inches(1.05)
        add_text(s, Inches(0.7), y, Inches(3.6), Inches(0.9), h, size=21, color=BLUE, bold=True, anchor=MSO_ANCHOR.MIDDLE)
        add_text(s, Inches(4.4), y, Inches(7.2), Inches(0.9), b, size=17, color=INK, anchor=MSO_ANCHOR.MIDDLE)
    add_text(s, Inches(0.6), Inches(7.3), Inches(10.8), Inches(0.6), "Open source (MIT).  " + REPO_URL, size=15, color=GREY)
    add_footer(s, n)

    # 5 same data, controlled views (kept)
    s = new_slide("Same data, controlled views", sources="tutorial deck 5; showcase B/C/D presentation renders")
    third = Inches(3.6)
    for i, (name, cap) in enumerate([("B_box_points_outline_preset_pres.png", "Box + observations"),
                                     ("C_violin_points_preset_pres.png", "Violin + observations"),
                                     ("D_bar_points_jittered_preset_pres.png", "Bar + observations")]):
        x = L + i * (third + Inches(0.1))
        add_picture_fit(s, show("1_group_comparison", name), x, CONTENT_TOP, third, Inches(5.0), border=False, kind="plot")
        add_caption(s, x, Inches(6.85), third, cap, size=15)
    add_message(s, "The scientific data do not change. The presentation can.", top=Inches(7.3), size=22)
    add_text(s, Inches(0.6), Inches(7.95), Inches(10.8), Inches(0.5), "Same 40 observations (n = 7, 9, 11, 13), same Welch tests, same P values; three experimental publication presets.", size=14, color=GREY)
    add_footer(s, n)

    # 6 observations are first-class data (kept)
    s = new_slide("Observations are first-class data", sources="tutorial deck 6; showcase J1-J6")
    names = [("J1_small_narrow_jitter_pres.png", "small points, narrow jitter"), ("J2_large_moderate_jitter_pres.png", "large points, moderate jitter"),
             ("J3_open_circles_pres.png", "open circles"), ("J4_black_edged_filled_pres.png", "filled, dark edge"),
             ("J5_beeswarm_pres.png", "beeswarm arrangement"), ("J6_centered_no_jitter_pres.png", "centred, translucent, no jitter")]
    cw, ch = Inches(3.6), Inches(2.75)
    for i, (name, cap) in enumerate(names):
        r, c = divmod(i, 3)
        x = L + c * (cw + Inches(0.1)); y = CONTENT_TOP + r * (ch + Inches(0.35))
        add_picture_fit(s, show("1_group_comparison", name), x, y, cw, ch - Inches(0.05), border=False, kind="plot")
        add_caption(s, x, y + ch - Inches(0.05), cw, cap, size=13)
    add_message(s, "Summaries never hide the observations; how the points are drawn is a decision, not a default.", top=Inches(7.85), size=18)
    add_footer(s, n)

    # 7 live-demo roadmap
    s = new_slide("What I am going to do in the next five minutes", sources="new; demo dataset showcase_group_comparison.csv")
    steps = ["TABLE", "MAP", "DRAW", "TEST", "STYLE", "EXPORT"]
    subs = ["open an ordinary table", "assign column roles", "render, show observations", "choose the test, annotate", "preview a preset, adjust", "figure, PlotSpec, package"]
    bw = Inches(1.7); gap = Inches(0.16); x0 = Inches(0.55)
    for i, (st, sub) in enumerate(zip(steps, subs)):
        x = x0 + i * (bw + gap)
        sh = s.shapes.add_shape(MSO_SHAPE.CHEVRON if i else MSO_SHAPE.PENTAGON, x, Inches(2.3) + Y_OFF, bw, Inches(1.1))
        sh.fill.solid(); sh.fill.fore_color.rgb = BLUE if i % 2 == 0 else RGBColor(0x2F, 0x6D, 0xB5); sh.line.fill.background()
        add_text(s, x + Inches(0.15), Inches(2.3), bw - Inches(0.3), Inches(1.1), st, size=20, color=WHITE, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        add_text(s, x, Inches(3.5), bw, Inches(0.9), sub, size=13, color=INK2, align=PP_ALIGN.CENTER)
    add_message(s, "From an ordinary research table to a publication figure, its statistics, its specification and a portable Figure Package.", top=Inches(4.7), size=20)
    box(s, Inches(0.6), Inches(5.8), Inches(10.8), Inches(1.6))
    add_bullets(s, Inches(0.85), Inches(5.95), Inches(10.4), Inches(1.5), [
        "Demo table: 40 animals in 4 groups, unequal n (7 / 9 / 11 / 13); one readout - simulated, no biological meaning",
        "Everything that follows happens in the real application; the slides resume afterwards",
    ], size=16, gap=6)
    add_footer(s, n)

    # 8 one workflow, many scientific figures
    s = new_slide("One workflow, many scientific figures", sources="tutorial deck 10-13 refined renders (volcano, heatmap, scatter, Kaplan-Meier)")
    quad = [("2_volcano", "B_refined_pres.png", "volcano - differential results"), ("3_heatmap", "B_refined_pres.png", "clustered heatmap - feature x sample matrix"),
            ("4_scatter", "B_refined_pres.png", "scatter with regression"), ("5_survival", "B_refined_pres.png", "Kaplan-Meier survival")]
    qw, qh = Inches(5.45), Inches(2.55)
    for i, (folder, name, cap) in enumerate(quad):
        r, c = divmod(i, 2)
        x = L + c * (qw + Inches(0.1)); y = CONTENT_TOP + r * (qh + Inches(0.4))
        add_picture_fit(s, show(folder, name), x, y, qw, qh, border=False, kind="plot")
        add_caption(s, x, y + qh, qw, cap, size=13)
    add_message(s, "Different scientific questions; the same explicit role-based workflow.", top=Inches(7.85), size=20)
    add_footer(s, n)

    # 9 manuscript Fig 1: capability -> manuscript (panel B large, whole figure as context)
    s = new_slide("From application capability to manuscript figure (Fig. 1)", sources="manuscript Figure 1 (legend: fragmented tools vs connected six-stage workflow); panel B enlarged, whole figure as context")
    add_picture_fit(s, fig_rows(figdir, 1, "B"), L, CONTENT_TOP, Inches(7.9), Inches(5.6), border=False, kind="manuscript")
    add_picture_fit(s, fig_path(figdir, 1), Inches(8.7), CONTENT_TOP, Inches(3.0), Inches(3.4), border=True, kind="manuscript-thumb")
    add_caption(s, Inches(8.7), Inches(5.2), Inches(3.0), "whole Figure 1: A the fragmented landscape (separate tools, context lost at each hand-off); B the connected workflow", size=11)
    add_bullets(s, Inches(8.7), Inches(5.9), Inches(3.0), Inches(1.7), [
        "six stages, each writing a specification",
        "the demo = stages 1, 2, 4, 5, 6 on one table",
    ], size=13, gap=4)
    add_message(s, "The live demo and the paper describe the same six stages and the same records.", top=Inches(7.6), size=18)
    add_footer(s, n)

    # 10a manuscript Fig 2 A-F: decisions remain explicit
    s = new_slide("Decisions remain explicit: the guided matrix workflow (Fig. 2A-F)", sources="manuscript Figure 2 panels A-F (legend), whole figure as context")
    add_picture_fit(s, fig_rows(figdir, 2, "A-F"), L, CONTENT_TOP, Inches(11.0), Inches(5.35), border=False, kind="manuscript")
    add_bullets(s, Inches(0.6), Inches(7.15), Inches(10.8), Inches(1.2), [
        "Deposited count matrix (GSE299655, 55,665 genes x 16 samples): A-B roles and groups proposed and confirmed by the user; C profiled, preprocessing suggested (advisory)",
        "D the user's chain is applied to a derived copy, raw matrix retained, PreprocessingSpec written; E same profiler, different advice for a different matrix; F tests chosen by the user",
    ], size=13, gap=3)
    add_footer(s, n)

    # 10b manuscript Fig 2 G: the plots from the same workflow
    s = new_slide("The plots come from the same workflow (Fig. 2G)", sources="manuscript Figure 2 panel G, whole figure as context")
    add_picture_fit(s, fig_rows(figdir, 2, "G"), L, CONTENT_TOP, Inches(7.9), Inches(4.4), border=False, kind="manuscript")
    add_picture_fit(s, fig_path(figdir, 2), Inches(8.7), CONTENT_TOP, Inches(3.0), Inches(3.0), border=True, kind="manuscript-thumb")
    add_caption(s, Inches(8.7), Inches(4.8), Inches(3.0), "whole Figure 2 for context", size=11)
    add_bullets(s, Inches(0.6), Inches(6.55), Inches(10.8), Inches(1.0), [
        "PCA, heatmap and volcano generated through the same plotting workflow; Welch's t-test with Benjamini-Hochberg correction chosen by the user (Fig. 2F)",
    ], size=14, gap=3)
    add_message(s, "Recommendations are advisory; nothing is applied until the user confirms.", top=Inches(7.5), size=18)
    add_footer(s, n)

    # 11a manuscript Fig 3 A-B: reconstruct and reuse
    s = new_slide("Reproducibility in the manuscript: reconstruct and reuse (Fig. 3A-B)", sources="manuscript Figure 3 panels A-B (legend), whole figure as context")
    add_picture_fit(s, fig_rows(figdir, 3, "A-B"), L, CONTENT_TOP, Inches(8.2), Inches(5.6), border=False, kind="manuscript")
    add_picture_fit(s, fig_path(figdir, 3), Inches(9.0), CONTENT_TOP, Inches(2.7), Inches(3.0), border=True, kind="manuscript-thumb")
    add_bullets(s, Inches(9.0), Inches(5.0), Inches(2.7), Inches(2.6), [
        ("A Reconstruct", 0, True), ("PlotSpec + data, separate session: identical plot, 47 fields restored", 1),
        ("B Reuse", 0, True), ("a Figure Preset carries appearance only; the new dataset keeps its values", 1),
    ], size=12, gap=3)
    add_message(s, "A specification regenerates the plot; a preset transfers only the look.", top=Inches(7.6), size=18)
    add_footer(s, n)

    # 11b manuscript Fig 3 C: compose, and what a package adds
    s = new_slide("Reproducibility in the manuscript: compose (Fig. 3C)", sources="manuscript Figure 3 panel C (legend); package statement from Results")
    add_picture_fit(s, fig_rows(figdir, 3, "C"), L, CONTENT_TOP, Inches(11.0), Inches(4.4), border=False, kind="manuscript")
    box(s, Inches(0.6), Inches(6.55), Inches(10.8), Inches(1.3), fill=RGBColor(0xE3, 0xEB, 0xF5))
    add_text(s, Inches(0.8), Inches(6.65), Inches(10.4), Inches(1.2),
             ["Data + PlotSpec + StatsSpec + rendering information = reconstructable figure.   Figure Package = recipe + ingredients.",
              "In the manuscript's test a packaged figure was moved and reopened after the original data were removed, and failed its integrity check when the packaged data were altered."],
             size=14, color=INK2)
    add_footer(s, n)

    # 12 manuscript figures 1-6 capability map
    s = new_slide("Manuscript Figures 1-6: what the paper demonstrates", sources="manuscript Figures 1-6; roles from the figure legends")
    tw, th = Inches(3.6), Inches(2.45)
    for i in range(6):
        r, c = divmod(i, 3)
        x = L + c * (tw + Inches(0.1)); y = CONTENT_TOP + r * (th + Inches(0.85))
        add_picture_fit(s, fig_path(figdir, i + 1), x, y, tw, th, border=True, kind="manuscript-thumb")
        add_text(s, x, y + th + Inches(0.02), tw, Inches(0.8), f"Fig. {i + 1} - {FIG_ROLE[i + 1]}", size=11, color=INK2)
    add_footer(s, n)

    # 13 a figure should carry its provenance
    s = new_slide("A figure should carry its provenance", sources="tutorial deck 16 (package confirmation); package members from the validated run")
    # left: PlotSpec vs Figure Package
    box(s, Inches(0.6), Inches(1.85), Inches(3.4), Inches(2.0))
    add_text(s, Inches(0.8), Inches(1.95), Inches(3.0), Inches(0.6), "PlotSpec", size=24, color=BLUE, bold=True)
    add_text(s, Inches(0.8), Inches(2.55), Inches(3.0), Inches(1.2), ["The recipe", "plot type, roles, options, statistics settings, digest of the source table - needs the data file to redraw"], size=14, color=INK)
    box(s, Inches(0.6), Inches(4.05), Inches(3.4), Inches(2.2), fill=RGBColor(0xE3, 0xEB, 0xF5))
    add_text(s, Inches(0.8), Inches(4.15), Inches(3.0), Inches(0.6), "Figure Package", size=24, color=BLUE, bold=True)
    add_text(s, Inches(0.8), Inches(4.75), Inches(3.0), Inches(1.4), ["The recipe + ingredients", "one .mmfpackage file; verified before anything is drawn"], size=14, color=INK)
    # middle: package diagram (members from the real package written in figure_package run)
    px = Inches(4.3)
    folder = s.shapes.add_shape(MSO_SHAPE.FOLDED_CORNER, px, Inches(1.85) + Y_OFF, Inches(3.5), Inches(4.4))
    folder.fill.solid(); folder.fill.fore_color.rgb = WHITE; folder.line.color.rgb = RGBColor(0xB0, 0xB8, 0xC4)
    add_text(s, px + Inches(0.2), Inches(1.95), Inches(3.1), Inches(0.5), "box.mmfpackage", size=15, color=INK2, bold=True)
    members = ["manifest.json  -  SHA-256 per member", "plot_spec.json", "stats_spec.json  -  settings + results", "render_metadata.json",
               "data/source.csv + typed table", "data/original/  -  the source file", "preview/figure.png .svg .pdf", "environment/environment.json", "README.txt"]
    add_bullets(s, px + Inches(0.2), Inches(2.5), Inches(3.2), Inches(4.6), members, size=13, gap=4)
    # right: real confirmation dialog
    add_picture_fit(s, shot("figure_package", "03_package_confirmation.png"), Inches(8.1), Inches(1.85), Inches(3.6), Inches(3.4), kind="ui")
    add_caption(s, Inches(8.1), Inches(5.3), Inches(3.6), "the real confirmation: what goes in, and a privacy reminder", size=12)
    add_message(s, "Move one package. Reopen it. Verify integrity. Restore specification, data, options and statistical annotations.", top=Inches(7.5), size=18)
    add_footer(s, n)

    # 14 figure builder
    s = new_slide("From one plot to a complete figure", sources="tutorial deck 17 composite; manuscript Figure 3 as context (panel C = Compose)")
    comp = os.path.join(OUTS, "figure_builder", "composite.png")
    if os.path.exists(comp):
        add_picture_fit(s, comp, L, CONTENT_TOP, Inches(7.4), Inches(4.3), border=False, kind="plot")
    add_caption(s, L, Inches(6.1), Inches(7.4), "two-panel composite from the tutorial: panels keep their own data and specification", size=13)
    add_picture_fit(s, fig_path(figdir, 3), Inches(8.1), CONTENT_TOP, Inches(3.6), Inches(4.3), border=True, kind="manuscript-thumb")
    add_caption(s, Inches(8.1), Inches(6.1), Inches(3.6), "manuscript Fig. 3; panel C: a four-panel composite rebuilt from its FigureSpec", size=12)
    add_bullets(s, Inches(0.6), Inches(6.95), Inches(10.8), Inches(1.1), [
        "Panel letters, width in millimetres, common fonts; PNG / PDF / SVG export and a Figure Package of the composite",
        "Grid layout; free positioning and layering are not supported (manuscript Discussion)",
    ], size=15, gap=3)
    add_footer(s, n)

    # 15 the tutorial is executed, not mocked up
    s = new_slide("The tutorial is executed, not mocked up", sources="tutorial deck 18 + validation totals from audit/validation/*.json")
    x = Inches(0.6)
    for i, t in enumerate(["Tutorial action script", "real MMF MainWindow", "screenshots / video", "validation record"]):
        box(s, x, Inches(1.85), Inches(2.5), Inches(0.95), fill=LIGHT if i % 2 == 0 else RGBColor(0xE3, 0xEB, 0xF5))
        add_text(s, x + Inches(0.1), Inches(1.85), Inches(2.3), Inches(0.95), t, size=15, color=INK2, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        if i < 3:
            add_text(s, x + Inches(2.5), Inches(2.0), Inches(0.4), Inches(0.6), "\u2192", size=22, color=BLUE, align=PP_ALIGN.CENTER)
        x += Inches(2.85)
    add_text(s, Inches(0.6), Inches(3.0), Inches(5.2), Inches(0.9), "No mock-ups.", size=34, color=INK2, bold=True)
    add_bullets(s, Inches(0.6), Inches(3.95), Inches(5.2), Inches(1.9), [
        "Every screenshot comes from production widgets",
        "Every demonstrated action is executable",
        "Validation records PASS / FAIL per step",
    ], size=16, gap=5)
    nums = [(str(totals["workflows"]), "tutorial workflows"), (str(totals["checks"]), "checks"), (str(totals["captures"]), "captures"),
            ("PASS" if totals["all_pass"] else "FAIL", "all workflows")]
    for i, (num, lab) in enumerate(nums):
        r, c = divmod(i, 2)
        xx = Inches(0.6) + c * Inches(2.7); yy = Inches(5.95) + r * Inches(1.0)
        add_text(s, xx, yy, Inches(1.2), Inches(0.9), num, size=26, color=GREEN if num == "PASS" else BLUE, bold=True, align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
        add_text(s, xx + Inches(1.3), yy, Inches(1.4), Inches(0.9), lab, size=14, color=INK, anchor=MSO_ANCHOR.MIDDLE)
    add_picture_fit(s, shot("observations_jitter", "01_defaults_options.png"), Inches(6.1), Inches(3.0), Inches(5.6), Inches(2.4), crop=(0, 0, 566, 240), kind="ui")
    add_picture_fit(s, shot("observations_jitter", "09_preview_dialog.png"), Inches(6.1), Inches(5.5), Inches(5.6), Inches(2.5), crop=(0, 0, 908, 410), kind="ui")
    add_caption(s, Inches(6.1), Inches(8.0), Inches(5.6), "captures from the observations tutorial: 3. Options, and the real Preview & apply dialog", size=11)
    add_footer(s, n)

    # 16 what comes next
    s = new_slide("What comes next", sources="tutorial MAINTAINING doc; manuscript Discussion (future development principle, Builder limits)")
    nxt = [
        ("Broader guided workflows", "Tutorial coverage across the remaining plot families and the matrix workflow, each generated and validated against the running application."),
        ("Reproducible figure construction", "Figure Builder (grid layout today; free positioning and layering are not supported), matrix workflow records, portable Figure Packages."),
        ("Records with every capability", "The manuscript's principle for future development: a new capability ships with a record that can be inspected and validated."),
    ]
    for i, (h, b) in enumerate(nxt):
        x = Inches(0.6) + i * Inches(3.75)
        box(s, x, Inches(1.9), Inches(3.5), Inches(4.4))
        add_text(s, x + Inches(0.25), Inches(2.1), Inches(3.0), Inches(0.9), h, size=21, color=BLUE, bold=True)
        add_text(s, x + Inches(0.25), Inches(3.1), Inches(3.0), Inches(3.0), b, size=16, color=INK)
    add_footer(s, n)

    # 17 final
    s = new_slide(sources="new closing slide; QR to the repository")
    add_text(s, Inches(0.6), Inches(1.8), Inches(10.8), Inches(0.9), "The application suggests.", size=38, color=INK2, bold=True, align=PP_ALIGN.CENTER, raw=True)
    add_text(s, Inches(0.6), Inches(2.65), Inches(10.8), Inches(0.9), "The researcher decides.", size=38, color=BLUE, bold=True, align=PP_ALIGN.CENTER, raw=True)
    fin = [("YOUR DATA", "Observations remain visible and traceable."),
           ("YOUR DECISIONS", "Roles, tests and presentation remain under researcher control."),
           ("YOUR FIGURE", "Specification, statistics and frozen data can travel together.")]
    for i, (h, b) in enumerate(fin):
        x = Inches(0.6) + i * Inches(3.75)
        box(s, x, Inches(3.6), Inches(3.5), Inches(2.1))
        add_text(s, x + Inches(0.25), Inches(3.75), Inches(3.0), Inches(0.6), h, size=20, color=BLUE, bold=True)
        add_text(s, x + Inches(0.25), Inches(4.4), Inches(3.0), Inches(1.3), b, size=16, color=INK)
    add_text(s, Inches(0.6), Inches(6.3), Inches(8.2), Inches(0.7), "Make My Figure", size=26, color=INK2, bold=True)
    add_text(s, Inches(0.6), Inches(6.95), Inches(8.2), Inches(0.6), "One dataset, many controlled views.", size=20, color=INK2)
    add_text(s, Inches(0.6), Inches(7.55), Inches(8.2), Inches(0.5), REPO_URL + "   (MIT license)", size=14, color=GREY)
    add_picture_fit(s, qr_png(REPO_URL), Inches(9.6), Inches(6.1), Inches(1.9), Inches(1.9), border=False, kind="qr")
    add_footer(s, n)

    # ================================================================ BACKUP
    s = new_slide(layout=section_layout, backup=True, sources="divider")
    add_text(s, Inches(3.0), Inches(3.4), Inches(8.6), Inches(1.0), "Backup slides", size=36, color=WHITE, bold=True, raw=True)
    add_text(s, Inches(3.0), Inches(4.4), Inches(8.6), Inches(1.6), "Detailed examples, preset behaviour, package contents, validation table, plot gallery, manuscript Figures 4-6 at full size, development status",
             size=18, color=WHITE, raw=True)

    # B1 preset: may / must not (simplified) + preview screenshot
    s = new_slide("Publication presets: presentation may change, scientific meaning must not", backup=True, sources="tutorial deck 8-9 simplified; preview dialog screenshot")
    add_picture_fit(s, shot("observations_jitter", "09_preview_dialog.png"), L, CONTENT_TOP, Inches(6.6), Inches(4.7), kind="ui")
    box(s, Inches(7.4), Inches(1.85), Inches(4.3), Inches(2.3), fill=RGBColor(0xE8, 0xF3, 0xEA), line=RGBColor(0xB5, 0xD6, 0xBC))
    add_text(s, Inches(7.6), Inches(1.95), Inches(4.0), Inches(0.5), "A preset may change", size=17, color=GREEN, bold=True)
    add_bullets(s, Inches(7.6), Inches(2.45), Inches(4.0), Inches(1.7), ["marker size, opacity, fill, edge", "typography, line weights", "box / bar widths, spacing, legend, export"], size=14, gap=3)
    box(s, Inches(7.4), Inches(4.3), Inches(4.3), Inches(2.3), fill=RGBColor(0xFB, 0xEA, 0xEA), line=RGBColor(0xE3, 0xB4, 0xB4))
    add_text(s, Inches(7.6), Inches(4.4), Inches(4.0), Inches(0.5), "A preset must not silently change", size=17, color=RED, bold=True)
    add_bullets(s, Inches(7.6), Inches(4.9), Inches(4.0), Inches(1.7), ["data", "column roles", "statistical test, threshold", "transformation"], size=14, gap=3)
    add_message(s, "Presentation may change. Scientific meaning must not change silently.", top=Inches(6.75), size=19)
    add_text(s, Inches(0.6), Inches(7.4), Inches(10.8), Inches(0.7), "Experimental presets are derived from published open-access figures and publishers' stated requirements; the letters (N) (S) (C) name the evidence set. They are starting configurations, not journal endorsements or locked templates.", size=13, color=GREY)
    add_footer(s, n, backup=True)

    # B2-B5 same data pairs (from tutorial deck 10-13)
    pairs = [
        ("Same data, different presentation - volcano", "2_volcano", "A_default_pres.png", "B_refined_pres.png", "default: raw P, ten labels", "refined: adjusted P (FDR), boxed labels, larger markers",
         "1,200 features, identical values; the axis, labels and markers changed, the numbers did not."),
        ("Same data, different presentation - clustered heatmap", "3_heatmap", "A_basic_pres.png", "B_refined_pres.png", "basic: unscaled values, auto colormap, clustered columns", "refined: row z-score, RdBu_r, samples in file order",
         "The same 30 most variable features. Scaling and colormap are presentation choices the reader must be told about."),
        ("Same data, different presentation - scatter with regression", "4_scatter", "A_basic_pres.png", "B_refined_pres.png", "basic: two roles, one fit", "refined: colour by cell line, per-group fit, r / R² / P / n",
         "Adding a colour role turns one regression into one per group; the sixty points are the same."),
        ("Same data, different presentation - Kaplan-Meier", "5_survival", "A_default_pres.png", "B_refined_pres.png", "default: fraction, auto ticks", "refined: percent, 50 % reference, log-rank P on the figure",
         "Eighty subjects, the same curves; the log-rank test is written on the figure and stored with it."),
    ]
    for title, folder, a, b, ca, cb, msg in pairs:
        s = new_slide(title, backup=True, sources=f"tutorial deck pair; showcase {folder}")
        half = Inches(5.4)
        add_picture_fit(s, show(folder, a), L, CONTENT_TOP, half, Inches(4.9), border=False, kind="plot")
        add_picture_fit(s, show(folder, b), L + half + Inches(0.2), CONTENT_TOP, half, Inches(4.9), border=False, kind="plot")
        add_caption(s, L, Inches(6.75), half, ca, size=14); add_caption(s, L + half + Inches(0.2), Inches(6.75), half, cb, size=14)
        add_message(s, msg, top=Inches(7.3), size=18)
        add_footer(s, n, backup=True)

    # B6 ambiguous-column mapping (from tutorial deck 15)
    s = new_slide("When the detector does not know your headers, you assign the roles", backup=True, sources="tutorial deck 15")
    add_picture_fit(s, shot("volcano_manual_mapping", "04b_window_before.png"), L, CONTENT_TOP, Inches(11.0), Inches(1.3), crop=(612, 48, 1680, 125), kind="ui")
    add_picture_fit(s, shot("volcano_manual_mapping", "04_mapping_renamed_before.png"), L, Inches(3.3), Inches(5.4), Inches(1.45), kind="ui")
    add_caption(s, L, Inches(4.75), Inches(5.4), "every role starts at (none): the detector does not know these headers", size=13)
    add_picture_fit(s, shot("volcano_manual_mapping", "05_mapping_renamed_after.png"), L, Inches(5.25), Inches(5.4), Inches(1.45), kind="ui")
    add_caption(s, L, Inches(6.7), Inches(5.4), "x, p, label, id_col assigned by hand", size=13)
    add_picture_fit(s, show("2_volcano", "B_refined_pres.png"), Inches(6.1), Inches(3.3), Inches(5.5), Inches(4.1), border=False, kind="plot")
    add_message(s, "The Messages tab names the missing roles; four drop-downs later the volcano renders - P values read from the table, never recomputed.", top=Inches(7.55), size=16)
    add_footer(s, n, backup=True)

    # B7 the table-to-figure hero (tutorial deck 14)
    s = new_slide("From an ambiguous table to a publication figure", backup=True, sources="tutorial deck 14")
    tbl2 = B.table_excerpt_image(os.path.join(TUT, "datasets", "showcase_group_comparison.csv"), rows=6, out_name="showcase_excerpt.png")
    add_picture_fit(s, tbl2, L, CONTENT_TOP, Inches(5.3), Inches(2.3), border=False, kind="table")
    add_caption(s, L, Inches(4.1), Inches(5.3), "1  open the table: 40 animals, 4 groups, unequal n", size=14)
    add_picture_fit(s, shot("observations_jitter", "07b_options_after.png"), Inches(6.2), CONTENT_TOP, Inches(5.4), Inches(2.3), crop=(0, 0, 566, 240), kind="ui")
    add_caption(s, Inches(6.2), Inches(4.1), Inches(5.4), "2  map the roles; choose how the observations are drawn", size=14)
    add_picture_fit(s, show("1_group_comparison", "B_box_points_outline_preset_pres.png"), L, Inches(4.5), Inches(3.9), Inches(3.4), border=False, kind="plot")
    add_caption(s, L, Inches(7.85), Inches(4.0), "3  statistics, publication preset, export", size=14)
    add_text(s, Inches(4.9), Inches(5.0), Inches(6.7), Inches(2.6), ["Open, map, draw, test, preset, export.", "", "From a table with unnamed columns to a figure with brackets, a methods sentence, its PlotSpec and a Figure Package."], size=19, color=INK2)
    add_footer(s, n, backup=True)

    # B8 statistics detail (tutorial deck 7)
    s = new_slide("Statistics on the figure - the panel and its output", backup=True, sources="tutorial deck 7")
    add_picture_fit(s, show("1_group_comparison", "B_box_points_outline_preset_pres.png"), L, CONTENT_TOP, Inches(5.5), Inches(5.4), border=False, kind="plot")
    add_picture_fit(s, shot("group_comparison_box", "05_statistics.png"), Inches(6.2), CONTENT_TOP, Inches(5.4), Inches(5.4), crop=(0, 20, 566, 520), kind="ui")
    add_message(s, "Welch's t-test, selected pairs, Holm correction: brackets with exact P, a results table, and the methods sentence to paste.", top=Inches(7.5), size=18)
    add_footer(s, n, backup=True)

    # B9.. manuscript figures 4, 5, 6: panel rows large, whole figure as context
    details = [
        (4, "A-B", "Fig. 4A-B - input equivalence and platform agreement", "A eleven file encodings load identically (Excel: numerically equivalent); B Windows vs Linux statistics, coordinates, limits, matrix values exact or numerically equivalent; only text placement differs"),
        (4, "C-D", "Fig. 4C-D - rendering consistency and export fidelity", "C scientific geometry identical on both systems; text-dependent layout differs only with different fonts; D every applicable export property holds in PNG, TIFF, PDF, SVG, EPS; EPS cannot store transparency"),
        (4, "E-F", "Fig. 4E-F - computational scaling and repeatability", "E runtime and peak memory of load-analyze-render-export with input size, both systems; F twenty renders reproduce every value and coordinate except repelled network labels"),
        (5, "A-C", "Fig. 5A-C - published panels recreated from source data", "A regression of tRNA abundance on RNA polymerase III occupancy; B xenograft tumour volume under a WRN inhibitor (mean +/- s.e.m., n = 5 per arm); C oncoprint of 271 pancreatic tumours - every value from the deposited tables"),
        (5, "D-F", "Fig. 5D-F - published panels recreated from source data", "D clustered heatmap of transcription-factor activity in granulosa cells; E UMAP of Drosophila mesoderm and muscle nuclei; F overall survival of 75 melanoma patients by CMV serostatus - assembled with the Figure Builder"),
        (6, "A-B", "Fig. 6A-B - agreement with independent R calculations", "A same data through MakeMyFigure and independent R, compared; annotations come only from the stored StatsSpec; B nine procedures, every compared statistic, P value and estimate within tolerance"),
        (6, "C-D", "Fig. 6C-D - published statistics reproduced", "C pairwise Welch t-tests on published microglia counts: P = 0.0646, 0.0011, 0.0003 as published; D Kruskal-Wallis + Dunn (Bonferroni) on CSF C3: adjusted P 0.113, 0.026, 1.000 as published"),
        (6, "E-F", "Fig. 6E-F - imported results plotted; survival reproduced", "E a published DESeq2 table plotted at the article's thresholds: 834 up, 1,226 down as reported (visualisation of imported results, not recalculation); F log-rank P = 0.001 for 33 patients matches the published value"),
    ]
    for k, key, ttl, blurb in details:
        s = new_slide(ttl, backup=True, sources=f"manuscript Figure {k} panels {key} (legend and Results), whole figure as context")
        add_picture_fit(s, fig_rows(figdir, k, key), L, CONTENT_TOP, Inches(8.3), Inches(5.3), border=False, kind="manuscript")
        add_picture_fit(s, fig_path(figdir, k), Inches(9.1), CONTENT_TOP, Inches(2.6), Inches(3.0), border=True, kind="manuscript-thumb")
        add_caption(s, Inches(9.1), Inches(4.8), Inches(2.6), f"whole Figure {k} for context", size=11)
        add_text(s, Inches(0.6), Inches(7.05), Inches(10.8), Inches(1.3), blurb, size=13, color=INK)
        add_footer(s, n, backup=True)

    # B12 full validation table (tutorial deck 19)
    s = new_slide("Every tutorial instruction executed against the application", backup=True, sources="tutorial deck 19; audit/validation/*.json")
    rows = [("Tutorial", "Status", "Checks")] + totals["rows"]
    rh = Inches(0.38)
    tbl = s.shapes.add_table(len(rows), 3, Inches(0.6), CONTENT_TOP + Y_OFF, Inches(10.8), rh * len(rows)).table
    tbl.columns[0].width = Inches(6.2); tbl.columns[1].width = Inches(1.4); tbl.columns[2].width = Inches(3.2)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = tbl.cell(i, j); cell.text = val
            B._style_runs(cell.text_frame, 13 if i else 14, INK if i else WHITE, bold=(i == 0))
            cell.fill.solid(); cell.fill.fore_color.rgb = BLUE if i == 0 else (WHITE if i % 2 else LIGHT)
            if j == 1 and i:
                B._style_runs(cell.text_frame, 13, GREEN if val == "PASS" else RED, bold=True)
    add_footer(s, n, backup=True)

    # B13 gallery (tutorial deck 20)
    s = new_slide(f"{n_plots} plot types, one workflow", backup=True, sources="tutorial deck 20; PLOT_GALLERY thumbnails")
    gal = json.load(open(os.path.join(TUT, "audit", "gallery_index.json"), encoding="utf-8"))
    thumbs = [g for g in gal if g["thumb"]]
    cw, ch = Inches(1.38), Inches(1.28)
    for i, g in enumerate(thumbs[:40]):
        r_, c_ = divmod(i, 8)
        add_picture_fit(s, os.path.join(TUT, g["thumb"]), Inches(0.45) + c_ * cw, Inches(1.65) + r_ * ch, cw - Inches(0.08), ch - Inches(0.08), border=False, kind="thumbnail")
    add_caption(s, Inches(0.5), Inches(8.1), Inches(11), "Thumbnails for breadth only - each is a real render of the bundled synthetic example (tutorial/PLOT_GALLERY.md)")
    add_footer(s, n, backup=True)

    # B14 development status (tutorial deck 21)
    s = new_slide("Development status of the tutorial branch", backup=True, sources="tutorial deck 21")
    add_bullets(s, Inches(0.7), CONTENT_TOP, Inches(10.6), Inches(6.0), [
        ("Reviewed and rebuilt", 0, True),
        ("tutorial and slides re-evaluated as visual demonstrations; observations, jitter and publication presets shown at readable size", 1),
        ("After author review", 0, True),
        ("remaining plot tutorials with the same template; matrix workflow tutorial and video; master and plot videos recorded live", 1),
        ("decision whether the presets branch (observation controls, experimental presets) is merged - without it those chapters cannot ship", 1),
        ("Not merged, tagged, released, published or pushed", 0, True),
    ], size=18, gap=9)
    add_footer(s, n, backup=True)

    prs.save(out)
    os.makedirs(B.PRES_AUDIT, exist_ok=True)
    with open(os.path.join(B.PRES_AUDIT, "seminar_placements.json"), "w", encoding="utf-8") as fh:
        json.dump(B.placements, fh, indent=1)
    with open(os.path.join(HERE, "_seminar_slide_map.json"), "w", encoding="utf-8") as fh:
        json.dump(mapping, fh, indent=1)
    print(f"saved {out} ({n} slides: {sum(1 for m in mapping if m[1] == 'main')} main + {sum(1 for m in mapping if m[1] == 'backup')} backup); {len(B.placements)} images")
    return mapping


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--figures", required=True, help="folder with Figure1.png ... Figure6.png from the manuscript package")
    ap.add_argument("--out", default=os.path.join(HERE, "MakeMyFigure_Seminar_Revised.pptx"))
    a = ap.parse_args()
    build(a.template, a.figures, a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
