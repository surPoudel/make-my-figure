"""Render every slide of a .pptx to PNG (and optionally export a PDF) with PowerPoint on Windows.

    python tutorial\\slides\\render_pptx_windows.py deck.pptx out_dir [deck.pdf]

Requires PowerPoint and pywin32. PowerPoint is started without a window and closed afterwards.
"""
from __future__ import annotations

import os
import sys


def main() -> int:
    import win32com.client  # type: ignore

    src = os.path.abspath(sys.argv[1])
    out = os.path.abspath(sys.argv[2])
    pdf = os.path.abspath(sys.argv[3]) if len(sys.argv) > 3 else None
    os.makedirs(out, exist_ok=True)
    app = win32com.client.Dispatch("PowerPoint.Application")
    pres = app.Presentations.Open(src, ReadOnly=True, Untitled=False, WithWindow=False)
    try:
        for i, slide in enumerate(pres.Slides, 1):
            slide.Export(os.path.join(out, f"slide_{i:02d}.png"), "PNG", 1600, 1200)
        print(f"rendered {pres.Slides.Count} slides to {out}")
        if pdf:
            tmp = os.path.join(os.environ.get("TEMP", out), os.path.basename(pdf))
            pres.SaveAs(tmp, 32)  # ppSaveAsPDF
            import shutil
            shutil.copyfile(tmp, pdf)
            print(f"pdf: {pdf}")
    finally:
        pres.Close()
        app.Quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
