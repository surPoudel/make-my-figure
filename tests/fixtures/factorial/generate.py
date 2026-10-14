"""Generate the SYNTHETIC factorial-design fixtures (deterministic).

These tables are simulated. They are shaped like an insect-behaviour experiment
(treatment x social setting x time, one colony per row, body size as a
covariate) so the tutorial reads naturally, but they are NOT observations of
real bees and must never be presented as such.

Run:  python tests/fixtures/factorial/generate.py
Writes one CSV per design into this directory plus ``cases.csv`` (the models the
R validation fits). Re-running reproduces the files byte for byte.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
TRT = ["control", "exposed"]
SOC = ["group", "isolated", "paired"]
TIME = ["day2", "day4"]


def _design(n_per_cell, seed, *, effects, sd=1.0):
    rng = np.random.default_rng(seed)
    rows, k = [], 0
    for a in TRT:
        for b in SOC:
            for t in TIME:
                n = n_per_cell(a, b, t) if callable(n_per_cell) else n_per_cell
                for _ in range(n):
                    k += 1
                    size = round(float(rng.normal(3.4, 0.25)), 3)
                    mu = 10.0 + effects(a, b, t) + 0.8 * (size - 3.4)
                    rows.append({"colony_id": f"C{k:03d}", "treatment": a, "social": b, "time": t,
                                 "body_size_mm": size, "quantity": round(float(mu + rng.normal(0, sd)), 4)})
    return pd.DataFrame(rows)


def interaction_effects(a, b, t):
    e = 2.0 * (a == "exposed") + 0.6 * (t == "day4") + 1.5 * (a == "exposed") * (t == "day4")
    return e + 1.2 * (a == "exposed") * (b == "isolated") * (t == "day4")


def additive_effects(a, b, t):
    return 2.0 * (a == "exposed") + 0.5 * (b == "isolated") + 0.6 * (t == "day4")


def build() -> dict:
    sets = {}
    sets["balanced_interaction"] = _design(4, 101, effects=interaction_effects)
    sets["balanced_additive"] = _design(4, 202, effects=additive_effects)
    sizes = {("control", "group", "day2"): 2, ("control", "isolated", "day4"): 5,
             ("exposed", "paired", "day2"): 3, ("exposed", "group", "day4"): 6}
    sets["unbalanced"] = _design(lambda a, b, t: sizes.get((a, b, t), 4), 303, effects=interaction_effects)
    d = _design(4, 404, effects=interaction_effects)
    d.loc[[3, 17, 30], "quantity"] = np.nan
    d.loc[8, "social"] = np.nan
    sets["missing_values"] = d
    d = _design(3, 505, effects=additive_effects)
    sets["missing_cell"] = d[~((d.treatment == "exposed") & (d.social == "paired") & (d.time == "day4"))]
    d = _design(3, 606, effects=additive_effects)
    d["time"] = np.where(d.treatment == "control", "day2", "day4")
    sets["confounded"] = d
    d = _design(1, 707, effects=additive_effects)
    sets["one_per_cell"] = d
    d = _design(3, 808, effects=additive_effects)
    d["quantity"] = 100.0
    sets["constant_response"] = d
    d = _design(4, 909, effects=interaction_effects)
    d["colony_id"] = [f"C{(i % 12) + 1:03d}" for i in range(len(d))]
    sets["repeated_colony"] = d
    return sets


# case_id, dataset, response, factors (;), covariates (;), interactions, ss_type, expected
CASES = [
    ("A1", "balanced_interaction", "quantity", "treatment;social;time", "", "full", 2, "estimable"),
    ("A2", "balanced_interaction", "quantity", "treatment;social;time", "", "full", 3, "estimable"),
    ("A3", "balanced_additive", "quantity", "treatment;social;time", "", "full", 2, "estimable"),
    ("A4", "balanced_additive", "quantity", "treatment;social;time", "", "main", 2, "estimable"),
    ("B1", "unbalanced", "quantity", "treatment;social;time", "", "full", 2, "estimable"),
    ("B2", "unbalanced", "quantity", "treatment;social;time", "", "full", 3, "estimable"),
    ("B3", "unbalanced", "quantity", "treatment;time", "", "full", 2, "estimable"),
    ("B4", "unbalanced", "quantity", "treatment;time", "", "full", 3, "estimable"),
    ("C1", "missing_values", "quantity", "treatment;social;time", "", "full", 2, "estimable"),
    ("C2", "missing_values", "quantity", "treatment;social;time", "", "full", 3, "estimable"),
    ("D1", "balanced_interaction", "quantity", "treatment;time", "body_size_mm", "full", 2, "estimable"),
    ("D2", "unbalanced", "quantity", "treatment;social", "body_size_mm", "full", 3, "estimable"),
    ("D3", "balanced_interaction", "quantity", "treatment", "", "full", 2, "estimable"),
    ("E1", "missing_cell", "quantity", "treatment;social;time", "", "full", 2, "not_estimable"),
    ("E2", "missing_cell", "quantity", "treatment;social;time", "", "main", 2, "estimable"),
    ("E3", "confounded", "quantity", "treatment;time", "", "main", 2, "not_estimable"),
    ("E4", "one_per_cell", "quantity", "treatment;social;time", "", "full", 2, "not_estimable"),
    ("E5", "constant_response", "quantity", "treatment;social", "", "full", 2, "not_estimable"),
    ("E6", "repeated_colony", "quantity", "treatment;time", "", "full", 2, "not_estimable_subject"),
]


def main() -> None:
    for name, df in build().items():
        df.to_csv(os.path.join(HERE, f"{name}.csv"), index=False, lineterminator="\n")
    pd.DataFrame(CASES, columns=["case_id", "dataset", "response", "factors", "covariates",
                                 "interactions", "ss_type", "expected"]).to_csv(
        os.path.join(HERE, "cases.csv"), index=False, lineterminator="\n")


if __name__ == "__main__":
    main()
