"""Effective font sizes of the plots placed in the deck (presentation/audit/plot_font_qc.csv).

For every *_pres render placed by build_slides.py: effective_pt = render_pt x placed_width_in / figure_width_in,
where figure_width_in = pixel_width / dpi of the PNG and render_pt are the PRESENTATION_STYLE values of
tutorial/showcase/build_showcase.py. UI crops are reported as effective pixel scale (UI text is ~12 px).
"""
import csv, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tutorial", "showcase"))
import build_showcase as b
pl = json.load(open(os.path.join(ROOT, "presentation", "audit", "placements.json"), encoding="utf-8"))
rows = []
for p in pl:
    if p["kind"] == "plot" and "_pres" in p["file"]:
        dpi = p["dpi"] or 220
        fig_w_in = p["pixel_width"] / dpi
        scale = p["placed_width_in"] / fig_w_in
        st = b.PRESENTATION_STYLE
        rows.append({"file": p["file"], "placed_width_in": p["placed_width_in"], "scale": round(scale, 2),
                     "tick_pt": round(st["tick_label_pt"] * scale, 1), "axis_label_pt": round(st["axis_font_pt"] * scale, 1),
                     "legend_pt": round(st["legend_pt"] * scale, 1), "annotation_pt": round(b.PRES_STATS_FONT * scale, 1),
                     "verdict": "OK" if st["tick_label_pt"] * scale >= 9 else "SMALL"})
    elif p["kind"] == "ui":
        px_per_in = p["pixel_width"] / p["placed_width_in"]
        eff_pt = 12 / px_per_in * 72
        rows.append({"file": p["file"], "placed_width_in": p["placed_width_in"], "scale": round(72 / px_per_in, 2),
                     "tick_pt": "", "axis_label_pt": "", "legend_pt": "", "annotation_pt": round(eff_pt, 1),
                     "verdict": "OK" if eff_pt >= 9 else ("BORDERLINE" if eff_pt >= 7 else "SMALL")})
out = os.path.join(ROOT, "presentation", "audit", "plot_font_qc.csv")
with open(out, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
small = [r for r in rows if r["verdict"] != "OK"]
print(f"{len(rows)} placements checked; {len(small)} not OK:")
for r in small: print("  ", r["verdict"], r["file"], r["placed_width_in"], "in ->", r["annotation_pt"] or r["tick_pt"], "pt")
