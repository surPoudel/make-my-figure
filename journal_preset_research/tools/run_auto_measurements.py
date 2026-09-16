"""Batch automated measurements over the corpus -> auto_measurements.csv (research tool).

Usage: python run_auto_measurements.py CORPUS_DIR OUT_CSV [--official-widths WIDTHS.json]

For every paper folder with metadata.json:
* if typeset/figNN_typeset_600dpi.json exists (Nature-family typeset PDF route) the PNG is measured
  with the OBSERVED typeset width -> point sizes are INFERRED;
* otherwise the web JPEG in figures/ is measured and the point size is ESTIMATED under the stated
  assumption: the figure is typeset at the publisher's official full width when its aspect ratio
  is > 1.25, at the official single-column width otherwise (widths from --official-widths, which
  is derived from official_guidelines_audit.csv and records its sources).

One row per figure. Panel-level rows are produced by the visual review, not here.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import measure_figure as mf  # noqa: E402

COLUMNS = [
    "paper_id", "journal", "journal_family", "year", "figure_number", "image_path", "route",
    "image_width_px", "image_height_px", "figure_aspect", "typeset_width_mm", "width_evidence",
    "width_assumption", "n_panels_detected", "n_text_lines", "text_size_clusters_pt",
    "smallest_cluster_pt", "dominant_cluster_pt", "largest_cluster_pt", "text_evidence",
    "stroke_pt_inferred", "line_widths_pt_observed", "coloured_fraction", "n_hue_clusters",
    "mean_saturation", "dark_fraction", "license_url",
]


def _official(widths: dict, family: str, aspect: float):
    fam = widths.get(family) or {}
    if not fam:
        return None, "UNKNOWN", "no official width recorded for this family"
    if aspect > 1.25 and fam.get("full_mm"):
        return fam["full_mm"], "ESTIMATED", f"assumed full width {fam['full_mm']} mm ({fam.get('source', '')}) because aspect > 1.25"
    if fam.get("single_mm"):
        return fam["single_mm"], "ESTIMATED", f"assumed single column {fam['single_mm']} mm ({fam.get('source', '')}) because aspect <= 1.25"
    return None, "UNKNOWN", "no usable official width"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus_dir")
    ap.add_argument("out_csv")
    ap.add_argument("--official-widths", default=None)
    ap.add_argument("--extra-dir", action="append", default=[],
                    help="additional paper folders in figure_library layout (group/paper/)")
    a = ap.parse_args()
    widths = json.load(open(a.official_widths, encoding="utf-8")) if a.official_widths else {}
    rows = []
    papers = sorted(glob.glob(os.path.join(a.corpus_dir, "*", "metadata.json")))
    for meta_path in papers:
        d = json.load(open(meta_path, encoding="utf-8"))
        pdir = os.path.dirname(meta_path)
        typeset = {json.load(open(j))["figure_number"]: json.load(open(j))
                   for j in glob.glob(os.path.join(pdir, "typeset", "fig*_typeset_*dpi.json"))}
        for fig in d.get("figures") or []:
            fno = fig.get("figure_number")
            img = fig.get("local_path") or fig.get("image_path") or ""
            if img and not os.path.isabs(img):
                img = os.path.join(pdir, img) if not img.startswith(a.corpus_dir) else img
            if not img or not os.path.exists(img):
                cands = glob.glob(os.path.join(pdir, "figures", f"Fig{fno}.*")) + \
                        glob.glob(os.path.join(pdir, "figures", f"fig{fno:02d}_*.jpg"))
                img = cands[0] if cands else ""
            row = {c: "" for c in COLUMNS}
            row.update({"paper_id": d["paper_id"], "journal": d.get("journal", ""),
                        "journal_family": d.get("journal_family", ""), "year": d.get("year", ""),
                        "figure_number": fno, "license_url": d.get("license_url", "")})
            try:
                if fno in typeset:
                    t = typeset[fno]
                    m = mf.measure(t["png"], typeset_width_mm=t["typeset_width_mm"])
                    row.update({"route": "typeset_pdf", "image_path": t["png"],
                                "typeset_width_mm": t["typeset_width_mm"], "width_evidence": "OBSERVED",
                                "width_assumption": "", "text_evidence": "INFERRED",
                                "line_widths_pt_observed": json.dumps(t.get("line_widths_pt", {}))})
                elif img and os.path.exists(img):
                    m0 = mf.measure(img)
                    w_mm, ev, assumption = _official(widths, d.get("journal_family", ""), m0["figure_aspect"])
                    m = mf.measure(img, typeset_width_mm=w_mm) if w_mm else m0
                    row.update({"route": "web_jpeg", "image_path": img, "typeset_width_mm": w_mm or "",
                                "width_evidence": ev, "width_assumption": assumption,
                                "text_evidence": ev if w_mm else "UNKNOWN", "line_widths_pt_observed": ""})
                else:
                    row["route"] = "missing_image"
                    rows.append(row)
                    continue
            except Exception as exc:  # noqa: BLE001
                row["route"] = f"error: {str(exc)[:80]}"
                rows.append(row)
                continue
            f = m["figure"]
            clusters = f.get("text_size_clusters_pt") or []
            row.update({
                "image_width_px": m["image_width_px"], "image_height_px": m["image_height_px"],
                "figure_aspect": m["figure_aspect"], "n_panels_detected": m["n_panels_detected"],
                "n_text_lines": f.get("n_text_lines", 0),
                "text_size_clusters_pt": json.dumps(clusters),
                "smallest_cluster_pt": clusters[0]["pt"] if clusters else "",
                "dominant_cluster_pt": (max(clusters, key=lambda c: c["n_lines"])["pt"] if clusters else ""),
                "largest_cluster_pt": clusters[-1]["pt"] if clusters else "",
                "stroke_pt_inferred": f.get("stroke_pt_inferred", ""),
                "coloured_fraction": f.get("coloured_fraction", ""), "n_hue_clusters": f.get("n_hue_clusters", ""),
                "mean_saturation": f.get("mean_saturation", ""), "dark_fraction": f.get("dark_fraction", ""),
            })
            rows.append(row)
        print(d["paper_id"], len(d.get("figures") or []), "figures", flush=True)
    with open(a.out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "rows ->", a.out_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
