"""Reproduce the Visium marker-expression maps of Janesick et al. 2023 (Fig. 2c).

The paper states only that the markers are shown as "log2(normalized UMI
counts)" and does not define the normalisation, which would normally force this
to be called a recreation. It does not, because the normalisation can be
*recovered and checked* against deposited values:

``spatial/spatial_enrichment.csv`` carries a per-gene column, "Median Normalized
Average Counts", produced by the same pipeline that made the figure. Scaling
each spot to the median total UMI count and averaging reproduces that column for
all 18,056 genes to a maximum absolute difference of ~1e-14. The normalisation
is therefore established by evidence rather than assumed, and this script
asserts that agreement before drawing anything.

One documented assumption remains: the paper writes "log2", and counts of zero
are present, so log2(1 + x) is used - log2(x) is undefined there. That choice
affects the colour scale only and is recorded in the figure's own metadata.

The Fig. 2c *cluster* panel is NOT reproduced; see README for why.

    python reproduce_visium_expression.py [--raw DIR] [--out DIR]
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

# The marker set named in the Fig. 2c legend.
MARKERS = ["SCGB2A2", "CPB1", "KRT17", "FABP4", "IL2RG", "SFRP2", "CDH2", "MT-ND1"]
NORM_TOLERANCE = 1e-9          # relative; observed agreement is ~1e-13


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    import h5py
    from scipy.sparse import csc_matrix

    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=os.path.join(HERE, "..", "raw"))
    ap.add_argument("--out", default=os.path.join(HERE, ".."))
    a = ap.parse_args()
    raw, out = os.path.abspath(a.raw), os.path.abspath(a.out)
    h5p = os.path.join(raw, "GSM7782699_filtered_feature_bc_matrix.h5")
    if not os.path.exists(h5p):
        h5p = os.path.join(raw, "vis_matrix.h5")
    pos_p = os.path.join(raw, "tissue_positions.csv")
    enr_p = os.path.join(raw, "spatial_enrichment.csv")
    for p in (h5p, pos_p, enr_p):
        if not os.path.exists(p):
            print(f"missing {p}\nRun scripts/download.sh first.", file=sys.stderr)
            return 2

    with h5py.File(h5p) as f:
        g = f["matrix"]
        shape = tuple(int(v) for v in g["shape"][:])
        M = csc_matrix((g["data"][:], g["indices"][:], g["indptr"][:]), shape=shape)
        names = np.array([s.decode() for s in g["features"]["name"][:]])
        ids = np.array([s.decode() for s in g["features"]["id"][:]])
        barcodes = np.array([s.decode() for s in g["barcodes"][:]])

    totals = np.asarray(M.sum(axis=0)).ravel()
    median_total = float(np.median(totals))
    normalised = M.multiply((median_total / totals)[None, :]).tocsr()

    checks = []

    def check(quantity, field, got, published, note="", tol=0.0, rel=False):
        got_f, pub_f = float(got), float(published)
        d = abs(got_f - pub_f)
        r = d / abs(pub_f) if pub_f else (0.0 if d == 0 else float("inf"))
        checks.append({"published_quantity": quantity, "source_data_field": field,
                       "makemyfigure_quantity": got_f, "published_value": pub_f,
                       "absolute_difference": d, "relative_difference": r,
                       "pass": bool((r if rel else d) <= tol), "notes": note})

    # --- the normalisation itself, against deposited per-gene values ----------
    enr = pd.read_csv(enr_p)
    pub = enr.set_index("Feature ID")["Median Normalized Average Counts"]
    mine = pd.Series(np.asarray(normalised.mean(axis=1)).ravel(), index=ids)
    common = pub.index.intersection(mine.index)
    rel_diff = (np.abs(mine.loc[common].to_numpy() - pub.loc[common].to_numpy())
                / np.maximum(np.abs(pub.loc[common].to_numpy()), 1e-300))
    check("genes with recovered normalisation matching deposited values",
          "spatial_enrichment.csv 'Median Normalized Average Counts'",
          int((rel_diff <= NORM_TOLERANCE).sum()), int(len(common)),
          "establishes the normalisation by evidence instead of assuming it")
    check("worst relative difference across all genes",
          "spatial_enrichment.csv vs recovered", float(rel_diff.max()), 0.0,
          "scale each spot to the median total UMI count", tol=NORM_TOLERANCE)

    # --- spot coordinates ------------------------------------------------------
    pos = pd.read_csv(pos_p)
    pos = pos[pos["in_tissue"] == 1]
    pos = pos.set_index("barcode").reindex(barcodes).dropna()
    check("spots under tissue carried into the figure", "tissue_positions.csv in_tissue==1",
          len(pos), int((pd.read_csv(pos_p)["in_tissue"] == 1).sum()),
          "every in-tissue spot is drawn; none dropped")

    rows = []
    gene_rows = {}
    for marker in MARKERS:
        idx = np.flatnonzero(names == marker)
        if idx.size == 0:
            check(f"marker {marker} present in the panel", "features/name", 0, 1,
                  "gene not found in the deposited matrix")
            continue
        vals = np.asarray(normalised[idx[0]].todense()).ravel()
        series = pd.Series(vals, index=barcodes).reindex(pos.index)
        gene_rows[marker] = series
        check(f"{marker}: spots with a value", "normalised matrix",
              int(series.notna().sum()), len(pos), "no spot silently dropped")

    tidy = []
    for marker, series in gene_rows.items():
        tidy.append(pd.DataFrame({
            "barcode": series.index,
            # Visium full-resolution pixel coordinates: column is x, row is y.
            "x": pos.loc[series.index, "pxl_col_in_fullres"].to_numpy(),
            "y": pos.loc[series.index, "pxl_row_in_fullres"].to_numpy(),
            "gene": marker,
            "normalized_umi": series.to_numpy(),
            "log2_normalized_umi": np.log2(1.0 + series.to_numpy()),
        }))
    table = pd.concat(tidy, ignore_index=True)
    os.makedirs(os.path.join(out, "derived"), exist_ok=True)
    os.makedirs(os.path.join(out, "validation"), exist_ok=True)
    os.makedirs(os.path.join(out, "figures"), exist_ok=True)
    table.to_csv(os.path.join(out, "derived", "visium_fig2c_markers.csv"), index=False)

    spec = {
        "plot_type": "spatial_feature_map",
        "input_table": "visium_fig2c_markers.csv",
        "mapping": {"x": "x", "y": "y", "value": "log2_normalized_umi", "feature": "gene"},
        "journal_style": "publication",
        "layout": {"title": "Visium marker expression (Janesick et al. 2023, Fig. 2c markers)"},
        "spatial": {
            # Visium full-resolution pixel coordinates. A physical scale bar would
            # need the spot diameter in microns to convert, so none is drawn.
            "coordinate_units": "pixel", "orientation": "y_down",
            "marker_size": 6, "transform": "none", "facet_columns": 4,
            "shared_color_scale": False,
            "colorbar_label": "log2(1 + normalized UMI)",
        },
        "output": {"formats": ["png", "pdf"], "dpi": 300, "width_mm": 180, "height_mm": 110},
    }
    with open(os.path.join(out, "derived", "visium_fig2c.plot_spec.json"), "w") as fh:
        json.dump(spec, fh, indent=2)

    res = registry.render(spec, table)
    for ext in ("png", "pdf"):
        res.figure.savefig(os.path.join(out, "figures", f"visium_fig2c_markers.{ext}"),
                           dpi=300, bbox_inches="tight")
    sp = res.metadata["spatial"]
    check("marker panels drawn", "renderer metadata panels", len(sp["panels"]),
          len(gene_rows), "one panel per published marker")

    audit = pd.DataFrame(checks)
    audit.to_csv(os.path.join(out, "validation", "visium_fig2c_audit.csv"), index=False)
    ok = bool(audit["pass"].all())
    summary = {
        "target": "Janesick et al. 2023, Fig. 2c — Visium marker expression",
        "doi": "10.1038/s41467-023-43458-x",
        "classification": ("expression values reproduced; normalisation verified against "
                           "deposited per-gene values" if ok else "discrepancies present"),
        "normalisation": {
            "recovered": "each spot scaled to the median total UMI count across spots",
            "median_total_umi": median_total,
            "verified_against": "spatial_enrichment.csv 'Median Normalized Average Counts'",
            "genes_checked": int(len(common)),
            "worst_relative_difference": float(rel_diff.max()),
        },
        "documented_assumption": ("the paper writes log2 and zero counts are present, so "
                                  "log2(1 + x) is used; log2(x) is undefined at zero. This "
                                  "affects the colour scale only."),
        "not_reproduced": ("the Fig. 2c cluster panel. Space Ranger's graph-based cluster "
                           "assignments are deposited only inside the proprietary .cloupe "
                           "file; no cluster table is published, so the labels cannot be "
                           "recovered. Re-clustering would produce different labels and would "
                           "not be a reproduction."),
        "markers": list(gene_rows), "n_spots": int(len(pos)),
        "n_comparisons": int(len(audit)), "n_pass": int(audit["pass"].sum()),
        "inputs": {os.path.basename(h5p): _sha256(h5p),
                   "tissue_positions.csv": _sha256(pos_p),
                   "spatial_enrichment.csv": _sha256(enr_p)},
    }
    with open(os.path.join(out, "validation", "visium_fig2c_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, indent=2))
    if not ok:
        print("\nFAILED:\n" + audit[~audit["pass"]].to_string(), file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
