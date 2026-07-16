"""Feature-level differential summary for a *normalized* feature matrix.

This is a generic per-feature comparison between user-defined groups — NOT a
raw-count differential-expression pipeline and NOT a count-based model, and it
uses no R. The user confirms the value scale, the groups,
and the test; every reported p-value / adjusted p-value / effect size traces to
the returned table.

Fold-change rules (never inferred silently):
  * ``log_normalized`` -> effect is the mean difference on the log scale
    (which *is* the log2 fold change when the data are log2);
  * ``normalized`` / ``raw_numeric`` (linear, non-negative) -> log2 fold change
    of (mean_a + pseudocount) / (mean_b + pseudocount);
  * ``unknown_user_confirmed`` -> report the mean difference only and warn that a
    ratio fold change needs a confirmed scale.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats

from make_my_figure_core.matrix_workflow.matrix_spec import MatrixSpec
from make_my_figure_core.matrix_workflow.metadata_spec import SampleMetadataSpec

TWO_GROUP_TESTS = ("welch_t", "students_t", "mann_whitney", "paired_t", "wilcoxon")
MULTI_GROUP_TESTS = ("anova", "kruskal")
CORRECTIONS = ("benjamini_hochberg", "bonferroni", "holm")
_TEST_LABELS = {
    "welch_t": "Welch's t-test", "students_t": "Student's t-test",
    "mann_whitney": "Mann-Whitney U test", "paired_t": "paired t-test",
    "wilcoxon": "Wilcoxon signed-rank test", "anova": "one-way ANOVA",
    "kruskal": "Kruskal-Wallis test",
}
_CORR_LABELS = {"benjamini_hochberg": "Benjamini-Hochberg FDR",
                "bonferroni": "Bonferroni", "holm": "Holm"}


@dataclass
class DifferentialSummary:
    table: pd.DataFrame
    test_name: str
    correction_method: str
    groups: List[str]
    value_type: str
    warnings: List[str] = field(default_factory=list)
    method_sentence_text: str = ""
    source_matrix_id: Optional[str] = None       # provenance: which (derived) matrix
    preprocessing_spec_id: Optional[str] = None  # provenance: which preprocessing chain

    def method_sentence(self) -> str:
        return self.method_sentence_text


def _correct(pvals: np.ndarray, method: str) -> np.ndarray:
    from statsmodels.stats.multitest import multipletests

    finite = np.isfinite(pvals)
    adj = np.full_like(pvals, np.nan, dtype=float)
    if finite.sum() == 0:
        return adj
    key = {"benjamini_hochberg": "fdr_bh", "bonferroni": "bonferroni", "holm": "holm"}[method]
    adj[finite] = multipletests(pvals[finite], method=key)[1]
    return adj


def feature_differential_summary(
    df: pd.DataFrame, matrix_spec: MatrixSpec, metadata: SampleMetadataSpec, *,
    group_a: str, group_b: Optional[str] = None, test: str = "welch_t",
    correction: str = "benjamini_hochberg", pseudocount: float = 1.0,
    preprocessing_note: str = "", source_matrix_id: Optional[str] = None,
    preprocessing_spec_id: Optional[str] = None,
) -> DifferentialSummary:
    """Compute a feature-level differential summary. See module docstring.

    ``preprocessing_note`` (e.g. from ``PreprocessingSpec.method_sentence()``) is
    prepended to the method sentence so a plot annotation traces back to how the
    matrix was processed; ``source_matrix_id`` / ``preprocessing_spec_id`` record
    the provenance on the returned summary."""
    if not matrix_spec.confirmed_by_user:
        raise ValueError("MatrixSpec must be confirmed before a differential summary.")
    if not metadata.confirmed_by_user:
        raise ValueError("SampleMetadataSpec must be confirmed before a differential summary.")

    frame = matrix_spec.feature_frame(df)  # features x samples (numeric)
    fid = matrix_spec.feature_id_column or "feature_id"
    feats = list(frame.index)
    warnings: List[str] = []

    groups = metadata.groups()
    is_multi = test in MULTI_GROUP_TESTS
    if not is_multi:
        if group_b is None:
            others = [g for g in groups if g != group_a]
            if len(others) < 1:
                raise ValueError("Two-group test needs at least two groups; specify group_b.")
            group_b = others[0]
        if group_a == group_b:
            raise ValueError(
                "Group A and Group B are the same — a two-group comparison needs two "
                "different groups. Pick distinct groups (or choose a different test).")
        used_groups = [group_a, group_b]
    else:
        used_groups = groups

    def cols_for(g: str) -> List[str]:
        return [s for s in metadata.samples_in_group(g) if s in frame.columns]

    group_cols = {g: cols_for(g) for g in used_groups}
    for g, cs in group_cols.items():
        if len(cs) < 2:
            warnings.append(f"Group '{g}' has {len(cs)} sample(s); results may be unreliable.")

    records: List[Dict[str, Any]] = []
    labels = matrix_spec.display_labels(df)
    label_by_feat = dict(zip(feats, labels)) if labels is not None else {}
    ann_cols = [c for c in matrix_spec.annotation_columns if c in df.columns]
    ann_by_feat = (df.set_index(matrix_spec.feature_id_column)[ann_cols]
                   if matrix_spec.feature_id_column in df.columns and ann_cols else None)

    pvals: List[float] = []
    if not is_multi:
        A = frame[group_cols[group_a]].to_numpy(dtype=float)
        B = frame[group_cols[group_b]].to_numpy(dtype=float)
        for i, feat in enumerate(feats):
            a = A[i][np.isfinite(A[i])]
            b = B[i][np.isfinite(B[i])]
            rec = _two_group_record(feat, a, b, test, matrix_spec.value_type, pseudocount)
            rec[fid] = feat
            records.append(rec)
            pvals.append(rec["p_value"])
    else:
        arrs = [frame[group_cols[g]].to_numpy(dtype=float) for g in used_groups]
        for i, feat in enumerate(feats):
            samples = [a[i][np.isfinite(a[i])] for a in arrs]
            rec = _multi_group_record(feat, samples, test, used_groups)
            rec[fid] = feat
            records.append(rec)
            pvals.append(rec["p_value"])

    p = np.asarray(pvals, dtype=float)
    adj = _correct(p, correction)
    for rec, a in zip(records, adj):
        rec["adjusted_p_value"] = float(a) if np.isfinite(a) else np.nan
        rec["correction_method"] = correction
        rec["test_name"] = test
        # attach label + annotations
        rec["feature_label"] = str(label_by_feat.get(rec[fid], rec[fid]))
        if ann_by_feat is not None and rec[fid] in ann_by_feat.index:
            for c in ann_cols:
                val = ann_by_feat.loc[rec[fid], c]
                rec[c] = val if not isinstance(val, pd.Series) else val.iloc[0]

    # column order
    base = [fid, "feature_label", *ann_cols]
    stat_cols = ["n_a", "n_b", "mean_a", "mean_b", "median_a", "median_b",
                 "effect_type", "log2_fold_change", "mean_difference",
                 "statistic", "effect_size", "ci_low", "ci_high",
                 "p_value", "adjusted_p_value", "correction_method", "test_name"]
    table = pd.DataFrame(records)
    ordered = [c for c in base + stat_cols if c in table.columns]
    ordered += [c for c in table.columns if c not in ordered]
    table = table[ordered]

    scale_note = {
        "log_normalized": "log-scale data: effect is the mean difference (log2 fold change).",
        "normalized": "linear data: log2 fold change of group means (+pseudocount).",
        "raw_numeric": "linear data: log2 fold change of group means (+pseudocount).",
        "unknown_user_confirmed": "scale unconfirmed: reporting mean difference only.",
    }.get(matrix_spec.value_type, "")
    if matrix_spec.value_type == "unknown_user_confirmed":
        warnings.append("Value scale is unconfirmed — ratio fold change not computed; "
                        "confirm value_type to enable log2 fold change.")
    grp = " vs ".join(used_groups)
    prep = ""
    if preprocessing_note and preprocessing_note.strip() and \
            "No preprocessing" not in preprocessing_note:
        prep = preprocessing_note.strip().rstrip(".") + ", then "
    sentence = (f"{prep}compared between {grp} using a feature-level differential summary "
                f"({_TEST_LABELS.get(test, test)}, {_CORR_LABELS.get(correction, correction)}). "
                f"Not a raw-count differential-expression model. {scale_note}").strip()
    return DifferentialSummary(table=table, test_name=test, correction_method=correction,
                               groups=used_groups, value_type=matrix_spec.value_type,
                               warnings=warnings, method_sentence_text=sentence,
                               source_matrix_id=source_matrix_id,
                               preprocessing_spec_id=preprocessing_spec_id)


def _fold_change(mean_a: float, mean_b: float, value_type: str, pseudocount: float):
    """Return (effect_type, log2_fold_change, mean_difference)."""
    mean_diff = mean_a - mean_b
    if value_type == "log_normalized":
        # data already log-scale -> the difference of log-means IS log2 FC
        return "log2_fold_change", mean_diff, mean_diff
    if value_type in ("normalized", "raw_numeric"):
        num, den = mean_a + pseudocount, mean_b + pseudocount
        if num > 0 and den > 0:
            return "log2_fold_change", float(np.log2(num / den)), mean_diff
        return "mean_difference", np.nan, mean_diff
    return "mean_difference", np.nan, mean_diff


def _two_group_record(feat, a, b, test, value_type, pseudocount) -> Dict[str, Any]:
    na, nb = int(a.size), int(b.size)
    mean_a = float(np.mean(a)) if na else np.nan
    mean_b = float(np.mean(b)) if nb else np.nan
    med_a = float(np.median(a)) if na else np.nan
    med_b = float(np.median(b)) if nb else np.nan
    stat = pval = eff = ci_lo = ci_hi = np.nan
    if na >= 1 and nb >= 1:
        try:
            if test == "welch_t":
                stat, pval = stats.ttest_ind(a, b, equal_var=False)
                eff, ci_lo, ci_hi = _cohen_d_ci(a, b)
            elif test == "students_t":
                stat, pval = stats.ttest_ind(a, b, equal_var=True)
                eff, ci_lo, ci_hi = _cohen_d_ci(a, b)
            elif test == "mann_whitney":
                stat, pval = stats.mannwhitneyu(a, b, alternative="two-sided")
                eff = 1.0 - (2.0 * stat) / (na * nb) if na * nb else np.nan  # rank-biserial
            elif test == "paired_t":
                n = min(na, nb)
                stat, pval = stats.ttest_rel(a[:n], b[:n])
                eff, ci_lo, ci_hi = _cohen_d_ci(a[:n], b[:n])
            elif test == "wilcoxon":
                n = min(na, nb)
                stat, pval = stats.wilcoxon(a[:n], b[:n])
            else:
                raise ValueError(f"Unknown two-group test: {test}")
        except Exception:
            stat = pval = np.nan
    eff_type, log2fc, mean_diff = _fold_change(mean_a, mean_b, value_type, pseudocount)
    return {"n_a": na, "n_b": nb, "mean_a": mean_a, "mean_b": mean_b,
            "median_a": med_a, "median_b": med_b, "effect_type": eff_type,
            "log2_fold_change": log2fc, "mean_difference": mean_diff,
            "statistic": float(stat) if np.isfinite(stat) else np.nan,
            "effect_size": float(eff) if np.isfinite(eff) else np.nan,
            "ci_low": float(ci_lo) if np.isfinite(ci_lo) else np.nan,
            "ci_high": float(ci_hi) if np.isfinite(ci_hi) else np.nan,
            "p_value": float(pval) if np.isfinite(pval) else np.nan}


def _multi_group_record(feat, samples, test, group_names) -> Dict[str, Any]:
    nonempty = [s for s in samples if s.size >= 1]
    stat = pval = np.nan
    if len(nonempty) >= 2:
        try:
            if test == "anova":
                stat, pval = stats.f_oneway(*nonempty)
            elif test == "kruskal":
                stat, pval = stats.kruskal(*nonempty)
        except Exception:
            stat = pval = np.nan
    rec = {"statistic": float(stat) if np.isfinite(stat) else np.nan,
           "p_value": float(pval) if np.isfinite(pval) else np.nan,
           "n_groups": len(nonempty)}
    for g, s in zip(group_names, samples):
        rec[f"mean_{g}"] = float(np.mean(s)) if s.size else np.nan
    return rec


def _cohen_d_ci(a, b):
    """Cohen's d and an approximate 95% CI for the mean difference (t-based)."""
    na, nb = a.size, b.size
    if na < 2 or nb < 2:
        return np.nan, np.nan, np.nan
    va, vb = np.var(a, ddof=1), np.var(b, ddof=1)
    sp = np.sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2))
    d = (np.mean(a) - np.mean(b)) / sp if sp > 0 else np.nan
    se = np.sqrt(va / na + vb / nb)
    diff = np.mean(a) - np.mean(b)
    tcrit = stats.t.ppf(0.975, max(1, na + nb - 2))
    return float(d), float(diff - tcrit * se), float(diff + tcrit * se)
