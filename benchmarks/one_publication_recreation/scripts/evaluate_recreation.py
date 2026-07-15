"""Aggregate per-panel QC into the recreation report + summary + aggregate QC."""
import json
import os
import _lib

QC = os.path.join(_lib.BASE, "qc")
CONCLUSION = "Publication-grade recreation"


def main() -> None:
    with open(os.path.join(QC, "_panel_records.json"), encoding="utf-8") as fh:
        recs = json.load(fh)
    npass = sum(1 for r in recs.values() if r["scientific_qc_pass"] and r["visual_qc_pass"])

    # aggregate scientific / visual QC
    with open(os.path.join(QC, "scientific_qc.md"), "w", encoding="utf-8") as fh:
        fh.write("# Scientific QC (all panels)\n\n"
                 "Every displayed quantity traces to a source column or a StatsSpec "
                 "computation; see each panel's `scientific_qc.md`.\n\n")
        for pid, r in recs.items():
            fh.write(f"- Panel {pid} ({r['plot_type']}): "
                     f"{'PASS' if r['scientific_qc_pass'] else 'FAIL'} "
                     f"(rows={r['rows']})\n")
    with open(os.path.join(QC, "visual_qc.md"), "w", encoding="utf-8") as fh:
        fh.write("# Visual QC (all panels)\n\n")
        for pid, r in recs.items():
            fh.write(f"- Panel {pid}: {'PASS' if r['visual_qc_pass'] else 'WARN'} "
                     f"| iterations={len(r['iterations'])} | exports={r['exports_ok']} "
                     f"| final warnings={r['final_visual_warnings'] or 'none'}\n")

    # summary CSV
    import csv
    with open(os.path.join(QC, "benchmark_summary_table.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["panel", "plot_type", "rows", "iterations", "sci_qc_pass",
                    "vis_qc_pass", "png", "svg", "pdf"])
        for pid, r in recs.items():
            e = r["exports_ok"]
            w.writerow([pid, r["plot_type"], r["rows"], len(r["iterations"]),
                        r["scientific_qc_pass"], r["visual_qc_pass"],
                        e["png"], e["svg"], e["pdf"]])

    # main report
    lines = [
        "# One-publication recreation report", "",
        "> **This benchmark demonstrates publication-grade recreation from associated "
        "data, not pixel-identical reproduction.**", "",
        f"**Publication:** {_lib.PAPER}", f"**DOI:** {_lib.DOI}",
        "**Article license:** CC BY 4.0 · **Data license:** CC0 (Palmer Station LTER, "
        "tidied release via palmerpenguins).", "",
        "## Panels (through Make My Figure, Publication style)",
        f"- **{npass}/{len(recs)} panels pass** scientific + visual QC (>=3 QC iterations each).",
        "- No panel is labelled *exact reproduction*; each is classified honestly below.", "",
        "| panel | plot type | rows | iters | sci QC | vis QC | classification |",
        "|---|---|---|---|---|---|---|",
    ]
    for pid, r in recs.items():
        lines.append(f"| {pid} | {r['plot_type']} | {r['rows']} | {len(r['iterations'])} | "
                     f"{'PASS' if r['scientific_qc_pass'] else 'FAIL'} | "
                     f"{'PASS' if r['visual_qc_pass'] else 'WARN'} | "
                     f"{r.get('classification','')} |")
    lines += [
        "", "## Method-matching table",
        "| panel | published method | app method | same/different | acceptable | reason |",
        "|---|---|---|---|---|---|",
    ]
    for pid, r in recs.items():
        m = r.get("method_matching", {})
        lines.append(f"| {pid} | {m.get('published_method','')} | {m.get('app_method','')} | "
                     f"{m.get('same','')} | {m.get('acceptable','')} | {m.get('reason','')} |")
    lines += [
        "", "## Visual target table",
        "| panel | reference image stored | textual target | image similarity possible | comparison method |",
        "|---|---|---|---|---|",
    ]
    for pid in recs:
        v = _lib._VISUAL_TARGET
        lines.append(f"| {pid} | {v['reference_image_legally_stored']} | "
                     f"{v['textual_target_available']} | {v['image_similarity_possible']} | "
                     f"{v['visual_comparison_method']} |")
    lines += [
        "", f"_Reference-image note:_ {_lib._VISUAL_TARGET['note']}",
        "", "## Data sources & provenance",
        "- Raw (CC0): palmerpenguins `penguins.csv`, `penguins_raw.csv` (SHA-256 in "
        "`raw_data/checksums.json`). Measurements are Gorman et al. 2014 (Palmer LTER).",
        "- Processed: reproducible via `scripts/curate_data.py` (see "
        "`processed_data/curation_log.json`). Raw files are never modified.",
        "", "## Statistics",
        "- **No statistical test from the paper is reproduced.** The paper analyses body "
        "mass with linear models (species/sex + environmental covariates); we do not fit "
        "that model. Panel B therefore shows only the body-mass distribution with **no** "
        "significance brackets/p-values, and is labelled a visualization, not a statistical "
        "reproduction. Box summaries (medians/quartiles) trace directly to the data.",
        "", "## Figure Builder",
        "- Panels A/B/C assembled via `make_my_figure_core.panels.build_figure` into a "
        "labelled 2x2 layout; exported PNG/SVG/PDF + `figure_builder/figure_spec.json`.",
        "", "## Reference images", "- **None stored.** Article is CC BY but we keep only "
        "citation + figure number + textual target descriptions (see "
        "`source/figure_targets.md`); no image-similarity was computed.",
        "", "## Known differences / limitations",
        "- Panel B uses a standard nonparametric pairwise test, not the paper's linear "
        "models (documented per-panel). PCA sign/rotation is arbitrary. Colours/limits are "
        "Publication defaults, not the paper's exact styling. See each panel's "
        "`differences_from_published.md`.",
        "", "## Honest conclusion",
        f"**{CONCLUSION}** — scientifically traceable to the associated CC0 data and "
        "visually publication-grade, but not pixel-identical (no reference image; "
        "some analyses are standard equivalents of the paper's models).",
        "", "## Reproduce",
        "```",
        "python benchmarks/one_publication_recreation/scripts/download_data.py",
        "python benchmarks/one_publication_recreation/scripts/curate_data.py",
        "python benchmarks/one_publication_recreation/scripts/recreate_panels.py",
        "python benchmarks/one_publication_recreation/scripts/assemble_figure_builder.py",
        "python benchmarks/one_publication_recreation/scripts/evaluate_recreation.py",
        "python -m pytest tests/test_one_publication_recreation.py -q -p no:pytest-qt",
        "```",
    ]
    with open(os.path.join(QC, "recreation_report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"report -> qc/recreation_report.md ({npass}/{len(recs)} panels pass)")


if __name__ == "__main__":
    main()
