"""A basic in-app differential screen for a NORMALIZED matrix (no R).

Given a normalized features x samples matrix (e.g. voom / log2-CPM / log2-TPM) and
a two-group sample assignment, compute per-feature group differences:

* ``log2FoldChange`` — from group means (a difference of means when the input is
  already log2, else log2 of the ratio),
* ``pvalue`` — a per-feature Welch's t-test (default) or Mann-Whitney U test,
* ``padj`` — Benjamini-Hochberg FDR across features,
* ``AveExpr`` — mean across all used samples (for an MA plot).

**Scope / honesty (important):** this is a *basic exploratory screen*, not a
count-based differential-expression model. It is NOT DESeq2 / edgeR / limma-voom
and does not model count dispersion, library size, or design covariates. For
publication-grade differential expression from raw counts, run a proper tool and
load its results table. This screen is intended for a normalized/log matrix so a
user can quickly produce a volcano/MA-style results table in-app; every value is
computed transparently and traceable to the inputs (nothing is fabricated).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Per-feature test choices — the two-group tests already in the app's statistics
# engine (see statistics.TESTS). No count-based / RNA-seq-specific models.
TESTS = ("welch_t", "students_t", "mann_whitney")
_TEST_LABELS = {"welch_t": "Welch's t-test", "students_t": "Student's t-test",
                "mann_whitney": "Mann-Whitney U test"}


@dataclass
class DifferentialResult:
    table: pd.DataFrame
    method: str
    reference_group: str
    test_group: str
    n_reference: int
    n_test: int
    n_features_tested: int
    log_input: bool
    warnings: List[str] = field(default_factory=list)

    def method_sentence(self) -> str:
        test = _TEST_LABELS.get(self.method, self.method)
        scale = "log2 (difference of means)" if self.log_input else "log2 ratio of means"
        return (f"Basic differential screen (NOT a count-based model such as DESeq2/edgeR/"
                f"limma-voom): per-feature {test} of '{self.test_group}' (n={self.n_test}) vs "
                f"reference '{self.reference_group}' (n={self.n_reference}) on the supplied "
                f"normalized matrix; log2 fold-change as {scale}; Benjamini-Hochberg FDR across "
                f"{self.n_features_tested} tested features.")


def _bh_fdr(pvals: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg adjusted p-values; NaN p's stay NaN and are excluded."""
    p = np.asarray(pvals, dtype=float)
    adj = np.full(p.shape, np.nan)
    mask = np.isfinite(p)
    m = int(mask.sum())
    if m == 0:
        return adj
    idx = np.where(mask)[0]
    order = idx[np.argsort(p[idx])]
    ranked = p[order] * m / (np.arange(1, m + 1))
    # enforce monotonicity from the largest rank down
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    adj[order] = np.clip(ranked, 0, 1)
    return adj


def differential_screen(df: pd.DataFrame, *, feature_col: str,
                        group_labels: Dict[str, str], test: str = "welch_t",
                        log_input: bool = True,
                        reference_group: Optional[str] = None) -> DifferentialResult:
    """Run a two-group per-feature differential screen on a normalized matrix.

    ``group_labels`` maps sample column -> group name (blank/None = excluded).
    Exactly two non-empty groups are required. ``reference_group`` (else the
    alphabetically first) is the denominator; log2FC is test-vs-reference.
    """
    from scipy import stats

    if test not in TESTS:
        raise ValueError(f"Unknown test '{test}'. Options: {TESTS}")
    if feature_col not in df.columns:
        raise ValueError(f"Feature column '{feature_col}' not found.")
    assigned = {s: g for s, g in group_labels.items()
                if s in df.columns and str(g).strip() != ""}
    groups = sorted(set(assigned.values()))
    if len(groups) != 2:
        raise ValueError(f"Differential screen needs exactly 2 groups; got {len(groups)}: {groups}.")
    ref = reference_group if reference_group in groups else groups[0]
    test_g = [g for g in groups if g != ref][0]
    a_cols = [s for s, g in assigned.items() if g == ref]     # reference
    b_cols = [s for s, g in assigned.items() if g == test_g]  # test
    warnings: List[str] = []
    if len(a_cols) < 2 or len(b_cols) < 2:
        warnings.append("At least 2 samples per group are recommended; p-values may be unreliable.")

    features = df[feature_col].astype(str).to_numpy()
    A = df[a_cols].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
    B = df[b_cols].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)

    # This screen expects a NORMALIZED matrix. Warn (don't block) if the values
    # look like raw counts — the app does not normalize; the user should supply a
    # normalized/log matrix (e.g. voom / log2-CPM) before running.
    allvals = np.concatenate([A, B], axis=1)
    finite = allvals[np.isfinite(allvals)]
    if finite.size and float(np.nanmin(finite)) >= 0 and float(np.nanmax(finite)) >= 1000 \
            and float(np.nanmax(finite)) > 50 * (float(np.nanmedian(finite)) + 1):
        warnings.append("Values look like raw counts (large, non-negative, wide range). This "
                        "screen expects a NORMALIZED matrix (e.g. voom / log2-CPM); normalize "
                        "before running, or results/log2FC may be misleading.")

    mean_a = np.nanmean(A, axis=1)
    mean_b = np.nanmean(B, axis=1)
    ave = np.nanmean(np.concatenate([A, B], axis=1), axis=1)
    if log_input:
        log2fc = mean_b - mean_a
    else:
        eps = 1e-9
        log2fc = np.log2((np.clip(mean_b, 0, None) + eps) / (np.clip(mean_a, 0, None) + eps))

    with np.errstate(all="ignore"):
        if test in ("welch_t", "students_t"):
            res = stats.ttest_ind(B, A, axis=1, equal_var=(test == "students_t"),
                                  nan_policy="omit")
            stat = np.asarray(res.statistic, dtype=float)
            pvals = np.asarray(res.pvalue, dtype=float)
        else:  # mann_whitney (per-feature loop; not vectorised in scipy)
            stat = np.full(len(features), np.nan)
            pvals = np.full(len(features), np.nan)
            for i in range(len(features)):
                # Rank tests must see mathematically equal values as ties. Log-CPM of
                # zero counts is identical across libraries in exact arithmetic but can
                # differ in the last bit, which broke ties arbitrarily (an all-zero gene
                # scored p = 0.28 instead of 1). Rounding to 12 decimals restores the ties.
                a = np.round(A[i][np.isfinite(A[i])], 12)
                b = np.round(B[i][np.isfinite(B[i])], 12)
                if a.size >= 1 and b.size >= 1 and not (np.all(a == b[0]) and np.all(b == b[0])):
                    try:
                        u = stats.mannwhitneyu(b, a, alternative="two-sided")
                        stat[i], pvals[i] = float(u.statistic), float(u.pvalue)
                    except ValueError:
                        pass
    # scalars -> arrays (scipy can return 0-d when one feature)
    stat = np.atleast_1d(stat).astype(float)
    pvals = np.atleast_1d(pvals).astype(float)
    pvals = np.where(np.isfinite(pvals), pvals, np.nan)
    padj = _bh_fdr(pvals)

    table = pd.DataFrame({
        feature_col: features,
        "log2FoldChange": log2fc,
        "AveExpr": ave,
        f"mean_{ref}": mean_a,
        f"mean_{test_g}": mean_b,
        "stat": stat,
        "pvalue": pvals,
        "padj": padj,
    })
    return DifferentialResult(
        table=table, method=test, reference_group=ref, test_group=test_g,
        n_reference=len(a_cols), n_test=len(b_cols),
        n_features_tested=int(np.isfinite(pvals).sum()), log_input=log_input,
        warnings=warnings)
