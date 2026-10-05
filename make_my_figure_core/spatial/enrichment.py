"""Cell-type / cellular-neighbourhood enrichment, and neighbourhood QC.

The enrichment score is the published CNTools definition (Tao et al. 2024, PLOS
Comput Biol 20(8):e1012344, "CN analysis methods / CT Enrichment"): the log
ratio of the frequency of cell type ``t`` in neighbourhood ``n`` to its overall
frequency, with the pseudocounts the paper specifies,

    score(t, n) = log2( (|C_n,t| + F(t)) / (|C_n| + 1) ) - log2( F(t) )

where ``|C_n,t|`` is the number of cells of type ``t`` in neighbourhood ``n``,
``|C_n|`` the number of cells in ``n``, and ``F(t)`` the overall frequency
(proportion, not count) of ``t`` across all cells.

Purity uses the paper's Shannon entropy of cell type conditioned on neighbourhood,

    H(CT|CN) = sum_{n,t} |C_n,t|/|C| * log2( |C_n| / |C_n,t| )

Reported as a number, never as a verdict: a purer neighbourhood is not
automatically a more biologically meaningful one.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

import numpy as np
import pandas as pd

from make_my_figure_core.spatial.neighbors import SpatialError


def contingency(cell_types: pd.Series, neighborhoods: pd.Series,
                *, ct_levels: Optional[Sequence[str]] = None,
                cn_levels: Optional[Sequence[str]] = None) -> pd.DataFrame:
    """|C_n,t| as a (neighbourhood x cell type) table with explicit level order."""
    ct = cell_types.astype(str)
    cn = neighborhoods.astype(str)
    ctl = [str(v) for v in ct_levels] if ct_levels is not None else sorted(ct.unique())
    cnl = [str(v) for v in cn_levels] if cn_levels is not None else sorted(cn.unique())
    tab = pd.crosstab(cn, ct)
    return tab.reindex(index=cnl, columns=ctl, fill_value=0).astype(float)


def ct_cn_enrichment(cell_types: pd.Series, neighborhoods: pd.Series,
                     *, ct_levels: Optional[Sequence[str]] = None,
                     cn_levels: Optional[Sequence[str]] = None) -> pd.DataFrame:
    """Tidy CT-CN enrichment table, one row per (neighbourhood, cell type)."""
    counts = contingency(cell_types, neighborhoods, ct_levels=ct_levels, cn_levels=cn_levels)
    total = float(counts.to_numpy().sum())
    if total <= 0:
        raise SpatialError("no cells available for enrichment.")

    overall_freq = counts.sum(axis=0) / total          # F(t)
    cn_size = counts.sum(axis=1)                       # |C_n|

    rows = []
    for n in counts.index:
        size_n = float(cn_size.loc[n])
        for t in counts.columns:
            c_nt = float(counts.loc[n, t])
            f_t = float(overall_freq.loc[t])
            if f_t <= 0:
                score = float("nan")
            else:
                score = np.log2((c_nt + f_t) / (size_n + 1.0)) - np.log2(f_t)
            rows.append({
                "neighborhood": n,
                "cell_type": t,
                "enrichment_score": score,
                "cell_type_frequency_in_neighborhood": (c_nt / size_n) if size_n else float("nan"),
                "cell_count": int(c_nt),
                "neighborhood_count": int(size_n),
                "overall_cell_type_frequency": f_t,
            })
    return pd.DataFrame(rows)


def conditional_entropy(cell_types: pd.Series, neighborhoods: pd.Series) -> float:
    """H(CT|CN) in bits, by the paper's formula. Lower means more homogeneous."""
    counts = contingency(cell_types, neighborhoods)
    total = float(counts.to_numpy().sum())
    if total <= 0:
        return float("nan")
    cn_size = counts.sum(axis=1)
    h = 0.0
    for n in counts.index:
        size_n = float(cn_size.loc[n])
        if size_n <= 0:
            continue
        for t in counts.columns:
            c_nt = float(counts.loc[n, t])
            if c_nt <= 0:                      # 0 * log(1/0) -> 0 by convention
                continue
            h += (c_nt / total) * np.log2(size_n / c_nt)
    return float(h)


def neighborhood_qc(cell_types: pd.Series, neighborhoods: pd.Series,
                    *, samples: Optional[pd.Series] = None,
                    rare_fraction: float = 0.01) -> pd.DataFrame:
    """Per-neighbourhood diagnostics. Metrics only — no judgement about quality."""
    counts = contingency(cell_types, neighborhoods)
    total = float(counts.to_numpy().sum())
    rows = []
    for n in counts.index:
        row = counts.loc[n]
        size = float(row.sum())
        frac = row / size if size else row * np.nan
        nz = frac[frac > 0]
        entropy = float(-(nz * np.log2(nz)).sum()) if len(nz) else float("nan")
        dominant = str(row.idxmax()) if size else ""
        rec = {
            "neighborhood": n,
            "n_cells": int(size),
            "fraction_of_all_cells": (size / total) if total else float("nan"),
            "dominant_cell_type": dominant,
            "dominant_fraction": float(frac.max()) if size else float("nan"),
            "shannon_entropy_bits": entropy,
            "n_cell_types_present": int((row > 0).sum()),
            "is_rare": bool(total and (size / total) < rare_fraction),
        }
        if samples is not None:
            mask = neighborhoods.astype(str) == n
            rec["n_samples_represented"] = int(samples[mask].nunique())
        rows.append(rec)
    return pd.DataFrame(rows)
