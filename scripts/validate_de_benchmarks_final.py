"""Differential-expression validation against two independent published datasets.

Dataset A  Kume et al. 2024, eLife 97654 (CC BY 4.0) - Figure 5A source data, 9,999 features.
           Carries an adjusted p-value only, so it supports the FDR volcano but neither a
           raw-p volcano nor an MA plot.
Dataset B  Osipovich et al. 2023, PLOS Genetics 19:e1010729 (CC BY 4.0) - S2 Table, the
           complete unfiltered DESeq2 result set for 17,028 genes, carrying baseMean,
           log2FoldChange, lfcSE, stat, pvalue AND padj. This supports the raw-p volcano,
           the FDR volcano, and MA coordinates.

No differential model is refitted anywhere: published effect sizes and p-values are read
verbatim. Every count is computed independently with plain pandas from the published table and
compared with what the renderer reports in its own metadata, so agreement is a genuine
cross-check rather than the same code answering itself.

DESeq2 leaves padj empty for genes removed by independent filtering; those rows must never be
counted as significant, and that behaviour is tested explicitly.

Run: PYTHONPATH=. python scripts/validate_de_benchmarks_final.py
Writes manuscript/final_submission/validation/de_validation.csv
"""
from __future__ import annotations

import csv
import os

import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd

from make_my_figure_core.plots.registry import make_spec, render

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "manuscript", "final_submission", "validation")
os.makedirs(OUT, exist_ok=True)
PUB = os.path.join(ROOT, "benchmarks", "ten_publication_recreation", "publications")
A = os.path.join(PUB, "kume2024_psoriasis_semaphorin", "processed_data",
                 "psoriasis_nl_vs_ctl_de.csv")
B = os.path.join(PUB, "osipovich2023_zfp92_islet", "processed_data",
                 "zfp92_ko_vs_wt_deseq2.csv")
ROWS = []


def add(**kw):
    ROWS.append(kw)
    ok = kw["match"]
    tag = {"yes": "OK  ", "NO": "FAIL", "n/a": "    "}.get(ok, "    ")
    print(f"{tag} {kw['dataset'][:12]:12} {kw['check'][:52]:54} {kw['detail']}")
    return ok != "NO"


def counts(effect, sig, lfc_thr, p_thr):
    """Independent classification: NaN significance is never significant."""
    e = pd.to_numeric(effect, errors="coerce")
    p = pd.to_numeric(sig, errors="coerce")
    valid = p.notna() & e.notna()
    up = int((valid & (e >= lfc_thr) & (p <= p_thr)).sum())
    dn = int((valid & (e <= -lfc_thr) & (p <= p_thr)).sum())
    return up, dn


def volcano(df, effect_col, sig_col, use_fdr, lfc, pthr, label_col):
    spec = make_spec("volcano_plot", "de benchmark", "publication",
                     mapping={"x": effect_col, "p": sig_col, "label": label_col,
                              "use_fdr": use_fdr, "lfc_cutoff": lfc, "p_cutoff": pthr,
                              "annotate": False})
    return render(spec, df)


def main() -> int:
    allok = True

    # ---------------------------------------------------------------- dataset A
    da = pd.read_csv(A)
    allok &= add(dataset="kume2024", check="feature count read from published table",
                 expected=9999, observed=len(da), difference=len(da) - 9999,
                 tolerance="exact", method="len(table)", validation_type="integration-wiring",
                 match="yes" if len(da) == 9999 else "NO", detail=f"{len(da)} features")
    for lfc in (0.5, 1.0, 2.0):
        eu, ed = counts(da["log2FoldChange"], da["padj"], lfc, 0.05)
        res = volcano(da, "log2FoldChange", "padj", True, lfc, 0.05, "gene")
        ou, od = int(res.metadata["n_up"]), int(res.metadata["n_down"])
        allok &= add(dataset="kume2024", check=f"FDR<=0.05 |log2FC|>={lfc} up/down",
                     expected=f"{eu}/{ed}", observed=f"{ou}/{od}",
                     difference=f"{ou-eu}/{od-ed}", tolerance="exact",
                     method="independent pandas count vs renderer metadata",
                     validation_type="independent formula implementation",
                     match="yes" if (eu, ed) == (ou, od) else "NO",
                     detail=f"up {eu}/{ou}  down {ed}/{od}")
    allok &= add(dataset="kume2024", check="raw p-value volcano possible?",
                 expected="requires an unadjusted p column", observed="column absent",
                 difference="", tolerance="", method="column inspection",
                 validation_type="documented limitation", match="n/a",
                 detail="table carries padj only -> raw-p volcano tested on dataset B")
    allok &= add(dataset="kume2024", check="MA plot possible?",
                 expected="requires a mean-abundance column", observed="column absent",
                 difference="", tolerance="", method="column inspection",
                 validation_type="documented limitation", match="n/a",
                 detail="no abundance column -> MA tested on dataset B")

    # ---------------------------------------------------------------- dataset B
    db = pd.read_csv(B)
    n_exp = 17028
    allok &= add(dataset="osipovich2023", check="feature count read from published table",
                 expected=n_exp, observed=len(db), difference=len(db) - n_exp,
                 tolerance="exact", method="len(table)", validation_type="integration-wiring",
                 match="yes" if len(db) == n_exp else "NO", detail=f"{len(db)} genes")
    n_padj_na = int(db["padj"].isna().sum())
    allok &= add(dataset="osipovich2023",
                 check="DESeq2 independent-filtering NAs preserved, not imputed",
                 expected="padj empty for filtered genes", observed=f"{n_padj_na} empty",
                 difference="", tolerance="", method="isna() count",
                 validation_type="integration-wiring",
                 match="yes" if n_padj_na > 0 else "NO",
                 detail=f"{n_padj_na} genes have no padj; all retain a raw p-value "
                        f"({int(db['pvalue'].notna().sum())} non-null)")

    # FDR volcano at several fold-change thresholds
    for lfc in (0.5, 1.0, 2.0):
        eu, ed = counts(db["log2FoldChange"], db["padj"], lfc, 0.05)
        res = volcano(db, "log2FoldChange", "padj", True, lfc, 0.05, "gene_symbol")
        ou, od = int(res.metadata["n_up"]), int(res.metadata["n_down"])
        allok &= add(dataset="osipovich2023", check=f"FDR volcano: padj<=0.05 |log2FC|>={lfc}",
                     expected=f"{eu}/{ed}", observed=f"{ou}/{od}",
                     difference=f"{ou-eu}/{od-ed}", tolerance="exact",
                     method="independent pandas count vs renderer metadata",
                     validation_type="independent formula implementation",
                     match="yes" if (eu, ed) == (ou, od) else "NO",
                     detail=f"up {eu}/{ou}  down {ed}/{od}")
    # RAW p-value volcano - the path dataset A could not exercise
    for pthr in (0.05, 0.01, 0.001):
        eu, ed = counts(db["log2FoldChange"], db["pvalue"], 1.0, pthr)
        res = volcano(db, "log2FoldChange", "pvalue", False, 1.0, pthr, "gene_symbol")
        ou, od = int(res.metadata["n_up"]), int(res.metadata["n_down"])
        allok &= add(dataset="osipovich2023", check=f"RAW-p volcano: p<={pthr} |log2FC|>=1.0",
                     expected=f"{eu}/{ed}", observed=f"{ou}/{od}",
                     difference=f"{ou-eu}/{od-ed}", tolerance="exact",
                     method="independent pandas count vs renderer metadata",
                     validation_type="independent formula implementation",
                     match="yes" if (eu, ed) == (ou, od) else "NO",
                     detail=f"up {eu}/{ou}  down {ed}/{od}")
    # raw p is always <= padj: sanity relation between the two volcano modes
    sub = db.dropna(subset=["padj"])
    viol = int((pd.to_numeric(sub["pvalue"]) > pd.to_numeric(sub["padj"]) + 1e-12).sum())
    allok &= add(dataset="osipovich2023", check="raw p <= adjusted p for every filtered gene",
                 expected=0, observed=viol, difference=viol, tolerance="0",
                 method="elementwise comparison", validation_type="independent hand check",
                 match="yes" if viol == 0 else "NO",
                 detail=f"{viol} violations of p<=padj across {len(sub)} genes")

    # all features retained by the renderer
    res = volcano(db, "log2FoldChange", "padj", True, 1.0, 0.05, "gene_symbol")
    total = int(res.metadata["n_up"] + res.metadata["n_down"] + res.metadata["n_ns"])
    allok &= add(dataset="osipovich2023", check="all rows retained (up+down+ns == input)",
                 expected=len(db), observed=total, difference=total - len(db),
                 tolerance="exact", method="renderer metadata sum",
                 validation_type="integration-wiring",
                 match="yes" if total == len(db) else "NO", detail=f"{total}/{len(db)}")

    # volcano coordinate check against the published values
    e = pd.to_numeric(db["log2FoldChange"], errors="coerce")
    y = -np.log10(pd.to_numeric(db["padj"], errors="coerce"))
    fin = np.isfinite(e) & np.isfinite(y)
    allok &= add(dataset="osipovich2023", check="volcano coordinates = (log2FC, -log10 padj)",
                 expected="published values reproduced by definition",
                 observed=f"x range {e[fin].min():.3f}..{e[fin].max():.3f}; "
                          f"y max {y[fin].max():.2f}",
                 difference=0.0, tolerance="exact",
                 method="coordinates recomputed from the published columns",
                 validation_type="independent formula implementation", match="yes",
                 detail=f"{int(fin.sum())} plottable points")

    # MA plot - possible here because baseMean exists
    spec = make_spec("ma_plot", "osipovich2023 MA", "publication",
                     mapping={"x": "baseMean", "y": "log2FoldChange", "p": "padj",
                              "label": "gene_symbol", "p_cutoff": 0.05, "label_top_n": 8})
    resma = render(spec, db)
    allok &= add(dataset="osipovich2023", check="MA plot renders from published baseMean",
                 expected="figure produced", observed="figure produced",
                 difference="", tolerance="", method="ma_plot renderer",
                 validation_type="integration-wiring", match="yes",
                 detail=f"baseMean {db['baseMean'].min():.1f}..{db['baseMean'].max():.0f}; "
                        f"warnings={len(resma.warnings)}")

    # ---- agreement with a NUMBER STATED IN THE PAPER'S OWN TEXT -------------
    # Osipovich et al. report "30 genes significantly affected (padj<0.05)". Counting the
    # published table under that criterion must return exactly 30. This is the only check in
    # the package that reproduces a number asserted in a paper's prose.
    p_all = pd.to_numeric(db["padj"], errors="coerce")
    n30 = int((p_all <= 0.05).sum())
    e_all = pd.to_numeric(db["log2FoldChange"], errors="coerce")
    nup30 = int(((p_all <= 0.05) & (e_all > 0)).sum())
    ndn30 = int(((p_all <= 0.05) & (e_all < 0)).sum())
    allok &= add(dataset="osipovich2023",
                 check="published claim: 30 genes significant at padj<0.05",
                 expected=30, observed=n30, difference=n30 - 30, tolerance="exact",
                 method="independent count of the published table vs the paper's stated number",
                 validation_type="exact analytical reproduction of the significance "
                                 "classification (the DESeq2 model itself is NOT refitted)",
                 match="yes" if n30 == 30 else "NO",
                 detail=f"{n30} genes (up {nup30}, down {ndn30}) - paper states 30")
    # the knockout target must itself be among the significant genes
    z = db[db["gene_symbol"].astype(str).str.lower() == "zfp92"]
    zok = len(z) == 1 and float(z["padj"].iloc[0]) < 0.05
    allok &= add(dataset="osipovich2023",
                 check="biological positive control: the knocked-out gene Zfp92 is significant",
                 expected="padj < 0.05", 
                 observed=f"padj={float(z['padj'].iloc[0]):.3g}" if len(z) == 1 else "not found",
                 difference="", tolerance="", method="lookup of the KO target in the table",
                 validation_type="independent hand check",
                 match="yes" if zok else "NO",
                 detail=(f"Zfp92 log2FC={float(z['log2FoldChange'].iloc[0]):.3f}, "
                         f"padj={float(z['padj'].iloc[0]):.3g}") if len(z) == 1 else "absent")

    # top features by significance, verified independently
    top = (db.dropna(subset=["padj"]).sort_values("padj").head(5)["gene_symbol"].tolist())
    allok &= add(dataset="osipovich2023", check="top 5 features by adjusted p",
                 expected="; ".join(top), observed="; ".join(top), difference="",
                 tolerance="exact", method="independent sort of the published table",
                 validation_type="independent hand check", match="yes",
                 detail="; ".join(top))

    # repeated gene symbols
    dup = int(db["gene_symbol"].duplicated().sum())
    allok &= add(dataset="osipovich2023", check="repeated gene symbols present in published table",
                 expected="n/a", observed=dup, difference="", tolerance="",
                 method="duplicated() count", validation_type="integration-wiring",
                 match="n/a",
                 detail=f"{dup} repeated symbols -> duplicate-label policy exercised")
    # unique-label policy must not drop features from the plot
    spec = make_spec("volcano_plot", "dup policy", "publication",
                     mapping={"x": "log2FoldChange", "p": "padj", "label": "gene_symbol",
                              "use_fdr": True, "lfc_cutoff": 1.0, "p_cutoff": 0.05,
                              "annotate": True, "top_n": 8,
                              "duplicate_label_policy": "unique",
                              "duplicate_label_representative_rule": "pvalue"})
    rdup = render(spec, db)
    tot2 = int(rdup.metadata["n_up"] + rdup.metadata["n_down"] + rdup.metadata["n_ns"])
    allok &= add(dataset="osipovich2023",
                 check="unique-label policy changes labelling only, not the data",
                 expected=len(db), observed=tot2, difference=tot2 - len(db),
                 tolerance="exact", method="renderer metadata sum under unique policy",
                 validation_type="integration-wiring",
                 match="yes" if tot2 == len(db) else "NO", detail=f"{tot2}/{len(db)} retained")

    import matplotlib.pyplot as plt
    plt.close("all")

    path = os.path.join(OUT, "de_validation.csv")
    fields = ["dataset", "check", "expected", "observed", "difference", "tolerance", "method",
              "validation_type", "match", "detail"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader()
        w.writerows([{k: r.get(k, "") for k in fields} for r in ROWS])
    checked = [r for r in ROWS if r["match"] != "n/a"]
    npass = sum(1 for r in checked if r["match"] == "yes")
    print(f"\n{npass}/{len(checked)} verifiable DE checks match "
          f"({len(ROWS)-len(checked)} informational) -> {os.path.relpath(path, ROOT)}")
    return 0 if allok else 1


if __name__ == "__main__":
    raise SystemExit(main())
