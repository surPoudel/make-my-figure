"""Render every statistics example into a single QA gallery image.

Loads each example under ``examples/statistics/``, renders it with its embedded
StatsSpec, and tiles the results so figure quality (brackets, panels, spacing)
can be eyeballed in one place. Writes ``reports/stats_qa_gallery.png``.

Usage:
    python scripts/generate_stats_qa_gallery.py
"""

from __future__ import annotations

import json
import math
import os
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from make_my_figure_core.io.loaders import load_table  # noqa: E402
from make_my_figure_core.plots.registry import figure_to_bytes, render  # noqa: E402

STATS_DIR = os.path.join(_ROOT, "examples", "statistics")
OUT = os.path.join(_ROOT, "reports", "stats_qa_gallery.png")


def main() -> int:
    manifest = json.load(open(os.path.join(STATS_DIR, "manifest.json")))
    slugs = [e["slug"] for e in manifest["examples"]]
    import io

    import matplotlib.image as mpimg

    images = []
    for slug in slugs:
        folder = os.path.join(STATS_DIR, slug)
        spec = json.load(open(os.path.join(folder, "plotspec.json")))
        df = load_table(os.path.join(folder, "data.csv")).dataframe
        try:
            res = render(spec, df)
            png = figure_to_bytes(res.figure, "png", dpi=110)
            images.append((slug, mpimg.imread(io.BytesIO(png))))
            plt.close(res.figure)
        except Exception as exc:  # keep the gallery going
            print(f"  {slug}: FAILED {exc}")

    n = len(images)
    ncols = 3
    nrows = math.ceil(n / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(ncols * 4.2, nrows * 3.4))
    axes = axes.ravel() if hasattr(axes, "ravel") else [axes]
    for ax, (slug, img) in zip(axes, images):
        ax.imshow(img)
        ax.set_title(slug, fontsize=9)
        ax.axis("off")
    for ax in axes[n:]:
        ax.axis("off")
    fig.tight_layout()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=130)
    plt.close(fig)
    print(f"Wrote {OUT} ({n} examples)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
