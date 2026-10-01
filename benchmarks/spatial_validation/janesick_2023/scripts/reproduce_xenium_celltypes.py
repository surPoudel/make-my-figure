"""Reproduce the Xenium cell-type spatial map of Janesick et al. 2023 (Fig. 3l).

What makes this a reproduction rather than a recreation: the cell type of every
cell is the **published supervised annotation** deposited with the paper
(GSM7780153_Xenium_R1_Fig1-5_supervised.csv.gz, the labels used for Figures 1-5),
and the coordinates are the cell centroids from the deposited Xenium output.
Nothing is re-clustered, re-annotated or re-normalised here - the figure is
redrawn from the authors' own numbers.

    python reproduce_xenium_celltypes.py [--raw DIR] [--out DIR]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, ROOT)

from make_my_figure_core.plots import registry  # noqa: E402

CELLS = "xenium_cells.csv.gz"
ANNOT = "xen_sup.csv.gz"
N_CELLS_PUBLISHED = 167780          # stated by the deposited files themselves


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=os.path.join(HERE, "..", "raw"))
    ap.add_argument("--out", default=os.path.join(HERE, ".."))
    a = ap.parse_args()
    raw, out = os.path.abspath(a.raw), os.path.abspath(a.out)
    cells_p, annot_p = os.path.join(raw, CELLS), os.path.join(raw, ANNOT)
    for p in (cells_p, annot_p):
        if not os.path.exists(p):
            print(f"missing {p}\nRun scripts/download.sh first.", file=sys.stderr)
            return 2

    cells = pd.read_csv(cells_p)
    annot = pd.read_csv(annot_p)
    merged = cells.merge(annot, left_on="cell_id", right_on="Barcode", how="inner")

    checks = []

    def check(quantity, source_field, got, published, note="", tol=0.0):
        d = abs(float(got) - float(published)) if isinstance(got, (int, float, np.number)) else (
            0.0 if got == published else 1.0)
        checks.append({
            "published_quantity": quantity, "source_data_field": source_field,
            "makemyfigure_quantity": got, "published_value": published,
            "absolute_difference": d,
            "relative_difference": (d / abs(float(published))) if isinstance(published, (int, float, np.number)) and published else (0.0 if d == 0 else float("inf")),
            "pass": bool(d <= tol), "notes": note,
        })

    check("cell count (Xenium Rep 1)", "cells.csv rows", len(cells), N_CELLS_PUBLISHED,
          "every deposited cell is carried through")
    check("annotated cell count", "Fig1-5_supervised rows", len(annot), N_CELLS_PUBLISHED)
    check("cells joined on cell_id", "cells.csv x supervised", len(merged), N_CELLS_PUBLISHED,
          "a 100% join means no cell was dropped or duplicated")

    # Per-cell-type counts must survive exactly: the figure must not quietly
    # lose a population through a join or a dtype.
    for ct, n in annot["Cluster"].value_counts().items():
        check(f"cells of type {ct!r}", "supervised Cluster", int((merged["Cluster"] == ct).sum()),
              int(n), "count preserved through the join")

    # Coordinates are passed through untouched.
    check("x centroid sum (um)", "cells.csv x_centroid",
          round(float(merged["x_centroid"].sum()), 3),
          round(float(cells.set_index("cell_id").loc[merged["cell_id"], "x_centroid"].sum()), 3),
          "coordinates are not transformed", tol=1e-6)
    check("y centroid sum (um)", "cells.csv y_centroid",
          round(float(merged["y_centroid"].sum()), 3),
          round(float(cells.set_index("cell_id").loc[merged["cell_id"], "y_centroid"].sum()), 3),
          "coordinates are not transformed", tol=1e-6)

    table = pd.DataFrame({
        "cell_id": merged["cell_id"].astype("int64"),
        "x": merged["x_centroid"].to_numpy(),
        "y": merged["y_centroid"].to_numpy(),
        "cell_type": merged["Cluster"].astype(str).to_numpy(),
        "transcript_counts": merged["transcript_counts"].to_numpy(),
        "cell_area": merged["cell_area"].to_numpy(),
    })
    os.makedirs(os.path.join(out, "derived"), exist_ok=True)
    os.makedirs(os.path.join(out, "validation"), exist_ok=True)
    derived_p = os.path.join(out, "derived", "xenium_rep1_cells_celltypes.csv")
    table.to_csv(derived_p, index=False)

    spec = {
        "plot_type": "spatial_categorical_map",
        "input_table": "xenium_rep1_cells_celltypes.csv",
        "mapping": {"x": "x", "y": "y", "category": "cell_type"},
        "journal_style": "publication",
        "layout": {"title": "Xenium Rep 1 — published cell types (Janesick et al. 2023, Fig. 3l)"},
        "spatial": {
            # Xenium centroids are micrometres, so a physical scale bar is meaningful
            # here - unlike the pixel-coordinate CRC example.
            "coordinate_units": "micrometre", "orientation": "y_down",
            "marker_size": 1.2, "alpha": 0.75, "rasterize": True,
            "scale_bar": True, "scale_bar_length": 1000.0, "legend_columns": 1,
        },
        "output": {"formats": ["png", "pdf"], "dpi": 300, "width_mm": 180, "height_mm": 140},
    }
    with open(os.path.join(out, "derived", "xenium_celltypes.plot_spec.json"), "w") as fh:
        json.dump(spec, fh, indent=2)

    res = registry.render(spec, table)
    fig_dir = os.path.join(out, "figures")
    os.makedirs(fig_dir, exist_ok=True)
    for ext in ("png", "pdf"):
        res.figure.savefig(os.path.join(fig_dir, f"xenium_rep1_celltypes.{ext}"),
                           dpi=300, bbox_inches="tight")

    sp = res.metadata["spatial"]
    check("cells drawn", "renderer metadata n_cells", sp["n_cells"], len(table),
          "no silent subsampling")
    check("cell types drawn", "renderer metadata categories", len(sp["categories"]),
          merged["Cluster"].nunique(), "every published population appears in the legend")
    check("coordinate units declared", "spec spatial.coordinate_units",
          sp["coordinate_units"], "micrometre", "units are declared, never inferred")

    audit = pd.DataFrame(checks)
    audit.to_csv(os.path.join(out, "validation", "xenium_fig3l_audit.csv"), index=False)

    summary = {
        "target": "Janesick et al. 2023, Fig. 3l — Xenium cell-type spatial map",
        "doi": "10.1038/s41467-023-43458-x",
        "classification": ("exact reproduction of the published annotation"
                           if bool(audit["pass"].all()) else "discrepancies present"),
        "basis": ("cell types are the authors' deposited supervised labels and coordinates are "
                  "the deposited centroids; nothing is re-clustered, re-annotated or "
                  "re-normalised"),
        "n_cells": int(len(table)), "n_cell_types": int(merged["Cluster"].nunique()),
        "coordinate_units": "micrometre",
        "n_comparisons": int(len(audit)), "n_pass": int(audit["pass"].sum()),
        "styling_note": ("Colours, marker size and layout follow the MakeMyFigure Publication "
                         "style and do not attempt to match the published artwork; the claim "
                         "is about the data drawn, not the appearance."),
        "inputs": {CELLS: _sha256(cells_p), ANNOT: _sha256(annot_p)},
    }
    with open(os.path.join(out, "validation", "xenium_fig3l_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, indent=2))
    failed = audit[~audit["pass"]]
    if len(failed):
        print("\nFAILED CHECKS:\n" + failed.to_string(), file=sys.stderr)
    return 0 if bool(audit["pass"].all()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
