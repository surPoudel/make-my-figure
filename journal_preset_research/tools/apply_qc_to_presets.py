"""Write the QC outcome into each experimental preset's provenance block (research tool).

Usage: python apply_qc_to_presets.py [--qc reports/journal_presets/qc/qc_matrix.csv]

For every preset: ``experimental.recommended_for`` = plot types whose QC cell is PASS,
``experimental.qc`` = counts and the list of non-PASS plot types with their issue, and a
``qc_date``. Nothing about the style values changes; a preset with fewer than 5 passing plot types
is reported (not deleted) so the author can decide.
"""

from __future__ import annotations

import argparse
import collections
import csv
import datetime as _dt
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from make_my_figure_core import experimental_presets as xp  # noqa: E402
from make_my_figure_core import presets  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--qc", default=str(ROOT / "reports" / "journal_presets" / "qc" / "qc_matrix.csv"))
    a = ap.parse_args()
    rows = list(csv.DictReader(open(a.qc, encoding="utf-8")))
    by_preset = collections.defaultdict(list)
    for r in rows:
        by_preset[r["preset_id"]].append(r)
    for e in xp.list_experimental_presets():
        cells = by_preset.get(e.preset_id, [])
        if not cells:
            continue
        p = xp.load_experimental_preset(e.path)
        passing = sorted(r["plot_type"] for r in cells if r["status"] == "PASS")
        not_pass = sorted(({"plot_type": r["plot_type"], "status": r["status"], "issues": r["issues"][:160]}
                           for r in cells if r["status"] != "PASS"), key=lambda d: (d["status"], d["plot_type"]))
        if not p.get("universal"):
            passing = [t for t in passing if t == p["plot_type"]] or passing
        p["experimental"]["recommended_for"] = passing
        p["experimental"]["qc"] = {
            "date": _dt.date.today().isoformat(),
            "cells": len(cells),
            "pass": sum(1 for r in cells if r["status"] == "PASS"),
            "warn": sum(1 for r in cells if r["status"] == "WARN"),
            "fail": sum(1 for r in cells if r["status"] == "FAIL"),
            "not_pass": not_pass,
            "rule": "PASS = no overlapping text, no clipped annotation, smallest text >= 5 pt at the target width; "
                    "WARN = legend over data or width off target by > 15 %; FAIL cells are reported, never fixed by shrinking text",
        }
        xp.validate_experimental_preset(p)
        with open(e.path, "w", encoding="utf-8") as fh:
            fh.write(presets.preset_to_json(p))
        flag = "  <-- fewer than 5 passing plot types" if len(passing) < 5 else ""
        print(f"{e.preset_id:28s} pass {len(passing):2d} / {len(cells)}{flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
