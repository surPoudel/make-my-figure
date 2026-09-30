"""Render every bundled spatial example to reports/example_figures/.

Rendered images are deliberately not committed (see .gitignore): they are
reproducible from the bundled data and spec, so the repository keeps the inputs
and this script regenerates the pictures.

    python scripts/render_spatial_examples.py [--out DIR] [--formats png,pdf,svg]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from make_my_figure_core import examples  # noqa: E402
from make_my_figure_core.plots import registry  # noqa: E402

SPATIAL_PREFIXES = ("spatial_", "neighborhood_")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "reports", "example_figures"))
    ap.add_argument("--formats", default="png,pdf,svg")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    formats = [f.strip() for f in a.formats.split(",") if f.strip()]

    targets = [p for p in examples.plot_types_with_examples()
               if p.startswith(SPATIAL_PREFIXES)]
    if not targets:
        print("no spatial examples found", file=sys.stderr)
        return 1

    failures = 0
    for pt in sorted(targets):
        entry = examples.entry(pt)
        df = pd.read_csv(os.path.join(ROOT, entry["files"]["csv"]))
        with open(os.path.join(ROOT, entry["files"]["plotspec"]), encoding="utf-8") as fh:
            spec = json.load(fh)
        try:
            res = registry.render(spec, df)
        except Exception as exc:                      # noqa: BLE001 - report, don't mask
            failures += 1
            print(f"FAIL {pt}: {type(exc).__name__}: {exc}", file=sys.stderr)
            continue
        written = []
        for fmt in formats:
            path = os.path.join(a.out, f"{pt}.{fmt}")
            res.figure.savefig(path, dpi=300, bbox_inches="tight")
            written.append(os.path.basename(path))
        note = f" ({len(res.warnings)} warning(s))" if res.warnings else ""
        print(f"{pt}: {', '.join(written)}  rows={len(df)}{note}")
        for w in res.warnings:
            print(f"    - {w}")
    if failures:
        print(f"\n{failures} example(s) failed to render", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
