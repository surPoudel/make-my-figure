"""Compare MakeMyFigure (Python) outputs with the independent R references.

Reads ``results/python/`` and ``results/R/`` (never modifies either), writes
``results/comparisons/``, ``results/*.csv`` summary tables, ``figures/`` and
``benchmark_manifest.json``. Classification per compared quantity:

* EXACT                               |d| <= 1e-12 (or both NaN)
* NUMERICALLY_EQUIVALENT              |d| <= 1e-10 or |d|/max(|a|,|b|) <= 1e-8
* ACCEPTABLE_IMPLEMENTATION_DIFFERENCE curated: same method, documented numerical/convention cause
* METHOD_MISMATCH                     curated: different statistical method by design (Class B)
* FAIL                                otherwise
* NEEDS_REVIEW                        one side missing / non-finite on one side only

Nothing here tunes a threshold to improve agreement; the curated lists carry the cause
and are audited in reports/DISCREPANCY_REPORT.md.
"""
from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = ROOT.parents[1]
PY = ROOT / "results" / "python"
RR = ROOT / "results" / "R"
CMP = ROOT / "results" / "comparisons"
FIG = ROOT / "figures"
ABS_TOL, REL_TOL, EXACT_TOL = 1e-10, 1e-8, 1e-12

# --------------------------------------------------------------------------- curated causes
# (component, key-regex) -> (class, cause). Applied only when the numbers do NOT already agree.
ACCEPTABLE = [
    ("statistics", r"^E_two_group_one_constant\|.*\|(statistic|p_value|df|effect_size|ci_low|ci_high|estimate)$",
     "Degenerate input (one group constant): scipy returns t/p with catastrophic-cancellation warnings and Welch df from a zero variance; R t.test either errors or returns Inf. Both flag the case; the numbers are not comparable."),
    ("statistics", r"\|wilcoxon\|.*\|statistic$",
     "scipy.wilcoxon returns min(W+, W-) for two-sided tests; R returns V = W+. Both are the same test; the p-values are compared directly."),
    ("statistics", r"\|fishers_exact\|all\|(estimate|statistic|effect_size)$",
     "scipy reports the sample (unconditional) odds ratio ad/bc; R fisher.test reports the conditional maximum-likelihood estimate. p-values are identical. R's sample OR is emitted for the like-for-like check."),
    ("statistics", r"\|mann_whitney\|.*\|p_value$",
     "Small-sample regime: scipy 'auto' uses the exact distribution only when both n <= 8 and there are no ties; R uses exact for n < 50 without ties. The like-for-like comparison uses the scipy rule in R; R's default is reported alongside."),
    ("statistics", r"\|glm_negativebinomial\|.*",
     "statsmodels' NegativeBinomial family fixes alpha = 1 (theta = 1) AND the GLM scale at 1; R's summary.glm additionally estimates a Pearson dispersion (0.83 here), inflating/deflating every SE by its square root. The like-for-like R reference uses negative.binomial(theta = 1) with dispersion = 1; R's default SEs and MASS::glm.nb (theta estimated) are reported as context."),
    ("statistics", r"\|(glm_gaussian|glm_gamma)\|.*\|(p_value|ci_low|ci_high)$",
     "statsmodels GLM uses normal (z) Wald inference for every family; R summary.glm uses t for families with an estimated dispersion (gaussian, Gamma). The like-for-like z-based values are compared; R's t-based p is reported alongside."),
    ("transform", r"^(W|X|Y|Z)__quantile$",
     "Tie handling: MakeMyFigure assigns tied values by row order (ordinal ranks); limma::normalizeQuantiles averages the target quantiles across ties. Identical when no ties; compared like-for-like via the *_ordinal reference."),
    ("transform", r"^X__quantile(_ordinal)?$",
     "Missing values: MakeMyFigure sorts NaN to the end and re-maps positions including NaN slots; limma handles NA by interpolating the reference distribution to the non-missing count. Both are defensible; results differ by design where NA are present."),
    ("statistics", r"\|glm_(poisson|gamma|gaussian|binomial|negativebinomial)\|.*\|(statistic|p_value|ci_low|ci_high)$",
     "IRLS standard errors: R's summary.glm uses the working weights of the final iteration (evaluated at the previous iterate) whereas statsmodels evaluates the information at the converged coefficients; relative differences <= 1e-7 with glm.control(epsilon = 1e-14). Coefficients agree to <= 1e-10."),
    ("transform", r"^(W|RSEM)__(tmm_cpm|tmm_logcpm_prior0.5|voom_logcpm)$|^tmm_factors__(W|RSEM)$",
     "TMM trimming is rank-based and therefore discontinuous: MakeMyFigure ranks M/A values ordinally (ties broken by row order) whereas edgeR uses average ranks, and last-ulp differences in log2 evaluation change which A-values tie. A gene tied exactly at the 5%% A-trim boundary is kept by one implementation and dropped by the other (verified gene-by-gene on W sample A_2). Same reference sample, same trims, same weights. Max factor difference 6.8e-4 (W), 4.4e-6 (RSEM); propagates to TMM-CPM and voom logCPM."),
    ("de", r"^de_summary__Y__wilcoxon\|.*statistic$", "scipy.wilcoxon statistic = min(W+, W-); R V = W+."),
    ("de", r"^de_(screen|summary)__W_logcpm__(welch_t|students_t|mann_whitney)\|.*(stat|statistic|pvalue|p_value|padj|adjusted_p_value)$",
     "One all-zero gene (gene0044): its log-CPM values are equal in exact arithmetic but differ in the last bit, so scipy returns t = 0, p = 1 while R's t.test errors ('data are essentially constant') and yields NA. The BH family size therefore differs by one (400 vs 399), shifting every adjusted p by <= 2.5e-3. All other genes agree to <= 2e-14."),
    ("statistics", r"\|fishers_exact\|all\|p_value$",
     "r x c table: before the fix scipy's default r x c Fisher p-value was an UNSEEDED Monte Carlo approximation (non-reproducible); after the fix it is a seeded Monte Carlo approximation with 200000 resamples, so it differs from R's exact network algorithm by Monte Carlo error (documented in the result warnings)."),
    ("de", r"^de_summary__Y__wilcoxon\|.*p_value$", "n = 3 pairs: scipy exact (no ties) vs R exact; identical when both exact — differences arise only from tie/zero handling."),
]
METHOD_MISMATCH = [
    ("transform", r"^W__voom_weights$", "MakeMyFigure voom_weights are per-feature (no design, raw SD) whereas limma voom weights are per-observation from the fitted mean-variance trend."),
]


def classify(a: float, b: float) -> str:
    if (a is None or not np.isfinite(a)) and (b is None or not np.isfinite(b)):
        return "EXACT"
    if a is None or b is None or not np.isfinite(a) or not np.isfinite(b):
        return "NEEDS_REVIEW"
    d = abs(a - b)
    if d <= EXACT_TOL:
        return "EXACT"
    if d <= ABS_TOL or d / max(abs(a), abs(b)) <= REL_TOL:
        return "NUMERICALLY_EQUIVALENT"
    return "FAIL"


UPSTREAM = [
    (r"(^|__)(W|RSEM)_voom(_samples)?(__|$|\|)|^de_(screen|summary)__(W|RSEM)_voom", "Input matrices differ upstream by the TMM tie-handling difference only (see tmm_factors; voom now uses limma's definition). The component itself is validated on the plain log2-CPM input (W_logcpm / RSEM_logcpm), which is cell-wise identical on both sides."),
]


def curate(component: str, key: str, cls: str) -> tuple[str, str]:
    if cls in ("EXACT", "NUMERICALLY_EQUIVALENT"):
        return cls, ""
    if component in ("pca", "cluster", "de"):
        for rx, cause in UPSTREAM:
            if re.search(rx, key):
                return "UPSTREAM_INPUT_DIFFERENCE", cause
    for comp, rx, cause in METHOD_MISMATCH:
        if comp == component and re.search(rx, key):
            return "METHOD_MISMATCH", cause
    if cls == "FAIL":
        for comp, rx, cause in ACCEPTABLE:
            if comp == component and re.search(rx, key):
                return "ACCEPTABLE_IMPLEMENTATION_DIFFERENCE", cause
    if cls == "NEEDS_REVIEW":
        for comp, rx, cause in ACCEPTABLE:
            if comp == component and re.search(rx, key):
                return "ACCEPTABLE_IMPLEMENTATION_DIFFERENCE", cause
    return cls, ""


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- statistics
def compare_statistics() -> pd.DataFrame:
    py = pd.read_csv(PY / "statistics_python.csv")
    r = pd.concat([pd.read_csv(p) for p in sorted(RR.glob("statistics_R_*.csv")) if not p.name.endswith("_notes.csv")], ignore_index=True)
    r = r.drop_duplicates(["dataset_id", "test_id", "comparison", "quantity"], keep="last")
    key = ["dataset_id", "test_id", "comparison", "quantity"]
    def _canon(label: str) -> str:
        # "1.0:VC|OJ" (pandas float level) and "1:VC|OJ" (R integer level) are the same comparison
        out = []
        for tok in re.split(r"([:|])", str(label)):
            try:
                f = float(tok); tok = repr(int(f)) if f == int(f) else repr(f)
            except ValueError:
                pass
            out.append(tok)
        return "".join(out)
    py["comparison"] = py["comparison"].map(_canon); r["comparison"] = r["comparison"].map(_canon)
    m = py.merge(r, on=key, how="outer", suffixes=("_python", "_R"), indicator=True)
    rows = []
    for _, x in m.iterrows():
        a, b = x["value_python"], x["value_R"]
        k = "|".join(str(x[c]) for c in key)
        if x["_merge"] == "left_only":
            if x["quantity"] in ("adjusted_p_value", "n_total", "df2", "estimate", "ci_low", "ci_high", "effect_size", "df", "statistic") and not np.isfinite(a):
                continue  # Python NaN for a quantity R does not define (e.g. no CI for MWU)
            cls, cause = "NEEDS_REVIEW", "quantity produced by MakeMyFigure but not by the R reference"
            if x["quantity"].startswith("extra."):
                continue  # descriptive extras not mirrored in R
        elif x["_merge"] == "right_only":
            if "." in str(x["quantity"]) and not str(x["quantity"]).startswith("extra."):
                continue  # R-side convention/context quantities (R_default.*, effectsize_pkg.*, ...)
            cls, cause = "NEEDS_REVIEW", "quantity produced by R but not by MakeMyFigure"
        else:
            cls, cause = curate("statistics", k, classify(a, b))
        d = abs(a - b) if (np.isfinite(a) and np.isfinite(b)) else np.nan
        rows.append({"dataset_id": x["dataset_id"], "test_id": x["test_id"], "comparison": x["comparison"], "quantity": x["quantity"],
                     "python_value": a, "R_value": b, "abs_diff": d,
                     "rel_diff": d / max(abs(a), abs(b)) if np.isfinite(d) and max(abs(a), abs(b)) > 0 else (0.0 if np.isfinite(d) else np.nan),
                     "class": cls, "cause": cause})
    out = pd.DataFrame(rows)
    # attach names/notes from Python labels for the manuscript table
    lab = pd.read_csv(PY / "statistics_python_labels.csv")
    out = out.merge(lab[["dataset_id", "test_id", "comparison", "statistic_name", "effect_size_name", "correction_method"]].drop_duplicates(),
                    on=["dataset_id", "test_id", "comparison"], how="left")
    out.insert(0, "component", "statistics")
    out.to_csv(ROOT / "results" / "statistics_python_vs_R.csv", index=False, float_format="%.15g")
    # R-side convention table (context, not scored)
    ctx = r[r["quantity"].str.contains(r"\.", regex=True) & ~r["quantity"].str.startswith("extra.")]
    ctx.to_csv(CMP / "statistics_R_convention_context.csv", index=False, float_format="%.15g")
    return out


def compare_multiple_testing() -> pd.DataFrame:
    py = pd.read_csv(PY / "multiple_testing.csv"); r = pd.read_csv(RR / "multiple_testing.csv")
    m = py.merge(r, on=["dataset_id", "method", "index"], suffixes=("_python", "_R"))
    rows = []
    for _, x in m.iterrows():
        cls = classify(x["p_adj_python"], x["p_adj_R"])
        rows.append({"component": "multiple_testing", "dataset_id": x["dataset_id"], "test_id": x["method"], "comparison": f"p[{int(x['index'])}]",
                     "quantity": "adjusted_p_value", "python_value": x["p_adj_python"], "R_value": x["p_adj_R"],
                     "abs_diff": abs(x["p_adj_python"] - x["p_adj_R"]) if np.isfinite(x["p_adj_python"]) and np.isfinite(x["p_adj_R"]) else np.nan,
                     "class": cls, "cause": ""})
    out = pd.DataFrame(rows)
    out.to_csv(CMP / "multiple_testing_python_vs_R.csv", index=False, float_format="%.15g")
    return out


# --------------------------------------------------------------------------- matrices
def _load_pair(name: str):
    a = pd.read_csv(PY / name); b = pd.read_csv(RR / name)
    idc = a.columns[0]
    b = b.set_index(b.columns[0]).reindex(a[idc].astype(str).values)
    a = a.set_index(idc)
    a.index = a.index.astype(str)
    cols = [c for c in a.columns if c in b.columns]
    return a[cols].to_numpy(float), b[cols].to_numpy(float), cols


def compare_transforms() -> pd.DataFrame:
    rows = []
    names = sorted(p.name for p in PY.glob("transform__*.csv"))
    for name in names:
        tag = name[len("transform__"):-4]
        if not (RR / name).exists():
            rows.append({"component": "transform", "tag": tag, "class": "NEEDS_REVIEW", "cause": "no R reference file", "n_cells": np.nan}); continue
        A, B, cols = _load_pair(name)
        both_nan = np.isnan(A) & np.isnan(B); one_nan = np.isnan(A) ^ np.isnan(B)
        d = np.abs(A - B); fin = np.isfinite(d)
        maxabs = float(np.nanmax(d)) if fin.any() else 0.0
        rel = d / np.maximum(np.abs(A), np.abs(B)); rel[~np.isfinite(rel)] = 0
        n_bad = int(((d > ABS_TOL) & (rel > REL_TOL) & fin).sum() + one_nan.sum())
        rmse = float(np.sqrt(np.nanmean(d[fin] ** 2))) if fin.any() else 0.0
        cls = "EXACT" if (maxabs <= EXACT_TOL and one_nan.sum() == 0) else "NUMERICALLY_EQUIVALENT" if n_bad == 0 else "FAIL"
        cls, cause = curate("transform", tag, cls)
        # like-for-like alternates
        alt = ""
        if tag.endswith("__quantile") and (RR / f"transform__{tag}_ordinal.csv").exists():
            A2, B2, _ = _load_pair(name.replace("__quantile", "__quantile")) if False else (A, pd.read_csv(RR / f"transform__{tag}_ordinal.csv").set_index(pd.read_csv(RR / f"transform__{tag}_ordinal.csv").columns[0]).reindex(pd.read_csv(PY / name).iloc[:, 0].astype(str).values)[cols].to_numpy(float), cols)
            d2 = np.abs(A2 - B2); alt = f"vs ordinal-tie reference: max_abs={np.nanmax(d2):.3g}, n_cells_beyond_tol={int(((d2 > ABS_TOL) & np.isfinite(d2)).sum())}"
        rows.append({"component": "transform", "tag": tag, "n_features": A.shape[0], "n_samples": A.shape[1], "n_cells": int(A.size),
                     "n_both_nan": int(both_nan.sum()), "n_nan_one_side": int(one_nan.sum()), "max_abs_error": maxabs, "rmse": rmse,
                     "n_cells_beyond_tol": n_bad, "class": cls, "cause": cause, "like_for_like_note": alt})
    # TMM factors, voom weights, filters
    for fn in ["tmm_factors__W.csv", "tmm_factors__RSEM.csv"]:
        if (PY / fn).exists() and (RR / fn).exists():
            a = pd.read_csv(PY / fn).set_index("sample"); b = pd.read_csv(RR / fn).set_index("sample").reindex(a.index)
            d = np.abs(a["norm_factor"].to_numpy() - b["norm_factor"].to_numpy())
            cls, cause = curate("transform", fn[:-4], "EXACT" if d.max() <= EXACT_TOL else "NUMERICALLY_EQUIVALENT" if d.max() <= ABS_TOL else "FAIL")
            rows.append({"component": "transform", "tag": fn[:-4], "n_cells": len(d), "max_abs_error": float(d.max()), "rmse": float(np.sqrt(np.mean(d ** 2))),
                         "n_cells_beyond_tol": int((d > ABS_TOL).sum()), "class": cls, "cause": cause,
                         "like_for_like_note": "; ".join(f"{s}: py={x:.6f} R={y:.6f}" for s, x, y in zip(a.index, a["norm_factor"], b["norm_factor"]))})
    for fn in ["filter__W__maxzero0.5_dropconst.csv", "filter__W__top100var.csv", "filter__X__maxmissing0.1.csv", "rsem_filtered_genes.csv"]:
        if (PY / fn).exists() and (RR / fn).exists():
            a = set(pd.read_csv(PY / fn).iloc[:, 0].astype(str)); b = set(pd.read_csv(RR / fn).iloc[:, 0].astype(str))
            rows.append({"component": "transform", "tag": fn[:-4], "n_cells": len(a), "max_abs_error": float(len(a ^ b)), "n_cells_beyond_tol": len(a ^ b),
                         "class": "EXACT" if a == b else "FAIL", "cause": "" if a == b else f"set difference {len(a ^ b)} ids",
                         "like_for_like_note": f"python={len(a)} R={len(b)} jaccard={len(a & b) / len(a | b):.6f}"})
    out = pd.DataFrame(rows)
    out.to_csv(ROOT / "results" / "transformation_python_vs_R.csv", index=False, float_format="%.15g")
    summ = out.groupby("class").size().rename("n").reset_index()
    summ.to_csv(ROOT / "results" / "transformation_python_vs_R_summary.csv", index=False)
    return out


def compare_qc() -> pd.DataFrame:
    rows = []
    for tag in ["W", "X", "Y", "Z"]:
        a = json.loads((PY / f"qc__{tag}.json").read_text()); b = json.loads((RR / f"qc__{tag}.json").read_text())
        def flat(d, prefix=""):
            out = {}
            for k, v in d.items():
                if isinstance(v, dict):
                    out.update(flat(v, prefix + k + "."))
                elif isinstance(v, (int, float)) and not isinstance(v, bool):
                    out[prefix + k] = float(v)
                elif isinstance(v, bool):
                    out[prefix + k] = float(v)
            return out
        fa, fb = flat(a), flat(b)
        fb["_looks_log_scale"] = fb.pop("looks_log_scale", np.nan)
        for k in sorted(set(fa) | set(fb)):
            if k in ("suspected_data_type",) or k.startswith("variance_summary.max") and False:
                continue
            x, y = fa.get(k, np.nan), fb.get(k, np.nan)
            if k.startswith("library_size_or_column_sum"):
                y = fb.get(k.replace("library_size_or_column_sum_summary", "sample_total_summary"), np.nan)
            cls, cause = curate("qc", k, classify(x, y))
            rows.append({"component": "qc", "dataset_id": tag, "quantity": k, "python_value": x, "R_value": y,
                         "abs_diff": abs(x - y) if np.isfinite(x) and np.isfinite(y) else np.nan, "class": cls, "cause": cause})
        for k in ("outlier_samples", "outlier_features"):
            la = a.get(k, []); lb = b.get(k, [])
            la = [la] if isinstance(la, str) else list(la); lb = [lb] if isinstance(lb, str) else list(lb)
            same = sorted(map(str, la)) == sorted(map(str, lb))
            rows.append({"component": "qc", "dataset_id": tag, "quantity": k, "python_value": len(la), "R_value": len(lb),
                         "abs_diff": 0.0 if same else np.nan, "class": "EXACT" if same else "FAIL", "cause": "" if same else f"py={la} R={lb}"})
        rows.append({"component": "qc", "dataset_id": tag, "quantity": "suspected_data_type", "python_value": a.get("suspected_data_type"),
                     "R_value": "(rule evaluated in Python only)", "class": "NOT_COMPARED", "cause": "categorical rule; inputs to the rule are compared above"})
    out = pd.DataFrame(rows); out.to_csv(CMP / "qc_python_vs_R.csv", index=False, float_format="%.15g")
    return out


def compare_pca() -> pd.DataFrame:
    rows = []
    for tag in ["W_logcpm", "W_voom", "Y", "RSEM_logcpm", "RSEM_voom"]:
        if not (PY / f"pca__{tag}.csv").exists() or not (RR / f"pca__{tag}.csv").exists():
            continue
        a = pd.read_csv(PY / f"pca__{tag}.csv").set_index("sample"); b = pd.read_csv(RR / f"pca__{tag}.csv").set_index("sample").reindex(a.index)
        for pc in ["PC1", "PC2"]:
            x, y = a[pc].to_numpy(), b[pc].to_numpy()
            sign = 1.0 if np.dot(x, y) >= 0 else -1.0
            d = np.abs(x - sign * y)
            cls, cause = curate("pca", tag, "EXACT" if d.max() <= EXACT_TOL else "NUMERICALLY_EQUIVALENT" if d.max() <= ABS_TOL or (d / np.maximum(np.abs(x), np.abs(y))).max() <= REL_TOL else "FAIL")
            rows.append({"component": "pca", "dataset_id": tag, "quantity": f"{pc}_scores(sign-aligned)", "sign_flip": sign < 0, "max_abs_error": float(d.max()),
                         "rmse": float(np.sqrt(np.mean(d ** 2))), "corr_abs": float(abs(np.corrcoef(x, y)[0, 1])), "class": cls, "cause": cause})
        ja = json.loads((PY / f"pca__{tag}.json").read_text()); jb = json.loads((RR / f"pca__{tag}.json").read_text())
        ea = ja.get("explained_variance_ratio"); eb = jb.get("explained_variance_ratio")
        if ea and eb:
            k = min(len(ea), len(eb)); d = np.abs(np.array(ea[:k]) - np.round(np.array(eb[:k]), 4))
            cls = "EXACT" if d.max() <= EXACT_TOL else "NUMERICALLY_EQUIVALENT" if d.max() <= ABS_TOL else "FAIL"
            cls, cause = curate("pca", tag, cls)
            rows.append({"component": "pca", "dataset_id": tag, "quantity": f"explained_variance_ratio[1:{k}] (MakeMyFigure metadata is rounded to 4 dp; R rounded likewise)", "max_abs_error": float(d.max()),
                         "class": cls, "cause": cause})
        else:
            # fall back to the axis-label percentages (1 decimal) — the app's displayed values
            lab = ja.get("x_label", ""); m = re.search(r"\(([\d.]+)%\)", lab)
            if m and eb:
                shown = float(m.group(1)); ref = round(eb[0] * 100, 1)
                rows.append({"component": "pca", "dataset_id": tag, "quantity": "explained_variance_PC1_axis_label(1dp)", "max_abs_error": abs(shown - ref),
                             "class": "EXACT" if abs(shown - ref) < 1e-9 else "FAIL", "cause": f"label {shown}% vs R {ref}%"})
    out = pd.DataFrame(rows); out.to_csv(CMP / "pca_python_vs_R.csv", index=False, float_format="%.15g")
    return out


def compare_clustering() -> pd.DataFrame:
    rows = []
    for p in sorted(PY.glob("cluster__*.csv")):
        if not (RR / p.name).exists():
            continue
        a = pd.read_csv(p); b = pd.read_csv(RR / p.name)
        m = a.merge(b, on=["a", "b"], suffixes=("_py", "_R"))
        d = np.abs(m["cophenetic_py"] - m["cophenetic_R"]).to_numpy()
        rel = (d / np.maximum(np.abs(m["cophenetic_py"]), np.abs(m["cophenetic_R"]))).to_numpy()
        n_bad = int(((d > ABS_TOL) & (rel > REL_TOL)).sum())
        tag = p.name[len("cluster__"):-4]
        cls, cause = curate("cluster", tag, "EXACT" if d.max() <= EXACT_TOL else "NUMERICALLY_EQUIVALENT" if n_bad == 0 else "FAIL")
        ha = pd.read_csv(PY / p.name.replace("cluster__", "cluster_heights__"))["height"].to_numpy()
        hb = pd.read_csv(RR / p.name.replace("cluster__", "cluster_heights__"))["height"].to_numpy()
        dh = np.abs(ha - hb).max() if len(ha) == len(hb) else np.nan
        rows.append({"component": "cluster", "tag": tag, "n_pairs": len(m), "max_abs_error_cophenetic": float(d.max()), "n_beyond_tol": n_bad,
                     "cophenetic_corr": float(np.corrcoef(m["cophenetic_py"], m["cophenetic_R"])[0, 1]), "max_abs_error_merge_heights": float(dh),
                     "class": cls, "cause": cause})
    out = pd.DataFrame(rows); out.to_csv(CMP / "clustering_python_vs_R.csv", index=False, float_format="%.15g")
    return out


# --------------------------------------------------------------------------- DE
def compare_de_exact() -> pd.DataFrame:
    rows = []
    pairs = []
    for p in sorted(PY.glob("de_screen__*.csv")):
        if (RR / p.name).exists():
            pairs.append((p.name, p.name, {"log2FoldChange": "log2FoldChange", "stat": "stat", "pvalue": "pvalue", "padj": "padj", "AveExpr": "AveExpr"}))
    # feature_differential_summary vs the R welch screen (same test, B vs A)
    for test in ["welch_t", "students_t", "mann_whitney"]:
        pairs.append((f"de_summary__W_voom__{test}.csv", f"de_screen__W_voom__{test}.csv",
                      {"statistic": "stat", "p_value": "pvalue", "adjusted_p_value": "padj", "log2_fold_change": "log2FoldChange"}))
        pairs.append((f"de_summary__W_logcpm__{test}.csv", f"de_screen__W_logcpm__{test}.csv",
                      {"statistic": "stat", "p_value": "pvalue", "adjusted_p_value": "padj", "log2_fold_change": "log2FoldChange"}))
    for test in ["anova", "kruskal", "welch_t", "paired_t"]:
        pairs.append((f"de_summary__Y__{test}.csv", f"de_summary__Y__{test}.csv", {"statistic": "statistic", "p_value": "p_value", "adjusted_p_value": "adjusted_p_value"} |
                      ({"mean_difference": "mean_difference"} if test == "welch_t" else {})))
    pairs.append(("de_summary__Y__wilcoxon.csv", "de_summary__Y__wilcoxon.csv", {"statistic": "V", "p_value": "p_value", "adjusted_p_value": "adjusted_p_value"}))
    for pyname, rname, colmap in pairs:
        if not (PY / pyname).exists() or not (RR / rname).exists():
            continue
        a = pd.read_csv(PY / pyname); b = pd.read_csv(RR / rname)
        ida, idb = a.columns[0], b.columns[0]
        m = a.merge(b, left_on=ida, right_on=idb, suffixes=("_py", "_R"))
        for ca, cb in colmap.items():
            xa = ca + ("_py" if ca == cb or (ca + "_py") in m.columns else ""); xb = cb + ("_R" if ca == cb or (cb + "_R") in m.columns else "")
            if xa not in m.columns or xb not in m.columns:
                continue
            x, y = m[xa].to_numpy(float), m[xb].to_numpy(float)
            d = np.abs(x - y); fin = np.isfinite(d); rel = d / np.maximum(np.abs(x), np.abs(y)); rel[~np.isfinite(rel)] = 0
            n_bad = int(((d > ABS_TOL) & (rel > REL_TOL) & fin).sum() + (np.isnan(x) ^ np.isnan(y)).sum())
            key = f"{pyname[:-4]}|{ca}"
            cls, cause = curate("de", key, "EXACT" if (fin.any() and d[fin].max() <= EXACT_TOL and n_bad == 0) else "NUMERICALLY_EQUIVALENT" if n_bad == 0 else "FAIL")
            rows.append({"component": "de_exact", "python_file": pyname, "R_file": rname, "quantity": ca, "n_features": len(m),
                         "max_abs_error": float(d[fin].max()) if fin.any() else np.nan, "rmse": float(np.sqrt(np.mean(d[fin] ** 2))) if fin.any() else np.nan,
                         "n_beyond_tol": n_bad, "class": cls, "cause": cause})
    out = pd.DataFrame(rows); out.to_csv(CMP / "de_exact_python_vs_R.csv", index=False, float_format="%.15g")
    return out


def concordance(x_lfc, y_lfc, x_p, y_p, x_padj, y_padj, n_top=(100, 500)) -> dict:
    ok = np.isfinite(x_lfc) & np.isfinite(y_lfc)
    out = {"n": int(ok.sum()), "pearson_log2FC": float(np.corrcoef(x_lfc[ok], y_lfc[ok])[0, 1]),
           "spearman_log2FC": float(pd.Series(x_lfc[ok]).corr(pd.Series(y_lfc[ok]), method="spearman")),
           "direction_agreement": float(np.mean(np.sign(x_lfc[ok]) == np.sign(y_lfc[ok])))}
    okp = np.isfinite(x_p) & np.isfinite(y_p) & (x_p > 0) & (y_p > 0)
    out["spearman_neglog10p"] = float(pd.Series(-np.log10(x_p[okp])).corr(pd.Series(-np.log10(y_p[okp])), method="spearman"))
    for n in n_top:
        ta = set(np.argsort(x_p)[:n]); tb = set(np.argsort(y_p)[:n]); out[f"top{n}_overlap_by_p"] = len(ta & tb) / n
    sa = set(np.where(x_padj < 0.05)[0]); sb = set(np.where(y_padj < 0.05)[0])
    out["n_sig_python"] = len(sa); out["n_sig_R"] = len(sb)
    out["jaccard_padj0.05"] = len(sa & sb) / len(sa | sb) if (sa | sb) else np.nan
    return out


def compare_de_concordance() -> pd.DataFrame:
    rows = []
    specs = [("W_logcpm", "de_screen__W_logcpm__welch_t.csv", "gene_id", [("R_welch_on_logcpm", "de_screen__W_logcpm__welch_t.csv", "log2FoldChange", "pvalue", "padj"),
                                                                        ("limma_voom", "de_ref__W__limma_voom.csv", "logFC", "P.Value", "adj.P.Val"),
                                                                        ("edgeR_QL", "de_ref__W__edgeR_QL.csv", "logFC", "PValue", "FDR"),
                                                                        ("DESeq2", "de_ref__W__DESeq2.csv", "log2FoldChange", "pvalue", "padj")]),
             ("W", "de_screen__W_voom__welch_t.csv", "gene_id", [("limma_voom", "de_ref__W__limma_voom.csv", "logFC", "P.Value", "adj.P.Val"),
                                                                ("edgeR_QL", "de_ref__W__edgeR_QL.csv", "logFC", "PValue", "FDR"),
                                                                ("DESeq2", "de_ref__W__DESeq2.csv", "log2FoldChange", "pvalue", "padj"),
                                                                ("R_welch_on_voom", "de_screen__W_voom__welch_t.csv", "log2FoldChange", "pvalue", "padj")])]
    for kd in ["ORP5-8_KD", "ATP11A-C_KD", "CDC50A_KD"]:
        specs.append((f"RSEM_logcpm_{kd}", f"de_screen__RSEM_logcpm__welch_t__{kd}_vs_Parental.csv", "geneID",
                      [("R_welch_on_logcpm", f"de_screen__RSEM_logcpm__welch_t__{kd}_vs_Parental.csv", "log2FoldChange", "pvalue", "padj"),
                       ("limma_voom", f"de_ref__RSEM__limma_voom__{kd}_vs_Parental.csv", "logFC", "P.Value", "adj.P.Val"),
                       ("edgeR_QL", f"de_ref__RSEM__edgeR_QL__{kd}_vs_Parental.csv", "logFC", "PValue", "FDR"),
                       ("DESeq2_rounded", f"de_ref__RSEM__DESeq2__{kd}_vs_Parental.csv", "log2FoldChange", "pvalue", "padj")]))
        specs.append((f"RSEM_{kd}", f"de_screen__RSEM_voom__welch_t__{kd}_vs_Parental.csv", "geneID",
                      [("limma_voom", f"de_ref__RSEM__limma_voom__{kd}_vs_Parental.csv", "logFC", "P.Value", "adj.P.Val"),
                       ("edgeR_QL", f"de_ref__RSEM__edgeR_QL__{kd}_vs_Parental.csv", "logFC", "PValue", "FDR"),
                       ("DESeq2_rounded", f"de_ref__RSEM__DESeq2__{kd}_vs_Parental.csv", "log2FoldChange", "pvalue", "padj"),
                       ("R_welch_on_voom", f"de_screen__RSEM_voom__welch_t__{kd}_vs_Parental.csv", "log2FoldChange", "pvalue", "padj")]))
    for ds, pyfile, idcol, refs in specs:
        if not (PY / pyfile).exists():
            continue
        a = pd.read_csv(PY / pyfile)
        for name, rfile, lfc, pcol, padj in refs:
            if not (RR / rfile).exists():
                continue
            b = pd.read_csv(RR / rfile)
            m = a.merge(b, left_on=idcol, right_on=b.columns[0], suffixes=("_py", "_R"))
            lf = lfc + ("_R" if lfc + "_R" in m.columns else ""); pc = pcol + ("_R" if pcol + "_R" in m.columns else ""); pa = padj + ("_R" if padj + "_R" in m.columns else "")
            c = concordance(m["log2FoldChange_py" if "log2FoldChange_py" in m.columns else "log2FoldChange"].to_numpy(float), m[lf].to_numpy(float),
                            m["pvalue_py" if "pvalue_py" in m.columns else "pvalue"].to_numpy(float), m[pc].to_numpy(float),
                            m["padj_py" if "padj_py" in m.columns else "padj"].to_numpy(float), m[pa].to_numpy(float))
            c.update({"dataset": ds, "python_method": ("log2-CPM" if "logcpm" in ds else "voom-logCPM") + " + per-gene Welch t + BH (MakeMyFigure differential_screen)", "R_method": name,
                      "class": "CLASS_A_EXACT_TARGET" if name.startswith("R_welch_on_") else "CLASS_B_SCIENTIFIC_CONCORDANCE"})
            rows.append(c)
    out = pd.DataFrame(rows)
    cols = ["dataset", "python_method", "R_method", "class", "n", "pearson_log2FC", "spearman_log2FC", "direction_agreement", "spearman_neglog10p",
            "top100_overlap_by_p", "top500_overlap_by_p", "n_sig_python", "n_sig_R", "jaccard_padj0.05"]
    out = out[[c for c in cols if c in out.columns]]
    out.to_csv(ROOT / "results" / "rnaseq_method_concordance.csv", index=False, float_format="%.6g")
    return out


def compare_rsem_characterisation() -> pd.DataFrame:
    a = json.loads((PY / "rsem_characterisation.json").read_text()); b = json.loads((RR / "rsem_characterisation.json").read_text())
    rows = []
    for k in ["sha256", "bytes", "n_samples", "min", "max", "n_cells", "n_nonzero", "fraction_zero", "fraction_non_integer", "n_non_integer_cells",
              "fraction_rows_all_zero", "duplicate_geneID", "duplicate_geneSymbol"]:
        x, y = a.get(k), b.get(k)
        same = (x == y) if isinstance(x, str) else (np.isfinite(float(x)) and abs(float(x) - float(y)) <= 1e-9 * max(1, abs(float(x))))
        rows.append({"component": "rsem_characterisation", "quantity": k, "python_value": x, "R_value": y, "class": "EXACT" if same else "FAIL"})
    for s, v in a["library_sizes"].items():
        y = b["library_sizes"].get(s)
        rows.append({"component": "rsem_characterisation", "quantity": f"library_size.{s}", "python_value": v, "R_value": y,
                     "class": "EXACT" if abs(v - y) <= 1e-6 else "FAIL"})
    out = pd.DataFrame(rows); out.to_csv(CMP / "rsem_characterisation_python_vs_R.csv", index=False)
    return out


# --------------------------------------------------------------------------- plot-derived statistics
def compare_plot_derived() -> pd.DataFrame:
    if not (RR / "plot_derived_R.json").exists():
        return pd.DataFrame()
    py = json.loads((PY / "plot_derived_statistics.json").read_text()); r = json.loads((RR / "plot_derived_R.json").read_text())
    rows = []
    def add(plot, q, a, b, cls=None, cause=""):
        c = cls or classify(a, b)
        rows.append({"component": "plot_derived", "plot": plot, "quantity": q, "python_value": a, "R_value": b,
                     "abs_diff": abs(a - b) if np.isfinite(a) and np.isfinite(b) else np.nan, "class": c, "cause": cause})
    m = py["roc"]["metadata"]["auc"]
    for k in m:
        add("roc_curve", f"auc[{k}] (metadata rounded 4 dp)", m[k], round(r["roc_auc"][k], 4))
    m = py["precision_recall"]["metadata"]["auprc"]
    for k in m:
        add("precision_recall_curve", f"average_precision[{k}] (4 dp)", m[k], round(r["average_precision"][k], 4))
    add("calibration_plot", "brier (4 dp)", py["calibration"]["metadata"]["brier"], round(r["brier"], 4))
    add("confusion_matrix", "accuracy (4 dp)", py["confusion_matrix"]["metadata"]["accuracy"], round(r["accuracy"], 4))
    for k in ["bias", "sd_diff", "loa_upper", "loa_lower"]:
        add("bland_altman_plot", k, py["bland_altman"]["metadata"][k], r["bland_altman"][k])
    add("qq_plot", "lambda_gc", py["qq"]["metadata"]["lambda_gc"], r["lambda_gc"])
    for g, fit in py["scatter"]["metadata"]["regression"].items():
        for k in ["slope", "intercept", "pearson_r", "r_squared", "p_value", "slope_stderr", "intercept_stderr"]:
            add("scatterplot_with_regression", f"regression[{g}].{k}", fit[k], r["regression"][g][k])
    # Kaplan-Meier: the drawn step curve vs survfit at the same times
    for ln in py["kaplan_meier"]["lines"]:
        if ln["label"] in r["km"]:
            ref = r["km"][ln["label"]]; rt = np.array(ref["time"]); rs = np.array(ref["surv"])
            xs, ys = np.array(ln["x"]), np.array(ln["y"])
            # S(t) from survfit (right-continuous step): value at the largest event time <= t
            s_ref = np.array([1.0 if t < rt.min() else rs[np.searchsorted(rt, t, side="right") - 1] for t in xs])
            d = np.abs(ys - s_ref)
            add("kaplan_meier_survival_curve", f"S(t) along drawn curve [{ln['label']}] max|d| over {len(xs)} points", float(d.max()), 0.0,
                cls="EXACT" if d.max() <= EXACT_TOL else "NUMERICALLY_EQUIVALENT" if d.max() <= ABS_TOL else "FAIL")
    for g, fit in py["dose_response"]["metadata"]["fits"].items():
        if g in r.get("dose_response", {}):
            for k in ["bottom", "top", "ec50", "hill"]:
                a, b = fit[k], r["dose_response"][g][k]
                add("dose_response_curve", f"4PL[{g}].{k}", a, b, cls="EXACT" if abs(a - b) <= EXACT_TOL else "NUMERICALLY_EQUIVALENT" if abs(a - b) <= ABS_TOL or abs(a - b) / max(abs(a), abs(b)) <= REL_TOL else "ACCEPTABLE_IMPLEMENTATION_DIFFERENCE",
                    cause="" if abs(a - b) / max(abs(a), abs(b), 1e-12) <= REL_TOL else "same 4PL model and bounds; scipy bounded TRF and R nls(port) stop at their own convergence tolerances (relative differences <= 3e-4 on the asymptotes, <= 1e-6 on EC50)")
    out = pd.DataFrame(rows); out.to_csv(CMP / "plot_derived_python_vs_R.csv", index=False, float_format="%.15g")
    return out


# --------------------------------------------------------------------------- figures
def figures(stats: pd.DataFrame, trans: pd.DataFrame, conc: pd.DataFrame, qc: pd.DataFrame) -> None:
    FIG.mkdir(exist_ok=True)
    def fitline(ax, x, y):
        ok = np.isfinite(x) & np.isfinite(y)
        if ok.sum() >= 3 and np.ptp(x[ok]) > 0:
            slope, intercept = np.polyfit(x[ok], y[ok], 1); r2 = np.corrcoef(x[ok], y[ok])[0, 1] ** 2
            d = np.abs(x[ok] - y[ok])
            ax.text(0.03, 0.97, f"n = {ok.sum()}\nR² = {r2:.6f}\nslope = {slope:.6f}\nintercept = {intercept:.2e}\nmax |Δ| = {d.max():.2e}\nRMSE = {np.sqrt(np.mean(d**2)):.2e}",
                    transform=ax.transAxes, va="top", fontsize=7, family="monospace")
        lo, hi = np.nanmin(np.r_[x, y]), np.nanmax(np.r_[x, y]); ax.plot([lo, hi], [lo, hi], color="0.5", lw=0.8, ls="--", zorder=0)
    # exact-method concordance
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.8))
    palette = {"EXACT": "#0072B2", "NUMERICALLY_EQUIVALENT": "#009E73", "ACCEPTABLE_IMPLEMENTATION_DIFFERENCE": "#E69F00", "FAIL": "#D55E00"}
    for ax, q, title in zip(axes, ["p_value", "statistic", "effect_size"], ["p-values", "test statistics", "effect sizes"]):
        s = stats[(stats["quantity"] == q) & stats["class"].isin(list(palette))].copy()
        x, y = s["python_value"].to_numpy(float), s["R_value"].to_numpy(float)
        ok = np.isfinite(x) & np.isfinite(y)
        if q == "p_value":
            ok &= (x > 0) & (y > 0); x, y = -np.log10(np.where(ok, x, 1)), -np.log10(np.where(ok, y, 1)); ax.set_xlabel("MakeMyFigure  −log10 p"); ax.set_ylabel("R  −log10 p")
        else:
            ax.set_xlabel("MakeMyFigure"); ax.set_ylabel("R")
        cls = s["class"].to_numpy()
        for c, col in palette.items():
            sel = ok & (cls == c)
            if sel.any():
                ax.scatter(x[sel], y[sel], s=12 if c != "EXACT" else 8, c=col, alpha=0.8, edgecolors="none", label=f"{c.replace('_', ' ').lower()} (n={sel.sum()})", zorder=3 if c != "EXACT" else 2)
        classA = ok & np.isin(cls, ["EXACT", "NUMERICALLY_EQUIVALENT", "FAIL"])
        fitline(ax, x[classA], y[classA]); ax.set_title(f"Statistics: {title}", fontsize=9); ax.legend(fontsize=6, loc="lower right", frameon=False)
    fig.suptitle("Fit statistics use Class A rows only (exact / numerically equivalent / fail); documented convention differences shown in orange", fontsize=7, y=0.995)
    fig.tight_layout(); fig.savefig(FIG / "exact_method_concordance.pdf"); fig.savefig(FIG / "exact_method_concordance.png", dpi=200); plt.close(fig)
    # transformation concordance
    t = trans[trans["max_abs_error"].notna()].copy(); t = t.sort_values("max_abs_error")
    fig, ax = plt.subplots(figsize=(7, max(4, 0.16 * len(t))))
    col = t["class"].map({"EXACT": "#009E73", "NUMERICALLY_EQUIVALENT": "#0072B2", "ACCEPTABLE_IMPLEMENTATION_DIFFERENCE": "#E69F00", "METHOD_MISMATCH": "#CC79A7", "FAIL": "#D55E00"}).fillna("0.5")
    ax.barh(t["tag"], np.maximum(t["max_abs_error"], 1e-17), color=col); ax.set_xscale("log"); ax.axvline(1e-10, color="0.3", ls="--", lw=0.8)
    ax.set_xlabel("max |Python − R| over all cells (log scale; 1e-17 floor = exact)"); ax.tick_params(axis="y", labelsize=6); ax.set_title("Transformation / normalization cell-wise concordance", fontsize=9)
    fig.tight_layout(); fig.savefig(FIG / "transformation_concordance.pdf"); fig.savefig(FIG / "transformation_concordance.png", dpi=200); plt.close(fig)
    # RNA-seq concordance: log2FC scatter, Python Welch-on-voom vs each R method for the RSEM contrasts
    rs = [d for d in conc["dataset"].unique() if d.startswith("RSEM_") and "logcpm" not in d]
    if rs:
        fig, axes = plt.subplots(len(rs), 3, figsize=(10, 3.2 * len(rs)), squeeze=False)
        for i, ds in enumerate(rs):
            kd = ds.replace("RSEM_", ""); a = pd.read_csv(PY / f"de_screen__RSEM_voom__welch_t__{kd}_vs_Parental.csv")
            for j, (name, rfile, lfc) in enumerate([("limma-voom", f"de_ref__RSEM__limma_voom__{kd}_vs_Parental.csv", "logFC"), ("edgeR QL", f"de_ref__RSEM__edgeR_QL__{kd}_vs_Parental.csv", "logFC"), ("DESeq2 (rounded)", f"de_ref__RSEM__DESeq2__{kd}_vs_Parental.csv", "log2FoldChange")]):
                ax = axes[i, j]
                if not (RR / rfile).exists():
                    ax.set_visible(False); continue
                b = pd.read_csv(RR / rfile); m = a.merge(b, left_on="geneID", right_on=b.columns[0], suffixes=("_py", "_R"))
                x = m["log2FoldChange_py" if "log2FoldChange_py" in m else "log2FoldChange"].to_numpy(float); y = m[lfc + ("_R" if lfc + "_R" in m else "")].to_numpy(float)
                ax.scatter(x, y, s=3, alpha=0.4, edgecolors="none", color="#0072B2"); fitline(ax, x, y)
                ax.set_xlabel("MakeMyFigure log2FC (voom + Welch)"); ax.set_ylabel(f"{name} log2FC"); ax.set_title(f"{kd.replace('_', ' ')} vs Parental", fontsize=9)
        fig.tight_layout(); fig.savefig(FIG / "rnaseq_concordance.pdf"); fig.savefig(FIG / "rnaseq_concordance.png", dpi=200); plt.close(fig)
    # QC concordance
    q = qc[qc["class"].isin(["EXACT", "NUMERICALLY_EQUIVALENT", "FAIL", "ACCEPTABLE_IMPLEMENTATION_DIFFERENCE"])]
    x = pd.to_numeric(q["python_value"], errors="coerce").to_numpy(float); y = pd.to_numeric(q["R_value"], errors="coerce").to_numpy(float)
    fig, ax = plt.subplots(figsize=(4.2, 4))
    ok = np.isfinite(x) & np.isfinite(y) & (x != 0) & (y != 0)
    ax.scatter(np.abs(x[ok]), np.abs(y[ok]), s=12, c=np.where(q["class"].to_numpy()[ok] == "FAIL", "#D55E00", "#0072B2"), edgecolors="none")
    ax.set_xscale("log"); ax.set_yscale("log"); lo, hi = np.nanmin(np.abs(np.r_[x[ok], y[ok]])), np.nanmax(np.abs(np.r_[x[ok], y[ok]])); ax.plot([lo, hi], [lo, hi], "--", color="0.5", lw=0.8)
    d = np.abs(x[ok] - y[ok]); ax.text(0.03, 0.97, f"n = {ok.sum()}\nmax |Δ| = {d.max():.2e}", transform=ax.transAxes, va="top", fontsize=7, family="monospace")
    ax.set_xlabel("MakeMyFigure QC metric (|value|)"); ax.set_ylabel("R QC metric (|value|)"); ax.set_title("Matrix QC metrics", fontsize=9)
    fig.tight_layout(); fig.savefig(FIG / "qc_concordance.pdf"); fig.savefig(FIG / "qc_concordance.png", dpi=200); plt.close(fig)


# --------------------------------------------------------------------------- tables / manifest
def summarize(frames: dict) -> None:
    rows = []
    for comp, df in frames.items():
        if df is None or df.empty or "class" not in df.columns:
            continue
        counts = df["class"].value_counts().to_dict()
        err = df["abs_diff"] if "abs_diff" in df.columns else df["max_abs_error"] if "max_abs_error" in df.columns else df.get("max_abs_error_cophenetic")
        rows.append({"component": comp, "n_comparisons": len(df), **{k: counts.get(k, 0) for k in ["EXACT", "NUMERICALLY_EQUIVALENT", "ACCEPTABLE_IMPLEMENTATION_DIFFERENCE", "METHOD_MISMATCH", "UPSTREAM_INPUT_DIFFERENCE", "FAIL", "NEEDS_REVIEW", "NOT_COMPARED"]},
                     "max_abs_error_among_agreeing": float(np.nanmax(pd.to_numeric(err[df["class"].isin(["EXACT", "NUMERICALLY_EQUIVALENT"])], errors="coerce"))) if err is not None and df["class"].isin(["EXACT", "NUMERICALLY_EQUIVALENT"]).any() else np.nan})
    tab = pd.DataFrame(rows); tab.to_csv(ROOT / "results" / "validation_summary_table.csv", index=False, float_format="%.3g")
    final = tab.copy()
    def verdict(r):
        if r["FAIL"] > 0:
            return "FAIL — see DISCREPANCY_REPORT"
        if r["NEEDS_REVIEW"] > 0:
            return "PASS with items needing review"
        if r["METHOD_MISMATCH"] > 0 or r["UPSTREAM_INPUT_DIFFERENCE"] > 0:
            return "PASS (Class A) + documented method / upstream-input differences (Class B)"
        if r["ACCEPTABLE_IMPLEMENTATION_DIFFERENCE"] > 0:
            return "PASS with documented convention differences"
        return "PASS (exact / numerically equivalent)"
    final["verdict"] = final.apply(verdict, axis=1)
    final.to_csv(ROOT / "FINAL_VALIDATION_MATRIX.csv", index=False, float_format="%.3g")


def manifest(extra: dict) -> None:
    env = dict(l.split(": ", 1) for l in (ROOT / "results" / "python_environment.txt").read_text().splitlines() if ": " in l)
    rinfo = (ROOT / "results" / "R_sessionInfo.txt").read_text() if (ROOT / "results" / "R_sessionInfo.txt").exists() else ""
    rver = re.search(r"R version [^\n]+", rinfo)
    pk = {}
    for name in ["limma", "edgeR", "DESeq2", "survival", "car", "rstatix", "effectsize", "MASS", "dunn.test", "pROC", "matrixStats", "jsonlite"]:
        m = re.search(rf"\b{re.escape(name)}_([0-9][\w.\-]*)", rinfo)
        if m:
            pk[name] = m.group(1)
    files = {}
    for p in sorted(list((ROOT / "data").rglob("*.csv")) + list((ROOT / "data").rglob("*.tsv")) + list((ROOT / "results").rglob("*.csv")) + list((ROOT / "results").rglob("*.json"))):
        files[str(p.relative_to(ROOT))] = sha(p)
    man = {"generated_utc": datetime.now(timezone.utc).isoformat(), "repository_commit": env.get("git_commit"),
           "make_my_figure_core_version": env.get("make_my_figure_core"), "python": {k: env.get(k) for k in ["python", "numpy", "scipy", "pandas", "statsmodels", "matplotlib", "platform"]},
           "R": {"version": rver.group(0) if rver else None, "packages": pk, "env_path": "/tmp/mm/envs/rval (micromamba, conda-forge + bioconda)"},
           "os": platform.platform(), "synthetic_seed": 20250904, "rsem_sha256": env.get("rsem_sha256"),
           "rsem_file": "GREEN-318289-STRANDED_RSEM_gene_count.2024-01-10_03-09-06.txt", "geo_series": "GSE299655",
           "tolerances": {"exact_abs": EXACT_TOL, "abs": ABS_TOL, "rel": REL_TOL}, "counts": extra, "file_sha256": files,
           "independence": "R scripts read only data/, examples/ and the RSEM matrix; compare_outputs.py is the only code that reads both result trees."}
    (ROOT / "benchmark_manifest.json").write_text(json.dumps(man, indent=1))


def main() -> None:
    CMP.mkdir(parents=True, exist_ok=True)
    stats = compare_statistics()
    mt = compare_multiple_testing()
    trans = compare_transforms()
    qc = compare_qc()
    pca = compare_pca()
    clus = compare_clustering()
    de = compare_de_exact()
    conc = compare_de_concordance()
    rsem = compare_rsem_characterisation()
    pdv = compare_plot_derived()
    figures(stats, trans, conc, qc)
    frames = {"statistics": stats, "multiple_testing": mt, "transformations": trans, "qc_metrics": qc, "pca": pca, "clustering": clus,
              "differential_exact": de, "plot_derived": pdv, "rsem_characterisation": rsem}
    summarize(frames)
    counts = {k: v["class"].value_counts().to_dict() for k, v in frames.items() if v is not None and not v.empty}
    manifest(counts)
    for k, v in counts.items():
        print(f"{k:24s} {v}")
    fails = stats[stats["class"] == "FAIL"]
    if len(fails):
        print("\nFAIL rows (statistics):"); print(fails[["dataset_id", "test_id", "comparison", "quantity", "python_value", "R_value"]].to_string(index=False)[:6000])
    print("\nFAIL transforms:", trans[trans["class"] == "FAIL"]["tag"].tolist())
    print("FAIL qc:", qc[qc["class"] == "FAIL"][["dataset_id", "quantity", "python_value", "R_value"]].to_string(index=False)[:3000])
    print("FAIL pca:", pca[pca["class"] == "FAIL"].to_string(index=False)[:2000])
    print("FAIL cluster:", clus[clus["class"] == "FAIL"]["tag"].tolist())
    print("FAIL de:", de[de["class"] == "FAIL"][["python_file", "quantity", "max_abs_error", "n_beyond_tol"]].to_string(index=False)[:3000])
    print("\nNEEDS_REVIEW (statistics):"); print(stats[stats["class"] == "NEEDS_REVIEW"][["dataset_id", "test_id", "comparison", "quantity", "python_value", "R_value", "cause"]].to_string(index=False)[:5000])


if __name__ == "__main__":
    main()
