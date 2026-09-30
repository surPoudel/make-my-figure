"""Design goal 7: rendering must never alter the data the user supplied.

The renderer contract says a renderer copies before it modifies. This checks the contract from
the outside, the way a user would experience it: hand the public render() entrypoint a DataFrame,
then verify the caller's own object is byte-for-byte what it was.

Fixtures come from examples/by_plot_type/, which carries a data.csv plus the plotspec.json that
plots it for every registered plot type, so coverage is the whole registry rather than the subset
with golden test inputs.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from make_my_figure_core.plots.registry import _RENDERERS, render  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EX = os.path.join(ROOT, "examples", "by_plot_type")
OUT = os.path.join(ROOT, "manuscriptv3", "benchmarks", "input_immutability.csv")


def fingerprint(df):
    """A representation sensitive to values, dtypes, column order and index order alike."""
    return {
        "shape": df.shape,
        "columns": list(df.columns),
        "dtypes": [str(d) for d in df.dtypes],
        "index": df.index.tolist(),
        # to_json is NaN-stable, unlike equality comparison
        "values": df.to_json(orient="split", date_format="iso", double_precision=15),
    }


def main():
    rows, tested, unchanged = [], 0, 0
    for d in sorted(os.listdir(EX)):
        data_path = os.path.join(EX, d, "data.csv")
        spec_path = os.path.join(EX, d, "plotspec.json")
        if not (os.path.exists(data_path) and os.path.exists(spec_path)):
            rows.append({"example": d, "plot_type": "", "rendered": "skipped",
                         "input_unchanged": "not tested", "detail": "example incomplete"})
            continue
        spec = json.load(open(spec_path, encoding="utf-8"))
        ptype = spec.get("plot_type", "")
        if ptype not in _RENDERERS:
            rows.append({"example": d, "plot_type": ptype, "rendered": "skipped",
                         "input_unchanged": "not tested", "detail": "plot type not registered"})
            continue
        df = pd.read_csv(data_path)
        before = fingerprint(df)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                res = render(spec, df)
            plt.close(res.figure)
            rendered, detail = "yes", ""
        except Exception as exc:  # noqa: BLE001 - a render failure is still a valid observation
            rendered, detail = "no", f"{type(exc).__name__}: {exc}"[:160]
        after = fingerprint(df)
        same = after == before
        if rendered == "yes":
            tested += 1
            unchanged += int(same)
        if not same and not detail:
            diff = [k for k in before if before[k] != after[k]]
            detail = "changed: " + ",".join(diff)
        rows.append({"example": d, "plot_type": ptype, "rendered": rendered,
                     "input_unchanged": "yes" if same else "NO", "detail": detail})

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["example", "plot_type", "rendered",
                                           "input_unchanged", "detail"])
        w.writeheader()
        w.writerows(rows)

    print(f"examples: {len(rows)}   rendered: {tested}   input unchanged: {unchanged}/{tested}")
    failed = [r for r in rows if r["input_unchanged"] == "NO"]
    for r in failed:
        print("  MUTATED:", r["plot_type"], r["detail"])
    notrendered = [r for r in rows if r["rendered"] == "no"]
    for r in notrendered:
        print("  render failed:", r["plot_type"], r["detail"])
    print("->", OUT)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
