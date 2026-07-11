"""Import external figure/image files as Figure Builder panels (v0.5).

Scientists often already have figures from R, GraphPad Prism, Illustrator,
BioRender, microscopy, flow, etc. This module lets those files be imported as
panels in the multi-panel Figure Builder alongside Make My Figure plots.

Design / honesty notes:
- Raster (PNG/JPG/JPEG/TIFF/TIF/WEBP/BMP) load via Pillow — always available.
- PDF rasterizes the selected page via PyMuPDF (``fitz``) **if installed**; else a
  friendly message. PDF/SVG are **not** kept as vector — the multi-panel composite
  embeds every panel (including Make My Figure's own) as raster, so imported vector
  files are rasterized at high DPI and this is recorded in the FigureSpec.
- SVG rasterizes via ``cairosvg`` or ``svglib`` **if installed**; else a friendly
  message telling the user to export PNG/PDF or install a converter.
- Nothing here raises on an unsupported/oversized file: it returns a clear error
  string in the metadata and the caller surfaces it (never crash).

Imported files are COPIED into a managed assets folder so the panel survives the
user moving/deleting the original; the FigureSpec stores the relative asset path
+ metadata (dims, DPI, checksum, page, rasterization DPI, warnings).
"""

from __future__ import annotations

import hashlib
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

RASTER_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp"}
VECTOR_EXTS = {".svg", ".pdf", ".eps"}
SUPPORTED_EXTS = RASTER_EXTS | VECTOR_EXTS
ASSETS_DIRNAME = "figure_builder_assets"
DEFAULT_RASTER_DPI = 300


class ImportError_(Exception):
    """Raised for a hard import failure (unsupported format, unreadable file)."""


@dataclass
class ImportedAsset:
    """The result of importing an external figure file."""

    image: Any = None                 # RGBA float array in [0,1], HxWx4, or None on error
    metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None       # set when the file could not be imported


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _to_rgba_float(arr: np.ndarray) -> np.ndarray:
    """Coerce any HxW / HxWx3 / HxWx4 uint8/float array to RGBA float [0,1]."""
    a = np.asarray(arr)
    if a.dtype == np.uint8:
        a = a.astype(float) / 255.0
    elif a.max() > 1.0:
        a = a.astype(float) / 255.0
    else:
        a = a.astype(float)
    if a.ndim == 2:  # grayscale -> RGB
        a = np.stack([a, a, a], axis=-1)
    if a.shape[-1] == 3:  # add opaque alpha
        a = np.concatenate([a, np.ones((*a.shape[:2], 1))], axis=-1)
    return a


def _load_raster(path: str) -> Tuple[np.ndarray, Dict[str, Any]]:
    from PIL import Image

    with Image.open(path) as im:
        dpi = im.info.get("dpi", (None, None))
        im = im.convert("RGBA")
        arr = np.asarray(im).astype(float) / 255.0
        meta = {"orig_width_px": im.width, "orig_height_px": im.height,
                "dpi": float(dpi[0]) if dpi and dpi[0] else None}
    return arr, meta


def _load_pdf(path: str, page: int, dpi: int) -> Tuple[np.ndarray, Dict[str, Any], List[str]]:
    warnings: List[str] = []
    try:
        import fitz  # PyMuPDF
    except Exception:
        raise ImportError_(
            "PDF import needs PyMuPDF. Install it (`pip install pymupdf`) or export "
            "your figure as PNG/PDF-rasterized. Or import a PNG/TIFF instead.")
    doc = fitz.open(path)
    if page < 0 or page >= doc.page_count:
        warnings.append(f"Requested page {page} out of range (1..{doc.page_count}); used page 1.")
        page = 0
    pg = doc.load_page(page)
    zoom = dpi / 72.0
    pix = pg.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=True)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    arr = _to_rgba_float(arr)
    meta = {"orig_width_px": pix.width, "orig_height_px": pix.height, "dpi": float(dpi),
            "page": page, "n_pages": doc.page_count, "rasterization_dpi": dpi}
    warnings.append(f"PDF rasterized at {dpi} DPI (vector not preserved in the composite).")
    doc.close()
    return arr, meta, warnings


def _load_svg(path: str, dpi: int) -> Tuple[np.ndarray, Dict[str, Any], List[str]]:
    import io as _io

    warnings: List[str] = []
    png_bytes = None
    try:
        import cairosvg

        png_bytes = cairosvg.svg2png(url=path, dpi=dpi)
    except Exception:
        try:
            from svglib.svglib import svg2rlg
            from reportlab.graphics import renderPM

            drawing = svg2rlg(path)
            png_bytes = renderPM.drawToString(drawing, fmt="PNG", dpi=dpi)
        except Exception:
            raise ImportError_(
                "SVG import needs a converter (`pip install cairosvg`). Without one, "
                "export your figure to PNG or PDF and import that instead.")
    from PIL import Image

    im = Image.open(_io.BytesIO(png_bytes)).convert("RGBA")
    arr = np.asarray(im).astype(float) / 255.0
    warnings.append(f"SVG rasterized at {dpi} DPI (vector not preserved in the composite).")
    return arr, {"orig_width_px": im.width, "orig_height_px": im.height,
                 "dpi": float(dpi), "rasterization_dpi": dpi}, warnings


def import_asset(src_path: str, assets_dir: str, *, rasterize_dpi: int = DEFAULT_RASTER_DPI,
                 pdf_page: int = 0, import_time: Optional[str] = None) -> ImportedAsset:
    """Import ``src_path`` into ``assets_dir`` and return an :class:`ImportedAsset`.

    Never raises for a bad file — returns ``ImportedAsset(error=...)`` instead so
    the GUI can show a friendly message.
    """
    if not os.path.exists(src_path):
        return ImportedAsset(error=f"File not found: {src_path}")
    ext = os.path.splitext(src_path)[1].lower()
    if ext not in SUPPORTED_EXTS:
        return ImportedAsset(error=(
            f"Unsupported format '{ext}'. Supported: "
            f"{', '.join(sorted(e[1:] for e in SUPPORTED_EXTS))}."))

    os.makedirs(assets_dir, exist_ok=True)
    stored_name = os.path.basename(src_path)
    stored_path = os.path.join(assets_dir, stored_name)
    # Avoid clobbering a different file with the same name.
    if os.path.exists(stored_path) and os.path.abspath(stored_path) != os.path.abspath(src_path):
        base, e = os.path.splitext(stored_name)
        stored_name = f"{base}_{_sha256(src_path)[:8]}{e}"
        stored_path = os.path.join(assets_dir, stored_name)
    if os.path.abspath(stored_path) != os.path.abspath(src_path):
        shutil.copy2(src_path, stored_path)

    warnings: List[str] = []
    try:
        if ext in RASTER_EXTS:
            arr, meta = _load_raster(stored_path)
            meta["rasterization_dpi"] = None
        elif ext == ".pdf":
            arr, meta, w = _load_pdf(stored_path, pdf_page, rasterize_dpi)
            warnings += w
        elif ext == ".svg":
            arr, meta, w = _load_svg(stored_path, rasterize_dpi)
            warnings += w
        else:  # .eps
            return ImportedAsset(error=(
                "EPS import is not enabled (no reliable converter available). "
                "Export to PDF or PNG and import that instead."))
    except ImportError_ as exc:
        return ImportedAsset(error=str(exc), metadata={"stored_asset": stored_name})

    meta.update({
        "original_filename": os.path.basename(src_path),
        "stored_asset": stored_name,
        "file_type": ext[1:],
        "is_vector_source": ext in VECTOR_EXTS,
        "sha256": _sha256(stored_path),
        "import_time": import_time or datetime.now(timezone.utc).isoformat(),
    })
    return ImportedAsset(image=arr, metadata=meta, warnings=warnings)


# --- image processing -------------------------------------------------------

def _auto_trim(arr: np.ndarray, thresh: float = 0.99) -> np.ndarray:
    """Trim near-white / fully-transparent margins."""
    rgb, alpha = arr[..., :3], arr[..., 3]
    content = (alpha > 0.01) & (rgb.min(axis=-1) < thresh)
    rows = np.where(content.any(axis=1))[0]
    cols = np.where(content.any(axis=0))[0]
    if rows.size == 0 or cols.size == 0:
        return arr
    return arr[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1, :]


def process_image(arr: np.ndarray, *, crop: Optional[Dict[str, float]] = None,
                  rotate: int = 0, flip_h: bool = False, flip_v: bool = False,
                  auto_trim: bool = False, background: str = "white") -> np.ndarray:
    """Apply crop (fractional margins), rotate (0/90/180/270), flips, trim, and a
    background composite for transparency. Returns a new RGBA float array."""
    a = np.array(arr, dtype=float)
    if crop:
        h, w = a.shape[:2]
        t = int(round(h * max(0.0, min(0.9, crop.get("top", 0)))))
        b = int(round(h * max(0.0, min(0.9, crop.get("bottom", 0)))))
        left = int(round(w * max(0.0, min(0.9, crop.get("left", 0)))))
        right = int(round(w * max(0.0, min(0.9, crop.get("right", 0)))))
        a = a[t:h - b if b else h, left:w - right if right else w, :]
    if auto_trim:
        a = _auto_trim(a)
    rotate = int(rotate) % 360
    if rotate in (90, 180, 270):
        a = np.rot90(a, k=rotate // 90)
    if flip_h:
        a = a[:, ::-1, :]
    if flip_v:
        a = a[::-1, :, :]
    if background == "white" and a.shape[-1] == 4:
        rgb, alpha = a[..., :3], a[..., 3:4]
        a = np.concatenate([rgb * alpha + (1.0 - alpha), np.ones_like(alpha)], axis=-1)
    return a


def resolution_warnings(meta: Dict[str, Any], target_width_in: Optional[float]) -> List[str]:
    """Warn about likely-blurry raster imports at the chosen export width."""
    out: List[str] = []
    w_px = meta.get("orig_width_px")
    if not w_px:
        return out
    if meta.get("dpi") is None and not meta.get("is_vector_source"):
        out.append("Imported image has no embedded DPI; effective resolution depends on the "
                   "export size.")
    if target_width_in and target_width_in > 0:
        eff_dpi = w_px / float(target_width_in)
        if eff_dpi < 150:
            out.append(f"Imported image is {int(w_px)} px wide. At {target_width_in:g} in that is "
                       f"~{eff_dpi:.0f} DPI — likely blurry (aim for >=300 DPI).")
        elif eff_dpi < 300:
            out.append(f"Imported image is ~{eff_dpi:.0f} DPI at {target_width_in:g} in "
                       "(<300 DPI); consider a higher-resolution source for print.")
    return out
