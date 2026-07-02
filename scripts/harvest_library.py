"""Run the license-aware figure-library harvest (Milestone 3).

HTTPS-only. Downloads figures/data only for CC BY / CC BY-SA / CC0 papers from
post-2020 Nature/Science/Cell-family OA journals.

Usage:
    python scripts/harvest_library.py --out figure_library --papers 10
"""

from __future__ import annotations

import argparse
import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from make_my_figure_core.harvest.pipeline import HarvestConfig, harvest_library


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(_REPO_ROOT, "figure_library"))
    ap.add_argument("--papers", type=int, default=10)
    ap.add_argument("--min-year", type=int, default=2021)
    ap.add_argument("--per-journal-cap", type=int, default=3)
    ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--no-figures", action="store_true")
    ap.add_argument("--no-supplementary", action="store_true")
    args = ap.parse_args()

    cfg = HarvestConfig(
        out_dir=args.out,
        target_papers=args.papers,
        min_year=args.min_year,
        per_journal_cap=args.per_journal_cap,
        request_delay=args.delay,
        download_figures=not args.no_figures,
        download_supplementary=not args.no_supplementary,
    )
    result = harvest_library(cfg)
    print(f"Accepted {len(result.accepted)}/{cfg.target_papers} papers; "
          f"rejected {len(result.rejected)}.")
    for a in result.accepted:
        print(f"  [{a['journal']}] {a['year']} {a['doi']} — "
              f"{a['n_figure_images']}/{a['n_figures']} figs, "
              f"{a['supplementary_files']} supp — {a['folder']}")
    print(f"Report: {os.path.join(cfg.out_dir, 'provenance_report.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
