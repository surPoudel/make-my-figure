"""Visual QA gallery for the v0.4 manuscript plot types.

Renders every new v0.4 plot type from its bundled example dataset and writes one
PNG per plot plus a combined contact sheet under ``reports/v04_qa/``. Run after
regenerating examples:

    python scripts/generate_example_data.py
    python scripts/generate_v04_qa_gallery.py

Inspect the output for clipped labels, tiny text, overlapping legends,
unreadable colors, and bad spacing.
"""

from __future__ import annotations

import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from make_my_figure_core import examples  # noqa: E402
from make_my_figure_core.plots.registry import display_name, make_spec, render  # noqa: E402

# The 18 new v0.4 plot types (dot_strip first is the exemplar).
V04_PLOT_TYPES = [
    "dot_strip_plot",
    "beeswarm_plot",
    "paired_slopegraph",
    "raincloud_plot",
    "hierarchical_dendrogram",
    "ma_plot",
    "manhattan_plot",
    "qq_plot",
    "bland_altman_plot",
    "precision_recall_curve",
    "confusion_matrix",
    "calibration_plot",
    "dose_response_curve",
    "upset_plot",
    "swimmer_plot",
    "spider_plot",
    "sankey_plot",
    "embedding_scatter",
]

OUT_DIR = os.path.join(_ROOT, "reports", "v04_qa")


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    made = []
    problems = []
    for pt in V04_PLOT_TYPES:
        if not examples.has_example(pt):
            problems.append(f"{pt}: no example in manifest")
            continue
        info, aux, _spec = examples.load_example(pt)
        aux_dfs = {k: v.dataframe for k, v in aux.items()} or None
        spec = make_spec(pt, "data.csv", "publication")
        try:
            result = render(spec, info.dataframe, aux=aux_dfs)
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{pt}: RENDER FAILED: {exc}")
            continue
        out = os.path.join(OUT_DIR, f"{pt}.png")
        result.figure.savefig(out, dpi=150, bbox_inches="tight")
        check = result.metadata.get("publication_check", {})
        if not check.get("passed", True):
            problems.append(f"{pt}: publication check: {check.get('warnings')}")
        made.append((pt, out))
        plt.close(result.figure)
        print(f"  {pt}: {os.path.relpath(out, _ROOT)}")

    # Contact sheet.
    n = len(made)
    if n:
        ncols = 3
        nrows = (n + ncols - 1) // ncols
        fig, axes = plt.subplots(nrows, ncols, figsize=(ncols * 4.2, nrows * 3.4))
        axes = axes.ravel() if hasattr(axes, "ravel") else [axes]
        for ax, (pt, path) in zip(axes, made):
            ax.imshow(plt.imread(path))
            ax.set_title(display_name(pt), fontsize=9)
            ax.axis("off")
        for ax in axes[n:]:
            ax.axis("off")
        fig.tight_layout()
        sheet = os.path.join(OUT_DIR, "_contact_sheet.png")
        fig.savefig(sheet, dpi=130, bbox_inches="tight")
        plt.close(fig)
        print(f"\nContact sheet: {os.path.relpath(sheet, _ROOT)}")

    print(f"\nRendered {len(made)}/{len(V04_PLOT_TYPES)} v0.4 plots to {os.path.relpath(OUT_DIR, _ROOT)}")
    if problems:
        print("\nISSUES:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("All v0.4 QA plots rendered and passed the publication check.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
