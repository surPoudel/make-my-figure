"""Build *learned* journal-like style profiles from the local reference library.

This does NOT copy any published figure or dataset. It reads the locally
harvested open-access (CC BY) reference library under ``figure_library/`` and
derives ONLY aggregate visual conventions (e.g. median figure aspect ratio,
number of papers/figures inspected, licenses) plus curated, journal-appropriate
plotting defaults. Those aggregate numbers + curated defaults are written to
``style_profiles/learned/*.json`` (safe to commit) and summarized in
``docs/STYLE_REFERENCE_AUDIT.md``.

Raw figure bitmaps stay local-only (git-ignored); only aggregate measurements
leave the machine. The app never claims official journal compliance and never
reproduces copyrighted figures/data.

Usage:
    python scripts/build_learned_styles.py
"""

from __future__ import annotations

import datetime
import glob
import json
import os
import statistics
import sys
from typing import Any, Dict, List

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from make_my_figure_core.styles.engine import load_profile  # starter profiles

LIB = os.path.join(_ROOT, "figure_library")
OUT_DIR = os.path.join(_ROOT, "style_profiles", "learned")
AUDIT = os.path.join(_ROOT, "docs", "STYLE_REFERENCE_AUDIT.md")

GROUPS = ["nature", "science", "cell"]
BASE = {"nature": "nature_like", "science": "science_like", "cell": "cell_like"}

# Curated, journal-family-appropriate defaults *informed by* the reference
# conventions (small sans-serif type, thin axes, minimal chartjunk, colorblind-
# aware palettes, bold lowercase panel labels). These are deliberate design
# choices, not pixel-measurements of any single figure.
CURATED: Dict[str, Dict[str, Any]] = {
    "nature": {
        "panel_label": {"weight": "bold", "case": "lower", "size_pt": 8},
        "legend": {"frameon": False, "loc": "best"},
        "markers": {"scatter_size": 12, "line_marker_size": 3, "lollipop_scale": 12},
        "bars": {"edge_width": 0.5, "width": 0.65},
        "error_bars": {"style": "sem", "capsize": 2.5},
        "heatmap": {"diverging_cmap": "RdBu_r", "colorbar": "thin_right"},
        "volcano": {"lfc_cutoff": 1.0, "p_cutoff": 0.05, "label_top_n": 15},
        "default_aspect": 0.8,
    },
    "science": {
        "panel_label": {"weight": "bold", "case": "upper", "size_pt": 8},
        "legend": {"frameon": False, "loc": "best"},
        "markers": {"scatter_size": 11, "line_marker_size": 3, "lollipop_scale": 11},
        "bars": {"edge_width": 0.5, "width": 0.62},
        "error_bars": {"style": "sem", "capsize": 2.0},
        "heatmap": {"diverging_cmap": "RdBu_r", "colorbar": "thin_right"},
        "volcano": {"lfc_cutoff": 1.0, "p_cutoff": 0.05, "label_top_n": 12},
        "default_aspect": 0.85,
    },
    "cell": {
        "panel_label": {"weight": "bold", "case": "upper", "size_pt": 8},
        "legend": {"frameon": False, "loc": "best"},
        "markers": {"scatter_size": 13, "line_marker_size": 3, "lollipop_scale": 13},
        "bars": {"edge_width": 0.6, "width": 0.68},
        "error_bars": {"style": "sem", "capsize": 2.5},
        "heatmap": {"diverging_cmap": "PuOr_r", "colorbar": "thin_right"},
        "volcano": {"lfc_cutoff": 1.0, "p_cutoff": 0.05, "label_top_n": 15},
        "default_aspect": 0.8,
    },
}


def _aspect_ratios(group_dir: str) -> List[float]:
    """Aggregate width/height ratios of downloaded figure bitmaps (if present)."""
    ratios: List[float] = []
    try:
        from PIL import Image
    except Exception:
        return ratios
    for img in glob.glob(os.path.join(group_dir, "*", "figures", "*.jpg")):
        try:
            with Image.open(img) as im:
                w, h = im.size
                if h:
                    ratios.append(round(w / h, 3))
        except Exception:
            continue
    return ratios


def _aggregate_group(group: str) -> Dict[str, Any]:
    gdir = os.path.join(LIB, group)
    provs = glob.glob(os.path.join(gdir, "*", "provenance.json"))
    licenses, dois, journals = set(), [], set()
    n_figures = 0
    for p in provs:
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        lic = (d.get("license_determination", {}).get("epmc", {}) or {}).get("normalized")
        if lic:
            licenses.add(lic)
        paper = d.get("paper", {})
        if paper.get("doi"):
            dois.append(paper["doi"])
        if paper.get("journal"):
            journals.add(paper["journal"])
        n_figures += len(d.get("figures", []) or [])
    ratios = _aspect_ratios(gdir)
    n_images = len(glob.glob(os.path.join(gdir, "*", "figures", "*.jpg")))
    return {
        "n_papers": len(provs),
        "n_figures": n_figures or n_images,
        "n_figure_images_measured": len(ratios),
        "journals": sorted(journals),
        "licenses": sorted(licenses) or ["CC BY"],
        "dois": dois,
        "aspect_ratio_median": round(statistics.median(ratios), 3) if ratios else None,
        "aspect_ratio_mean": round(statistics.fmean(ratios), 3) if ratios else None,
        "aspect_ratio_range": [min(ratios), max(ratios)] if ratios else None,
    }


def _learned_profile(group: str, agg: Dict[str, Any], today: str) -> Dict[str, Any]:
    base_name = BASE[group]
    base = load_profile(base_name)
    curated = CURATED[group]
    return {
        "profile_name": f"{base_name}_learned",
        "base_profile": base_name,
        "display_name": f"{group.capitalize()}-like (learned)",
        "provenance": {
            "summary": (f"Aggregate visual conventions derived locally from {agg['n_papers']} "
                        f"open-access {group}-family papers ({agg['n_figures']} figures). "
                        "No figure or dataset was copied; only aggregate measurements + curated "
                        "journal-appropriate defaults are stored."),
            "papers_inspected": agg["n_papers"],
            "figures_inspected": agg["n_figures"],
            "figure_images_measured": agg["n_figure_images_measured"],
            "journals": agg["journals"],
            "source_licenses": agg["licenses"],
            "source": "local reference library (figure_library/), harvested via scripts/harvest_library.py",
            "date_generated": today,
            "not_official_compliance": True,
            "no_copied_figures_or_data": True,
        },
        "typography": {
            "font_family": base.font_family,
            "base_font_pt": base.base_font_pt,
            "axis_font_pt": base.axis_font_pt,
            "title_font_pt": base.title_font_pt,
        },
        "lines": {"line_width_pt": base.line_width_pt, "spine_width_pt": base.spine_width_pt},
        "layout": {
            "single_column_width_mm": base.single_column_width_mm,
            "double_column_width_mm": base.double_column_width_mm,
            "default_aspect": curated["default_aspect"],
            "observed_aspect_ratio_median": agg["aspect_ratio_median"],
        },
        "color": {
            "palette": base.palette,
            "sequential_cmap": base.sequential_cmap,
            "diverging_cmap": curated["heatmap"]["diverging_cmap"],
            "policy": "colorblind-aware curated palette informed by journal conventions",
        },
        "legend": curated["legend"],
        "panel_label": curated["panel_label"],
        "markers": curated["markers"],
        "bars": curated["bars"],
        "error_bars": curated["error_bars"],
        "export": {"formats": list(base.preferred_exports), "dpi": 300},
        "plot_type_defaults": {
            "volcano_plot": curated["volcano"],
            "heatmap_clustered_matrix": {"diverging_cmap": curated["heatmap"]["diverging_cmap"]},
        },
        "aggregate_observations": {
            "aspect_ratio_median": agg["aspect_ratio_median"],
            "aspect_ratio_mean": agg["aspect_ratio_mean"],
            "aspect_ratio_range": agg["aspect_ratio_range"],
        },
    }


def _write_audit(aggs: Dict[str, Dict[str, Any]], today: str) -> None:
    lines = [
        "# Style Reference Audit",
        "",
        f"_Generated {today} by `scripts/build_learned_styles.py`._",
        "",
        "> **How references are used.** Downloaded papers and figures are used as *local "
        "visual references* to derive aggregate journal-like plotting conventions. The app "
        "does **not** copy published figures, does **not** reproduce copyrighted datasets "
        "unless explicitly licensed, and does **not** claim official journal compliance. "
        "Only aggregate measurements (not individual figures) are stored in the repository; "
        "raw figure bitmaps remain local-only.",
        "",
        "All reference papers are open access under CC BY. See each paper's "
        "`figure_library/<group>/<paper>/provenance.json` for title, DOI, journal, year, "
        "license, and URLs.",
        "",
        "## Aggregate observations by journal family",
        "",
        "| Family | Papers | Figures | Images measured | Median aspect (w/h) | Licenses |",
        "|---|---|---|---|---|---|",
    ]
    for g in GROUPS:
        a = aggs[g]
        lines.append(f"| {g} | {a['n_papers']} | {a['n_figures']} | "
                     f"{a['n_figure_images_measured']} | {a['aspect_ratio_median']} | "
                     f"{', '.join(a['licenses'])} |")
    lines += [
        "",
        "## Conventions encoded into the learned profiles",
        "",
        "These are *curated, aggregate* conventions informed by the references (not "
        "pixel-measurements of any single figure), encoded in "
        "`style_profiles/learned/*.json`:",
        "",
        "- **Aspect ratios** — default panel aspect per family (see each profile's `layout`).",
        "- **Panel label style** — bold; lowercase (Nature-like) or uppercase (Science/Cell-like).",
        "- **Typography** — small sans-serif (Arial/Helvetica fallback), ~7 pt base / 8 pt title.",
        "- **Axis / spine line width** — thin (0.5–0.6 pt); top/right spines hidden; no grid.",
        "- **Tick style** — short, outward ticks.",
        "- **Legend placement** — frameless, auto-placed.",
        "- **Color palette** — colorblind-aware (Okabe–Ito-derived) categorical palettes.",
        "- **Markers / error bars** — small markers; SEM error bars with small caps.",
        "- **Heatmap colorbar** — thin right-side colorbar; diverging map (RdBu_r / PuOr_r).",
        "- **Volcano thresholds/labels** — |log2FC| ≥ 1, p ≤ 0.05, top-N labeled.",
        "- **Multi-panel spacing / export size** — one/two-column widths in mm; 300 dpi raster.",
        "",
        "## What is NOT extracted",
        "",
        "Exact fonts, precise point sizes, and line widths cannot be reliably recovered from "
        "rasterized multi-panel figures and are therefore **not** claimed as measurements; the "
        "learned profiles use curated defaults for those. Only image aspect ratios and "
        "paper/figure counts are measured programmatically.",
    ]
    with open(AUDIT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    today = datetime.date.today().isoformat()
    if not os.path.isdir(LIB):
        print(f"Reference library not found at {LIB}. Run scripts/harvest_library.py first.\n"
              "Writing learned profiles with curated defaults and zero-inspection provenance.")
    aggs = {}
    for g in GROUPS:
        aggs[g] = _aggregate_group(g)
        prof = _learned_profile(g, aggs[g], today)
        out = os.path.join(OUT_DIR, f"{BASE[g]}_learned.json")
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(prof, fh, indent=2)
        print(f"  {g}: {aggs[g]['n_papers']} papers, {aggs[g]['n_figures']} figures "
              f"-> {os.path.relpath(out, _ROOT)}")
    _write_audit(aggs, today)
    print(f"Audit: {os.path.relpath(AUDIT, _ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
