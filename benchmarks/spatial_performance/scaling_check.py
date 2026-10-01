"""Confirm the neighbour graph is sub-quadratic, by measurement rather than claim.

The brief asks that default workflows avoid O(n^2) where a scalable alternative
exists. Asserting "we use a cKDTree" is not evidence; this fits an exponent to
observed timings, so a regression to a brute-force path would show up as an
exponent near 2 instead of near 1.

    python scaling_check.py [--sizes 25000,50000,100000,200000,400000]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))

from make_my_figure_core.spatial import (  # noqa: E402
    NeighborGraphSpec, build_neighbor_graph, local_composition,
)

QUADRATIC_ALARM = 1.6      # an exponent above this is not near-linear


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", default="25000,50000,100000,200000,400000")
    ap.add_argument("--out", default=HERE)
    a = ap.parse_args()
    sizes = [int(s) for s in a.sizes.split(",")]
    rng = np.random.default_rng(0)

    rows, prev = [], None
    for n in sizes:
        df = pd.DataFrame({"x": rng.uniform(0, 6000, n), "y": rng.uniform(0, 6000, n),
                           "cell_type": rng.choice(list("ABCDEFGH"), n), "sample": "s"})
        spec = NeighborGraphSpec(method="knn", k=10, sample_column="sample")
        t0 = time.perf_counter()
        graph = build_neighbor_graph(df, "x", "y", spec)
        t_graph = time.perf_counter() - t0
        t0 = time.perf_counter()
        local_composition(df, "cell_type", graph)
        t_comp = time.perf_counter() - t0
        exp = (np.log(t_graph / prev[1]) / np.log(n / prev[0])) if prev else None
        rows.append({"n": n, "graph_seconds": round(t_graph, 4),
                     "composition_seconds": round(t_comp, 4),
                     "implied_exponent": round(float(exp), 3) if exp is not None else None})
        prev = (n, t_graph)

    table = pd.DataFrame(rows)
    table.to_csv(os.path.join(a.out, "scaling.csv"), index=False)
    # Ignore the first measured exponent: it carries process warm-up.
    exps = [r["implied_exponent"] for r in rows[2:] if r["implied_exponent"] is not None]
    worst = max(exps) if exps else float("nan")
    verdict = {
        "measured_exponents": exps,
        "worst_exponent": worst,
        "near_linear": bool(worst < QUADRATIC_ALARM),
        "interpretation": ("~1.0-1.2 is near-linear, as a k-d tree should be; 2.0 would "
                           "mean a brute-force all-pairs path had crept in"),
    }
    with open(os.path.join(a.out, "scaling_verdict.json"), "w") as fh:
        json.dump(verdict, fh, indent=2)
    print(table.to_string(index=False))
    print(f"\nworst exponent {worst:.2f} -> "
          f"{'near-linear' if verdict['near_linear'] else 'NOT near-linear'}")
    return 0 if verdict["near_linear"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
