"""Reproducible generator for statistics example/workflow datasets.

For every applicable statistical workflow this writes, under
``examples/statistics/<slug>/``:

    data.csv / data.tsv / data.xlsx   synthetic table
    plotspec.json                     PlotSpec (with an embedded StatsSpec)
    statsspec.json                    the StatsSpec config alone
    README.md                         test design + required columns
    expected_method_report.md         the method sentence(s) produced

plus a machine-readable manifest at ``examples/statistics/manifest.json``.

ALL DATA ARE SYNTHETIC (fixed seed). They look plausible but are not real
measurements and must not be cited as findings. Safe to re-run: only writes
inside ``examples/statistics/``.

Usage:
    python scripts/generate_stats_examples.py
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Callable, Dict, List, Tuple

import numpy as np
import pandas as pd

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import matplotlib  # noqa: E402

matplotlib.use("Agg")

from make_my_figure_core.plots.registry import make_spec, render  # noqa: E402
from make_my_figure_core.statistics.schemas import normalize_stats_spec  # noqa: E402

SEED = 20240601
OUT_DIR = os.path.join(_ROOT, "examples", "statistics")


def _write_tables(df: pd.DataFrame, folder: str) -> None:
    df.to_csv(os.path.join(folder, "data.csv"), index=False)
    df.to_csv(os.path.join(folder, "data.tsv"), sep="\t", index=False)
    try:
        df.to_excel(os.path.join(folder, "data.xlsx"), index=False)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Builders: each returns (df, plot_type, mapping, stats_spec, readme, layout)
# ---------------------------------------------------------------------------

def two_group_unpaired(rng):
    rows = []
    for grp, mu in [("Control", 5.0), ("Treated", 6.4)]:
        for i in range(18):
            rows.append({"group": grp, "subject": f"{grp[:1]}{i+1}",
                         "response": round(float(rng.normal(mu, 1.1)), 3)})
    df = pd.DataFrame(rows)
    ss = {"enabled": True, "test": "welch_t", "comparison_mode": "all_pairs",
          "correction": "none", "annotation": {"mode": "both"}}
    readme = ("Two independent groups (Control vs Treated), ~18 samples each.\n\n"
              "Design: unpaired, two-sided. Default test: Welch's t-test (does not "
              "assume equal variance). Alternatives: Student's t-test, Mann-Whitney U.\n\n"
              "Required columns: `group` (categorical), `response` (numeric).")
    return df, "boxplot_or_violin_with_points", {"x": "group", "y": "response", "kind": "box"}, ss, readme, {}


def two_group_paired(rng):
    rows = []
    for i in range(15):
        base = rng.normal(5.0, 1.0)
        rows.append({"subject": f"S{i+1:02d}", "timepoint": "Pre", "value": round(float(base), 3)})
        rows.append({"subject": f"S{i+1:02d}", "timepoint": "Post",
                     "value": round(float(base + rng.normal(0.9, 0.6)), 3)})
    df = pd.DataFrame(rows)
    ss = {"enabled": True, "test": "paired_t", "comparison_mode": "all_pairs",
          "subject_column": "subject", "correction": "none", "annotation": {"mode": "both"}}
    readme = ("Paired measurements (Pre vs Post) on the same 15 subjects.\n\n"
              "Design: paired (matched on `subject`), two-sided. Default test: paired "
              "t-test. Alternative: Wilcoxon signed-rank. A subject/pair ID is REQUIRED.\n\n"
              "Required columns: `subject` (pair ID), `timepoint` (Pre/Post), `value` (numeric).")
    return df, "boxplot_or_violin_with_points", {"x": "timepoint", "y": "value", "kind": "box"}, ss, readme, {}


def one_way(rng):
    rows = []
    for grp, mu in [("Low", 4.0), ("Medium", 5.2), ("High", 6.8)]:
        for i in range(16):
            rows.append({"dose_group": grp, "measurement": round(float(rng.normal(mu, 1.0)), 3)})
    df = pd.DataFrame(rows)
    ss = {"enabled": True, "test": "one_way_anova", "posthoc": True,
          "posthoc_test": "welch_t", "comparison_mode": "all_pairs",
          "correction": "benjamini_hochberg", "annotation": {"mode": "stars"}}
    readme = ("Three groups (Low/Medium/High), 16 samples each.\n\n"
              "Design: one categorical factor, >2 groups. Default: one-way ANOVA "
              "(omnibus) with post-hoc pairwise Welch t-tests, Benjamini-Hochberg "
              "corrected. Nonparametric alternative: Kruskal-Wallis + Dunn.\n\n"
              "Required columns: `dose_group` (categorical), `measurement` (numeric).")
    return df, "boxplot_or_violin_with_points", {"x": "dose_group", "y": "measurement", "kind": "box"}, ss, readme, {}


def two_way(rng):
    base = {("WT", "Vehicle"): 1.0, ("WT", "Drug"): 1.9,
            ("KO", "Vehicle"): 0.9, ("KO", "Drug"): 1.1}
    rows = []
    for geno in ["WT", "KO"]:
        for treat in ["Vehicle", "Drug"]:
            for i in range(8):
                rows.append({"genotype": geno, "treatment": treat,
                             "expression": round(float(rng.normal(base[(geno, treat)], 0.18)), 3)})
    df = pd.DataFrame(rows)
    ss = {"enabled": True, "test": "two_way_anova", "correction": "none",
          "group_column": "genotype", "subgroup_column": "treatment"}
    readme = ("Two-factor design: genotype (WT/KO) x treatment (Vehicle/Drug), 8 "
              "replicates per cell.\n\n"
              "Design: two categorical factors. Default: two-way ANOVA reporting both "
              "main effects and their interaction. For within-cell pairwise brackets, "
              "switch comparison mode to 'within each x category'.\n\n"
              "Required columns: `genotype`, `treatment` (categorical), `expression` (numeric).")
    return (df, "grouped_barplot_with_error_bar",
            {"x": "genotype", "group": "treatment", "y": "expression", "error": "sem"}, ss, readme, {})


def repeated_measures(rng):
    rows = []
    for i in range(12):
        subj_effect = rng.normal(0, 0.8)
        for t, add in [("T0", 0.0), ("T1", 0.8), ("T2", 1.6)]:
            rows.append({"subject": f"P{i+1:02d}", "time": t,
                         "signal": round(float(5.0 + subj_effect + add + rng.normal(0, 0.4)), 3)})
    df = pd.DataFrame(rows)
    ss = {"enabled": True, "test": "rm_anova", "group_column": "time",
          "subject_column": "subject", "correction": "none"}
    readme = ("Repeated measures: 12 subjects each measured at 3 timepoints "
              "(T0/T1/T2).\n\n"
              "Design: within-subject factor `time`, subject ID `subject`. Default: "
              "repeated-measures ANOVA (requires a complete, balanced design - one row "
              "per subject per timepoint). Sphericity is assumed and not corrected.\n\n"
              "Required columns: `subject` (ID), `time` (within factor), `signal` (numeric).")
    return df, "boxplot_or_violin_with_points", {"x": "time", "y": "signal", "kind": "box"}, ss, readme, {}


def nonparametric(rng):
    rows = []
    # Skewed (log-normal) data where a nonparametric test is appropriate.
    for grp, scale in [("A", 1.0), ("B", 1.8)]:
        for i in range(20):
            rows.append({"group": grp, "value": round(float(rng.lognormal(0.0, 0.6) * scale), 3)})
    df = pd.DataFrame(rows)
    ss = {"enabled": True, "test": "mann_whitney", "comparison_mode": "all_pairs",
          "correction": "none", "annotation": {"mode": "both"}}
    readme = ("Two groups with right-skewed (log-normal) data, 20 each.\n\n"
              "Design: unpaired, nonparametric. Default: Mann-Whitney U with a "
              "rank-biserial effect size. Use this instead of a t-test when normality "
              "is doubtful.\n\n"
              "Required columns: `group` (categorical), `value` (numeric).")
    return df, "boxplot_or_violin_with_points", {"x": "group", "y": "value", "kind": "violin"}, ss, readme, {}


def categorical_2x2(rng):
    # Responders by treatment arm (2x2).
    rows = []
    design = {("Arm_A", "Responder"): 22, ("Arm_A", "Non_responder"): 8,
              ("Arm_B", "Responder"): 12, ("Arm_B", "Non_responder"): 18}
    for (arm, resp), n in design.items():
        for _ in range(n):
            rows.append({"treatment_arm": arm, "response": resp, "count": 1})
    df = pd.DataFrame(rows).sample(frac=1.0, random_state=SEED).reset_index(drop=True)
    ss = {"enabled": True, "test": "fishers_exact", "row_column": "treatment_arm",
          "col_column": "response", "correction": "none"}
    readme = ("A 2x2 table: treatment arm (A/B) x response (Responder/Non-responder).\n\n"
              "Design: categorical association, 2x2. Default: Fisher's exact test (odds "
              "ratio + p). Chi-square is available for larger tables / large counts.\n\n"
              "Required columns: `treatment_arm`, `response` (both categorical).")
    return df, "stacked_bar_composition", {"x": "treatment_arm", "stack": "response", "y": "count"}, ss, readme, {}


def contingency_large(rng):
    rows = []
    grid = {
        ("TypeI", "Grade1"): 18, ("TypeI", "Grade2"): 10, ("TypeI", "Grade3"): 4,
        ("TypeII", "Grade1"): 8, ("TypeII", "Grade2"): 16, ("TypeII", "Grade3"): 9,
        ("TypeIII", "Grade1"): 5, ("TypeIII", "Grade2"): 11, ("TypeIII", "Grade3"): 20,
    }
    for (subtype, grade), n in grid.items():
        for _ in range(n):
            rows.append({"subtype": subtype, "grade": grade, "count": 1})
    df = pd.DataFrame(rows).sample(frac=1.0, random_state=SEED).reset_index(drop=True)
    ss = {"enabled": True, "test": "chi_square", "row_column": "subtype",
          "col_column": "grade", "correction": "none"}
    readme = ("A 3x3 contingency table: tumor subtype x grade.\n\n"
              "Design: categorical association, larger than 2x2. Default: chi-square "
              "test of independence (with Cramer's V). The app warns if any expected "
              "cell count < 5.\n\n"
              "Required columns: `subtype`, `grade` (both categorical).")
    return df, "stacked_bar_composition", {"x": "subtype", "stack": "grade", "y": "count"}, ss, readme, {}


def survival_km(rng):
    rows = []
    for grp, scale in [("Standard", 12.0), ("Experimental", 20.0)]:
        for i in range(40):
            t = rng.exponential(scale)
            censor_time = rng.uniform(18, 36)
            event = 1 if t <= censor_time else 0
            rows.append({"patient": f"{grp[:3]}{i+1}", "group": grp,
                         "time_months": round(float(min(t, censor_time)), 2),
                         "event": int(event)})
    df = pd.DataFrame(rows)
    ss = {"enabled": True, "test": "logrank", "group_column": "group",
          "time_column": "time_months", "event_column": "event", "correction": "none"}
    readme = ("Survival data for two arms (Standard/Experimental), 40 patients each, "
              "with administrative censoring.\n\n"
              "Design: right-censored survival. Default: log-rank test comparing the two "
              "curves. A Cox model (hazard ratio) is available; its proportional-hazards "
              "assumption is not auto-checked.\n\n"
              "Required columns: `time_months` (numeric), `event` (1=event, 0=censored), "
              "`group` (categorical).")
    return df, "kaplan_meier_survival_curve", {"time": "time_months", "event": "event", "group": "group"}, ss, readme, {}


def scatter_correlation(rng):
    n = 50
    x = rng.uniform(0, 10, n)
    y = 1.2 * x + 2.0 + rng.normal(0, 1.8, n)
    df = pd.DataFrame({"biomarker": np.round(x, 3), "outcome": np.round(y, 3)})
    ss = {"enabled": True, "test": "pearson", "x_column": "biomarker",
          "y_column": "outcome", "correction": "none"}
    readme = ("Continuous x-y data (biomarker vs outcome), n=50.\n\n"
              "Design: bivariate association. Default: Pearson correlation (r, p, R², "
              "with a Fisher-z 95% CI). Alternatives: Spearman (monotonic) or linear "
              "regression (slope + CI). Per-group stats are computed if a color/group "
              "column is set.\n\n"
              "Required columns: `biomarker`, `outcome` (both numeric).")
    return df, "scatterplot_with_regression", {"x": "biomarker", "y": "outcome", "fit_line": True}, ss, readme, {}


def grouped_within_dose(rng):
    # ToothGrowth-like: dose x supplement, compare supplements within each dose.
    base = {("0.5", "VC"): 8.0, ("0.5", "OJ"): 13.0,
            ("1.0", "VC"): 16.5, ("1.0", "OJ"): 22.0,
            ("2.0", "VC"): 26.0, ("2.0", "OJ"): 26.5}
    rows = []
    for dose in ["0.5", "1.0", "2.0"]:
        for supp in ["VC", "OJ"]:
            for i in range(10):
                rows.append({"dose": dose, "supplement": supp,
                             "tooth_length": round(float(rng.normal(base[(dose, supp)], 2.5)), 2)})
    df = pd.DataFrame(rows)
    ss = {"enabled": True, "test": "welch_t", "comparison_mode": "within_x",
          "group_column": "dose", "subgroup_column": "supplement",
          "correction": "benjamini_hochberg", "annotation": {"mode": "both"}}
    readme = ("Grouped design (like the classic ToothGrowth data): dose (0.5/1.0/2.0) x "
              "supplement (VC/OJ), 10 per cell.\n\n"
              "Design: compare the two supplements WITHIN each dose. Default: Welch's "
              "t-test per dose, Benjamini-Hochberg corrected across the 3 comparisons; "
              "each dose gets its own bracket. Two-way ANOVA is also available.\n\n"
              "Required columns: `dose` (x), `supplement` (subgroup), `tooth_length` (numeric).")
    return (df, "grouped_barplot_with_error_bar",
            {"x": "dose", "group": "supplement", "y": "tooth_length", "error": "sem"}, ss, readme, {})


BUILDERS: Dict[str, Callable] = {
    "two_group_unpaired": two_group_unpaired,
    "two_group_paired": two_group_paired,
    "one_way_anova": one_way,
    "two_way_anova": two_way,
    "repeated_measures": repeated_measures,
    "nonparametric": nonparametric,
    "categorical_2x2": categorical_2x2,
    "contingency_large": contingency_large,
    "survival_km": survival_km,
    "scatter_correlation": scatter_correlation,
    "grouped_within_dose": grouped_within_dose,
}


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    manifest: List[Dict[str, Any]] = []
    for slug, builder in BUILDERS.items():
        rng = np.random.default_rng(SEED)
        df, plot_type, mapping, stats_spec, readme, layout = builder(rng)
        folder = os.path.join(OUT_DIR, slug)
        os.makedirs(folder, exist_ok=True)
        _write_tables(df, folder)

        clean_mapping = {k: v for k, v in mapping.items() if v is not None}
        spec = make_spec(plot_type, "data.csv", "publication", mapping=clean_mapping,
                         layout=layout or None)
        norm_stats = normalize_stats_spec(stats_spec)
        spec["statistics"] = norm_stats
        with open(os.path.join(folder, "plotspec.json"), "w", encoding="utf-8") as fh:
            json.dump(spec, fh, indent=2)
        with open(os.path.join(folder, "statsspec.json"), "w", encoding="utf-8") as fh:
            json.dump(norm_stats, fh, indent=2)

        # Run to capture the expected method report (transparency).
        method_lines = ["(method report unavailable)"]
        try:
            result = render(spec, df)
            report = getattr(result, "stats_report", None)
            if report is not None:
                method_lines = [report.method_paragraph, ""]
                method_lines += [f"- {r.method_sentence}" for r in report.results]
                if report.warnings:
                    method_lines += ["", "Warnings:"] + [f"- {w}" for w in report.warnings]
            import matplotlib.pyplot as plt

            plt.close(result.figure)
        except Exception as exc:  # keep going; note the failure
            method_lines = [f"(could not run: {exc})"]

        with open(os.path.join(folder, "README.md"), "w", encoding="utf-8") as fh:
            fh.write(f"# Statistics example: {slug}\n\n{readme}\n\n"
                     "All data are SYNTHETIC (fixed seed) and not real measurements.\n")
        with open(os.path.join(folder, "expected_method_report.md"), "w", encoding="utf-8") as fh:
            fh.write(f"# Expected method report: {slug}\n\n" + "\n".join(method_lines) + "\n")

        manifest.append({
            "slug": slug, "plot_type": plot_type, "test": norm_stats.get("test"),
            "comparison_mode": norm_stats.get("comparison_mode"),
            "n_rows": int(len(df)), "columns": list(df.columns),
        })
        print(f"  wrote examples/statistics/{slug}/  ({plot_type}, {norm_stats.get('test')})")

    with open(os.path.join(OUT_DIR, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump({"license": "CC0-1.0", "source": "scripts/generate_stats_examples.py",
                   "examples": manifest}, fh, indent=2)
    print(f"Wrote {len(manifest)} statistics examples to examples/statistics/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
