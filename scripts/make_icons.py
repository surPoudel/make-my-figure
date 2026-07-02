"""Generate placeholder application icons into assets/icons/.

Creates a simple bar-chart glyph as PNG and ICO (and multi-size PNGs).
macOS .icns is documented in docs/BUILD_INSTALLERS.md (built on a Mac).
Replace these with real branded icons later — see docs.
"""

from __future__ import annotations

import os

from PIL import Image, ImageDraw

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_OUT = os.path.join(_ROOT, "assets", "icons")

# Okabe-Ito-ish palette to match the app's figure styling.
BG = (247, 249, 252, 255)
BARS = [(0, 114, 178, 255), (213, 94, 0, 255), (0, 158, 115, 255), (204, 121, 167, 255)]


def _draw(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), BG)
    d = ImageDraw.Draw(img)
    margin = size * 0.16
    base = size - margin
    axis_w = max(1, int(size * 0.02))
    # axes
    d.line([(margin, margin), (margin, base)], fill=(40, 40, 40, 255), width=axis_w)
    d.line([(margin, base), (size - margin, base)], fill=(40, 40, 40, 255), width=axis_w)
    # bars
    n = len(BARS)
    span = (size - 2 * margin)
    bw = span / (n * 1.6)
    gap = (span - n * bw) / (n + 1)
    heights = [0.5, 0.78, 0.62, 0.9]
    x = margin + gap
    for i, color in enumerate(BARS):
        h = (base - margin) * heights[i]
        d.rectangle([x, base - h, x + bw, base], fill=color)
        x += bw + gap
    return img


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    sizes = [16, 32, 48, 64, 128, 256, 512]
    master = _draw(512)
    master.save(os.path.join(_OUT, "icon.png"))
    for s in sizes:
        _draw(s).save(os.path.join(_OUT, f"icon_{s}.png"))
    # Windows ICO with multiple embedded sizes.
    master.save(os.path.join(_OUT, "icon.ico"),
                sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"Wrote icons to {_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
