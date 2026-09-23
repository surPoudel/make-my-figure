"""Build tutorial/PLOT_GALLERY.md: one real render of every registered plot type.

Thumbnails are produced by the same core renderer the desktop application uses
(controller.render on the bundled example of each plot type), so the gallery always matches the
live registry. Tutorial and video links come from tutorial/plots/<plot_id>.md and
tutorial/videos/video_links.json.

    python tutorial/automation/build_gallery.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
TUT = os.path.join(ROOT, "tutorial")

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from apps.desktop_app.controller import DesktopController  # noqa: E402
from make_my_figure_core import examples, ui_hints, version  # noqa: E402
from make_my_figure_core.plots import registry  # noqa: E402
from make_my_figure_core.plots.registry import figure_to_bytes  # noqa: E402

from build_inventory import FAMILY  # noqa: E402

FAMILY_TITLES = {
    "02_Basic_Plots": "Basic plots and distributions",
    "03_Group_Comparisons": "Group comparisons",
    "04_Relationships_and_Regression": "Relationships, regression and classifier curves",
    "05_Matrix_and_Omics": "Matrices, dimension reduction and differential results",
    "07_Survival_and_Effect_Plots": "Survival, effect estimates and clinical timelines",
    "08_Advanced_Plots": "Specialised plots",
}


def main() -> int:
    ctrl = DesktopController()
    manifest = examples.load_manifest()
    by_pt = {e["plot_type"]: e for e in manifest.get("plot_types", [])}
    links = json.load(open(os.path.join(TUT, "videos", "video_links.json"), encoding="utf-8"))["videos"]
    thumbs = os.path.join(TUT, "screenshots", "gallery")
    os.makedirs(thumbs, exist_ok=True)
    rows = []
    for pt in registry.available_plot_types():
        display = registry.display_name(pt)
        thumb_rel = f"screenshots/gallery/{pt}.png"
        ok = False
        try:
            data = ctrl.load_example(pt)
            spec = registry.make_spec(pt, data.table_name, "publication", mapping=ctrl.default_mapping(pt))
            result = ctrl.render(spec, data)
            with open(os.path.join(TUT, thumb_rel), "wb") as fh:
                fh.write(figure_to_bytes(result.figure, "png", dpi=72))
            plt.close(result.figure)
            ok = True
        except Exception as exc:  # noqa: BLE001
            print(f"  {pt}: render failed: {type(exc).__name__}: {str(exc)[:160]}")
        ex = by_pt.get(pt, {})
        tut_path = os.path.join(TUT, "plots", f"{pt}.md")
        rows.append({
            "plot_id": pt, "display": display, "family": FAMILY.get(pt, "08_Advanced_Plots"),
            "purpose": (ex.get("use_case") or ex.get("description") or "").split(". ")[0].rstrip(".") ,
            "required": ", ".join(ui_hints.column_fields(pt)) or "chosen in Map columns",
            "thumb": thumb_rel if ok else "",
            "tutorial": f"plots/{pt}.md" if os.path.exists(tut_path) else "",
            "video": links.get(pt, ""),
        })
        print(f"  {pt:36s} {'thumb' if ok else 'NO THUMB':8s} {'tutorial' if rows[-1]['tutorial'] else '-'}")
    lines = [f"# Plot gallery - Make My Figure {version.__version__}", "",
             f"{len(rows)} registered plot types, rendered from the bundled synthetic examples with the same "
             "renderer the desktop application uses. Column roles are the rows of **2. Map columns** for that "
             "plot type. Tutorials appear as they are written; video links are filled from "
             "`videos/video_links.json`.", ""]
    for fam in sorted(FAMILY_TITLES):
        fam_rows = [r for r in rows if r["family"] == fam]
        if not fam_rows:
            continue
        lines += [f"## {FAMILY_TITLES[fam]}", "", "| | plot | purpose | column roles | tutorial | video |", "|---|---|---|---|---|---|"]
        for r in fam_rows:
            img = f'<img src="{r["thumb"]}" width="160">' if r["thumb"] else "(no example render)"
            tut = f"[tutorial]({r['tutorial']})" if r["tutorial"] else "not yet written"
            vid = "-" if not r["video"] else (f"[video]({r['video']})" if not r["video"].startswith("VIDEO_URL_") else f"`{r['video']}`")
            lines.append(f"| {img} | **{r['display']}**<br>`{r['plot_id']}` | {r['purpose']} | {r['required']} | {tut} | {vid} |")
        lines.append("")
    with open(os.path.join(TUT, "PLOT_GALLERY.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    with open(os.path.join(TUT, "audit", "gallery_index.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=2)
    print(f"gallery: {len(rows)} entries, {sum(1 for r in rows if r['thumb'])} thumbnails")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
