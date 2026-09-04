"""Generate the fixed synthetic ground-truth datasets for the R validation.

Every dataset is written once to ``benchmarks/r_validation/data/synthetic/`` from a
single seed. Both the Python export (``export_make_my_figure_reference.py``) and the
R reference scripts read these files; neither side ever reads the other's results.

Datasets A-S cover the statistical families; T-Z cover matrices for the
transformation / QC / PCA / clustering benchmarks. Each has a documented purpose
(``data/synthetic/MANIFEST.csv``) including deliberately awkward cases: ties, zeros,
unequal variance, small n (exact-test regime), unbalanced designs, censoring ties.
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20250904
HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "data" / "synthetic"


def _write(name: str, df: pd.DataFrame, purpose: str, manifest: list, sep: str = ",") -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    df.to_csv(path, index=False, sep=sep, float_format="%.10g", na_rep="NA")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest.append({"file": name, "rows": len(df), "cols": df.shape[1], "purpose": purpose,
                     "sha256": sha})


def main() -> None:
    rng = np.random.default_rng(SEED)
    man: list = []

    # ---- two-group (independent) -------------------------------------------------
    a = rng.normal(10.0, 2.0, 12); b = rng.normal(12.5, 2.0, 15)
    _write("A_two_group_normal.csv",
           pd.DataFrame({"group": ["ctrl"] * 12 + ["treat"] * 15, "value": np.r_[a, b]}),
           "Two groups, equal variance, n=12/15 (Student/Welch/MWU asymptotic regime)", man)
    a = rng.normal(10.0, 1.0, 10); b = rng.normal(11.0, 4.0, 20)
    _write("B_two_group_unequal_var.csv",
           pd.DataFrame({"group": ["ctrl"] * 10 + ["treat"] * 20, "value": np.r_[a, b]}),
           "Two groups, strongly unequal variance and n (Welch vs Student divergence)", man)
    a = rng.integers(1, 7, 14); b = rng.integers(2, 9, 14)
    _write("C_two_group_ties.csv",
           pd.DataFrame({"group": ["ctrl"] * 14 + ["treat"] * 14, "value": np.r_[a, b].astype(float)}),
           "Two groups of small integers -> many ties (rank-test tie corrections)", man)
    a = rng.normal(5.0, 1.0, 5); b = rng.normal(6.5, 1.0, 6)
    _write("D_two_group_small_n.csv",
           pd.DataFrame({"group": ["ctrl"] * 5 + ["treat"] * 6, "value": np.r_[a, b]}),
           "Two tiny groups n=5/6, no ties (scipy exact MWU regime; R exact by default)", man)
    _write("E_two_group_one_constant.csv",
           pd.DataFrame({"group": ["ctrl"] * 8 + ["treat"] * 8,
                         "value": np.r_[np.full(8, 3.0), rng.normal(4.0, 1.0, 8)]}),
           "One group constant (zero variance) -> degenerate t / rank tests", man)

    # ---- paired ------------------------------------------------------------------
    n = 14
    base = rng.normal(50, 8, n); post = base + rng.normal(3.0, 4.0, n)
    _write("F_paired_normal.csv",
           pd.DataFrame({"subject": [f"S{i:02d}" for i in range(n)] * 2,
                         "condition": ["pre"] * n + ["post"] * n, "value": np.r_[base, post]}),
           "Paired design, n=14 subjects, continuous (paired t / Wilcoxon signed-rank)", man)
    n = 16
    base = rng.integers(10, 20, n).astype(float)
    post = base + np.array([0, 0, 0, 1, -1, 2, 2, 3, -2, 1, 1, 4, 0, 2, -3, 5], float)
    _write("G_paired_zeros_ties.csv",
           pd.DataFrame({"subject": [f"P{i:02d}" for i in range(n)] * 2,
                         "condition": ["pre"] * n + ["post"] * n, "value": np.r_[base, post]}),
           "Paired design with zero differences and tied |d| (Wilcoxon zero/tie handling)", man)

    # ---- multi-group --------------------------------------------------------------
    g = np.repeat(["low", "mid", "high"], 10)
    v = np.r_[rng.normal(10, 2, 10), rng.normal(11, 2, 10), rng.normal(14, 2, 10)]
    _write("H_three_groups_balanced.csv", pd.DataFrame({"dose": g, "response": v}),
           "Three balanced groups (one-way ANOVA, Kruskal-Wallis, Dunn, post-hoc family)", man)
    sizes = [6, 9, 12, 7, 15]
    g = np.repeat(["g1", "g2", "g3", "g4", "g5"], sizes)
    v = np.concatenate([rng.normal(m, s, k) for m, s, k in zip([5, 5.5, 7, 6, 9], [1, 1.5, 2, 1, 3], sizes)])
    v = np.round(v, 1)  # one-decimal rounding introduces ties
    _write("I_five_groups_unbalanced.csv", pd.DataFrame({"group": g, "score": v}),
           "Five unbalanced groups, heteroscedastic, rounded (ties) -> KW/Dunn tie correction", man)

    # ---- two-way ------------------------------------------------------------------
    rows = []
    for A in ["WT", "KO"]:
        for B in ["vehicle", "drug"]:
            mu = 10 + (2 if A == "KO" else 0) + (3 if B == "drug" else 0) + (2.5 if (A == "KO" and B == "drug") else 0)
            for _ in range(8):
                rows.append({"genotype": A, "treatment": B, "value": rng.normal(mu, 1.5)})
    _write("J_two_way_balanced.csv", pd.DataFrame(rows),
           "2x2 balanced factorial with interaction (two-way ANOVA type II)", man)
    rows = []
    for A, B, k in [("WT", "vehicle", 5), ("WT", "drug", 9), ("KO", "vehicle", 7), ("KO", "drug", 4)]:
        mu = 10 + (2 if A == "KO" else 0) + (3 if B == "drug" else 0)
        for _ in range(k):
            rows.append({"genotype": A, "treatment": B, "value": rng.normal(mu, 1.5)})
    _write("K_two_way_unbalanced.csv", pd.DataFrame(rows),
           "2x2 unbalanced factorial (type II SS matters; car::Anova comparison)", man)

    # ---- repeated measures --------------------------------------------------------
    rows = []
    subj_eff = rng.normal(0, 2, 10)
    for i in range(10):
        for t, mu in zip(["t0", "t1", "t2", "t3"], [10, 11, 13, 12]):
            rows.append({"subject": f"R{i:02d}", "time": t, "value": mu + subj_eff[i] + rng.normal(0, 1)})
    _write("L_repeated_measures.csv", pd.DataFrame(rows),
           "One within-subject factor (4 levels) x 10 subjects, complete (RM-ANOVA)", man)

    # ---- correlation / regression -------------------------------------------------
    x = rng.uniform(0, 10, 40); y = 2.0 + 0.8 * x + rng.normal(0, 1.5, 40)
    _write("M_linear_xy.csv", pd.DataFrame({"x": x, "y": y}),
           "Linear relation with noise (Pearson, Spearman, OLS slope/intercept/SE)", man)
    x = rng.uniform(0.1, 5, 35); y = np.exp(0.6 * x) + rng.normal(0, 0.5, 35)
    x = np.round(x, 1)  # ties in x for Spearman
    _write("N_monotone_nonlinear_ties.csv", pd.DataFrame({"x": x, "y": y}),
           "Monotone non-linear relation with tied x (Spearman tie handling vs Pearson)", man)

    # ---- categorical --------------------------------------------------------------
    arm = np.r_[np.repeat("A", 40), np.repeat("B", 35)]
    resp = np.r_[rng.choice(["yes", "no"], 40, p=[0.6, 0.4]), rng.choice(["yes", "no"], 35, p=[0.35, 0.65])]
    _write("O_contingency_2x2.csv", pd.DataFrame({"arm": arm, "response": resp}),
           "2x2 table (chi-square with Yates, Fisher exact, odds ratio conventions)", man)
    sub = rng.choice(["s1", "s2", "s3"], 180, p=[0.4, 0.35, 0.25])
    grade = np.array([rng.choice(["g1", "g2", "g3", "g4"], p=p) for p in
                      [[.4, .3, .2, .1] if s == "s1" else [.2, .3, .3, .2] if s == "s2" else [.1, .2, .3, .4] for s in sub]])
    _write("P_contingency_3x4.csv", pd.DataFrame({"subtype": sub, "grade": grade}),
           "3x4 table (chi-square without Yates, Cramer's V)", man)
    _write("Q_contingency_small_expected.csv",
           pd.DataFrame({"arm": ["A"] * 9 + ["B"] * 7,
                         "response": ["yes"] * 7 + ["no"] * 2 + ["yes"] * 1 + ["no"] * 6}),
           "Small 2x2 with expected counts < 5 (Fisher exact regime; chi-square warning)", man)

    # ---- survival -----------------------------------------------------------------
    n1, n2 = 30, 30
    t1 = np.ceil(rng.exponential(12, n1)); t2 = np.ceil(rng.exponential(20, n2))  # integer months -> ties
    c1 = rng.uniform(5, 30, n1); c2 = rng.uniform(5, 30, n2)
    time = np.r_[np.minimum(t1, np.ceil(c1)), np.minimum(t2, np.ceil(c2))]
    event = np.r_[(t1 <= np.ceil(c1)).astype(int), (t2 <= np.ceil(c2)).astype(int)]
    _write("R_survival_two_groups.csv",
           pd.DataFrame({"group": ["A"] * n1 + ["B"] * n2, "time": time, "event": event}),
           "Two-arm survival with tied integer times and censoring (log-rank, Cox Breslow/Efron)", man)
    sizes = [20, 25, 18]; scales = [10, 15, 25]
    tt, ee, gg = [], [], []
    for k, (s, sc) in enumerate(zip(sizes, scales)):
        t = np.ceil(rng.exponential(sc, s)); c = np.ceil(rng.uniform(4, 28, s))
        tt.append(np.minimum(t, c)); ee.append((t <= c).astype(int)); gg += [f"arm{k+1}"] * s
    _write("S_survival_three_groups.csv",
           pd.DataFrame({"group": gg, "time": np.concatenate(tt), "event": np.concatenate(ee)}),
           "Three-arm survival, unbalanced (multi-group log-rank df=2; Cox with 2 dummies)", man)

    # ---- GLM ----------------------------------------------------------------------
    n = 120
    x1 = rng.normal(0, 1, n); x2 = rng.binomial(1, 0.4, n).astype(float)
    eta = -0.5 + 0.8 * x1 + 0.6 * x2
    _write("T_glm_predictors.csv",
           pd.DataFrame({"x1": x1, "x2": x2,
                         "y_gauss": eta + rng.normal(0, 1, n),
                         "y_binom": rng.binomial(1, 1 / (1 + np.exp(-eta))),
                         "y_pois": rng.poisson(np.exp(eta)),
                         "y_negbin": rng.negative_binomial(2, 2 / (2 + np.exp(eta + 1.0))),
                         "y_gamma": rng.gamma(2.0, np.exp(eta + 1.0) / 2.0)}),
           "Two predictors with Gaussian/binomial/Poisson/negative-binomial/gamma responses (GLM)", man)

    # ---- multiple testing ---------------------------------------------------------
    p = np.r_[rng.uniform(0, 1, 150), rng.beta(0.3, 8, 40), [1.0, 1.0, 0.05, 0.05, 1e-12, 0.5]]
    _write("U_pvalues.csv", pd.DataFrame({"p": p}),
           "196 p-values incl. duplicates, exact 1.0 and 1e-12 (BH/Holm/Bonferroni vs p.adjust)", man)
    p2 = p.copy(); p2[[3, 17, 88]] = np.nan
    _write("V_pvalues_with_na.csv", pd.DataFrame({"p": p2}),
           "Same vector with 3 NA entries (m = number of non-missing p-values)", man)

    # ---- matrices -----------------------------------------------------------------
    nf, ns = 400, 12
    lib = rng.uniform(0.6, 1.6, ns)
    mu_g = rng.lognormal(3.0, 1.6, nf)
    de = np.zeros(nf); de[:40] = rng.normal(1.5, 0.4, 40); de[40:80] = -rng.normal(1.5, 0.4, 40)
    groups = np.array(["A"] * 6 + ["B"] * 6)
    counts = np.empty((nf, ns))
    for j in range(ns):
        m = mu_g * lib[j] * (2.0 ** de if groups[j] == "B" else 1.0)
        counts[:, j] = rng.negative_binomial(5, 5 / (5 + m))
    feats = [f"gene{i:04d}" for i in range(nf)]
    dfW = pd.DataFrame(counts, columns=[f"{g}_{k+1}" for k, g in enumerate(groups)])
    dfW.insert(0, "gene_id", feats)
    dfW.insert(1, "biotype", rng.choice(["protein_coding", "lncRNA", "pseudogene"], nf, p=[.7, .2, .1]))
    _write("W_count_matrix.tsv", dfW,
           "400 x 12 NB count matrix with an annotation column, 80 true DE features, lib-size spread (CPM/TMM/voom/DE)", man, sep="\t")
    nf = 300
    inten = np.exp(rng.normal(8, 1.2, (nf, 8))) * rng.uniform(0.7, 1.4, 8)
    mask = rng.uniform(size=inten.shape) < 0.04
    inten[mask] = np.nan
    dfX = pd.DataFrame(inten, columns=[f"S{k+1}" for k in range(8)])
    dfX.insert(0, "protein", [f"prot{i:03d}" for i in range(nf)])
    _write("X_intensity_matrix_missing.tsv", dfX,
           "300 x 8 right-skewed intensity matrix with 4% missing (log/arcsinh/median-scale/impute/robust)", man, sep="\t")
    dfY = pd.DataFrame(rng.normal(0, 1.5, (200, 10)), columns=[f"L{k+1}" for k in range(10)])
    dfY.insert(0, "feature", [f"f{i:03d}" for i in range(200)])
    _write("Y_log_matrix_negatives.tsv", dfY,
           "200 x 10 centred log-like matrix with negatives (z-score / centering / PCA / clustering)", man, sep="\t")
    dfZ = pd.DataFrame(rng.integers(0, 6, (30, 5)).astype(float), columns=[f"c{k+1}" for k in range(5)])
    dfZ.iloc[3, :] = 2.0
    dfZ.insert(0, "id", [f"r{i:02d}" for i in range(30)])
    _write("Z_small_integer_matrix_ties.tsv", dfZ,
           "30 x 5 small-integer matrix with heavy ties and a constant row (quantile normalization tie rule, z-score sd=0)", man, sep="\t")

    with open(OUT / "MANIFEST.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["file", "rows", "cols", "purpose", "sha256"])
        w.writeheader(); w.writerows(man)
    print(f"wrote {len(man)} datasets to {OUT} (seed {SEED})")


if __name__ == "__main__":
    main()
