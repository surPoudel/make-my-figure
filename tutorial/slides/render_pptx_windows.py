"""Render every slide of a .pptx to PNG with PowerPoint (Windows, COM) for visual checking.

    python tutorial\\slides\\render_pptx_windows.py deck.pptx out_dir

Requires PowerPoint and pywin32. PowerPoint is started invisibly and closed afterwards.
"""
from __future__ import annotations

import os
import sys


def main() -> int:
    import win32com.client  # type: ignore

    src = os.path.abspath(sys.argv[1])
    out = os.path.abspath(sys.argv[2])
    os.makedirs(out, exist_ok=True)
    app = win32com.client.Dispatch("PowerPoint.Application")
    pres = app.Presentations.Open(src, ReadOnly=True, Untitled=False, WithWindow=False)
    try:
        for i, slide in enumerate(pres.Slides, 1):
            slide.Export(os.path.join(out, f"slide_{i:02d}.png"), "PNG", 1600, 1200)
        print(f"rendered {pres.Slides.Count} slides to {out}")
    finally:
        pres.Close()
        app.Quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
