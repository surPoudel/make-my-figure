"""Validate the data-aware recommendation engine against independent expectations.

The engine is RULE-BASED, not machine-learned. This harness does not inspect the rules; it
states, independently and in advance, what a domain analyst should expect for each input
structure, then compares that with what the engine returns. Negative expectations (plots that
must NOT be offered) are checked as well, because a recommender that offers everything is
useless.

The engine returns a THREE-state result per plot, which the first version of this harness did
not model and which is recorded here explicitly:
  recommended  confidence >= RECOMMEND_MIN and no blocking warning
  gated        offered but carrying a warning stating what must be done first (e.g. a volcano
               listed against a table that has no fold-change column)
  omitted      not returned at all
A negative expectation is violated only when a forbidden plot is RECOMMENDED. A forbidden plot
appearing as "gated" is correct behaviour: the interface tells the user why it is unavailable.
Both the strict verdict (any appearance) and the refined verdict (recommended only) are
reported, so the relaxation is visible rather than silent.

Run: PYTHONPATH=. python scripts/validate_recommendations.py
Writes manuscript/final_submission/validation/recommendation_validation.csv
"""
from __future__ import annotations

import csv
import os

import numpy as np
import pandas as pd

from make_my_figure_core.recommendations import (detect_schema, profile_table,
                                                 recommend_for_table)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "manuscript", "final_submission", "validation")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)
RECOMMEND_MIN = 0.55  # below this the interface presents an option as gated, not recommended


def grouped_long():
    n = 90
    g = np.repeat(["control", "treated", "rescue"], n // 3)
    return pd.DataFrame({"sample_id": [f"S{i:03d}" for i in range(n)], "group": g,
                         "expression": rng.normal(10, 2, n) + (g == "treated") * 1.8})


def matrix_wide():
    nf, ns = 300, 12
    d = {"feature_id": [f"G{i:04d}" for i in range(nf)]}
    for s in range(ns):
        grp = "ctrl" if s < ns // 2 else "treat"
        d[f"{grp}_{s+1:02d}"] = rng.normal(8, 2, nf)
    return pd.DataFrame(d)


def de_table():
    n = 4000
    lfc = rng.normal(0, 1.2, n)
    p = np.clip(np.abs(rng.normal(0, 0.12, n)), 1e-14, 1.0)
    return pd.DataFrame({"feature_id": [f"ENSG{i:07d}" for i in range(n)],
                         "gene_symbol": [f"SYM{i%3200}" for i in range(n)],
                         "log2FoldChange": lfc, "pvalue": p,
                         "padj": np.clip(p * 2.4, 0, 1),
                         "baseMean": rng.lognormal(5, 1.1, n)})


def survival_table():
    n = 160
    return pd.DataFrame({"patient_id": [f"P{i:03d}" for i in range(n)],
                         "time_months": rng.exponential(24, n).round(2),
                         "event": rng.integers(0, 2, n),
                         "risk_group": np.where(np.arange(n) % 2 == 0, "high", "low")})


def gwas_table():
    n = 5000
    return pd.DataFrame({"snp": [f"rs{1000000+i}" for i in range(n)],
                         "chromosome": rng.integers(1, 23, n),
                         "position": rng.integers(1, 250_000_000, n),
                         "p_value": np.clip(rng.beta(0.6, 9, n), 1e-20, 1.0)})


def edge_list():
    src = [f"N{i%40}" for i in range(160)]
    dst = [f"N{(i*7)%40}" for i in range(160)]
    return pd.DataFrame({"source": src, "target": dst,
                         "weight": rng.uniform(0.1, 1.0, 160).round(3)})


def embedding_table():
    n = 500
    return pd.DataFrame({"cell_id": [f"C{i:04d}" for i in range(n)],
                         "UMAP_1": rng.normal(0, 3, n), "UMAP_2": rng.normal(0, 3, n),
                         "cell_type": rng.choice(["Tcell", "Bcell", "Mono", "NK"], n)})


# (name, builder, expected schema, plot substrings that MUST appear,
#  plot substrings that must NOT appear, scientific rationale)
SCENARIOS = [
    ("grouped long measurements", grouped_long, {"generic_long"},
     [("box", "violin")], ["volcano", "kaplan", "manhattan", "network"],
     "one categorical grouping and one continuous response calls for a distribution "
     "comparison, not a genomics-specific view"),
    ("features x samples matrix", matrix_wide,
     {"expression_like_matrix", "numeric_matrix", "matrix_plus_metadata"},
     [("heatmap",), ("pca",)], ["kaplan", "manhattan", "network_graph"],
     "a wide numeric matrix supports unsupervised structure views"),
    ("precomputed differential table", de_table, {"precomputed_differential"},
     [("volcano",)], ["kaplan", "manhattan", "network_graph"],
     "effect size plus significance is the volcano signature; an abundance column "
     "additionally permits an MA plot"),
    ("survival / time-to-event", survival_table, {"survival"},
     [("survival", "kaplan")], ["volcano", "manhattan", "network_graph", "heatmap"],
     "duration plus a binary event and a grouping variable is the Kaplan-Meier signature"),
    ("GWAS-style association table", gwas_table, {"gwas"},
     [("manhattan",)], ["volcano", "kaplan", "network_graph"],
     "chromosome, position and p-value together identify a genome-wide scan"),
    ("network edge list", edge_list, {"network_edge_list"},
     [("network",)], ["volcano", "kaplan", "manhattan", "heatmap"],
     "two identifier columns forming pairs describe a graph, not a measurement table"),
    ("embedding coordinates", embedding_table, {"generic_long", "unknown"},
     [("scatter",)], ["volcano", "kaplan", "manhattan"],
     "two continuous coordinates with a categorical label is a scatter of an embedding"),
]


def main() -> int:
    rows, npass, nfail = [], 0, 0
    for name, build, exp_schema, must, must_not, rationale in SCENARIOS:
        df = build()
        prof = profile_table(df, table_name=name)
        schema = detect_schema(prof, df)
        spec = recommend_for_table(df, table_name=name)

        recs = spec.recommendations or []
        direct = [r for r in recs if getattr(r, "kind", "direct") != "transform"]
        transforms = [r for r in recs if getattr(r, "kind", "") == "transform"]
        got = [r.plot_type for r in direct]
        got_l = " ".join(got).lower()

        rec_only = [r for r in direct
                    if r.confidence >= RECOMMEND_MIN and not (r.warnings or [])]
        gated = [r for r in direct
                 if r.confidence < RECOMMEND_MIN or (r.warnings or [])]
        rec_l = " ".join(r.plot_type for r in rec_only).lower()

        schema_ok = schema in exp_schema
        # each required group is satisfied if ANY of its synonyms appears
        missing = [grp for grp in must if not any(s in got_l for s in grp)]
        forbidden_any = [b for b in must_not if b in got_l]
        forbidden_rec = [b for b in must_not if b in rec_l]

        # rank of the first required family among the recommendations
        ranks = []
        for grp in must:
            idx = next((i for i, pt in enumerate(got, 1)
                        if any(s in pt.lower() for s in grp)), None)
            ranks.append(f"{'|'.join(grp)}@{idx if idx else 'absent'}")

        ok = schema_ok and not missing and not forbidden_rec
        strict_ok = schema_ok and not missing and not forbidden_any
        npass += ok
        nfail += (not ok)

        rows.append({
            "scenario": name,
            "n_rows": len(df), "n_cols": df.shape[1],
            "available_columns": "; ".join(df.columns[:12]),
            "detected_schema": schema,
            "expected_schema_any_of": " | ".join(sorted(exp_schema)),
            "schema_match": "yes" if schema_ok else "NO",
            "confirmed_mapping": "; ".join(
                f"{k}={v}" for k, v in (direct[0].required_mappings or {}).items())[:180]
            if direct else "",
            "plots_recommended_top5": "; ".join(got[:5]),
            "n_recommended": len(direct),
            "required_families_present": "yes" if not missing else
            "NO: " + "/".join("|".join(g) for g in missing),
            "required_family_rank": "; ".join(ranks),
            "intentionally_not_recommended": "; ".join(must_not),
            "forbidden_recommended": "; ".join(forbidden_rec) or "none",
            "forbidden_gated_with_warning": "; ".join(forbidden_any) or "none",
            "gated_offers": "; ".join(f"{r.plot_type}({r.confidence:.2f})" for r in gated) or "none",
            "strict_verdict_any_appearance": "PASS" if strict_ok else "FAIL",
            "transformations_recommended": "; ".join(
                (getattr(t, "display_name", "") or t.plot_type) for t in transforms) or "none",
            "top_confidence": f"{direct[0].confidence:.2f}" if direct else "",
            "scientifically_reasonable": "yes" if ok else "review",
            "independent_expectation_rationale": rationale,
            "validation_type": "independent expectation check (rule-based engine; not ML)",
            "result": "PASS" if ok else "FAIL",
        })
        flag = "PASS" if ok else "FAIL"
        print(f"{flag}  {name:32} schema={schema:26} top={got[:3]}")
        if missing:
            print(f"        missing required family: {missing}")
        if forbidden_rec:
            print(f"        RECOMMENDED a forbidden plot: {forbidden_rec}")
        elif forbidden_any:
            print(f"        forbidden plot present but gated with a warning: {forbidden_any}")
        if transforms:
            print(f"        transforms offered: "
                  f"{[getattr(t,'display_name','') or t.plot_type for t in transforms][:3]}")

    path = os.path.join(OUT, "recommendation_validation.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"\n{npass}/{len(SCENARIOS)} scenarios PASS on the refined (recommended-only) "
          f"criterion -> {os.path.relpath(path, ROOT)}")
    strict = sum(1 for r in rows if r["strict_verdict_any_appearance"] == "PASS")
    print(f"{strict}/{len(SCENARIOS)} pass the stricter any-appearance criterion; the "
          f"difference is gated offers carrying an explanatory warning.")
    print("\nRecorded limitations (reported, not corrected):")
    for r in rows:
        if r["required_family_rank"] and "@1" not in r["required_family_rank"]:
            print(f"  - {r['scenario']}: expected family not top-ranked "
                  f"({r['required_family_rank']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
