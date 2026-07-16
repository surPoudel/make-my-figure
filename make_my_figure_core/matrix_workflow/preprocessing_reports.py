"""Before/after QC reporting for a preprocessing workflow.

Runs a confirmed preprocessing chain, renders matched QC plots on the raw and the
derived matrix, and writes a reproducible report (method sentence, QC metrics,
per-plot images, before/after contact sheet). Publication style throughout.
"""

from __future__ import annotations

import csv
import math
import os
from typing import Any, Dict, List, Optional

import matplotlib

matplotlib.use("Agg")

import pandas as pd

from make_my_figure_core.matrix_workflow.matrix_spec import MatrixSpec
from make_my_figure_core.matrix_workflow.preprocessing import run_preprocessing
from make_my_figure_core.matrix_workflow.qc_diagnostics import diagnose_matrix
from make_my_figure_core.matrix_workflow.qc_plots import qc_plot_inputs

_DEFAULT_QC = ["value_density", "sample_boxplot", "library_size", "mean_variance",
               "pca", "sample_correlation"]


def _render_pi(pi, out_base: str, formats=("png", "pdf", "svg"), dpi: int = 200) -> Optional[str]:
    """Render a PlotInputs to files; return the PNG path (or None on failure).

    Writes vector (PDF/SVG) plus a high-DPI PNG so each QC plot has a true
    publication-quality artifact (the contact sheet is a raster overview of these).
    """
    import matplotlib.pyplot as plt

    from make_my_figure_core.plots.registry import export_figure, make_spec, render

    try:
        spec = make_spec(pi.plot_type, "qc", "publication", mapping=pi.mapping)
        for k, v in (pi.spec_extra or {}).items():
            spec[k] = v
        result = render(spec, pi.dataframe, aux=pi.aux or None)
        export_figure(result.figure, out_base, list(formats), dpi=dpi)
        plt.close(result.figure)
        return out_base + ".png"
    except Exception:  # noqa: BLE001 - one QC plot failing must not abort the report
        return None


def before_after_report(df: pd.DataFrame, matrix_spec: MatrixSpec,
                        steps: List[Dict[str, Any]], out_dir: str, *,
                        metadata=None, qc_kinds: Optional[List[str]] = None,
                        output_matrix_id: str = "processed"):
    """Apply ``steps``, render before/after QC, and write the report to ``out_dir``.

    Returns ``(final_df, derived_spec, PreprocessingSpec, records)``. The original
    matrix is untouched; everything is reproducible from the returned spec."""
    qc_kinds = qc_kinds or _DEFAULT_QC
    per_dir = os.path.join(out_dir, "per_plot")
    os.makedirs(per_dir, exist_ok=True)

    qc_before = diagnose_matrix(df, matrix_spec)
    final_df, dspec, ps = run_preprocessing(df, matrix_spec, steps,
                                            metadata=metadata, output_matrix_id=output_matrix_id)
    qc_after = diagnose_matrix(final_df, dspec)

    records: List[Dict[str, Any]] = []
    for kind in qc_kinds:
        b = qc_plot_inputs(kind, df, matrix_spec, metadata=metadata, title=f"{kind} — before")
        a = qc_plot_inputs(kind, final_df, dspec, metadata=metadata, title=f"{kind} — after")
        pb = _render_pi(b, os.path.join(per_dir, f"{kind}_before"))
        pa = _render_pi(a, os.path.join(per_dir, f"{kind}_after"))
        records.append({"kind": kind, "before": pb, "after": pa})

    _contact_sheet(records, out_dir)
    from make_my_figure_core.matrix_workflow.qc_plots import short_sample_labels
    sample_labels = short_sample_labels(list(matrix_spec.value_columns))
    _write_reports(ps, qc_before, qc_after, records, out_dir, sample_labels=sample_labels)
    return final_df, dspec, ps, records


def _contact_sheet(records: List[Dict[str, Any]], out_dir: str) -> Optional[str]:
    """High-quality before/after overview: embeds the per-plot images in a
    constrained-layout grid (no clipped titles/row labels), saved as a crisp
    300-DPI PNG and PDF. The per-plot PDF/SVG files are the true vector artifacts."""
    import matplotlib.image as mpimg
    import matplotlib.pyplot as plt

    rows = [r for r in records if r["before"] and r["after"]]
    if not rows:
        return None
    n = len(rows)
    # Generous per-panel size; constrained_layout reserves room for titles/labels.
    fig, axes = plt.subplots(n, 2, figsize=(12.0, 4.3 * n), constrained_layout=True)
    if n == 1:
        axes = axes.reshape(1, 2)
    fig.suptitle("Preprocessing QC — before vs after", fontsize=15, fontweight="bold")
    for i, r in enumerate(rows):
        for j, key, hdr in ((0, "before", "Before"), (1, "after", "After")):
            ax = axes[i, j]
            # Keep the axes box (so the ylabel has reserved room) but hide ticks/spines.
            ax.set_xticks([])
            ax.set_yticks([])
            for sp in ax.spines.values():
                sp.set_visible(False)
            try:
                ax.imshow(mpimg.imread(r[key]))
            except Exception:  # noqa: BLE001
                pass
            if i == 0:
                ax.set_title(hdr, fontsize=13, fontweight="bold")
        pretty = str(r["kind"]).replace("_", " ").capitalize()
        axes[i, 0].set_ylabel(pretty, fontsize=11, fontweight="bold")
    png = os.path.join(out_dir, "before_after_contact_sheet.png")
    fig.savefig(png, dpi=300)
    fig.savefig(os.path.join(out_dir, "before_after_contact_sheet.pdf"), dpi=300)
    plt.close(fig)
    return png


def _write_reports(ps, qc_before, qc_after, records, out_dir: str, *,
                   sample_labels: Optional[Dict[str, str]] = None) -> None:
    with open(os.path.join(out_dir, "qc_summary.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        keys = ["n_features", "n_samples", "missing_values", "zero_fraction",
                "negative_value_fraction", "min", "max", "median", "suspected_data_type"]
        w.writerow(["metric", "before", "after"])
        b, a = qc_before.to_dict(), qc_after.to_dict()
        for k in keys:
            w.writerow([k, b.get(k), a.get(k)])
        w.writerow(["skew_overall", qc_before.skewness_summary.get("overall"),
                    qc_after.skewness_summary.get("overall")])

    lines = ["# Preprocessing QC report\n",
             "## Method\n", ps.method_sentence(), ""]
    if ps.warnings:
        lines += ["## Warnings", *[f"- {w}" for w in ps.warnings], ""]
    lines += ["## Diagnostics (before → after)",
              f"- features: {qc_before.n_features} → {qc_after.n_features}",
              f"- samples: {qc_before.n_samples}",
              f"- overall skew: {qc_before.skewness_summary.get('overall'):.2f} → "
              f"{qc_after.skewness_summary.get('overall'):.2f}",
              f"- zero fraction: {qc_before.zero_fraction:.2%} → {qc_after.zero_fraction:.2%}",
              f"- value range: [{qc_before.min:.1f}, {qc_before.max:.1f}] → "
              f"[{qc_after.min:.2f}, {qc_after.max:.2f}]",
              f"- suspected type (before): {qc_before.suspected_data_type}", ""]
    lines += ["## QC plots (before / after)"]
    for r in records:
        lines.append(f"- **{r['kind']}** — before: `{os.path.relpath(r['before'], out_dir) if r['before'] else 'n/a'}`, "
                     f"after: `{os.path.relpath(r['after'], out_dir) if r['after'] else 'n/a'}`")
    if sample_labels and any(k != v for k, v in sample_labels.items()):
        lines += ["", "## Sample labels (QC axes show the short label)",
                  "| short | full sample name |", "| --- | --- |",
                  *[f"| `{v}` | `{k}` |" for k, v in sample_labels.items()]]
    lines += ["", "See `before_after_contact_sheet.png` (300-DPI overview) and the vector "
              "per-plot files in `per_plot/` (PDF/SVG). Every step is reproducible from the "
              "PreprocessingSpec; the original matrix is unchanged."]
    with open(os.path.join(out_dir, "preprocessing_report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
