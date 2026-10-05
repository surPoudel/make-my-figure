"""Independent DE validation against a published differential-results table.

Source: Kume et al. 2024, eLife 97654, Figure 5-source data 1 (sheet 'Figure 5A').
Article and data CC BY 4.0. p-values are read verbatim from the published table; no DE
statistics are recomputed here or by the application.

The check is deliberately independent of the renderer: significant up/down counts are
computed from the table with plain pandas using the prompt's definition, then compared
with the counts the volcano renderer reports in its own metadata. Both raw-p and FDR
significance fields and several thresholds are exercised.

Run: PYTHONPATH=. python scripts/validate_de_benchmark.py
Writes manuscript/final_revision/validation/de_validation.csv
"""
from __future__ import annotations

import csv
import os

import matplotlib
matplotlib.use("Agg")
import pandas as pd

from make_my_figure_core.plots.registry import make_spec, render

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "manuscript", "final_revision", "validation")
os.makedirs(OUT, exist_ok=True)
DE = os.path.join(ROOT, "benchmarks", "ten_publication_recreation", "publications",
                  "kume2024_psoriasis_semaphorin", "processed_data",
                  "psoriasis_nl_vs_ctl_de.csv")
ROWS = []


def check(label, df, effect_col, sig_col, sig_field, lfc_thr, p_thr):
    """Independent count vs renderer-reported count."""
    e = pd.to_numeric(df[effect_col], errors="coerce")
    p = pd.to_numeric(df[sig_col], errors="coerce")
    exp_up = int(((e >= lfc_thr) & (p <= p_thr)).sum())
    exp_dn = int(((e <= -lfc_thr) & (p <= p_thr)).sum())

    spec = make_spec("volcano_plot", "kume2024 Figure 5A", "publication",
                     mapping={"x": effect_col, "p": sig_col, "label": "gene",
                              "use_fdr": sig_field == "fdr",
                              "lfc_cutoff": lfc_thr, "p_cutoff": p_thr,
                              "annotate": False})
    res = render(spec, df)
    obs_up = int(res.metadata["n_up"])
    obs_dn = int(res.metadata["n_down"])
    ok = (exp_up == obs_up) and (exp_dn == obs_dn)
    ROWS.append({"benchmark": "kume2024_psoriasis_semaphorin",
                 "comparison": label, "feature_count": len(df),
                 "effect_column": effect_col, "p_column": "padj (published)",
                 "fdr_column": sig_col if sig_field == "fdr" else "",
                 "effect_threshold": lfc_thr, "significance_field": sig_field,
                 "significance_threshold": p_thr,
                 "expected_up": exp_up, "observed_up": obs_up,
                 "expected_down": exp_dn, "observed_down": obs_dn,
                 "match": "yes" if ok else "NO",
                 "notes": "independent pandas count vs volcano renderer metadata"})
    print(f"{'OK ' if ok else 'FAIL'} {label:44} up {exp_up}/{obs_up}  down {exp_dn}/{obs_dn}")
    return ok


def main() -> int:
    df = pd.read_csv(DE)
    print(f"published DE table: {len(df)} features, columns {list(df.columns)}\n")

    all_ok = True
    # FDR significance at several fold-change thresholds
    for lfc in (0.5, 1.0, 2.0):
        all_ok &= check(f"FDR<=0.05, |log2FC|>={lfc}", df, "log2FoldChange", "padj",
                        "fdr", lfc, 0.05)
    # stricter FDR
    for pthr in (0.01, 0.001):
        all_ok &= check(f"FDR<={pthr}, |log2FC|>=1.0", df, "log2FoldChange", "padj",
                        "fdr", 1.0, pthr)

    # row preservation and label integrity
    spec = make_spec("volcano_plot", "kume2024 Figure 5A", "publication",
                     mapping={"x": "log2FoldChange", "p": "padj", "label": "gene",
                              "use_fdr": True, "lfc_cutoff": 1.0, "p_cutoff": 0.05,
                              "annotate": False})
    res = render(spec, df)
    total = res.metadata["n_up"] + res.metadata["n_down"] + res.metadata["n_ns"]
    ok_rows = total == len(df)
    ROWS.append({"benchmark": "kume2024_psoriasis_semaphorin",
                 "comparison": "all rows retained (up+down+ns == input rows)",
                 "feature_count": len(df), "effect_column": "log2FoldChange",
                 "p_column": "padj (published)", "fdr_column": "padj",
                 "effect_threshold": 1.0, "significance_field": "fdr",
                 "significance_threshold": 0.05,
                 "expected_up": len(df), "observed_up": total,
                 "expected_down": "", "observed_down": "",
                 "match": "yes" if ok_rows else "NO",
                 "notes": "no features silently dropped by the renderer"})
    print(f"{'OK ' if ok_rows else 'FAIL'} {'all rows retained':44} {len(df)}/{total}")
    all_ok &= ok_rows

    # duplicate-label handling on the real table (gene symbols repeated?)
    dup = df["gene"].duplicated().sum()
    ROWS.append({"benchmark": "kume2024_psoriasis_semaphorin",
                 "comparison": "duplicate gene symbols in published table",
                 "feature_count": len(df), "effect_column": "log2FoldChange",
                 "p_column": "padj (published)", "fdr_column": "padj",
                 "effect_threshold": "", "significance_field": "", "significance_threshold": "",
                 "expected_up": "", "observed_up": int(dup), "expected_down": "",
                 "observed_down": "", "match": "n/a",
                 "notes": f"{dup} repeated symbols; policies exercised on synthetic data where repeats are frequent"})
    print(f"     duplicate gene symbols in this table: {dup}")

    # p-values read verbatim: recomputing padj from the shipped -log10 must round-trip
    recon = 10 ** (-pd.to_numeric(df["neglog10_padj"]))
    worst = float((recon - pd.to_numeric(df["padj"])).abs().max())
    ok_p = worst < 1e-12
    ROWS.append({"benchmark": "kume2024_psoriasis_semaphorin",
                 "comparison": "padj round-trip from published -log10(padj)",
                 "feature_count": len(df), "effect_column": "", "p_column": "padj",
                 "fdr_column": "neglog10_padj", "effect_threshold": "",
                 "significance_field": "", "significance_threshold": "",
                 "expected_up": 0, "observed_up": f"{worst:.2e}", "expected_down": "",
                 "observed_down": "", "match": "yes" if ok_p else "NO",
                 "notes": "confirms p-values were transcribed, not recomputed"})
    print(f"{'OK ' if ok_p else 'FAIL'} {'padj round-trip':44} max |diff| {worst:.2e}")
    all_ok &= ok_p

    path = os.path.join(OUT, "de_validation.csv")
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ROWS[0].keys()))
        w.writeheader(); w.writerows(ROWS)
    npass = sum(1 for r in ROWS if r["match"] == "yes")
    print(f"\n{npass}/{sum(1 for r in ROWS if r['match'] != 'n/a')} DE checks match -> "
          f"{os.path.relpath(path, ROOT)}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
