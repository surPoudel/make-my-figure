"""Render the figures of a typeset open-access article PDF at a known physical scale (research tool).

Usage: python typeset_figures_from_pdf.py ARTICLE.pdf OUT_DIR [--dpi 600]

For each page that carries a figure caption ("Fig. N |" / "Figure N." / "Fig. N."), the figure
region is the part of the page above the caption that contains vector drawings or images. That
region is rendered to PNG at ``--dpi`` and a sidecar JSON records:

* ``typeset_width_mm`` / ``typeset_height_mm`` - the region's size on the page (OBSERVED);
* ``px_per_mm`` - so glyph heights in the PNG convert to points without assumptions (INFERRED);
* ``line_widths_pt`` - histogram of stroke widths of the vector drawings in the region (OBSERVED);
* ``text_spans`` - any real text spans in the region with font name, size and bold flag
  (OBSERVED; many production PDFs outline figure text, in which case this list is empty and the
  glyph-height route is used);
* ``page_width_mm`` and the caption's first line.

Nothing here is redistributed: the PNGs are private research references under
PRIVATE_REFERENCE_ONLY/. Only aggregate numbers derived from them leave that folder.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import re
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF

PT_PER_MM = 72.0 / 25.4
CAPTION_RE = re.compile(r"^\s*(Fig(?:ure)?\.?\s*(\d+)\s*(?:\||\.|:))", re.I)


def _caption_blocks(page) -> List[Dict[str, Any]]:
    td = page.get_text("dict")
    out = []
    for b in td["blocks"]:
        if b["type"] != 0 or not b["lines"]:
            continue
        first = "".join(s["text"] for s in b["lines"][0]["spans"])
        m = CAPTION_RE.match(first)
        if m:
            out.append({"bbox": b["bbox"], "first_line": first.strip()[:120],
                        "figure_number": int(m.group(2))})
    return out


def _region_above(page, y_cap: float, y_min: float = 0.0) -> Optional[fitz.Rect]:
    """Union of drawings and images that lie between y_min and the caption."""
    rect = None
    for d in page.get_drawings():
        r = d["rect"]
        # running-head rules and column separators: page-wide hairlines are not figure content
        if r.height < 1.5 and r.width > 0.8 * page.rect.width:
            continue
        if r.y1 <= y_cap + 1 and r.y0 >= y_min - 1 and r.width > 2 and r.height >= 0:
            rect = r if rect is None else rect | r
    for i in page.get_image_info():
        r = fitz.Rect(i["bbox"])
        if r.y1 <= y_cap + 1 and r.y0 >= y_min - 1 and r.width > 20:
            rect = r if rect is None else rect | r
    if rect is None:
        return None
    # include outlined text (drawn as paths) that sits just outside: pad by 2 mm
    pad = 2 * PT_PER_MM
    rect = fitz.Rect(rect.x0 - pad, rect.y0 - pad, rect.x1 + pad, min(rect.y1 + pad, y_cap))
    return rect & page.rect


def _spans_in(page, rect: fitz.Rect) -> List[Dict[str, Any]]:
    out = []
    for b in page.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        for l in b["lines"]:
            for s in l["spans"]:
                sb = fitz.Rect(s["bbox"])
                if not s["text"].strip() or not rect.contains(sb):
                    continue
                out.append({"text": s["text"][:40], "font": s["font"], "size_pt": round(s["size"], 2),
                            "bold": bool(s["flags"] & 16), "italic": bool(s["flags"] & 2)})
    return out


def _line_widths(page, rect: fitz.Rect) -> Dict[str, int]:
    c: collections.Counter = collections.Counter()
    for d in page.get_drawings():
        if d.get("width") is None or not rect.intersects(d["rect"]):
            continue
        if d["width"] <= 0:
            continue
        c[f"{round(d['width'], 2):.2f}"] += 1
    return dict(sorted(c.items(), key=lambda kv: -kv[1])[:12])


def _content_union(page) -> Optional[fitz.Rect]:
    """Union of all drawings/images on the page, excluding page-wide rules."""
    rect = None
    for d in page.get_drawings():
        r = d["rect"]
        if r.height < 1.5 and r.width > 0.8 * page.rect.width:
            continue
        if r.width > 2 or r.height > 2:
            rect = r if rect is None else rect | r
    for i in page.get_image_info():
        r = fitz.Rect(i["bbox"])
        if r.width > 20:
            rect = r if rect is None else rect | r
    return rect


def _is_figure_page(page, union: Optional[fitz.Rect]) -> bool:
    if union is None:
        return False
    area = union.width * union.height
    return area > 0.30 * page.rect.width * page.rect.height


def render_figures(pdf_path: str, out_dir: str, *, dpi: int = 600) -> List[Dict[str, Any]]:
    doc = fitz.open(pdf_path)
    os.makedirs(out_dir, exist_ok=True)
    records: List[Dict[str, Any]] = []
    seen = set()
    zoom = dpi / 72.0

    def emit(page, pno, fig_no, region, caption_first_line, route):
        if region is None or region.width < 20 * PT_PER_MM or region.height < 10 * PT_PER_MM:
            return
        seen.add(fig_no)
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=region, alpha=False)
        png = os.path.join(out_dir, f"fig{fig_no:02d}_typeset_{dpi}dpi.png")
        pix.save(png)
        rec = {
            "figure_number": fig_no, "page": pno + 1, "png": png, "dpi": dpi,
            "typeset_width_mm": round(region.width / PT_PER_MM, 2),
            "typeset_height_mm": round(region.height / PT_PER_MM, 2),
            "px_per_mm": round(pix.width / (region.width / PT_PER_MM), 3),
            "image_width_px": pix.width, "image_height_px": pix.height,
            "page_width_mm": round(page.rect.width / PT_PER_MM, 1),
            "caption_first_line": caption_first_line, "region_route": route,
            "line_widths_pt": _line_widths(page, region),
            "text_spans": _spans_in(page, region)[:200],
            "evidence": {"typeset_width_mm": "OBSERVED", "line_widths_pt": "OBSERVED",
                         "text_spans": "OBSERVED", "glyph_pt_from_png": "INFERRED"},
        }
        records.append(rec)
        with open(png[:-4] + ".json", "w", encoding="utf-8") as fh:
            json.dump(rec, fh, indent=1)

    # pass 1: caption and figure on the same page
    pending_captions: List[Dict[str, Any]] = []   # captions with no figure content above them
    figure_pages: List[int] = []                   # pages that are mostly drawing but had no caption
    for pno in range(doc.page_count):
        page = doc[pno]
        caps = sorted(_caption_blocks(page), key=lambda c: c["bbox"][1])
        union = _content_union(page)
        if not caps:
            if _is_figure_page(page, union):
                figure_pages.append(pno)
            continue
        y_prev = 0.0
        for cap in caps:
            fig_no = cap["figure_number"]
            if fig_no in seen:
                y_prev = cap["bbox"][3]
                continue
            region = _region_above(page, cap["bbox"][1], y_min=y_prev)
            y_prev = cap["bbox"][3]
            if region is not None and region.width >= 20 * PT_PER_MM and region.height >= 10 * PT_PER_MM:
                emit(page, pno, fig_no, region, cap["first_line"], "same_page")
            else:
                pending_captions.append({"page": pno, "figure_number": fig_no, "first_line": cap["first_line"]})
    # pass 2: a caption whose figure sits on a neighbouring full-page figure page
    used_pages = set()
    for cap in pending_captions:
        if cap["figure_number"] in seen:
            continue
        for cand in (cap["page"] + 1, cap["page"] - 1, cap["page"] + 2):
            if cand in figure_pages and cand not in used_pages and 0 <= cand < doc.page_count:
                page = doc[cand]
                union = _content_union(page)
                pad = 2 * PT_PER_MM
                region = fitz.Rect(union.x0 - pad, union.y0 - pad, union.x1 + pad, union.y1 + pad) & page.rect
                emit(page, cand, cap["figure_number"], region, cap["first_line"], "caption_on_neighbouring_page")
                used_pages.add(cand)
                break
    records.sort(key=lambda r: r["figure_number"])
    with open(os.path.join(out_dir, "typeset_index.json"), "w", encoding="utf-8") as fh:
        json.dump({"pdf": pdf_path, "figures": records}, fh, indent=1)
    return records


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("out_dir")
    ap.add_argument("--dpi", type=int, default=600)
    a = ap.parse_args()
    recs = render_figures(a.pdf, a.out_dir, dpi=a.dpi)
    for r in recs:
        print(f"Fig {r['figure_number']}: page {r['page']}, {r['typeset_width_mm']} x "
              f"{r['typeset_height_mm']} mm, {r['image_width_px']}x{r['image_height_px']} px, "
              f"spans {len(r['text_spans'])}, widths {list(r['line_widths_pt'].items())[:4]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
