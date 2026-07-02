"""Multiple-testing correction.

Implemented natively (not delegated) so the adjustment is transparent and
inspectable. Supported methods:

* ``none``         - no adjustment
* ``bonferroni``   - p_adj = min(1, p * m)
* ``holm``         - Holm-Bonferroni step-down
* ``benjamini_hochberg`` (aliases: ``bh``, ``fdr_bh``, ``fdr``) - BH FDR step-up

All functions preserve input order and treat ``None``/NaN p-values as missing
(they are excluded from ``m`` and returned as ``None``). Tests cross-check the
output against ``statsmodels.stats.multitest.multipletests``.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

_CANONICAL = {
    "none": "none",
    "bonferroni": "bonferroni",
    "holm": "holm",
    "holm-bonferroni": "holm",
    "bh": "benjamini_hochberg",
    "fdr": "benjamini_hochberg",
    "fdr_bh": "benjamini_hochberg",
    "benjamini_hochberg": "benjamini_hochberg",
    "benjamini-hochberg": "benjamini_hochberg",
}

DISPLAY_NAMES = {
    "none": "no correction",
    "bonferroni": "Bonferroni correction",
    "holm": "Holm-Bonferroni correction",
    "benjamini_hochberg": "Benjamini-Hochberg FDR correction",
}


def canonical_method(method: Optional[str]) -> str:
    if not method:
        return "none"
    key = str(method).strip().lower().replace(" ", "_")
    return _CANONICAL.get(key, _CANONICAL.get(key.replace("_", "-"), "none"))


def _valid_index(pvals: Sequence[Optional[float]]) -> List[int]:
    idx = []
    for i, p in enumerate(pvals):
        if p is None:
            continue
        try:
            fp = float(p)
        except (TypeError, ValueError):
            continue
        if math.isnan(fp):
            continue
        idx.append(i)
    return idx


def adjust_pvalues(
    pvals: Sequence[Optional[float]],
    method: str = "benjamini_hochberg",
    alpha: float = 0.05,
) -> Tuple[List[Optional[float]], List[Optional[bool]], str]:
    """Adjust a list of p-values.

    Returns ``(adjusted, reject, canonical_method)`` where ``adjusted`` and
    ``reject`` align with the input order; missing p-values map to ``None``.
    ``reject`` is the significance decision at ``alpha`` (based on the adjusted
    p-value; for ``none`` it is based on the raw p-value).
    """
    meth = canonical_method(method)
    n = len(pvals)
    adjusted: List[Optional[float]] = [None] * n
    reject: List[Optional[bool]] = [None] * n

    idx = _valid_index(pvals)
    m = len(idx)
    if m == 0:
        return adjusted, reject, meth
    p = [float(pvals[i]) for i in idx]

    if meth == "none":
        adj = list(p)
    elif meth == "bonferroni":
        adj = [min(1.0, pi * m) for pi in p]
    elif meth == "holm":
        order = sorted(range(m), key=lambda k: p[k])
        adj_sorted = [0.0] * m
        running = 0.0
        for rank, k in enumerate(order):
            val = (m - rank) * p[k]
            running = max(running, val)          # enforce monotonicity
            adj_sorted[k] = min(1.0, running)
        adj = adj_sorted
    elif meth == "benjamini_hochberg":
        order = sorted(range(m), key=lambda k: p[k])
        adj_sorted = [0.0] * m
        running = 1.0
        # step-up: iterate from largest p to smallest, enforce monotone non-decreasing
        for rank in range(m - 1, -1, -1):
            k = order[rank]
            val = p[k] * m / (rank + 1)
            running = min(running, val)
            adj_sorted[k] = min(1.0, running)
        adj = adj_sorted
    else:  # pragma: no cover - canonical_method guards this
        adj = list(p)

    for local, i in enumerate(idx):
        adjusted[i] = float(adj[local])
        decision_p = adjusted[i] if meth != "none" else p[local]
        reject[i] = bool(decision_p is not None and decision_p < alpha)
    return adjusted, reject, meth


def apply_correction(results, method: str = "benjamini_hochberg", alpha: float = 0.05) -> str:
    """Populate ``adjusted_p_value``/``correction_method``/``reject_null`` on a
    list of :class:`~make_my_figure_core.statistics.models.StatResult`.

    Only results with a finite ``p_value`` participate in the family. Returns
    the canonical correction method used.
    """
    pvals = [r.p_value for r in results]
    adjusted, reject, meth = adjust_pvalues(pvals, method=method, alpha=alpha)
    for r, adj, rej in zip(results, adjusted, reject):
        r.alpha = alpha
        r.correction_method = meth
        if meth == "none":
            r.adjusted_p_value = None
            r.reject_null = bool(r.p_value is not None and r.p_value < alpha)
        else:
            r.adjusted_p_value = adj
            r.reject_null = rej
    return meth
