#!/usr/bin/env python
"""Publication-QC gallery: every plot type + the matrix-workflow plots.

Renders each registered plot type from its bundled example, PLUS the matrix
workflow's own plots (heatmap, clustered z-score heatmap, PCA, sample-correlation
heatmap, volcano from a feature-level differential summary, and a selected-feature
violin from wide->long). Each is rendered with the single Publication style,
QC-scored with ``make_my_figure_core.qc.score_publication``, and exported to
PNG/SVG/PDF (non-empty checked). Writes a CSV, a Markdown report, per-plot PNGs,
and a tiled contact sheet.

This is a QA/regression gallery for the app's own renderers — not a claim of any
journal's formatting compliance. The matrix workflow is generic (expression /
protein / metabolite / any numeric feature matrix); it runs no raw-count
differential-expression pipeline and no R.

Outputs (regenerate on demand):
    reports/publication_qc_gallery/qc_summary.csv
    reports/publication_qc_gallery/qc_report.md
    reports/publication_qc_gallery/per_plot/<name>.png
    reports/publication_qc_gallery/contact_sheet.png

Usage:
    python scripts/generate_publication_qc_gallery.py
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import sys
from typing import Any, Dict, List, Optional

import matplotlib

matplotlib.use("Agg")

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

DEFAULT_OUT = os.path.join(_ROOT, "reports", "publication_qc_gallery")


def _export_checks(fig) -> List[str]:
    """Return a list of export problems (empty = all formats produced bytes)."""
    from make_my_figure_core.plots.registry import figure_to_bytes

    problems: List[str] = []
    for fmt in ("png", "svg", "pdf"):
        try:
            if len(figure_to_bytes(fig, fmt)) == 0:
                problems.append(f"empty {fmt}")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{fmt} export error: {exc}")
    return problems


def _score(result, spec) -> Dict[str, Any]:
    from make_my_figure_core.qc import score_publication

    s = score_publication(result=result, spec=spec)
    return {"qc_level": s.level, "qc_score": s.score,
            "warnings": [c.message for c in s.issues()]}


def _record(name, group, result, spec, per_plot_dir) -> Dict[str, Any]:
    import matplotlib.pyplot as plt
    from make_my_figure_core.plots.registry import export_figure

    rec: Dict[str, Any] = {"name": name, "group": group}
    fig = result.figure
    try:
        sc = _score(result, spec)
        rec.update(sc)
        rec["export_problems"] = _export_checks(fig)
        export_figure(fig, os.path.join(per_plot_dir, name), ["png"], dpi=200)
        rec["png"] = os.path.join("per_plot", f"{name}.png")
        rec["status"] = "rendered"
        rec["warnings"] = list(rec.get("warnings", [])) + rec["export_problems"]
    except Exception as exc:  # noqa: BLE001
        rec.update({"status": "error", "qc_level": "error", "qc_score": None,
                    "warnings": [f"{type(exc).__name__}: {exc}"], "png": None,
                    "export_problems": ["render error"]})
    finally:
        plt.close(fig)
    return rec


def _example_plots(per_plot_dir: str) -> List[Dict[str, Any]]:
    from make_my_figure_core.examples import load_example
    from make_my_figure_core.plots.registry import (
        available_plot_types,
        default_mapping,
        make_spec,
        render,
    )

    records: List[Dict[str, Any]] = []
    for pt in available_plot_types():
        try:
            table_info, aux, plotspec = load_example(pt)
            aux_dfs = {n: i.dataframe for n, i in aux.items()}
            spec = dict(plotspec) if plotspec else make_spec(
                pt, table_info.source_name, "publication", mapping=default_mapping(pt))
            spec["journal_style"] = "publication"
            result = render(spec, table_info.dataframe, aux=aux_dfs)
            records.append(_record(pt, "example", result, spec, per_plot_dir))
        except Exception as exc:  # noqa: BLE001
            records.append({"name": pt, "group": "example", "status": "error",
                            "qc_level": "error", "qc_score": None,
                            "warnings": [f"{type(exc).__name__}: {exc}"], "png": None})
    return records


def _matrix_workflow_plots(per_plot_dir: str) -> List[Dict[str, Any]]:
    import make_my_figure_core.matrix_workflow as mw
    from make_my_figure_core.matrix_workflow import transformations as T
    from make_my_figure_core.matrix_workflow.examples import (
        CTRL,
        SAMPLES,
        TREAT,
        build_example_matrix,
    )
    from make_my_figure_core.plots.registry import make_spec, render

    df = build_example_matrix()
    spec = mw.MatrixSpec(feature_id_column="feature_id", feature_display_column="feature_name",
                         annotation_columns=["bioType", "annotationLevel"],
                         value_columns=list(SAMPLES), value_type="log_normalized",
                         confirmed_by_user=True)
    groups = mw.metadata_from_assignment({**{c: "Ctrl" for c in CTRL},
                                          **{t: "Treatment" for t in TREAT}})
    records: List[Dict[str, Any]] = []

    def run(name, plot_type, data, mapping):
        try:
            ps = make_spec(plot_type, "mw.tsv", "publication", mapping=mapping)
            result = render(ps, data)
            records.append(_record(name, "matrix_workflow", result, ps, per_plot_dir))
        except Exception as exc:  # noqa: BLE001
            records.append({"name": name, "group": "matrix_workflow", "status": "error",
                            "qc_level": "error", "qc_score": None,
                            "warnings": [f"{type(exc).__name__}: {exc}"], "png": None})

    run("mw_heatmap", "heatmap_clustered_matrix", df,
        {"row_id": "feature_id", "value_columns": list(SAMPLES)})
    run("mw_heatmap_zscore", "heatmap_clustered_matrix", df,
        {"row_id": "feature_id", "value_columns": list(SAMPLES), "scale": "row_zscore"})
    run("mw_pca", "pca_scatter_from_matrix", df,
        {"matrix_row_id": "feature_id", "value_columns": list(SAMPLES)})
    # sample-correlation heatmap
    corr, _ = T.sample_correlation(df, spec)
    run("mw_sample_correlation", "heatmap_clustered_matrix", corr,
        {"row_id": "sample_id", "color_scale": "diverging"})
    # volcano from a feature-level differential summary
    ds = mw.feature_differential_summary(df, spec, groups, group_a="Treatment",
                                         group_b="Ctrl", test="welch_t")
    run("mw_volcano", "volcano_plot", ds.table,
        {"x": "log2_fold_change", "p": "adjusted_p_value", "label": "feature_label",
         "use_fdr": True})
    # selected-feature violin from wide->long
    long, _ = T.wide_to_long(df, spec, groups)
    sub = long[long["feature_id"].isin([f"FEAT{i:05d}" for i in range(3)])]
    run("mw_selected_violin", "boxplot_or_violin_with_points", sub,
        {"x": "group", "y": "value", "kind": "violin", "points": True})
    return records


def _contact_sheet(records: List[Dict[str, Any]], out_dir: str) -> Optional[str]:
    import matplotlib.image as mpimg
    import matplotlib.pyplot as plt

    imgs = [r for r in records if r.get("png") and os.path.exists(os.path.join(out_dir, r["png"]))]
    if not imgs:
        return None
    n = len(imgs)
    cols = 5
    rows = math.ceil(n / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 2.6, rows * 2.4))
    axes = axes.ravel() if hasattr(axes, "ravel") else [axes]
    for ax in axes:
        ax.axis("off")
    for ax, r in zip(axes, imgs):
        try:
            ax.imshow(mpimg.imread(os.path.join(out_dir, r["png"])))
        except Exception:  # noqa: BLE001
            pass
        color = {"pass": "#2c7", "warn": "#e90", "fail": "#c33", "error": "#c33"}.get(
            r.get("qc_level"), "#666")
        ax.set_title(r["name"], fontsize=6, color=color)
    fig.tight_layout()
    png = os.path.join(out_dir, "contact_sheet.png")
    fig.savefig(png, dpi=130)
    fig.savefig(os.path.join(out_dir, "contact_sheet.pdf"))
    plt.close(fig)
    return png


def run_gallery(out_dir: str) -> List[Dict[str, Any]]:
    per_plot = os.path.join(out_dir, "per_plot")
    os.makedirs(per_plot, exist_ok=True)
    records = _example_plots(per_plot) + _matrix_workflow_plots(per_plot)
    return records


def write_reports(records: List[Dict[str, Any]], out_dir: str) -> None:
    # CSV
    with open(os.path.join(out_dir, "qc_summary.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["name", "group", "status", "qc_level", "qc_score", "warnings"])
        for r in records:
            w.writerow([r["name"], r["group"], r.get("status"), r.get("qc_level"),
                        r.get("qc_score"), " | ".join(r.get("warnings", []) or [])])
    # Markdown
    levels = {k: sum(1 for r in records if r.get("qc_level") == k)
              for k in ("pass", "warn", "fail", "error")}
    lines = ["# Publication QC gallery\n",
             "Generated by `scripts/generate_publication_qc_gallery.py`. Every plot type "
             "(from its bundled example) and every matrix-workflow plot is rendered with the "
             "single **Publication** style, QC-scored, and exported to PNG/SVG/PDF. This is a "
             "QA/regression gallery for the app's renderers, not a journal-compliance claim; "
             "the volcano plots a feature-level differential summary (no raw-count pipeline).\n",
             f"**{len(records)} plots — {levels['pass']} pass, {levels['warn']} warn, "
             f"{levels['fail']} fail, {levels['error']} error.**\n",
             "| Plot | Group | QC | Score | Warnings |", "|---|---|---|---|---|"]
    for r in records:
        warns = "; ".join(r.get("warnings", []) or []) or "—"
        score = "n/a" if r.get("qc_score") is None else str(r.get("qc_score"))
        lines.append(f"| `{r['name']}` | {r['group']} | {r.get('qc_level')} | {score} | {warns} |")
    lines.append("\nSee `docs/PUBLICATION_QC.md` and `docs/MATRIX_WORKFLOW.md`.")
    with open(os.path.join(out_dir, "qc_report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Publication QC gallery (all plots + matrix workflow)")
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)
    records = run_gallery(out_dir)
    _contact_sheet(records, out_dir)
    write_reports(records, out_dir)
    errored = sum(1 for r in records if r.get("qc_level") in ("error", "fail"))
    print(f"Rendered {len(records)} plots -> {out_dir}")
    print(f"errors/fails: {errored}")
    return 1 if errored else 0


if __name__ == "__main__":
    raise SystemExit(main())
