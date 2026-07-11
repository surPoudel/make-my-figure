"""Publication-QC: independent statistics oracle validation.

Recomputes every implemented test from raw data with scipy/statsmodels (not the
app's code path) and asserts each reported field matches within a tight
tolerance. Backed by ``scripts/statistics_oracle.py`` so the same checks produce
``outputs/publication_qc/statistics_oracle_results.md``.
"""

import os
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from scripts.statistics_oracle import run_oracle

_ROWS = run_oracle()


def test_oracle_ran_and_covered_all_tests():
    tests_seen = {r["test"] for r in _ROWS}
    # Every implemented statistical method must appear in the oracle.
    for expected in ("Student's t", "Welch's t", "Mann-Whitney U", "Paired t",
                     "Wilcoxon", "One-way ANOVA", "Two-way ANOVA [A]", "Kruskal-Wallis",
                     "Chi-square", "Fisher's exact", "Log-rank", "Pearson", "Spearman",
                     "Linear regression", "Correction [benjamini_hochberg]"):
        assert any(t == expected or t.startswith(expected) for t in tests_seen), \
            f"oracle did not cover {expected}"
    assert len(_ROWS) >= 50


@pytest.mark.parametrize("row", _ROWS, ids=[f"{r['test']}:{r['field']}" for r in _ROWS])
def test_stat_matches_reference(row):
    assert row["pass"], (
        f"{row['test']} / {row['field']}: app={row['app']} vs reference={row['ref']} "
        f"({row['tol']}) {row['note']}")
