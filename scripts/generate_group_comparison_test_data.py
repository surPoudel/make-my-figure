"""Deterministic SYNTHETIC datasets for testing and previewing group-comparison plots.

Usage: python scripts/generate_group_comparison_test_data.py [--out examples/group_comparison_test_data]

Every table is generated from code with a fixed seed. Nothing here is measured from any experiment
or copied from any publication; the values are for exercising renderers, presets and previews at
different group counts and replicate numbers only. The manifest marks each file synthetic and
records the design so tests can assert on it (group names, n per group, expected effects).

Designs (long format: group[, subgroup], value; one row per observation):
  two_groups_n6            2 groups, n = 6 each
  three_groups_unequal     3 groups, n = 5 / 8 / 11
  four_groups_n4           4 groups, n = 4 each
  two_groups_n30           2 groups, n = 30 each
  two_by_three             2 x 3 design (group x subgroup), n = 6 per cell
  one_extreme_observation  2 groups, n = 8 each, one value 6 s.d. above its group
  overlapping_groups       3 groups whose distributions overlap heavily
  separated_groups         3 groups with strongly separated means
  unequal_5_vs_8, unequal_6_vs_17, unequal_4_9_13   the unequal designs from the brief
  n3, n4, n6, n10, n20, n50                        two-group designs at each n
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
SEED = 20260916
UNIT = "relative expression (a.u.)"


def _long(rng, groups, ns, means, sds, subgroups=None, sub_shift=0.0):
    rows = []
    for g, n, m, s in zip(groups, ns, means, sds):
        if subgroups:
            for j, sg in enumerate(subgroups):
                vals = rng.normal(m + j * sub_shift, s, size=n)
                rows += [{"group": g, "subgroup": sg, "value": round(float(v), 3)} for v in vals]
        else:
            vals = rng.normal(m, s, size=n)
            rows += [{"group": g, "value": round(float(v), 3)} for v in vals]
    return pd.DataFrame(rows)


def build(out_dir: str) -> dict:
    rng = np.random.default_rng(SEED)
    designs = {}
    designs["two_groups_n6"] = _long(rng, ["Control", "Treatment"], [6, 6], [1.0, 1.8], [0.25, 0.3])
    designs["three_groups_unequal"] = _long(rng, ["Control", "Low dose", "High dose"], [5, 8, 11],
                                            [1.0, 1.4, 2.1], [0.25, 0.3, 0.35])
    designs["four_groups_n4"] = _long(rng, ["WT", "KO-1", "KO-2", "Rescue"], [4, 4, 4, 4],
                                      [1.0, 0.45, 0.5, 0.95], [0.15, 0.12, 0.14, 0.18])
    designs["two_groups_n30"] = _long(rng, ["Vehicle", "Drug"], [30, 30], [1.0, 1.35], [0.3, 0.3])
    designs["two_by_three"] = _long(rng, ["Control", "Treatment"], [6, 6], [1.0, 1.7], [0.25, 0.3],
                                    subgroups=["Young", "Adult", "Old"], sub_shift=0.25)
    ext = _long(rng, ["Control", "Treatment"], [8, 8], [1.0, 1.6], [0.25, 0.25])
    ext.loc[ext.index[ext["group"] == "Treatment"][0], "value"] = round(1.6 + 6 * 0.25, 3)
    designs["one_extreme_observation"] = ext
    designs["overlapping_groups"] = _long(rng, ["A", "B", "C"], [10, 10, 10], [1.0, 1.05, 1.1], [0.4, 0.4, 0.4])
    designs["separated_groups"] = _long(rng, ["A", "B", "C"], [10, 10, 10], [1.0, 3.0, 5.0], [0.25, 0.25, 0.25])
    designs["unequal_5_vs_8"] = _long(rng, ["Control", "Treatment"], [5, 8], [1.0, 1.6], [0.25, 0.3])
    designs["unequal_6_vs_17"] = _long(rng, ["Control", "Treatment"], [6, 17], [1.0, 1.5], [0.25, 0.35])
    designs["unequal_4_9_13"] = _long(rng, ["Control", "Low", "High"], [4, 9, 13], [1.0, 1.3, 1.9], [0.2, 0.3, 0.35])
    for n in (3, 4, 6, 10, 20, 50):
        designs[f"n{n}"] = _long(rng, ["Control", "Treatment"], [n, n], [1.0, 1.6], [0.25, 0.3])

    os.makedirs(out_dir, exist_ok=True)
    manifest = {"notice": "SYNTHETIC test/preview data generated from code with a fixed seed; not measured, "
                          "not from any publication; CC0-1.0", "seed": SEED, "value_unit": UNIT, "datasets": []}
    for name, df in designs.items():
        path = os.path.join(out_dir, f"{name}.csv")
        df.to_csv(path, index=False)
        counts = df.groupby([c for c in ("group", "subgroup") if c in df.columns]).size()
        manifest["datasets"].append({
            "name": name, "file": os.path.relpath(path, ROOT), "columns": list(df.columns),
            "n_total": int(len(df)),
            "n_per_group": {"|".join(map(str, k)) if isinstance(k, tuple) else str(k): int(v) for k, v in counts.items()},
            "groups": list(dict.fromkeys(df["group"])),
            "subgroups": list(dict.fromkeys(df["subgroup"])) if "subgroup" in df.columns else None,
            "synthetic": True,
        })
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
    with open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("# Synthetic group-comparison test data\n\n" + manifest["notice"] + "\n\n"
                 "Long format: `group` (and `subgroup` for the 2 x 3 design), `value` (" + UNIT + ").\n\n"
                 "| dataset | groups | n per group |\n|---|---|---|\n" +
                 "\n".join(f"| {d['name']} | {', '.join(d['groups'])} | {d['n_per_group']} |" for d in manifest["datasets"]) + "\n")
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "examples" / "group_comparison_test_data"))
    a = ap.parse_args()
    m = build(a.out)
    print(f"{len(m['datasets'])} synthetic datasets -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
