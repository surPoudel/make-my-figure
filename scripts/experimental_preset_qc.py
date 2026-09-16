"""QC every experimental publication preset on every plot type at its target width.

Usage: python scripts/experimental_preset_qc.py [--presets-dir DIR] [--out reports/journal_presets/qc]
                                                 [--plot-types a,b,c] [--min-font-pt 5]

For each preset x plot type: render the bundled synthetic example with the preset applied through
the same guarded path the apps use, then measure the drawn figure (text overlap, clipped
annotations, legend over data, smallest effective font at the target width, exported width versus
target) and run the existing publication-readiness score. Writes:

* qc_matrix.csv - one row per preset x plot type with every metric and PASS / WARN / FAIL;
* previews/<preset>/<plot_type>.png - the rendered figure at export DPI (visual QC);
* README.md - summary counts and the failing cells.

Overlap is never "fixed" here by shrinking text; a failing cell is reported for the preset author.
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

from make_my_figure_core import experimental_presets as xp  # noqa: E402
from make_my_figure_core import preset_preview as pv  # noqa: E402
from make_my_figure_core.plots import registry  # noqa: E402
from make_my_figure_core.plots.registry import available_plot_types  # noqa: E402
from make_my_figure_core.qc.publication_score import score_publication  # noqa: E402
from make_my_figure_core.qc.text_layout_qc import check_text_layout  # noqa: E402

COLUMNS = ["preset_id", "preset_name", "plot_type", "target_width_mm", "status", "n_text",
           "overlapping_text_pairs", "clipped_text", "legend_overlaps_data", "legend_overlap_fraction",
           "min_font_pt", "min_font_role", "effective_min_font_pt", "tight_width_mm", "tight_height_mm",
           "width_deviation_pct", "max_tick_labels_on_one_axis", "publication_score", "publication_level",
           "render_warnings", "issues", "preview_png"]


def qc_cell(preset, plot_type, out_png, *, min_font_pt):
    spec, df, aux = pv.synthetic_spec(plot_type)
    res = pv.apply_with_guard(preset, spec, columns=list(df.columns))
    result = registry.render(res.spec, df, aux=aux)
    target = (preset.get(xp.EXPERIMENTAL_BLOCK) or {}).get("target_width_mm")
    qc = check_text_layout(result.figure, target_width_mm=target, min_font_pt=min_font_pt)
    score = score_publication(result=result, figure=result.figure, spec=res.spec)
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    dpi = int((res.spec.get("output") or {}).get("dpi") or 300)
    with open(out_png, "wb") as fh:
        fh.write(registry.figure_to_bytes(result.figure, "png", dpi=min(dpi, 200)))
    plt.close(result.figure)
    row = {"preset_id": (preset.get(xp.EXPERIMENTAL_BLOCK) or {}).get("preset_id", ""),
           "preset_name": preset.get("name", ""), "plot_type": plot_type,
           "target_width_mm": target, "publication_score": score.score, "publication_level": score.level,
           "render_warnings": " | ".join(w[:80] for w in (result.warnings or [])[:3]),
           "preview_png": os.path.relpath(out_png, ROOT)}
    row.update(qc.as_row())
    hard = qc.n_overlapping_pairs > 0 or qc.n_clipped > 0 or (
        qc.effective_min_font_pt is not None and qc.effective_min_font_pt < min_font_pt - 0.05)
    soft = qc.legend_overlaps_data or (qc.width_deviation_pct is not None and abs(qc.width_deviation_pct) > 15) \
        or score.level == "fail"
    row["status"] = "FAIL" if hard else ("WARN" if soft else "PASS")
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--presets-dir", default=None)
    ap.add_argument("--out", default=str(ROOT / "reports" / "journal_presets" / "qc"))
    ap.add_argument("--plot-types", default="")
    ap.add_argument("--min-font-pt", type=float, default=5.0)
    a = ap.parse_args()
    entries = xp.list_experimental_presets(a.presets_dir)
    if not entries:
        print("no experimental presets found", file=sys.stderr)
        return 1
    pts = [p for p in a.plot_types.split(",") if p] or available_plot_types()
    os.makedirs(a.out, exist_ok=True)
    rows = []
    for e in entries:
        preset = xp.load_experimental_preset(e.path)
        for pt in pts:
            png = os.path.join(a.out, "previews", e.preset_id, f"{pt}.png")
            try:
                row = qc_cell(preset, pt, png, min_font_pt=a.min_font_pt)
            except Exception as exc:  # noqa: BLE001 - a crash is a FAIL, not the end of the run
                row = {c: "" for c in COLUMNS}
                row.update({"preset_id": e.preset_id, "preset_name": e.name, "plot_type": pt,
                            "status": "FAIL", "issues": f"render error: {str(exc)[:160]}"})
            rows.append(row)
            print(e.preset_id, pt, row["status"], row.get("issues", ""), flush=True)
    csv_path = os.path.join(a.out, "qc_matrix.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLUMNS})
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in ("PASS", "WARN", "FAIL")}
    fails = [r for r in rows if r["status"] != "PASS"]
    lines = ["# Experimental preset QC", "",
             f"{len(entries)} presets x {len(pts)} plot types = {len(rows)} cells: "
             f"PASS {counts['PASS']}, WARN {counts['WARN']}, FAIL {counts['FAIL']}.", "",
             "FAIL = overlapping text, clipped annotation, or smallest text below the minimum at the target width. ",
             "WARN = legend over data, exported width off target by more than 15 %, or publication score 'fail'. ",
             "Nothing is auto-fixed; each non-PASS cell is listed for the preset author.", "",
             "| preset | plot type | status | issues |", "|---|---|---|---|"]
    for r in fails:
        lines.append(f"| {r['preset_id']} | {r['plot_type']} | {r['status']} | {r.get('issues', '')} |")
    with open(os.path.join(a.out, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(json.dumps(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
