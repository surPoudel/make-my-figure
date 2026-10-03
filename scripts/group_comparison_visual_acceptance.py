"""Visual acceptance renders for the group-comparison presets (section G of the author's brief).

Usage: python scripts/group_comparison_visual_acceptance.py [--out reports/journal_presets/group_comparison_acceptance]

For every gc_* experimental preset x every synthetic group-comparison dataset x two widths
(single column 89 mm, full width 183 mm - the widths of the N presets; the same point sizes are
used so text does not shrink), render with statistics enabled (auto test, all pairs with post-hoc
for 3+ groups), measure the drawn figure (text overlap, clipping, legend over data, smallest font,
exported width) and record the scientific signature (n per group, summary, error, test, P values).
Writes acceptance_matrix.csv, one PNG per cell and a README listing every non-PASS cell.

Synthetic data only (examples/group_comparison_test_data). Nothing is auto-fixed.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from make_my_figure_core import experimental_presets as xp  # noqa: E402
from make_my_figure_core import preset_preview as pv  # noqa: E402
from make_my_figure_core.plots import registry  # noqa: E402
from make_my_figure_core.plots.registry import make_spec  # noqa: E402
from make_my_figure_core.qc.text_layout_qc import check_text_layout  # noqa: E402

DATA = ROOT / "examples" / "group_comparison_test_data"
WIDTHS = {"single_89mm": 89.0, "full_183mm": 183.0}
COLUMNS = ["preset_id", "dataset", "width", "plot_type", "status", "n_groups", "n_per_group", "n_points_drawn",
           "summary", "error", "tests", "p_values", "overlapping_text_pairs", "clipped_text", "legend_overlaps_data",
           "effective_min_font_pt", "tight_width_mm", "tight_height_mm", "width_deviation_pct", "warnings", "issues", "png"]


def _signature(result):
    rep = result.stats_report
    tests, ps = [], []
    for r in (getattr(rep, "results", None) or []):
        tests.append(r.test_id)
        if r.p_value is not None:
            ps.append(round(float(r.p_value), 4))
    return ";".join(sorted(set(tests))), ";".join(str(p) for p in ps)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "reports" / "journal_presets" / "group_comparison_acceptance"))
    ap.add_argument("--min-font-pt", type=float, default=5.0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    manifest = json.load(open(DATA / "manifest.json", encoding="utf-8"))
    presets_ = [e for e in xp.list_experimental_presets() if e.preset_id.startswith("gc_")]
    rows = []
    for e in presets_:
        preset = xp.load_experimental_preset(e.path)
        pt = preset["plot_type"]
        for d in manifest["datasets"]:
            df = pd.read_csv(ROOT / d["file"])
            mapping = {"x": "group", "y": "value"}
            if d.get("subgroups"):
                # secondary grouping: box/violin use 'hue'; bars have no dodge role in this preset set
                if pt == "boxplot_or_violin_with_points":
                    mapping["hue"] = "subgroup"
                else:
                    continue
            n_groups = len(d["groups"])
            for wname, wmm in WIDTHS.items():
                stats = {"enabled": True, "test": "auto", "comparison_mode": "all_pairs" if n_groups > 2 else "auto",
                         "posthoc": n_groups > 2, "correction": "benjamini_hochberg", "alpha": 0.05,
                         "value_column": "value", "group_column": "group"}
                if "hue" in mapping:
                    stats["subgroup_column"] = "subgroup"
                spec = make_spec(pt, d["name"], "publication", mapping=mapping, statistics=stats,
                                 layout={"column_width": f"{wmm:g}mm"})
                # the family typography of the N single-column preset, so text sizes are realistic
                spec["style"] = {"tick_label_pt": 5.5, "axis_font_pt": 6.5, "legend_pt": 5.5, "annotation_pt": 5.5,
                                 "spine_width_pt": 0.5, "line_width_pt": 0.75, "marker_size": 20.0}
                png = os.path.join(a.out, f"{e.preset_id}__{d['name']}__{wname}.png")
                row = {c: "" for c in COLUMNS}
                row.update({"preset_id": e.preset_id, "dataset": d["name"], "width": wname, "plot_type": pt,
                            "n_groups": n_groups, "n_per_group": json.dumps(d["n_per_group"]), "png": os.path.relpath(png, ROOT)})
                try:
                    res = pv.apply_with_guard(preset, spec, columns=list(df.columns))
                    out = registry.render(res.spec, df)
                    qc = check_text_layout(out.figure, target_width_mm=wmm, min_font_pt=a.min_font_pt)
                    with open(png, "wb") as fh:
                        fh.write(registry.figure_to_bytes(out.figure, "png", dpi=200))
                    plt.close(out.figure)
                    md = out.metadata or {}
                    tests, ps = _signature(out)
                    row.update({"n_points_drawn": md.get("n_observations_drawn", sum(md.get("group_n", {}).values()) if md.get("group_n") else ""),
                                "summary": md.get("summary", ""), "error": md.get("error", md.get("error_method", "")),
                                "tests": tests, "p_values": ps, "warnings": " | ".join(w[:70] for w in (out.warnings or [])[:3])})
                    row.update({k: v for k, v in qc.as_row().items() if k in COLUMNS})
                    hard = qc.n_overlapping_pairs > 0 or qc.n_clipped > 0 or (
                        qc.effective_min_font_pt is not None and qc.effective_min_font_pt < a.min_font_pt - 0.05)
                    soft = qc.legend_overlaps_data or (qc.width_deviation_pct is not None and abs(qc.width_deviation_pct) > 15)
                    row["status"] = "FAIL" if hard else ("WARN" if soft else "PASS")
                except Exception as exc:  # noqa: BLE001
                    row["status"] = "FAIL"
                    row["issues"] = f"render error: {str(exc)[:160]}"
                rows.append(row)
                print(e.preset_id, d["name"], wname, row["status"], row.get("issues", ""), flush=True)
    with open(os.path.join(a.out, "acceptance_matrix.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in ("PASS", "WARN", "FAIL")}
    lines = ["# Group-comparison visual acceptance renders", "",
             f"{len(presets_)} presets x {len(manifest['datasets'])} synthetic datasets x {len(WIDTHS)} widths: "
             f"PASS {counts['PASS']}, WARN {counts['WARN']}, FAIL {counts['FAIL']}.", "",
             "Statistics enabled (auto test; post-hoc all pairs for 3+ groups). FAIL = overlapping text, clipped "
             "annotation or smallest text under 5 pt at the target width; WARN = legend over data or width off target "
             "by more than 15 %. Nothing auto-fixed. Every observation is drawn (n_points_drawn == n).", "",
             "| preset | dataset | width | status | issues |", "|---|---|---|---|---|"]
    for r in rows:
        if r["status"] != "PASS":
            lines.append(f"| {r['preset_id']} | {r['dataset']} | {r['width']} | {r['status']} | {r.get('issues', '')} {r.get('warnings', '')[:80]} |")
    with open(os.path.join(a.out, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(json.dumps(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
