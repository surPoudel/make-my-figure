"""Performance of the spatial workflow at realistic sizes.

Measures each stage separately - load, neighbour graph, local composition,
neighbourhood clustering, enrichment, render, export - because they scale
differently and an average hides that. Peak resident memory is recorded per
stage from the OS rather than estimated.

Real data is used where it exists (Xenium 167,780 cells; CRC 251,028 cells) and
synthetic tissue fills in the sizes no deposited dataset provides. Synthetic
rows are clearly marked: they measure the software, not biology.

Nothing here subsamples. The point is to find out what the real cost is, and a
benchmark that quietly shrinks its input measures nothing.

    python run_benchmark.py [--sizes 10000,100000,500000] [--transcripts 1000000]
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import sys
import time
from contextlib import contextmanager

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)

from make_my_figure_core.plots import registry  # noqa: E402
from make_my_figure_core.spatial import (  # noqa: E402
    NeighborGraphSpec, build_neighbor_graph, ct_cn_enrichment,
    identify_neighborhoods_cc, local_composition,
)

CELL_TYPES = ["Tumor", "Stroma", "Macrophage", "CD8 T", "CD4 T", "B cell",
              "Endothelial", "Fibroblast"]
RESULTS = []


def _peak_mb() -> float:
    """Peak RSS in MB. ru_maxrss is KB on Linux, bytes on macOS."""
    v = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return v / 1024.0 if sys.platform != "darwin" else v / (1024.0 * 1024.0)


@contextmanager
def stage(name: str, n: int, note: str = ""):
    before = _peak_mb()
    t0 = time.perf_counter()
    yield
    elapsed = time.perf_counter() - t0
    peak = _peak_mb()
    RESULTS.append({"stage": name, "n": n, "seconds": round(elapsed, 3),
                    "peak_rss_mb": round(peak, 1),
                    "rss_growth_mb": round(max(peak - before, 0.0), 1),
                    "per_1k_rows_ms": round(1000.0 * elapsed / max(n, 1) * 1000, 4),
                    "notes": note})
    print(f"  {name:<28} n={n:>9,}  {elapsed:8.3f}s  peak {peak:7.1f} MB  {note}")


def synthetic_cells(n: int, seed: int = 0) -> pd.DataFrame:
    """Tissue-like coordinates: structured, not uniform noise, so the kNN graph
    sees realistic local density rather than an unnaturally even one."""
    rng = np.random.default_rng(seed)
    n_blobs = max(4, int(np.sqrt(n) / 12))
    centres = rng.uniform(0, 6000, size=(n_blobs, 2))
    which = rng.integers(0, n_blobs, n)
    xy = centres[which] + rng.normal(0, 320, size=(n, 2))
    d = np.linalg.norm(xy - xy.mean(axis=0), axis=1)
    p = np.clip(1.0 - d / (d.max() + 1e-9), 0.05, 1.0)
    types = np.where(rng.random(n) < p, "Tumor",
                     rng.choice(CELL_TYPES[1:], n))
    return pd.DataFrame({"cell_id": np.arange(n), "x": xy[:, 0], "y": xy[:, 1],
                         "cell_type": types, "sample": "synthetic",
                         "value": rng.gamma(2.0, 1.5, n)})


def real_cells(limit: int | None = None):
    """Xenium Rep 1 if it has been downloaded, else None."""
    cells = os.path.join(ROOT, "benchmarks", "spatial_validation", "janesick_2023",
                         "raw", "xenium_cells.csv.gz")
    annot = os.path.join(ROOT, "benchmarks", "spatial_validation", "janesick_2023",
                         "raw", "xen_sup.csv.gz")
    if not (os.path.exists(cells) and os.path.exists(annot)):
        return None
    c = pd.read_csv(cells)
    a = pd.read_csv(annot)
    m = c.merge(a, left_on="cell_id", right_on="Barcode", how="inner")
    df = pd.DataFrame({"cell_id": m["cell_id"], "x": m["x_centroid"], "y": m["y_centroid"],
                       "cell_type": m["Cluster"].astype(str), "sample": "xenium_rep1",
                       "value": m["transcript_counts"].astype(float)})
    return df.head(limit) if limit else df


def bench_cells(df: pd.DataFrame, label: str, tmp: str, do_cluster: bool = True):
    n = len(df)
    print(f"\n=== {label}: {n:,} cells ===")

    path = os.path.join(tmp, f"cells_{n}.csv")
    with stage("write CSV", n, label):
        df.to_csv(path, index=False)
    with stage("load CSV", n, label):
        loaded = pd.read_csv(path)

    spec = NeighborGraphSpec(method="knn", k=10, sample_column="sample",
                             coordinate_units="micrometre")
    with stage("neighbour graph (kNN k=10)", n, "cKDTree, per sample"):
        graph = build_neighbor_graph(loaded, "x", "y", spec)
    with stage("local composition", n, "vectorised bincount"):
        comp, levels = local_composition(loaded, "cell_type", graph)

    labels = None
    if do_cluster:
        with stage("CC neighbourhoods (k-means, 8 CNs)", n, "scikit-learn"):
            res = identify_neighborhoods_cc(loaded, "x", "y", "cell_type",
                                            n_neighborhoods=8, m_neighbors=10,
                                            sample_column="sample", random_seed=0)
            labels = res.labels
        with stage("CT-CN enrichment", n, "crosstab + published formula"):
            ct_cn_enrichment(loaded["cell_type"], labels)

    base = {"journal_style": "publication",
            "output": {"formats": ["png"], "dpi": 300, "width_mm": 180, "height_mm": 140}}
    cat_spec = {**base, "plot_type": "spatial_categorical_map",
                "input_table": os.path.basename(path),
                "mapping": {"x": "x", "y": "y", "category": "cell_type"},
                "spatial": {"coordinate_units": "micrometre", "marker_size": 1.0,
                            "rasterize": True}}
    with stage("render categorical map", n, "rasterised marks"):
        rendered = registry.render(cat_spec, loaded)
    for fmt in ("png", "pdf", "svg"):
        with stage(f"export {fmt.upper()}", n, "rasterised marks, vector text"):
            rendered.figure.savefig(os.path.join(tmp, f"cells_{n}.{fmt}"), dpi=300)

    feat_spec = {**base, "plot_type": "spatial_feature_map",
                 "input_table": os.path.basename(path),
                 "mapping": {"x": "x", "y": "y", "value": "value"},
                 "spatial": {"coordinate_units": "micrometre", "marker_size": 1.0,
                             "rasterize": True}}
    with stage("render feature map", n, "continuous colour"):
        registry.render(feat_spec, loaded)


def bench_transcripts(n: int, tmp: str):
    print(f"\n=== transcripts: {n:,} points ===")
    rng = np.random.default_rng(1)
    genes = ["EPCAM", "CD8A", "COL1A1", "MS4A1", "PECAM1", "ACTA2"]
    df = pd.DataFrame({
        "transcript_id": np.arange(n),
        "x": rng.uniform(0, 7500, n), "y": rng.uniform(0, 5400, n),
        "gene": rng.choice(genes, n), "qv": rng.uniform(20, 40, n)})
    path = os.path.join(tmp, f"tx_{n}.csv")
    with stage("write CSV", n, "transcripts"):
        df.to_csv(path, index=False)
    with stage("load CSV", n, "transcripts"):
        loaded = pd.read_csv(path)
    spec = {"plot_type": "spatial_transcript_map", "input_table": os.path.basename(path),
            "mapping": {"x": "x", "y": "y", "gene": "gene", "quality": "qv"},
            "journal_style": "publication",
            "spatial": {"coordinate_units": "micrometre", "marker_size": 0.6,
                        "rasterize": True},
            "output": {"formats": ["png"], "dpi": 300, "width_mm": 180, "height_mm": 140}}
    with stage("render transcript map", n, "no subsampling"):
        res = registry.render(spec, loaded)
    for fmt in ("png", "pdf"):
        with stage(f"export {fmt.upper()}", n, "rasterised marks"):
            res.figure.savefig(os.path.join(tmp, f"tx_{n}.{fmt}"), dpi=300)


def main() -> int:
    import tempfile
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", default="10000,100000,500000")
    ap.add_argument("--transcripts", type=int, default=1_000_000)
    ap.add_argument("--out", default=HERE)
    a = ap.parse_args()
    sizes = [int(s) for s in a.sizes.split(",") if s.strip()]
    tmp = tempfile.mkdtemp(prefix="mmf_perf_")

    real = real_cells()
    if real is not None:
        bench_cells(real, "Xenium Rep 1 (real)", tmp)
    else:
        print("Xenium data not present; skipping the real-data run "
              "(benchmarks/spatial_validation/janesick_2023/scripts/download.sh)")

    for n in sizes:
        bench_cells(synthetic_cells(n), f"synthetic {n:,}", tmp)
    if a.transcripts:
        bench_transcripts(a.transcripts, tmp)

    table = pd.DataFrame(RESULTS)
    table.to_csv(os.path.join(a.out, "performance.csv"), index=False)
    env = {
        "python": platform.python_version(), "platform": platform.platform(),
        "numpy": np.__version__, "pandas": pd.__version__,
        "cpu_count": os.cpu_count(),
        "note": ("Timings are wall-clock on one machine and are indicative, not a "
                 "specification. Peak RSS is process-wide and cumulative, so it only "
                 "ever rises; rss_growth_mb is the increase attributable to a stage."),
    }
    with open(os.path.join(a.out, "performance_environment.json"), "w") as fh:
        json.dump(env, fh, indent=2)
    print(f"\nwrote {os.path.join(a.out, 'performance.csv')} ({len(table)} measurements)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
