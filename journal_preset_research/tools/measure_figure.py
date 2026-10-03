"""Automated image-level measurements for one published figure (research tool, not shipped).

Usage: python measure_figure.py IMAGE [--typeset-width-mm W] [--out-json PATH] [--panels-dir DIR]

Produces the automated part of ``style_measurements.csv`` (see measurement_protocol.md):
image size, aspect, whitespace-based panel segmentation, per-panel colour statistics, dark-line
(axis/stroke) relative width, and glyph-height statistics for small text. Categorical style
readings (spines, legend placement, error-bar style...) are recorded by a reviewer viewing the
image and are not attempted here.

Everything that depends on the physical figure width is reported twice: as a relative quantity
(OBSERVED) and, when ``--typeset-width-mm`` is given, as an absolute quantity (INFERRED). Without a
typeset width no point size is produced.
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List, Tuple

import numpy as np
from PIL import Image
from skimage import measure as skmeasure

CAP_HEIGHT_EM = 0.716  # Arial/Helvetica digits and capitals


def load_gray_rgb(path: str) -> Tuple[np.ndarray, np.ndarray]:
    im = Image.open(path).convert("RGB")
    rgb = np.asarray(im).astype(np.float32)
    gray = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2])
    return gray, rgb


def segment_panels(gray: np.ndarray, *, white: float = 245.0, min_frac: float = 0.12) -> List[Tuple[int, int, int, int]]:
    """Split a figure into panels by full-width/full-height white gutters (recursive, 2 levels).

    Returns boxes (x0, y0, x1, y1). A panel narrower or shorter than ``min_frac`` of the figure is
    merged into its neighbour, so tiny legends and colourbars do not become panels.
    """
    h, w = gray.shape

    def split(box, axis, depth):
        x0, y0, x1, y1 = box
        sub = gray[y0:y1, x0:x1]
        if axis == 0:
            prof = (sub < white).mean(axis=1)
            length = y1 - y0
        else:
            prof = (sub < white).mean(axis=0)
            length = x1 - x0
        blank = prof < 0.002
        # find runs of blank at least 1.5% of length
        min_run = max(4, int(0.015 * length))
        cuts = []
        i = 0
        while i < length:
            if blank[i]:
                j = i
                while j < length and blank[j]:
                    j += 1
                if j - i >= min_run and i > 0 and j < length:
                    cuts.append((i + j) // 2)
                i = j
            else:
                i += 1
        if not cuts:
            return [box]
        pieces = []
        prev = 0
        for c in cuts + [length]:
            if c - prev >= min_frac * (h if axis == 0 else w):
                pieces.append((prev, c))
            elif pieces:
                pieces[-1] = (pieces[-1][0], c)
            prev = c
        if len(pieces) <= 1:
            return [box]
        out = []
        for a, b in pieces:
            nb = (x0, y0 + a, x1, y0 + b) if axis == 0 else (x0 + a, y0, x0 + b, y1)
            out.append(nb)
        return out

    boxes = [(0, 0, w, h)]
    for depth, axis in enumerate((0, 1, 0, 1)):
        nxt = []
        for b in boxes:
            nxt.extend(split(b, axis, depth))
        boxes = nxt
    # trim white margins of each box
    trimmed = []
    for x0, y0, x1, y1 in boxes:
        sub = gray[y0:y1, x0:x1] < white
        if not sub.any():
            continue
        ys, xs = np.where(sub)
        trimmed.append((x0 + xs.min(), y0 + ys.min(), x0 + xs.max() + 1, y0 + ys.max() + 1))
    return trimmed


def colour_stats(rgb: np.ndarray) -> Dict[str, Any]:
    """Coloured-pixel fraction, number of distinct hues, mean saturation of coloured pixels."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = rgb.max(axis=-1)
    mn = rgb.min(axis=-1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
    coloured = (sat > 0.25) & (mx > 60)
    frac = float(coloured.mean())
    if coloured.sum() < 50:
        return {"coloured_fraction": round(frac, 4), "n_hue_clusters": 0, "mean_saturation": 0.0,
                "hue_hist": []}
    # hue in degrees
    cr, cg, cb = r[coloured], g[coloured], b[coloured]
    cmx = np.maximum(np.maximum(cr, cg), cb)
    cmn = np.minimum(np.minimum(cr, cg), cb)
    d = np.maximum(cmx - cmn, 1e-6)
    hue = np.where(cmx == cr, ((cg - cb) / d) % 6, np.where(cmx == cg, (cb - cr) / d + 2, (cr - cg) / d + 4)) * 60.0
    hist, _ = np.histogram(hue, bins=24, range=(0, 360))
    hist = hist / hist.sum()
    # a hue cluster is a bin (or run of bins) holding >= 4% of coloured pixels
    strong = hist >= 0.04
    n = 0
    prev = strong[-1]
    for s in strong:
        if s and not prev:
            n += 1
        prev = s
    if strong.all():
        n = 1
    return {"coloured_fraction": round(frac, 4), "n_hue_clusters": int(n),
            "mean_saturation": round(float(sat[coloured].mean()), 3),
            "hue_hist": [round(float(x), 3) for x in hist]}


def stroke_and_glyph_stats(gray: np.ndarray) -> Dict[str, Any]:
    """Dark-stroke width and small-glyph height from connected components of dark pixels."""
    h, w = gray.shape
    dark = gray < 110
    if dark.sum() < 20:
        return {"dark_fraction": 0.0, "stroke_px_median": None, "glyph_height_px_median": None,
                "n_glyph_like": 0}
    lab = skmeasure.label(dark, connectivity=2)
    props = skmeasure.regionprops(lab)
    glyph_h = []
    stroke = []
    for p in props:
        y0, x0, y1, x1 = p.bbox
        bh, bw = y1 - y0, x1 - x0
        # glyph-like: small compact components (letters/digits) - between 0.4% and 4% of width
        if 0.004 * w <= bh <= 0.04 * w and bw <= 0.06 * w and p.area >= 4 and 0.15 < p.extent:
            glyph_h.append(bh)
        # stroke-like: long thin components (axis lines, borders)
        if max(bh, bw) >= 0.15 * max(h, w) and min(bh, bw) <= 0.02 * w:
            stroke.append(min(bh, bw))
    out = {"dark_fraction": round(float(dark.mean()), 4),
           "stroke_px_median": (float(np.median(stroke)) if stroke else None),
           "glyph_height_px_median": (float(np.median(glyph_h)) if len(glyph_h) >= 8 else None),
           "glyph_height_px_q1": (float(np.percentile(glyph_h, 25)) if len(glyph_h) >= 8 else None),
           "glyph_height_px_q3": (float(np.percentile(glyph_h, 75)) if len(glyph_h) >= 8 else None),
           "n_glyph_like": int(len(glyph_h))}
    return out


def text_line_heights(gray: np.ndarray) -> Dict[str, Any]:
    """Cap-height of the dominant text size, from components that form horizontal text lines.

    Glyph components are grouped into lines when their baselines agree within a tolerance and they
    are horizontally adjacent (gap < 1.5 x height). A line needs >= 2 components. The height of a
    line is that of its tallest component (a digit or capital); the median over lines is the cap
    height of the dominant text size. Tick labels dominate most data figures, so this is the
    tick-label cap height. Also reports the distribution so a reviewer can spot a second size
    (axis labels, panel letters).
    """
    h, w = gray.shape
    dark = gray < 110
    if dark.sum() < 20:
        return {"line_cap_height_px_median": None, "n_text_lines": 0}
    lab = skmeasure.label(dark, connectivity=2)
    comps = []
    for p in skmeasure.regionprops(lab):
        y0, x0, y1, x1 = p.bbox
        bh, bw = y1 - y0, x1 - x0
        if 0.003 * w <= bh <= 0.05 * w and bw <= 0.08 * w and p.area >= 4 and p.extent > 0.12:
            comps.append((x0, y0, x1, y1, bh))
    comps.sort(key=lambda c: (c[3], c[0]))   # by baseline then x
    lines: List[List[Tuple[int, int, int, int, int]]] = []
    for c in comps:
        placed = False
        for ln in lines:
            last = ln[-1]
            tol = max(2, 0.25 * max(last[4], c[4]))
            if abs(last[3] - c[3]) <= tol and 0 <= c[0] - last[2] <= 1.5 * max(last[4], c[4]) and c[0] >= last[0]:
                ln.append(c)
                placed = True
                break
        if not placed:
            lines.append([c])
    heights = [max(cc[4] for cc in ln) for ln in lines if len(ln) >= 2]
    if len(heights) < 3:
        return {"line_cap_height_px_median": None, "n_text_lines": len(heights)}
    hist = np.bincount(np.asarray(heights))
    # size clusters: smooth the height histogram (+-8%) and keep peaks holding >= 10% of lines
    hs = np.asarray(heights, dtype=float)
    clusters = []
    remaining = hs.copy()
    while len(remaining) >= max(3, 0.10 * len(hs)):
        centre = float(np.median(remaining)) if not clusters else float(np.argmax(np.bincount(remaining.astype(int))))
        member = remaining[np.abs(remaining - centre) <= max(1.0, 0.12 * centre)]
        if len(member) < max(3, 0.10 * len(hs)):
            break
        clusters.append({"cap_height_px": round(float(np.median(member)), 1), "n_lines": int(len(member))})
        remaining = remaining[np.abs(remaining - centre) > max(1.0, 0.12 * centre)]
        if len(clusters) >= 4:
            break
    clusters.sort(key=lambda c: c["cap_height_px"])
    return {"line_cap_height_px_median": float(np.median(heights)),
            "line_cap_height_px_mode": int(np.argmax(hist)),
            "line_cap_height_px_q1": float(np.percentile(heights, 25)),
            "line_cap_height_px_q3": float(np.percentile(heights, 75)),
            "text_size_clusters_px": clusters,
            "n_text_lines": int(len(heights))}


def pt_from_px(height_px: float, image_width_px: int, typeset_width_mm: float) -> float:
    em_px = height_px / CAP_HEIGHT_EM
    mm_per_px = typeset_width_mm / image_width_px
    return em_px * mm_per_px / 25.4 * 72.0


def measure(path: str, typeset_width_mm: float | None = None, panels_dir: str | None = None) -> Dict[str, Any]:
    gray, rgb = load_gray_rgb(path)
    h, w = gray.shape
    rec: Dict[str, Any] = {
        "image_path": path, "image_width_px": int(w), "image_height_px": int(h),
        "figure_aspect": round(w / h, 3),
        "typeset_width_mm": typeset_width_mm,
        "figure": {**colour_stats(rgb), **stroke_and_glyph_stats(gray)},
        "panels": [],
    }
    rec["figure"].update(text_line_heights(gray))
    fig_glyph = rec["figure"].get("line_cap_height_px_median") or rec["figure"].get("glyph_height_px_median")
    if fig_glyph and typeset_width_mm:
        rec["figure"]["small_text_pt_inferred"] = round(pt_from_px(fig_glyph, w, typeset_width_mm), 2)
        mode = rec["figure"].get("line_cap_height_px_mode")
        if mode:
            rec["figure"]["dominant_text_pt_inferred"] = round(pt_from_px(mode, w, typeset_width_mm), 2)
        rec["figure"]["text_size_clusters_pt"] = [
            {"pt": round(pt_from_px(c["cap_height_px"], w, typeset_width_mm), 2), "n_lines": c["n_lines"]}
            for c in rec["figure"].get("text_size_clusters_px", [])]
        rec["figure"]["stroke_pt_inferred"] = (
            round(rec["figure"]["stroke_px_median"] * typeset_width_mm / w / 25.4 * 72.0, 2)
            if rec["figure"]["stroke_px_median"] else None)
    if fig_glyph:
        rec["figure"]["small_text_rel_height"] = round(fig_glyph / w, 5)
    boxes = segment_panels(gray)
    rec["n_panels_detected"] = len(boxes)
    if panels_dir:
        os.makedirs(panels_dir, exist_ok=True)
    for i, (x0, y0, x1, y1) in enumerate(boxes):
        sub_g, sub_rgb = gray[y0:y1, x0:x1], rgb[y0:y1, x0:x1]
        prec = {"index": i, "box": [int(x0), int(y0), int(x1), int(y1)],
                "aspect": round((x1 - x0) / max(1, y1 - y0), 3),
                **colour_stats(sub_rgb), **stroke_and_glyph_stats(sub_g), **text_line_heights(sub_g)}
        if typeset_width_mm and prec.get("line_cap_height_px_median"):
            prec["text_pt_inferred"] = round(pt_from_px(prec["line_cap_height_px_median"], w, typeset_width_mm), 2)
        prec.pop("hue_hist", None)
        if panels_dir:
            out = os.path.join(panels_dir, f"panel_{i:02d}.png")
            Image.fromarray(sub_rgb.astype(np.uint8)).save(out)
            prec["crop_path"] = out
        rec["panels"].append(prec)
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--typeset-width-mm", type=float, default=None)
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--panels-dir", default=None)
    a = ap.parse_args()
    rec = measure(a.image, a.typeset_width_mm, a.panels_dir)
    text = json.dumps(rec, indent=1)
    if a.out_json:
        with open(a.out_json, "w", encoding="utf-8") as fh:
            fh.write(text)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
