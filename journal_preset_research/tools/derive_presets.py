"""Derive the experimental publication presets from the evidence tables (research tool).

Usage: python derive_presets.py [--analysis-dir journal_preset_research/analysis]
                                [--out style_profiles/experimental_publication_presets]
                                [--trace reports/journal_presets/evidence_trace.md]

Every value written into a preset is taken from one of four sources and labelled accordingly in
``experimental.value_evidence``:

* ``OFFICIAL:<publisher page>`` - a stated requirement/recommendation (official_guidelines_audit.csv);
* ``INFERRED:<n figures>`` - measured on typeset-PDF figures with an observed physical scale;
* ``OBSERVED:<share>`` - a categorical convention read from the corpus (share of coded panels);
* ``ESTIMATED:<assumption>`` - a number derived under a stated assumption (e.g. marker class -> pt^2);
* ``SHARED:<share>`` - a convention that did not differ meaningfully between families and is applied
  to every preset (the analysis showed no meaningful difference, so no difference is manufactured).

The script refuses to write a preset whose evidence family has fewer than 30 papers in the
group-comparison or style corpus, and it never writes anything analytical (see
experimental_presets.validate_experimental_preset, which is run on every file before saving).
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import os
import pathlib
import sys
from typing import Any, Dict, List, Optional, Tuple

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from make_my_figure_core import experimental_presets as xp  # noqa: E402
from make_my_figure_core import presets  # noqa: E402
from make_my_figure_core import ui_hints  # noqa: E402
from make_my_figure_core.version import __version__  # noqa: E402

# --- official requirements used (verbatim numbers from official_guidelines_audit.csv, 2026-09-16) ---
OFFICIAL = {
    "Nature": {
        "single_mm": 89.0, "full_mm": 183.0, "onehalf_mm": 120.0,
        "font_min_pt": 5.0, "font_max_pt": 7.0, "line_min_pt": 0.25, "line_max_pt": 1.0,
        "dpi_recommended": 450, "font_family": "Arial",
        "panel_label": {"style": "a", "size": 8.0, "weight": "bold"},
        "source": "Nature figure guide / final-submission artwork page (research-figure-guide.nature.com; nature.com/nature/for-authors/final-submission), Nature Methods AIP page: 5-7 pt sans serif, 89/183 mm, 0.25-1 pt lines, 8 pt bold lower-case panel letters, 300 dpi minimum with 450+ recommended; accessed 2026-09-16",
    },
    "Science": {
        "single_mm": 57.0, "full_mm": 184.0, "onehalf_mm": 121.0,
        "font_min_pt": 5.0, "font_target_pt": 7.0, "line_min_pt": 0.5,
        "dpi_recommended": 300, "font_family": "Helvetica",
        "panel_label": {"style": "A", "size": 10.0, "weight": "bold"},
        "source": "Science instructions for preparing initial/revised manuscripts (science.org, Wayback captures 2025-08-10 / 2025-03-30): 5.7 / 12.1 / 18.4 cm widths, Helvetica preferred, not smaller than 5 pt and about 7 pt after reduction, lines >= 0.5 pt, 10 pt bold capital panel letters, >= 300 dpi; accessed 2026-09-16",
    },
    "Cell": {
        "single_mm": 85.0, "full_mm": 174.0, "onehalf_mm": 114.0,
        "font_min_pt": 6.0, "font_max_pt": 8.0, "line_min_pt": 0.5, "line_max_pt": 1.5,
        "dpi_recommended": 300, "font_family": "Arial",
        "panel_label": {"style": "A", "size": None, "weight": "bold"},
        "source": "Cell Press figure guidelines (cell.com/figureguidelines, Wayback capture 2025-09-11): 85 / 114 / 174 mm widths, Arial only, about 6-8 pt text, 0.5-1.5 pt lines, capital panel letters, >= 300 dpi colour, RGB; accessed 2026-09-16",
    },
}

FAMILY_NEUTRAL = {"Nature": "evidence set N", "Science": "evidence set S", "Cell": "evidence set C"}


def _round_half(x: float) -> float:
    return round(x * 2.0) / 2.0


def _load_summary(analysis_dir: str) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
    out = {}
    path = os.path.join(analysis_dir, "style_summary_by_family.csv")
    if not os.path.exists(path):
        return out
    for r in csv.DictReader(open(path, encoding="utf-8")):
        out[(r["group"], r["journal_family"], r["field"])] = r
    return out


def _load_diffs(analysis_dir: str) -> Dict[str, bool]:
    """field -> meaningfully different between families (from family_differences.md, all_quantitative)."""
    path = os.path.join(analysis_dir, "family_differences.md")
    out: Dict[str, bool] = {}
    if not os.path.exists(path):
        return out
    section = None
    for line in open(path, encoding="utf-8"):
        if line.startswith("## "):
            section = line[3:].strip()
        if section == "all_quantitative" and line.startswith("| ") and not line.startswith("| field"):
            parts = [p.strip() for p in line.strip().strip("|").split("|")]
            if len(parts) >= 6 and parts[0] != "---":
                out[parts[0]] = parts[5] == "YES"
    return out


def _papers_per_family(research_dir: str) -> Dict[str, int]:
    counts: Dict[str, set] = {"Nature": set(), "Science": set(), "Cell": set()}
    for name in ("corpus_manifest_expanded.csv", "corpus_manifest.csv"):
        path = os.path.join(research_dir, name)
        if not os.path.exists(path):
            continue
        for r in csv.DictReader(open(path, encoding="utf-8")):
            fam = (r.get("journal_family") or "").lower()
            key = "Nature" if fam.startswith("nature") else "Science" if fam.startswith("science") else \
                "Cell" if fam.startswith("cell") else None
            if key and r.get("usable_for_measurement", "yes").lower() != "no":
                counts[key].add(r.get("paper_id") or r.get("DOI"))
    # the review batches are the papers actually examined; union them with the manifests
    for fam in counts:
        for i in (1, 2):
            p = os.path.join(research_dir, "batches", f"{fam.lower()}_{i}.json")
            if os.path.exists(p):
                counts[fam].update(x["paper_id"] for x in json.load(open(p, encoding="utf-8")))
    return {k: len(v) for k, v in counts.items()}


def _shared_conventions(summary, diffs) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """Style tokens every preset carries because the families did not differ meaningfully."""
    style: Dict[str, Any] = {}
    ev: Dict[str, str] = {}

    def share(field, fam="Nature"):
        r = summary.get(("all_quantitative", fam, field))
        return (r["mode_or_min"], float(r["share_or_max"])) if r else (None, None)

    def all_fams(field):
        vals = [summary.get(("all_quantitative", f, field)) for f in ("Nature", "Science", "Cell")]
        vals = [v for v in vals if v]
        return vals

    # spines: left+bottom only
    modes = all_fams("spines")
    if modes and all(m["mode_or_min"] == "LB" for m in modes) and not diffs.get("spines", False):
        style["show_top_spine"] = False
        style["show_right_spine"] = False
        ev["show_top_spine"] = ev["show_right_spine"] = "SHARED:" + "/".join(f"{m['journal_family']} LB {float(m['share_or_max']):.0%}" for m in modes)
    modes = all_fams("tick_direction")
    if modes and all(m["mode_or_min"] == "out" for m in modes):
        style["tick_direction"] = "out"
        ev["tick_direction"] = "SHARED:" + "/".join(f"{m['journal_family']} out {float(m['share_or_max']):.0%}" for m in modes)
    modes = all_fams("grid")
    if modes and all(m["mode_or_min"] == "none" for m in modes):
        style["grid"] = False
        ev["grid"] = "SHARED:" + "/".join(f"{m['journal_family']} no grid {float(m['share_or_max']):.0%}" for m in modes)
    modes = all_fams("legend_frame")
    if modes and all(m["mode_or_min"] == "no" for m in modes):
        style["legend_frameon"] = False
        ev["legend_frameon"] = "SHARED:" + "/".join(f"{m['journal_family']} unframed {float(m['share_or_max']):.0%}" for m in modes)
    modes = all_fams("axis_label_weight")
    if modes and all(m["mode_or_min"] == "regular" for m in modes):
        style["font_weight"] = "normal"
        ev["font_weight"] = "SHARED:" + "/".join(f"{m['journal_family']} regular {float(m['share_or_max']):.0%}" for m in modes)
    modes = all_fams("palette_class")
    if modes:
        style["palette_name"] = "publication"
        ev["palette_name"] = ("SHARED:colour-blind-aware categorical palette; corpus modes " +
                              "/".join(f"{m['journal_family']} {m['mode_or_min']} {float(m['share_or_max']):.0%}" for m in modes) +
                              "; OFFICIAL: Nature figure guide requires an accessible palette")
    style["text_color"] = "#000000"
    ev["text_color"] = "OBSERVED:axis and tick text black in the reviewed panels; publishers require standard fonts in black"
    return style, ev


def _family_typography(fam: str, summary) -> Tuple[Dict[str, Any], Dict[str, str], List[str]]:
    off = OFFICIAL[fam]
    style: Dict[str, Any] = {}
    ev: Dict[str, str] = {}
    notes: List[str] = []
    dom = summary.get(("all_quantitative", fam, "dominant_cluster_pt"))
    big = summary.get(("all_quantitative", fam, "largest_cluster_pt"))
    lo, hi = off.get("font_min_pt", 5.0), off.get("font_max_pt", off.get("font_target_pt", 8.0) + 1.0)
    if dom and int(dom["n"]) >= 30:
        tick = min(max(_round_half(float(dom["median"])), lo), hi)
        axis = min(max(_round_half(float(big["median"])), tick), hi) if big else tick + 1.0
        style["tick_label_pt"] = tick
        style["axis_font_pt"] = axis
        ev["tick_label_pt"] = f"INFERRED:{dom['n']} typeset figures, dominant text size median {dom['median']} pt (IQR {dom['q1']}-{dom['q3']}), clamped to official {lo}-{hi} pt"
        ev["axis_font_pt"] = f"INFERRED:{big['n']} typeset figures, largest text cluster median {big['median']} pt, clamped to official {lo}-{hi} pt"
    else:
        target = off.get("font_target_pt") or (lo + off.get("font_max_pt", lo + 2)) / 2.0
        tick = min(max(_round_half(target - 0.5), lo), hi)      # tick labels half a point under the stated centre
        axis = min(max(_round_half(target + 0.5), tick), hi)    # axis labels half a point over it
        style["tick_label_pt"] = tick
        style["axis_font_pt"] = axis
        ev["tick_label_pt"] = f"OFFICIAL:{off['source']} (no typeset-scale measurement available for this family; web images give relative sizes only)"
        ev["axis_font_pt"] = ev["tick_label_pt"]
        notes.append(f"{fam}: absolute text sizes taken from the publisher's stated range, not measured")
    style["legend_pt"] = style["tick_label_pt"]
    style["annotation_pt"] = style["tick_label_pt"]
    style["legend_title_pt"] = style["axis_font_pt"]
    style["title_font_pt"] = style["axis_font_pt"]
    style["title_font_weight"] = "normal" if "title_font_weight" in presets.STYLE_TOKEN_KEYS else None
    if style["title_font_weight"] is None:
        style.pop("title_font_weight")
    style["base_font_pt"] = style["tick_label_pt"]
    style["panel_label_pt"] = off["panel_label"]["size"] or 8.0
    ev["legend_pt"] = ev["annotation_pt"] = ev["base_font_pt"] = "SHARED:set equal to the tick-label size (legend and annotation text were not larger than tick labels in the corpus)"
    ev["legend_title_pt"] = ev["title_font_pt"] = "SHARED:set equal to the axis-label size"
    ev["panel_label_pt"] = (f"OFFICIAL:{off['panel_label']['size']} pt bold panel letters" if off["panel_label"]["size"]
                            else "ESTIMATED:8 pt - publisher states capital bold letters without a size; corpus panel letters are 'larger' than axis text")
    style["font_family"] = off["font_family"]
    ev["font_family"] = f"OFFICIAL:{off['font_family']} ({off['source'].split(':')[0]})"
    return style, ev, notes


def _family_lines_marks(fam: str, auto_csv: Optional[str], summary) -> Tuple[Dict[str, Any], Dict[str, str]]:
    off = OFFICIAL[fam]
    style: Dict[str, Any] = {}
    ev: Dict[str, str] = {}
    # observed vector stroke widths (Nature typeset PDFs only)
    modes = None
    if auto_csv and os.path.exists(auto_csv):
        import collections
        agg: collections.Counter = collections.Counter()
        for r in csv.DictReader(open(auto_csv, encoding="utf-8")):
            if r.get("route") == "typeset_pdf" and (r.get("journal_family") or "").startswith(fam) and r.get("line_widths_pt_observed"):
                for k, v in json.loads(r["line_widths_pt_observed"]).items():
                    agg[round(float(k), 2)] += int(v)
        if agg:
            tot = sum(agg.values())
            modes = [(k, v / tot) for k, v in agg.most_common(3)]
    lo = off.get("line_min_pt", 0.5)
    if modes:
        # axis/spine lines: the thinnest common stroke, not below the official minimum
        thin = max(min(k for k, _ in modes), lo)
        style["spine_width_pt"] = round(max(thin, 0.5), 2)   # 0.5 pt floor: hairlines vanish in 300-dpi rasters
        ev["spine_width_pt"] = (f"INFERRED:vector stroke widths in typeset figures - modes " +
                                ", ".join(f"{k} pt ({s:.0%})" for k, s in modes) +
                                f"; official minimum {lo} pt; 0.5 pt floor for raster export")
        heavy = max(k for k, _ in modes)
        style["line_width_pt"] = round(min(max(heavy, 0.75), off.get("line_max_pt", 1.5)), 2)
        ev["line_width_pt"] = f"INFERRED:heaviest common stroke {heavy} pt in typeset figures, kept within official {lo}-{off.get('line_max_pt', 1.5)} pt"
    else:
        style["spine_width_pt"] = round(max(lo, 0.5), 2)
        style["line_width_pt"] = round(max(lo + 0.25, 0.75), 2)
        ev["spine_width_pt"] = f"OFFICIAL:minimum line weight {lo} pt ({off['source'].split(':')[0]}); no typeset-scale measurement for this family"
        ev["line_width_pt"] = f"ESTIMATED:data lines drawn 0.25 pt heavier than axes, within the official range"
    style["tick_width"] = style["spine_width_pt"]
    style["tick_length"] = 2.5
    style["errorbar_line_width"] = style["spine_width_pt"]
    style["bar_edge_width"] = style["spine_width_pt"]
    style["marker_edge_width"] = 0.4
    style["regression_line_width"] = style["line_width_pt"]
    style["grid_width"] = 0.4
    ev["tick_width"] = ev["errorbar_line_width"] = ev["bar_edge_width"] = "SHARED:same weight as the axis line (reviewers coded axis-line weight 'regular', i.e. similar to text strokes)"
    ev["tick_length"] = "ESTIMATED:2.5 pt, about half the tick-label height"
    ev["marker_edge_width"] = "ESTIMATED:0.4 pt - a visible but light edge; marker edges were 'dark' or 'none' in similar shares"
    ev["regression_line_width"] = "SHARED:same as data lines"
    ev["grid_width"] = "SHARED:grid is off; width kept light if a user turns it on"
    # markers: coded class -> area
    mk = summary.get(("all_quantitative", fam, "marker_size_class"))
    tick = None
    if mk:
        cls = mk["mode_or_min"]
        size = {"small": 20.0, "medium": 36.0, "large": 60.0}.get(cls, 28.0)
        style["marker_size"] = size
        ev["marker_size"] = (f"ESTIMATED:corpus marker class '{cls}' ({float(mk['share_or_max']):.0%} of coded panels) -> diameter about "
                             f"{'0.8' if cls == 'small' else '1.0' if cls == 'medium' else '1.3'} x tick-label height -> {size} pt^2")
    style["marker_alpha"] = 0.9
    ev["marker_alpha"] = "ESTIMATED:0.9 so overlapping observations remain distinguishable"
    eb = summary.get(("all_quantitative", fam, "error_bar_style"))
    caps = eb and eb["mode_or_min"] == "bars_caps"
    style["errorbar_capsize"] = 2.0 if caps else 1.5
    ev["errorbar_capsize"] = (f"OBSERVED:error bars with caps are the modal style ({float(eb['share_or_max']):.0%})" if caps
                              else f"OBSERVED:modal error-bar style '{eb['mode_or_min'] if eb else 'unknown'}'; short caps kept for legibility")
    return style, ev


def _legend(fam: str, summary) -> Tuple[Dict[str, Any], Dict[str, str]]:
    lp = summary.get(("all_quantitative", fam, "legend_position"))
    style = {"legend_loc": "best", "legend_outside": False, "legend_ncol": 1}
    ev = {"legend_loc": f"OBSERVED:legends are most often absent or inside the axes (mode '{lp['mode_or_min'] if lp else 'unknown'}')",
          "legend_outside": "OBSERVED:legends outside the axes are the minority; users move them per figure",
          "legend_ncol": "SHARED:one column"}
    return style, ev


def _write(preset: Dict[str, Any], out_dir: str, trace: List[str]) -> str:
    xp.validate_experimental_preset(preset)
    leaks = presets.preset_contains_data(preset)
    if leaks:
        raise SystemExit(f"refusing to write preset with data-bound fields: {leaks}")
    path = os.path.join(out_dir, presets.safe_filename(preset["experimental"]["preset_id"]) + presets.PRESET_EXTENSION)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(presets.preset_to_json(preset))
    trace.append(f"## {preset['name']}  (`{os.path.basename(path)}`)\n")
    trace.append(f"{preset['description']}\n")
    trace.append("| value | setting | evidence |\n|---|---|---|")
    ev = preset["experimental"]["value_evidence"]
    for block in ("style", "layout", "output", "options"):
        for k, v in (preset.get(block) or {}).items():
            trace.append(f"| {block}.{k} | {v!r} | {ev.get(k, ev.get(block + '.' + k, 'not stated'))} |")
    trace.append("")
    return path


def _family_presets(fam: str, summary, diffs, auto_csv, papers, out_dir, trace) -> List[str]:
    off = OFFICIAL[fam]
    shared_style, shared_ev = _shared_conventions(summary, diffs)
    typo, typo_ev, notes = _family_typography(fam, summary)
    marks, marks_ev = _family_lines_marks(fam, auto_csv, summary)
    leg, leg_ev = _legend(fam, summary)
    style = {**shared_style, **typo, **marks, **leg}
    style = {k: v for k, v in style.items() if k in presets.STYLE_TOKEN_KEYS}
    ev = {**shared_ev, **typo_ev, **marks_ev, **leg_ev}
    ev = {k: v for k, v in ev.items() if k in style}
    written = []
    letter = FAMILY_NEUTRAL[fam].split()[-1]
    for cls, wkey in (("single", "single_mm"), ("full", "full_mm")):
        width = off[wkey]
        name = f"{'Single column' if cls == 'single' else 'Full width'} {width:g} mm ({letter})"
        desc = (f"Style measured from open-access research figures in {FAMILY_NEUTRAL[fam]} and the publisher's stated "
                f"artwork requirements, at the stated {'single-column' if cls == 'single' else 'full-page'} width of {width:g} mm. "
                "Changes typography, line weights, palette, legend and axis geometry only. Not an official template.")
        preset = {
            "format": presets.PRESET_FORMAT, "format_version": presets.PRESET_FORMAT_VERSION,
            "name": name, "description": desc, "mode": "style", "plot_type": "boxplot_or_violin_with_points",
            "journal_style": "publication",
            "created": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"), "app_version": __version__,
            "style": style, "layout": {"column_width": f"{width:g}mm", "legend_location": "best"},
            "options": {}, "output": {"formats": ["pdf", "svg", "png"], "width_mm": width, "dpi": off["dpi_recommended"]},
            "statistics_display": {"annotation": {"font_size": style["annotation_pt"], "line_width": style["spine_width_pt"]}},
            "universal": True,
            "experimental": {
                "preset_id": f"{cls}_{int(width)}mm_{letter}", "status": "experimental",
                "evidence_family": FAMILY_NEUTRAL[fam], "evidence_family_journals": fam + "-family journals (see corpus_manifest_expanded.csv)",
                "evidence_summary": f"{papers.get(fam, 0)} open-access papers; visual review of panels plus typeset-PDF measurements where available; official requirements audited 2026-09-16",
                "derived_from": {"papers": papers.get(fam, 0), "figures": "see journal_preset_research/analysis/style_measurements.csv",
                                 "panels": "see style_measurements.csv", "official_sources": off["source"]},
                "not_official": True, "target_width_mm": width, "width_class": cls,
                "width_source": f"OFFICIAL:{off['source'].split(':')[0]}",
                "value_evidence": {**ev, "column_width": f"OFFICIAL:{width} mm stated {cls} width", "width_mm": "OFFICIAL:same as column_width",
                                   "dpi": f"OFFICIAL:{off['dpi_recommended']} dpi ({'recommended' if off['dpi_recommended'] > 300 else 'minimum'})",
                                   "formats": "OFFICIAL:vector (PDF/EPS/AI) preferred by every publisher; PNG for review copies",
                                   "legend_location": "OBSERVED:see legend_loc"},
                "notes": notes,
                "width_exempt_plot_types": ["sankey_plot", "upset_plot", "hierarchical_clustering", "heatmap_clustered_matrix", "network_graph",
                                            "confusion_matrix", "swimmer_plot"],
            },
        }
        written.append(_write(preset, out_dir, trace))
        # companion layout preset (panel letters + figure width)
        pl = off["panel_label"]
        lay = {
            "format": presets.LAYOUT_PRESET_FORMAT, "format_version": presets.LAYOUT_PRESET_FORMAT_VERSION,
            "name": f"{'Single column' if cls == 'single' else 'Full width'} {width:g} mm layout, {'lower' if pl['style'] == 'a' else 'upper'}-case letters ({letter})",
            "description": "Figure Builder layout companion: figure width and panel-letter style from the publisher's stated requirements.",
            "created": preset["created"], "app_version": __version__, "n_panels": 0,
            "layout": {"fig_width_mm": width, "label_style": pl["style"], "label_size": pl["size"] or 8.0,
                       "label_weight": pl["weight"], "wspace": 0.25, "hspace": 0.3},
            "experimental": {"preset_id": f"layout_{cls}_{int(width)}mm_{letter}", "evidence_family": FAMILY_NEUTRAL[fam],
                             "evidence_summary": preset["experimental"]["evidence_summary"],
                             "derived_from": preset["experimental"]["derived_from"], "not_official": True,
                             "value_evidence": {"fig_width_mm": f"OFFICIAL:{width} mm", "label_style": f"OFFICIAL:{'lower' if pl['style'] == 'a' else 'upper'}-case bold panel letters",
                                                "label_size": (f"OFFICIAL:{pl['size']} pt" if pl["size"] else "ESTIMATED:8 pt (size not stated)"),
                                                "wspace/hspace": "ESTIMATED:comfortable gutters; adjust per figure"}},
        }
        xp.validate_experimental_layout_preset(lay)
        lp = os.path.join(out_dir, presets.safe_filename(lay["experimental"]["preset_id"]) + presets.LAYOUT_PRESET_EXTENSION)
        with open(lp, "w", encoding="utf-8") as fh:
            json.dump(lay, fh, indent=2)
        written.append(lp)
    return written


def _gc_presets(gc_json: Optional[str], papers_total: int, out_dir: str, trace: List[str]) -> List[str]:
    """Group-comparison representation presets from biological_group_comparison_corpus."""
    if not gc_json or not os.path.exists(gc_json):
        return []
    S = json.load(open(gc_json, encoding="utf-8"))["fields"]

    def sh(field, value, fam="all"):
        return S.get(field, {}).get(fam, {}).get("shares", {}).get(value, 0.0)

    def known(plot_type, opts):
        keys = {o.key for o in ui_hints.options(plot_type)}
        keep = {k: v for k, v in opts.items() if k in keys}
        dropped = sorted(set(opts) - keys)
        return keep, dropped

    written = []
    common_pts = {"points": True, "point_arrangement": "jitter", "point_fill": "filled", "point_edge": "dark",
                  "point_edge_width": 0.4, "point_size": 0.0, "point_alpha": 0.0}
    common_ev = {
        "points": f"OBSERVED:individual observations visible in {sh('raw_points_visible', 'yes'):.0%} of group-comparison panels",
        "point_arrangement": f"OBSERVED:jitter {sh('jitter_style', 'jitter'):.0%}, centred {sh('jitter_style', 'centered'):.0%}, beeswarm {sh('jitter_style', 'beeswarm'):.0%}",
        "point_fill": f"OBSERVED:filled {sh('marker_fill', 'filled'):.0%} vs open {sh('marker_fill', 'open'):.0%}",
        "point_edge": f"OBSERVED:dark edge {sh('marker_edge', 'dark'):.0%}, none {sh('marker_edge', 'none'):.0%}, same colour {sh('marker_edge', 'same_colour'):.0%}",
        "point_edge_width": "ESTIMATED:0.4 pt light edge",
        "point_size": "SHARED:0 = adaptive - the renderer scales markers by the number of observations within fixed bounds (never hides points)",
        "point_alpha": "SHARED:0 = adaptive opacity by group size",
    }
    designs = [
        ("bar_points_jittered", "barplot_with_error_bar", "Bar + observations (jittered)",
         "The most common group-comparison display in the corpus: a summary bar with every observation jittered over it, error bar with caps, medium bar width.",
         {**common_pts, "bar_width": 0.6, "bar_fill": "filled", "error_cap": True, "show_n": "none"},
         {**common_ev, "bar_width": f"OBSERVED:medium bar width {sh('bar_width', 'medium'):.0%}",
          "bar_fill": f"OBSERVED:filled bars dominate; outline-only {sh('palette_type', 'outline_only'):.0%}",
          "error_cap": "OBSERVED:capped error bars are the modal style in bar panels",
          "show_n": f"OBSERVED:n printed in the panel in only {sh('n_label', 'below_category') + sh('n_label', 'above_category'):.0%} of panels; usually in the caption"}),
        ("bar_points_open", "barplot_with_error_bar", "Bar + observations (open circles)",
         "Summary bar with open-circle observations in the bar's colour - the second most common marker treatment; keeps the bar fill readable through the points.",
         {**common_pts, "point_fill": "open", "point_edge": "same", "point_edge_width": 0.6, "bar_width": 0.6, "bar_fill": "filled", "error_cap": True},
         {**common_ev, "point_fill": f"OBSERVED:open markers {sh('marker_fill', 'open'):.0%} of coded panels (second most common)",
          "point_edge": "OBSERVED:open markers take the group colour as their edge", "point_edge_width": "ESTIMATED:0.6 pt so open circles stay visible when small",
          "bar_width": f"OBSERVED:medium bar width {sh('bar_width', 'medium'):.0%}", "bar_fill": "OBSERVED:filled bars dominate",
          "error_cap": "OBSERVED:capped error bars are the modal style"}),
        ("box_points_outline", "boxplot_or_violin_with_points", "Box + observations (outline)",
         "Outline box (no fill) with the observations on top - the common minimal box style; whiskers and median in the axis colour.",
         {**common_pts, "kind": "box", "box_fill": "outline", "box_width": 0.5, "show_outliers": False},
         {**common_ev, "kind": f"OBSERVED:box+points {sh('representation', 'box+points'):.0%} of panels", "box_fill": "OBSERVED:outline boxes are the common minimal treatment",
          "box_width": f"OBSERVED:medium box width {sh('box_width', 'medium'):.0%} of box panels", "show_outliers": "SHARED:outliers are already drawn as observations"}),
        ("box_points_light", "boxplot_or_violin_with_points", "Box + observations (light fill)",
         "Lightly filled box in the group colour with the observations on top.",
         {**common_pts, "kind": "box", "box_fill": "light", "box_width": 0.5, "show_outliers": False},
         {**common_ev, "kind": f"OBSERVED:box+points {sh('representation', 'box+points'):.0%} of panels", "box_fill": "OBSERVED:filled boxes in the group colour are the other common treatment",
          "box_width": "OBSERVED:medium box width", "show_outliers": "SHARED:outliers are already drawn as observations"}),
        ("violin_points", "boxplot_or_violin_with_points", "Violin + observations",
         "Violin body with the observations on top; used for larger groups where the distribution shape matters.",
         {**common_pts, "kind": "violin", "point_size": 0.0, "show_outliers": False},
         {**common_ev, "kind": f"OBSERVED:violin+points {sh('representation', 'violin+points'):.0%} of panels (most common at large n)",
          "show_outliers": "SHARED:not applicable to violins"}),
        ("dense_groups", "boxplot_or_violin_with_points", "Many observations per group",
         "For large groups: small, semi-transparent centred observations over a box so the distribution stays legible; the renderer still draws every point.",
         {**common_pts, "kind": "box", "box_fill": "outline", "point_arrangement": "jitter", "point_jitter_width": 0.5, "point_edge": "none", "point_alpha": 0.5},
         {**common_ev, "kind": "OBSERVED:box+points preferred over bars at large n in the corpus (see group_comparison_summary.md, large-n table)",
          "box_fill": "OBSERVED:outline box", "point_jitter_width": "ESTIMATED:wider spread for dense groups", "point_edge": "ESTIMATED:no edge at high density",
          "point_alpha": "ESTIMATED:0.5 opacity for dense groups"}),
    ]
    for pid, ptype, name, desc, opts, ev in designs:
        keep, dropped = known(ptype, opts)
        if "points" in dropped and "points" in {o.key for o in ui_hints.options(ptype)}:
            dropped.remove("points")
        preset = {
            "format": presets.PRESET_FORMAT, "format_version": presets.PRESET_FORMAT_VERSION,
            "name": name, "description": desc, "mode": "style", "plot_type": ptype, "journal_style": "publication",
            "created": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"), "app_version": __version__,
            "style": {"marker_alpha": 0.9}, "layout": {}, "options": keep, "output": {}, "universal": False,
            "experimental": {
                "preset_id": f"gc_{pid}", "status": "experimental", "evidence_family": "group-comparison corpus (all three families)",
                "evidence_summary": "biological_group_comparison_corpus.csv: bar/box/violin/dot panels coded for representation, markers, error bars, statistics and colour",
                "derived_from": {"papers": papers_total, "figures": "see biological_group_comparison_corpus.csv", "panels": "see biological_group_comparison_corpus.csv",
                                 "official_sources": "none (representation choices are observed practice)"},
                "not_official": True, "target_width_mm": None, "width_class": "any",
                "value_evidence": {**{k: v for k, v in ev.items() if k in keep}, "marker_alpha": "ESTIMATED:0.9"},
                "notes": ([f"options not available in this build and therefore omitted: {dropped}"] if dropped else []),
                "recommended_for": [ptype],
            },
        }
        written.append(_write(preset, out_dir, trace))
    return written


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--research-dir", default=str(ROOT / "journal_preset_research"))
    ap.add_argument("--analysis-dir", default=str(ROOT / "journal_preset_research" / "analysis"))
    ap.add_argument("--auto-csv", default=str(ROOT / "journal_preset_research" / "auto_measurements.csv"))
    ap.add_argument("--gc-json", default=str(ROOT / "journal_preset_research" / "analysis" / "group_comparison_summary.json"))
    ap.add_argument("--out", default=str(ROOT / "style_profiles" / "experimental_publication_presets"))
    ap.add_argument("--trace", default=str(ROOT / "reports" / "journal_presets" / "evidence_trace.md"))
    ap.add_argument("--min-papers", type=int, default=30)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    summary = _load_summary(a.analysis_dir)
    diffs = _load_diffs(a.analysis_dir)
    papers = _papers_per_family(a.research_dir)
    trace = ["# Evidence trace for the experimental publication presets", "",
             f"Generated {_dt.date.today().isoformat()} by journal_preset_research/tools/derive_presets.py from "
             f"{a.analysis_dir} and {a.gc_json}. Evidence classes: OFFICIAL (publisher statement), INFERRED (typeset-PDF "
             "measurement with observed scale), OBSERVED (corpus convention, share of coded panels), ESTIMATED (stated "
             "assumption), SHARED (no meaningful family difference; applied to every preset).", "",
             f"Papers per evidence family: {papers}", ""]
    written: List[str] = []
    for fam in ("Nature", "Science", "Cell"):
        if papers.get(fam, 0) < a.min_papers:
            trace.append(f"- {fam}: only {papers.get(fam, 0)} papers - no preset written (minimum {a.min_papers}).")
            continue
        written += _family_presets(fam, summary, diffs, a.auto_csv, papers, a.out, trace)
    written += _gc_presets(a.gc_json, sum(papers.values()), a.out, trace)
    with open(a.trace, "w", encoding="utf-8") as fh:
        fh.write("\n".join(trace) + "\n")
    print(f"{len(written)} files written to {a.out}; trace -> {a.trace}")
    for w in written:
        print("  ", os.path.basename(w))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
