"""Build a browsable HTML copy of the tutorial under tutorial/html/ with Python-Markdown.

No documentation framework: one CSS file, one page per Markdown file, relative links rewritten
from .md to .html, screenshots referenced in place. Navigation: index -> gallery -> plot ->
tutorial -> video placeholder.

    python tutorial/automation/build_html.py
"""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
import sys

import markdown

HERE = os.path.dirname(os.path.abspath(__file__))
TUT = os.path.abspath(os.path.join(HERE, ".."))
OUT = os.path.join(TUT, "html")

CSS = """
body{font-family:Arial,Helvetica,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#111;line-height:1.5}
h1,h2,h3{color:#1F2937} a{color:#1D4E89} img{max-width:100%;border:1px solid #ddd;margin:.5rem 0}
table{border-collapse:collapse;margin:1rem 0} td,th{border:1px solid #ccc;padding:.3rem .6rem;vertical-align:top}
pre,code{background:#f4f4f4} pre{padding:.6rem;overflow:auto} nav{font-size:.95rem;margin-bottom:1.5rem}
blockquote{border-left:4px solid #ccc;margin:0;padding:.2rem 1rem;color:#333}
"""

NAV = ('<nav><a href="{root}index.html">Tutorial home</a> · <a href="{root}PLOT_GALLERY.html">Plot gallery</a> · '
       '<a href="{root}videos/RECORDING.html">Videos</a> · <a href="{root}audit/validation_report.html">Validation</a></nav>')


def convert(md_path: str) -> None:
    rel = os.path.relpath(md_path, TUT)
    out_path = os.path.join(OUT, os.path.splitext(rel)[0] + ".html")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    depth = rel.count(os.sep)
    root = "../" * depth
    with open(md_path, encoding="utf-8") as fh:
        text = fh.read()
    text = re.sub(r"\]\(([^)]+?)\.md(#[^)]*)?\)", r"](\1.html\2)", text)
    # video placeholders become visible tokens; real URLs become links
    links = json.load(open(os.path.join(TUT, "videos", "video_links.json"), encoding="utf-8"))["videos"]
    for key, url in links.items():
        token = url if str(url).startswith("VIDEO_URL_") else None
        if token:
            text = text.replace(f"`{token}`", f"<em>video not yet published ({token})</em>")
        elif url:
            text = re.sub(rf"`VIDEO_URL_[A-Z_]+`", f"[watch the video]({url})", text)
    body = markdown.markdown(text, extensions=["tables", "fenced_code", "toc"])
    title = re.search(r"^# (.+)$", text, re.M)
    html = (f"<!doctype html><html><head><meta charset='utf-8'><title>{title.group(1) if title else rel}</title>"
            f"<style>{CSS}</style></head><body>{NAV.format(root=root)}{body}</body></html>")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(html)


def main() -> int:
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    mds = [p for p in glob.glob(os.path.join(TUT, "**", "*.md"), recursive=True)
           if os.sep + "html" + os.sep not in p and os.sep + "automation" + os.sep not in p]
    for p in mds:
        convert(p)
    # screenshots are referenced relatively from the html tree: copy them alongside
    shutil.copytree(os.path.join(TUT, "screenshots"), os.path.join(OUT, "screenshots"), dirs_exist_ok=True)
    shutil.copy(os.path.join(OUT, "README.html"), os.path.join(OUT, "index.html"))
    print(f"html: {len(mds)} pages -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
