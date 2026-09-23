"""Contact sheet of every rendered slide: python tutorial/slides/build_montage.py <render_dir> <out.png> [cols]"""
import glob, os, sys
from PIL import Image, ImageDraw, ImageFont

src, out = sys.argv[1], sys.argv[2]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 4
files = sorted(glob.glob(os.path.join(src, "slide_*.png")))
tw, th, pad, cap = 480, 360, 18, 26
rows = (len(files) + cols - 1) // cols
sheet = Image.new("RGB", (cols * (tw + pad) + pad, rows * (th + pad + cap) + pad), "white")
draw = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype("DejaVuSans.ttf", 16)
except Exception:  # noqa: BLE001
    font = ImageFont.load_default()
for i, f in enumerate(files):
    r, c = divmod(i, cols)
    im = Image.open(f).convert("RGB"); im.thumbnail((tw, th))
    x = pad + c * (tw + pad); y = pad + r * (th + pad + cap)
    sheet.paste(im, (x, y))
    draw.rectangle([x - 1, y - 1, x + im.width, y + im.height], outline="#BBBBBB")
    draw.text((x, y + th + 4), f"slide {i + 1}", fill="#1F2937", font=font)
sheet.save(out)
print(f"montage {len(files)} slides -> {out} ({sheet.width}x{sheet.height})")
