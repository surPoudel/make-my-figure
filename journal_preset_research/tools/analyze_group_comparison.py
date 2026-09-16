"""Merge and summarise the group-comparison corpus subset (research tool).

Usage: python analyze_group_comparison.py "journal_preset_research/biological_group_comparison_corpus_*.csv"
                                          journal_preset_research/biological_group_comparison_corpus.csv
                                          journal_preset_research/analysis/group_comparison_summary.md

Answers, with counts and shares per journal family and overall:
* how often recent papers show individual observations over summary bars;
* bar+points vs box+points vs violin+points vs dot/strip+summary;
* how summary (mean/median) and error (SD/SEM/CI) are stated;
* marker size/edge/fill, jitter style, bar/box width, palette and control-colour behaviour;
* statistical annotation and P display style; axis style; legend; n labels; zero baseline;
* the same tables restricted to small-n panels (<= 10 per group) and large-n panels (>= 30).
Also writes a machine-readable JSON next to the markdown for the preset derivation step.
"""

from __future__ import annotations

import collections
import csv
import glob
import json
import re
import sys
from typing import Any, Dict, List

FIELDS = ["representation", "raw_points_visible", "summary", "summary_source", "error", "error_source",
          "marker_size_relative", "marker_edge", "marker_fill", "jitter_style", "bar_width", "box_width",
          "palette_type", "control_color_behavior", "statistical_annotation", "p_display", "axis_style",
          "legend_style", "n_label", "zero_baseline", "physical_panel_size"]


def norm_family(name: str) -> str:
    n = (name or "").strip().lower()
    for k, v in (("nature", "Nature"), ("science", "Science"), ("cell", "Cell")):
        if n.startswith(k):
            return v
    return name or "unknown"


def family_from_journal(journal: str) -> str:
    j = (journal or "").lower()
    if "nature" in j or "communications biology" in j or "scientific reports" in j:
        return "Nature"
    if "science" in j:
        return "Science"
    if "cell" in j or "iscience" in j or "molecular cell" in j or "cancer cell" in j:
        return "Cell"
    return "unknown"


def approx_n_class(text: str) -> str:
    """small (<=10 in every group), large (>=30 in some group), medium, or unknown."""
    if not text or "unknown" in text.lower():
        return "unknown"
    nums = [int(x) for x in re.findall(r"\d+", text)]
    if not nums:
        return "unknown"
    if max(nums) >= 30:
        return "large"
    if max(nums) <= 10:
        return "small"
    return "medium"


def share_table(rows: List[Dict[str, Any]], field: str, fams: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for f in ["all"] + fams:
        sub = rows if f == "all" else [r for r in rows if r["journal_family"] == f]
        cnt = collections.Counter((r.get(field) or "").strip() for r in sub if (r.get(field) or "").strip())
        n = sum(cnt.values())
        out[f] = {"n": n, "shares": {k: round(v / n, 3) for k, v in cnt.most_common()} if n else {}}
    return out


def md_table(title: str, tab: Dict[str, Any], fams: List[str], top: int = 6) -> List[str]:
    lines = [f"### {title}", "", "| family | n | values (share) |", "|---|---|---|"]
    for f in ["all"] + fams:
        t = tab[f]
        vals = ", ".join(f"{k} {v:.0%}" for k, v in list(t["shares"].items())[:top])
        lines.append(f"| {f} | {t['n']} | {vals} |")
    lines.append("")
    return lines


def main() -> int:
    pattern, out_csv, out_md = sys.argv[1], sys.argv[2], sys.argv[3]
    rows: List[Dict[str, Any]] = []
    for path in sorted(glob.glob(pattern)):
        for r in csv.DictReader(open(path, encoding="utf-8")):
            r["journal_family"] = family_from_journal(r.get("journal", "")) if not r.get("journal_family") \
                else norm_family(r["journal_family"])
            r["n_class"] = approx_n_class(r.get("approximate_n_per_group", ""))
            rows.append(r)
    if not rows:
        print("no rows", file=sys.stderr)
        return 1
    cols = list(rows[0].keys())
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    fams = sorted({r["journal_family"] for r in rows})
    papers = {f: len({r["paper_id"] for r in rows if r["journal_family"] == f}) for f in fams}

    summary: Dict[str, Any] = {"n_rows": len(rows), "papers_per_family": papers, "fields": {}}
    lines = ["# Group-comparison panels in the corpus: how published biology draws them", "",
             f"{len(rows)} panels from {sum(papers.values())} papers "
             f"({', '.join(f'{f}: {papers[f]} papers' for f in fams)}). One row per bar/box/violin/dot-strip panel; "
             "coded by visual review of web-resolution figures (see visual_review_protocol.md for the UNKNOWN rule). "
             "Shares are of coded (non-empty) values.", ""]

    # headline research question
    pts = share_table(rows, "raw_points_visible", fams)
    rep = share_table(rows, "representation", fams)
    lines += ["## Headline", ""]
    for f in ["all"] + fams:
        yes = pts[f]["shares"].get("yes", 0.0)
        lines.append(f"- **{f}**: individual observations visible in {yes:.0%} of {pts[f]['n']} group-comparison panels; "
                     f"bar+points {rep[f]['shares'].get('bar+points', 0):.0%}, bar without points {rep[f]['shares'].get('bar', 0):.0%}, "
                     f"box+points {rep[f]['shares'].get('box+points', 0):.0%}, violin+points {rep[f]['shares'].get('violin+points', 0):.0%}, "
                     f"dot/strip+summary {rep[f]['shares'].get('dot_strip+summary', 0):.0%}.")
    lines.append("")
    # bars only: how often do bars carry points
    bars = [r for r in rows if (r.get("representation") or "").startswith("bar")]
    bp = share_table(bars, "representation", fams)
    lines += ["## Among bar panels: points over the bar?", ""]
    for f in ["all"] + fams:
        lines.append(f"- {f}: {bp[f]['shares'].get('bar+points', 0):.0%} of {bp[f]['n']} bar panels show the observations.")
    lines.append("")
    summary["fields"]["raw_points_visible"] = pts
    summary["fields"]["representation"] = rep
    summary["fields"]["bars_with_points"] = bp

    lines += ["## Coded properties (all group-comparison panels)", ""]
    for field in FIELDS:
        if field in ("representation", "raw_points_visible"):
            continue
        tab = share_table(rows, field, fams)
        summary["fields"][field] = tab
        lines += md_table(field, tab, fams)

    for cls, title in (("small", "Small n (every group <= 10 observations)"), ("large", "Large n (a group >= 30)")):
        sub = [r for r in rows if r["n_class"] == cls]
        lines += [f"## {title}: {len(sub)} panels", ""]
        for field in ("representation", "marker_size_relative", "marker_fill", "jitter_style", "statistical_annotation", "n_label"):
            tab = share_table(sub, field, fams)
            summary["fields"][f"{cls}_n::{field}"] = tab
            lines += md_table(field, tab, fams, top=5)

    # what the captions say about summary/error
    stated = [r for r in rows if r.get("error_source") == "caption"]
    lines += ["## Error bars as stated in captions", ""]
    lines += md_table("error (caption-stated only)", share_table(stated, "error", fams), fams)
    stated_s = [r for r in rows if r.get("summary_source") == "caption"]
    lines += md_table("summary (caption-stated only)", share_table(stated_s, "summary", fams), fams)

    lines += ["## Reading the numbers", "",
              "- `unknown`/`UNKNOWN` cells are excluded from shares; low-resolution images limit marker and line judgements.",
              "- Sample sizes are the reviewers' counts of visible points (or the caption's n when stated), so `n_class` is approximate.",
              "- These are observed practices; the publishers' stated requirements are in official_guidelines_audit.csv.", ""]
    with open(out_md, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    with open(out_md[:-3] + ".json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1)
    print(f"{len(rows)} rows, {sum(papers.values())} papers -> {out_csv}, {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
