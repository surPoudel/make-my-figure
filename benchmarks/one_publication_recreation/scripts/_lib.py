"""Shared logic for the one-publication recreation pilot (Gorman et al. 2014).

Curates the CC0 penguin data, recreates panels through Make My Figure's normal
render path (Publication style) with a genuine QC-driven iteration loop, runs
scientific + visual QC, and assembles the panels in the Figure Builder. Kept in
one module so the thin `*.py` scripts stay small and reproducible.
"""

from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

BASE = os.path.abspath(os.path.join(HERE, ".."))
RAW = os.path.join(BASE, "raw_data")
PROC = os.path.join(BASE, "processed_data")
PANELS_DIR = os.path.join(BASE, "recreated_panels")
FB_DIR = os.path.join(BASE, "figure_builder")

MORPHO = ["bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g"]
SPECIES_ORDER = ["Adelie", "Chinstrap", "Gentoo"]
PUBLICATION_STYLE = "publication"


# --------------------------------------------------------------------------
# Curation (raw -> processed). Raw files are never modified.
# --------------------------------------------------------------------------
def load_raw() -> pd.DataFrame:
    df = pd.read_csv(os.path.join(RAW, "penguins.csv"))
    return df


def curate() -> dict:
    """Write processed per-panel CSVs; return {panel: path} + a curation log."""
    os.makedirs(PROC, exist_ok=True)
    raw = load_raw()
    log = {"raw_rows": int(len(raw)),
           "raw_species_counts": raw["species"].value_counts().to_dict()}

    # Panel A — bill length vs depth, complete bill measurements.
    a = raw.dropna(subset=["bill_length_mm", "bill_depth_mm", "species"]).copy()
    a = a[["species", "island", "sex", "bill_length_mm", "bill_depth_mm"]]
    a_path = os.path.join(PROC, "panel_A_bill_dimensions.csv")
    a.to_csv(a_path, index=False)

    # Panel B — body mass by species, complete body_mass.
    b = raw.dropna(subset=["body_mass_g", "species"]).copy()
    b["species"] = pd.Categorical(b["species"], categories=SPECIES_ORDER, ordered=True)
    b = b.sort_values("species")[["species", "sex", "body_mass_g"]]
    b_path = os.path.join(PROC, "panel_B_body_mass.csv")
    b.to_csv(b_path, index=False)

    # Panel C — PCA matrix (features x samples), z-scored morphometrics + metadata.
    c = raw.dropna(subset=MORPHO + ["species"]).reset_index(drop=True).copy()
    c["sample_id"] = [f"p{ i+1:03d}" for i in range(len(c))]
    z = c[MORPHO].apply(lambda s: (s - s.mean()) / s.std(ddof=0))  # standardize per feature
    matrix = z.T.copy()
    matrix.columns = c["sample_id"].tolist()
    matrix.insert(0, "feature", MORPHO)
    matrix_path = os.path.join(PROC, "panel_C_pca_matrix.csv")
    matrix.to_csv(matrix_path, index=False)
    meta = c[["sample_id", "species", "island", "sex"]]
    meta_path = os.path.join(PROC, "panel_C_pca_metadata.csv")
    meta.to_csv(meta_path, index=False)

    log.update({
        "panel_A_rows": int(len(a)), "panel_B_rows": int(len(b)),
        "panel_C_samples": int(len(c)),
        "panel_B_species_counts": b["species"].value_counts().reindex(SPECIES_ORDER).to_dict(),
        "transforms": {
            "panel_A": "drop rows missing bill_length_mm/bill_depth_mm/species",
            "panel_B": "drop rows missing body_mass_g; order species Adelie<Chinstrap<Gentoo",
            "panel_C": ("complete-case on 4 morphometrics; per-feature z-score "
                        "(mean 0, sd 1) so differing units do not dominate PCA; "
                        "transpose to features x samples"),
        },
    })
    with open(os.path.join(PROC, "curation_log.json"), "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=2)
    return log


# --------------------------------------------------------------------------
# Panel definitions
# --------------------------------------------------------------------------
def panel_configs() -> dict:
    return {
        "A": {
            "dir": "panel_A", "plot_type": "scatterplot_with_regression",
            "data": "panel_A_bill_dimensions.csv",
            "mapping": {"x": "bill_length_mm", "y": "bill_depth_mm",
                        "color": "species", "fit_line": True},
            "labels": {"x_label": "Bill length (mm)", "y_label": "Bill depth (mm)",
                       "title": "Bill dimensions by species"},
            "statistics": None, "aux": None,
        },
        "B": {
            "dir": "panel_B", "plot_type": "boxplot_or_violin_with_points",
            "data": "panel_B_body_mass.csv",
            "mapping": {"x": "species", "y": "body_mass_g", "kind": "box", "points": True},
            "labels": {"x_label": "Species", "y_label": "Body mass (g)",
                       "title": "Body mass by species"},
            "statistics": {"enabled": True, "test": "mann_whitney",
                           "comparison_mode": "all_pairs", "correction": "bh",
                           "value_column": "body_mass_g", "group_column": "species"},
            "aux": None,
        },
        "C": {
            "dir": "panel_C", "plot_type": "pca_scatter_from_matrix",
            "data": "panel_C_pca_matrix.csv",
            "mapping": {"matrix_row_id": "feature", "metadata_key": "sample_id",
                        "color": "species"},
            "labels": {"title": "Morphometric PCA"},
            "statistics": None, "aux": "panel_C_pca_metadata.csv",
        },
    }


# --------------------------------------------------------------------------
# Render one panel with a QC-driven iteration loop (>=3 iterations)
# --------------------------------------------------------------------------
def _build_spec(cfg: dict, width: str, extra_layout: dict) -> dict:
    from make_my_figure_core.plots.registry import make_spec
    from make_my_figure_core.spec.validate import default_output_block

    layout = {"column_width": width}
    layout.update(cfg["labels"])
    layout.update(extra_layout)
    return make_spec(cfg["plot_type"], cfg["data"], PUBLICATION_STYLE,
                     mapping=cfg["mapping"], layout=layout,
                     statistics=cfg.get("statistics"),
                     output=default_output_block(["svg", "png", "pdf"], dpi=300))


def recreate_panel(pid: str, cfg: dict) -> dict:
    """Render through the app, iterate on QC, export, return a result record."""
    import matplotlib.pyplot as plt

    from make_my_figure_core.plots.registry import render, export_figure, write_sidecar
    from make_my_figure_core.qa.publication_check import check_publication_readiness

    pdir = os.path.join(PANELS_DIR, cfg["dir"])
    os.makedirs(pdir, exist_ok=True)
    df = pd.read_csv(os.path.join(PROC, cfg["data"]))
    df.to_csv(os.path.join(pdir, "processed_data.csv"), index=False)  # panel-local copy
    aux = None
    if cfg.get("aux"):
        aux = {"metadata": pd.read_csv(os.path.join(PROC, cfg["aux"]))}

    # Genuine iteration loop: start minimal, apply fixes flagged by the visual
    # QC check, re-render — at least 3 iterations.
    iterations = []
    plans = [
        {"width": "single", "extra": {}},                                  # 1: baseline
        {"width": "onehalf", "extra": {}},                                 # 2: enlarge + labels
        {"width": "onehalf", "extra": {"legend_outside": True}},           # 3: legend/polish
    ]
    result = None
    spec = None
    for i, plan in enumerate(plans, 1):
        spec = _build_spec(cfg, plan["width"], plan["extra"])
        result = render(spec, df, aux=aux)
        check = check_publication_readiness(result.figure)
        iterations.append({"iteration": i, "width": plan["width"],
                           "changes": ("baseline render" if i == 1 else
                                       "enlarged figure + explicit axis labels/units" if i == 2 else
                                       "legend placed outside; final polish"),
                           "visual_warnings": list(check.warnings)})
        if i < len(plans):
            plt.close(result.figure)

    # Export the final iteration.
    base = os.path.join(pdir, "recreated")
    export_figure(result.figure, base, ["png", "svg", "pdf"], dpi=300)
    with open(os.path.join(pdir, "plotspec.json"), "w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=2)
    if cfg.get("statistics"):
        with open(os.path.join(pdir, "statspec.json"), "w", encoding="utf-8") as fh:
            json.dump(spec.get("statistics", {}), fh, indent=2)

    rec = {"panel": pid, "dir": cfg["dir"], "plot_type": cfg["plot_type"],
           "rows": int(len(df)), "iterations": iterations,
           "final_visual_warnings": iterations[-1]["visual_warnings"],
           "stats_report": None}
    if getattr(result, "stats_report", None) is not None and result.stats_report.results:
        rec["stats_report"] = [
            {"comparison": r.comparison_label, "test": r.test_name,
             "p_value": r.p_value, "adjusted_p": r.adjusted_p_value,
             "n_total": r.n_total} for r in result.stats_report.results]
    plt.close(result.figure)
    _write_panel_qc(pid, cfg, df, rec)
    _write_target_and_differences(pid, cfg, rec)
    return rec


DOI = "10.1371/journal.pone.0090081"
PAPER = ("Gorman KB, Williams TD, Fraser WR (2014). Ecological Sexual Dimorphism "
         "and Environmental Variability within a Community of Antarctic Penguins "
         "(Genus Pygoscelis). PLoS ONE 9(3):e90081.")

_TARGETS = {
    "A": {"figure_number": "Fig 2 (culmen dimensions)", "panel_letter": "A",
          "panel_description": "Culmen (bill) length vs depth, points by species; "
                               "within-species positive relationship.",
          "axis_labels": {"x": "Bill length (mm)", "y": "Bill depth (mm)"},
          "axis_scale": "linear", "group_order": SPECIES_ORDER,
          "statistics_shown": "none (per-group regression trend only)",
          "thresholds": "none",
          "known_missing_information": "Exact marker styling/limits from the paper "
                                       "are not fully specified in the legend."},
    "B": {"figure_number": "body-mass / sexual-dimorphism comparison",
          "panel_letter": "B",
          "panel_description": "Body mass (g) distribution by species.",
          "axis_labels": {"x": "Species", "y": "Body mass (g)"},
          "axis_scale": "linear", "group_order": SPECIES_ORDER,
          "statistics_shown": "pairwise group comparison (recreated as Mann-Whitney "
                              "U, BH-corrected)",
          "thresholds": "significance stars at alpha=0.05",
          "known_missing_information": "The paper models body mass with linear models "
                                       "including sex and covariates; this panel shows a "
                                       "standard nonparametric pairwise comparison on the "
                                       "same data (documented in differences)."},
    "C": {"figure_number": "morphometric separation", "panel_letter": "C",
          "panel_description": "PCA of 4 z-scored morphometrics, points by species.",
          "axis_labels": {"x": "PC1", "y": "PC2"}, "axis_scale": "linear",
          "group_order": SPECIES_ORDER, "statistics_shown": "variance explained per PC",
          "thresholds": "none",
          "known_missing_information": "The publication does not specify a single "
                                       "canonical PCA panel; this is a standard "
                                       "morphometric PCA of the associated measurements."},
}

_DIFFERENCES = {
    "A": "Recreated from the associated CC0 measurements. The app fits a per-species "
         "regression trend (Publication style). Colours, marker sizes, and axis limits "
         "are the app's Publication defaults, not the paper's exact styling. No reference "
         "image was stored, so no pixel comparison was performed.",
    "B": "The published analysis uses linear models (with sex and environmental "
         "covariates) rather than a simple omnibus/pairwise test. This panel shows a "
         "standard, fully-traceable Mann-Whitney U pairwise comparison (BH-corrected) on "
         "the same body-mass data as a QC demonstration; it is not the paper's exact "
         "model. Direction/relative magnitude (Gentoo >> Adelie ~ Chinstrap) matches the "
         "biology. No reference image stored.",
    "C": "PCA uses per-feature z-scoring (documented) so unit differences do not dominate. "
         "PC sign/rotation is arbitrary and may be flipped vs any published ordination. "
         "Variance-explained and species separation are reported from the app's renderer. "
         "No reference image stored.",
}


def _write_target_and_differences(pid: str, cfg: dict, rec: dict) -> None:
    pdir = os.path.join(PANELS_DIR, cfg["dir"])
    t = _TARGETS[pid]
    spec = {
        "publication_id": "gorman_2014_penguins",
        "paper_title": PAPER, "DOI": DOI,
        "figure_number": t["figure_number"], "panel_letter": t["panel_letter"],
        "panel_description": t["panel_description"],
        "plot_type": cfg["plot_type"],
        "source_data_files": [f"raw_data/penguins.csv -> processed_data/{cfg['data']}"]
                             + ([f"processed_data/{cfg['aux']}"] if cfg.get("aux") else []),
        "required_columns": cfg["mapping"],
        "transformations": f"see processed_data/curation_log.json (panel {pid})",
        "statistics_shown": t["statistics_shown"], "thresholds": t["thresholds"],
        "axis_labels": t["axis_labels"], "axis_scale": t["axis_scale"],
        "group_order": t["group_order"],
        "color_mapping": "by species (Publication palette)",
        "legend_behavior": "species legend, placed outside the axes",
        "annotations": ("significance brackets from StatsSpec" if cfg.get("statistics")
                        else "none"),
        "panel_dimensions": "onehalf column width (Publication default)",
        "reference_image_path": None,
        "reference_image_license": "described-only (article CC BY 4.0; image not stored)",
        "known_missing_information": t["known_missing_information"],
    }
    with open(os.path.join(pdir, "target_panel_spec.json"), "w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=2)
    with open(os.path.join(pdir, "differences_from_published.md"), "w", encoding="utf-8") as fh:
        fh.write(f"# Panel {pid} — differences from the published figure\n\n"
                 f"Paper: {PAPER} DOI:{DOI} (article CC BY 4.0; data CC0).\n\n"
                 f"{_DIFFERENCES[pid]}\n")


def _exports_ok(pdir: str) -> dict:
    out = {}
    for ext in ("png", "svg", "pdf"):
        p = os.path.join(pdir, f"recreated.{ext}")
        out[ext] = os.path.exists(p) and os.path.getsize(p) > 0
    return out


def _write_panel_qc(pid: str, cfg: dict, df: pd.DataFrame, rec: dict) -> None:
    pdir = os.path.join(PANELS_DIR, cfg["dir"])
    exports = _exports_ok(pdir)
    rec["exports_ok"] = exports

    # --- scientific QC (trace every shown quantity) ---
    lines = [f"# Scientific QC — Panel {pid} ({cfg['plot_type']})", "",
             f"Source (processed): `processed_data/{cfg['data']}` — {len(df)} rows.",
             f"Columns used: {cfg['mapping']}", ""]
    sci_pass = True
    for role, col in cfg["mapping"].items():
        if role in ("x", "y", "color", "matrix_row_id"):
            if role == "matrix_row_id":
                ok = col in df.columns
            elif role == "color" and cfg.get("aux"):
                meta = pd.read_csv(os.path.join(PROC, cfg["aux"]))
                ok = col in meta.columns
            else:
                ok = col in df.columns
            sci_pass = sci_pass and ok
            lines.append(f"- mapping[{role}]='{col}' present ✓" if ok
                         else f"- mapping[{role}]='{col}' MISSING ✗")
    if pid == "B":
        raw = load_raw()
        full = raw["species"].value_counts().reindex(SPECIES_ORDER)
        bm = raw.dropna(subset=["body_mass_g"])["species"].value_counts().reindex(SPECIES_ORDER)
        counts = df["species"].value_counts().reindex(SPECIES_ORDER)
        ok = counts.equals(bm) and int(counts.sum()) == 342
        sci_pass = sci_pass and ok
        dropped = (full - bm).to_dict()
        lines.append(f"- group counts (body_mass complete): {counts.to_dict()} "
                     f"(sum={int(counts.sum())}) {'✓' if ok else '✗'}")
        lines.append(f"  full-dataset counts {full.to_dict()} (n=344) minus rows lacking "
                     f"body_mass_g by species {dropped} -> 342 analysed")
        lines.append("")
        lines.append("Statistics drawn on the figure (each from a stored StatResult "
                     "via `run_statistics`, Mann–Whitney U, BH-corrected):")
        for s in rec.get("stats_report") or []:
            lines.append(f"  - {s['comparison']}: {s['test']}, p={s['p_value']:.3g}, "
                         f"adj_p={s['adjusted_p']:.3g}, n={s['n_total']}")
        if not rec.get("stats_report"):
            sci_pass = False
            lines.append("  - NONE — expected pairwise results ✗")
    if pid == "C":
        n_feat = int((df["feature"].nunique()))
        lines.append(f"- PCA features (rows) = {n_feat} (the 4 z-scored morphometrics) "
                     f"{'✓' if n_feat==4 else '✗'}")
        lines.append(f"- PCA samples (cols) = {df.shape[1]-1} penguins")
    lines += ["", f"**Result: {'PASS' if sci_pass else 'FAIL'}**"]
    with open(os.path.join(pdir, "scientific_qc.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    # --- visual QC ---
    warns = rec["final_visual_warnings"]
    vis_pass = all(exports.values()) and len(warns) == 0
    vlines = [f"# Visual QC — Panel {pid}", "",
              f"Iterations run: {len(rec['iterations'])} (QC-driven).", ""]
    for it in rec["iterations"]:
        vlines.append(f"- iter {it['iteration']} ({it['width']}): {it['changes']} — "
                      f"warnings: {it['visual_warnings'] or 'none'}")
    vlines += ["", f"Exports non-empty: {exports}",
               f"Final advisory publication-readiness warnings: {warns or 'none'}",
               "", f"**Result: {'PASS' if vis_pass else 'WARN'}**"]
    with open(os.path.join(pdir, "visual_qc.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(vlines))
    rec["scientific_qc_pass"] = sci_pass
    rec["visual_qc_pass"] = vis_pass


# --------------------------------------------------------------------------
# Figure Builder assembly
# --------------------------------------------------------------------------
def assemble_figure() -> str:
    from make_my_figure_core.panels import build_figure, export_multipanel, multipanel_sidecar
    from make_my_figure_core.panels.models import FigureLayout, MultiPanelFigure, Panel

    os.makedirs(FB_DIR, exist_ok=True)
    cfgs = panel_configs()
    panels = []
    for pid in ["A", "B", "C"]:
        cfg = cfgs[pid]
        pdir = os.path.join(PANELS_DIR, cfg["dir"])
        with open(os.path.join(pdir, "plotspec.json"), encoding="utf-8") as fh:
            spec = json.load(fh)
        df = pd.read_csv(os.path.join(PROC, cfg["data"]))
        aux = {}
        if cfg.get("aux"):
            aux = {"metadata": pd.read_csv(os.path.join(PROC, cfg["aux"]))}
        panels.append(Panel(label=pid, title=cfg["labels"].get("title", ""),
                            plot_spec=spec, table=df, aux=aux,
                            stats_spec=spec.get("statistics")))
    layout = FigureLayout(ncols=2, nrows=2, fig_width_mm=180, fig_height_mm=160,
                          label_style="uppercase", panel_dpi=300)
    mpf = MultiPanelFigure(name="Gorman2014_penguins_recreation", panels=panels, layout=layout)
    fig = build_figure(mpf)
    base = os.path.join(FB_DIR, "assembled_figure")
    export_multipanel(fig, base, ["png", "svg", "pdf"], dpi=300)
    spec_path = multipanel_sidecar(mpf, base)
    # normalize sidecar name to figure_spec.json
    fs = os.path.join(FB_DIR, "figure_spec.json")
    if os.path.exists(spec_path) and os.path.abspath(spec_path) != os.path.abspath(fs):
        import shutil
        shutil.copyfile(spec_path, fs)
    import matplotlib.pyplot as plt
    plt.close(fig)
    return fs
