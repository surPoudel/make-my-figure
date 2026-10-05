"""Reproduce CNTools Fig 3A (CRC, CC*) from the deposited source data.

CC* is defined in the Fig 3 legend as "the original CC results" - the
neighbourhood assignments from the original publication, deposited in the CRC
table as ``neighborhood10``. It is NOT a fresh CNTools CC run. The Methods
state the original had ten CNs "with one 'dirt' enriched CN removed", and CN 1
is 70.4% dirt against <= 3.75% for every other CN, so CN 1 is the removed one.

This script therefore validates the ENRICHMENT CALCULATION against an
independent group's published numbers. It does not validate our CC
implementation, which uses their labels here rather than its own.

    python reproduce_fig3a.py [--raw DIR] [--out DIR]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.stats import pearsonr

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
from make_my_figure_core.spatial import ct_cn_enrichment  # noqa: E402

DIRT_CN = 1          # the dirt-enriched neighbourhood removed in the original study
N_CN, N_CT = 9, 28


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _assign(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Index array aligning rows of ``a`` onto rows of ``b`` by best correlation.

    The sheet labels neither the neighbourhoods nor the cell types, so the
    correspondence has to be recovered rather than assumed.
    """
    cost = np.zeros((a.shape[0], b.shape[0]))
    for i in range(a.shape[0]):
        for j in range(b.shape[0]):
            v = np.corrcoef(a[i], b[j])[0, 1]
            cost[i, j] = 0.0 if not np.isfinite(v) else v
    mi, pj = linear_sum_assignment(-cost)
    idx = np.empty(b.shape[0], dtype=int)
    idx[pj] = mi
    return idx


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, ".."))
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=os.path.join(root, "raw"))
    ap.add_argument("--out", default=root)
    a = ap.parse_args()

    crc_path = os.path.join(a.raw, "CRC_clusters_neighborhoods_markers.csv")
    s1_path = os.path.join(a.raw, "cntools_S1_Data.xlsx")
    for p in (crc_path, s1_path):
        if not os.path.exists(p):
            print(f"missing {p}\nRun scripts/download.sh first.", file=sys.stderr)
            return 2

    cols = ["File Name", "groups", "patients", "ClusterName", "neighborhood10", "X:X", "Y:Y"]
    df = pd.read_csv(crc_path, usecols=cols, low_memory=False)

    # CC*: original CN labels, dirt-enriched CN removed, dirt cells discarded.
    keep = df[(df["neighborhood10"] != DIRT_CN) & (df["ClusterName"] != "dirt")].copy()
    assert keep["neighborhood10"].nunique() == N_CN, keep["neighborhood10"].nunique()
    assert keep["ClusterName"].nunique() == N_CT, keep["ClusterName"].nunique()

    tidy = ct_cn_enrichment(keep["ClusterName"], keep["neighborhood10"].astype(str))
    mine_e = tidy.pivot(index="neighborhood", columns="cell_type", values="enrichment_score")
    mine_f = tidy.pivot(index="neighborhood", columns="cell_type",
                        values="cell_type_frequency_in_neighborhood")

    raw = pd.read_excel(s1_path, sheet_name="Figure 3A", header=None)
    l0, l1 = raw[0].ffill(), raw[1].ffill()
    pub_e = raw.loc[(l0 == "CN Enrichment Score") & (l1 == "CC*"), raw.columns[2:]].astype(float).to_numpy()
    pub_f = raw.loc[(l0 == "CN Frequency per CN") & (l1 == "CC*"), raw.columns[2:]].astype(float).to_numpy()

    ci = _assign(mine_f.to_numpy().T, pub_f.T)
    ri = _assign(mine_f.to_numpy()[:, ci], pub_f)
    got_e = mine_e.to_numpy()[:, ci][ri]
    got_f = mine_f.to_numpy()[:, ci][ri]

    rows = []
    for i in range(N_CN):
        for j in range(N_CT):
            for name, got, pub in (("enrichment_score", got_e[i, j], pub_e[i, j]),
                                   ("cell_type_frequency_in_neighborhood", got_f[i, j], pub_f[i, j])):
                d = abs(got - pub)
                rows.append({
                    "published_quantity": f"Fig3A CC* {name}",
                    "source_data_field": f"S1 Data 'Figure 3A' row {i}, col {j}",
                    "makemyfigure_quantity": got, "published_value": pub,
                    "absolute_difference": d,
                    "relative_difference": (d / abs(pub)) if pub else (0.0 if d == 0 else np.inf),
                    "pass": bool(d <= 1e-9),
                })
    audit = pd.DataFrame(rows)
    os.makedirs(os.path.join(a.out, "validation"), exist_ok=True)
    os.makedirs(os.path.join(a.out, "derived"), exist_ok=True)
    audit.to_csv(os.path.join(a.out, "validation", "fig3a_audit.csv"), index=False)

    fin = np.isfinite(pub_e) & np.isfinite(got_e)
    summary = {
        "target": "CNTools Fig 3A, CRC, CC*",
        "cc_star_definition": "original CC results (deposited neighborhood10), dirt CN removed",
        "n_cells": int(len(keep)), "n_neighborhoods": N_CN, "n_cell_types": N_CT,
        "enrichment": {
            "pearson_r": float(pearsonr(got_e[fin], pub_e[fin])[0]),
            "max_abs_diff": float(np.abs(got_e - pub_e)[fin].max()),
            "median_abs_diff": float(np.median(np.abs(got_e - pub_e)[fin])),
        },
        "frequency": {
            "pearson_r": float(pearsonr(got_f.ravel(), pub_f.ravel())[0]),
            "max_abs_diff": float(np.abs(got_f - pub_f).max()),
            "median_abs_diff": float(np.median(np.abs(got_f - pub_f))),
        },
        "n_comparisons": int(len(audit)),
        "n_pass": int(audit["pass"].sum()),
        "classification": "exact numerical reproduction" if bool(audit["pass"].all())
                          else "not an exact reproduction",
        "validates": "the CT-CN enrichment calculation",
        "does_not_validate": ("our CC implementation - this uses the published CN labels, "
                              "not labels produced by our clustering"),
        "inputs": {"crc_sha256": _sha256(crc_path), "s1_sha256": _sha256(s1_path)},
    }
    with open(os.path.join(a.out, "validation", "fig3a_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)

    # Redistributable derived table: the published Fig 3A values, tidied.
    # S1 Data is CC BY 4.0, so this may be committed with attribution.
    pub_tidy = []
    for i in range(N_CN):
        for j in range(N_CT):
            pub_tidy.append({"neighborhood": f"CN{i+1}", "cell_type_index": j,
                             "enrichment_score": pub_e[i, j],
                             "cell_type_frequency_in_neighborhood": pub_f[i, j]})
    pd.DataFrame(pub_tidy).to_csv(
        os.path.join(a.out, "derived", "neighborhood_enrichment_cntools.csv"), index=False)

    print(json.dumps(summary, indent=2))
    return 0 if summary["classification"] == "exact numerical reproduction" else 1


if __name__ == "__main__":
    raise SystemExit(main())
