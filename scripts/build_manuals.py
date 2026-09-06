"""Assemble the two manuals and render them as Markdown, DOCX and PDF.

* Markdown: the User Manual is assembled from ``docs/manuals/User_Manual/parts/*.md`` (in name order)
  into ``MakeMyFigure_User_Manual.md``; the Quick Start is a single file. A version banner (app
  version, git commit, date) is injected at the top of both.
* DOCX: pandoc (``--toc``, numbered figures via captions; images resolved relative to the manual).
* PDF: there is no LaTeX or HTML-to-PDF engine in this environment, so the PDF is typeset with
  PyMuPDF's Story (HTML + CSS) - real pagination, embedded screenshots with numbered captions,
  page numbers and a generated table of contents with page references.

Run: python scripts/build_manuals.py            (prints page counts and image counts)
"""
from __future__ import annotations

import datetime as _dt
import io
import os
import re
import shutil
import subprocess
import sys

import fitz  # PyMuPDF
import markdown

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from make_my_figure_core.version import __version__, build_info  # noqa: E402

DOCS = os.path.join(ROOT, "docs", "manuals")
QS_DIR = os.path.join(DOCS, "Quick_Start")
UM_DIR = os.path.join(DOCS, "User_Manual")
ASSETS = os.path.join(DOCS, "assets")

COMMIT = build_info().get("commit") or "unknown"
DATE = _dt.date.today().isoformat()

CSS = """
@page { size: A4; margin: 18mm 17mm 20mm 17mm; }
body { font-family: sans-serif; font-size: 10.5pt; line-height: 1.38; color: #111; }
h1 { font-size: 22pt; margin: 22pt 0 8pt 0; color: #123; }
h2 { font-size: 15pt; margin: 14pt 0 6pt 0; color: #123; }
h3 { font-size: 12.5pt; margin: 11pt 0 4pt 0; color: #234; }
h4 { font-size: 11pt; margin: 9pt 0 3pt 0; color: #234; }
p { margin: 0 0 6pt 0; }
li { margin: 0 0 2pt 0; }
code { font-family: monospace; font-size: 9.2pt; background: #F3F3F3; }
pre { font-family: monospace; font-size: 8.8pt; background: #F3F3F3; border: 0.5pt solid #CCC; padding: 5pt; margin: 4pt 0 8pt 0; white-space: pre-wrap; }
table { border-collapse: collapse; margin: 4pt 0 10pt 0; font-size: 9.2pt; }
th, td { border: 0.5pt solid #999; padding: 3pt 5pt; vertical-align: top; }
th { background: #E8EEF4; }
img { max-width: 100%; max-height: 190mm; }
figure { margin: 6pt 0 10pt 0; }
figcaption { font-size: 9pt; color: #333; margin-top: 3pt; }
blockquote { border-left: 3pt solid #7A9CC6; margin: 6pt 0; padding: 4pt 8pt; background: #F5F8FC; }
.note { border: 0.6pt solid #7A9CC6; background: #F5F8FC; padding: 5pt 8pt; margin: 6pt 0; }
.warn { border: 0.6pt solid #D9A441; background: #FEF8EA; padding: 5pt 8pt; margin: 6pt 0; }
.title { font-size: 30pt; font-weight: bold; margin-top: 120pt; color: #123; }
.subtitle { font-size: 16pt; margin-top: 10pt; color: #345; }
.meta { font-size: 11pt; margin-top: 40pt; color: #333; }
.toc p { margin: 0 0 1.5pt 0; font-size: 10pt; }
"""


def banner(title: str) -> str:
    return (f"# {title}\n\n"
            f"**MakeMyFigure version:** {__version__}  \n"
            f"**Documentation generated from commit:** `{COMMIT}`  \n"
            f"**Date:** {DATE}\n\n"
            "This manual describes the application exactly as built at the commit above. Where the "
            "packaged installers of an earlier release differ, the text says so.\n\n")


def assemble_user_manual() -> str:
    parts_dir = os.path.join(UM_DIR, "parts")
    parts = sorted(f for f in os.listdir(parts_dir) if f.endswith(".md"))
    body = "\n\n".join(open(os.path.join(parts_dir, f), encoding="utf-8").read().strip() for f in parts)
    # parts live one folder deeper than the assembled manual: re-anchor the asset links
    body = body.replace("](../../assets/", "](../assets/")
    text = banner("Make My Figure — User Manual") + body + "\n"
    out = os.path.join(UM_DIR, "MakeMyFigure_User_Manual.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text)
    return out


def stamp_quick_start() -> str:
    src = os.path.join(QS_DIR, "MakeMyFigure_Quick_Start.src.md")
    out = os.path.join(QS_DIR, "MakeMyFigure_Quick_Start.md")
    body = open(src, encoding="utf-8").read()
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(banner("Make My Figure — Quick Start") + body)
    return out


# --------------------------------------------------------------------------------------------
# DOCX via pandoc
# --------------------------------------------------------------------------------------------

def build_docx(md_path: str) -> str:
    out = md_path[:-3] + ".docx"
    cmd = ["pandoc", md_path, "-f", "markdown+smart+pipe_tables+implicit_figures", "-t", "docx",
           "--toc", "--toc-depth=2", "--resource-path", os.path.dirname(md_path) + ":" + DOCS,
           "-o", out]
    subprocess.run(cmd, check=True, cwd=os.path.dirname(md_path))
    return out


# --------------------------------------------------------------------------------------------
# PDF via PyMuPDF Story
# --------------------------------------------------------------------------------------------

_IMG_CACHE = os.path.join(DOCS, "assets", "_pdf_cache")
MAX_PAGES = 400


def pdf_image(path: str) -> str:
    """A copy of ``path`` scaled to fit one page (<= 1500 px wide, <= 1050 px tall) for the PDF.

    Story cannot break an image across pages; an image taller than the text area would never be
    placed and pagination would not terminate. Scaling here keeps the source PNGs untouched.
    """
    from PIL import Image

    os.makedirs(_IMG_CACHE, exist_ok=True)
    out = os.path.join(_IMG_CACHE, os.path.basename(path))
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(path):
        with Image.open(path) as im:
            im = im.convert("RGB")
            w, h = im.size
            scale = min(1500 / w, 1050 / h, 1.0)
            if scale < 1.0:
                im = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
            im.save(out, optimize=True)
    return out


def md_to_html(md_text: str, base_dir: str) -> tuple:
    """Markdown -> HTML with numbered figure captions; returns (html, headings, n_images)."""
    # figure numbering: standalone image paragraphs become <figure> with a caption
    counter = {"n": 0}
    lines = md_text.split("\n")
    html_lines = []
    fig_re = re.compile(r"^!\[(?P<alt>[^\]]*)\]\((?P<src>[^)]+)\)\s*$")
    for ln in lines:
        m = fig_re.match(ln.strip())
        if m:
            counter["n"] += 1
            src = m.group("src")
            path = src if os.path.isabs(src) else os.path.normpath(os.path.join(base_dir, src))
            src_name = os.path.basename(pdf_image(path)) if os.path.exists(path) else os.path.basename(path)
            html_lines.append(
                f'<figure><img src="{src_name}"/><figcaption>Figure {counter["n"]}. {m.group("alt")}</figcaption></figure>')
        else:
            html_lines.append(ln)
    html = markdown.markdown("\n".join(html_lines), extensions=["tables", "fenced_code", "toc", "sane_lists"])
    # simple admonitions: paragraphs starting with **Note:** / **Warning:**
    html = re.sub(r"<p><strong>Note:</strong>", '<p class="note"><strong>Note:</strong>', html)
    html = re.sub(r"<p><strong>Warning:</strong>", '<p class="warn"><strong>Warning:</strong>', html)
    headings = [(int(m.group(1)), re.sub("<.*?>", "", m.group(2)).strip())
                for m in re.finditer(r"<h([12])[^>]*>(.*?)</h\1>", html)]
    return html, headings, counter["n"]


def render_story(html: str, title: str, subtitle: str, out_path: str) -> int:
    """Typeset ``html`` to ``out_path`` with PyMuPDF's Story; returns the page count.

    Story writes through a DocumentWriter, so the body is written first, then reopened to add the
    title page, a contents section with page references, page numbers and a PDF outline.
    """
    page_rect = fitz.paper_rect("a4")
    margins = (17 * 2.83, 18 * 2.83, 17 * 2.83, 20 * 2.83)  # mm -> pt (l, t, r, b)
    where = page_rect + (margins[0], margins[1], -margins[2], -margins[3])

    body_path = out_path + ".body.pdf"
    # images are looked up in an Archive (PyMuPDF does not read <img src> from the filesystem)
    story = fitz.Story(html=html, user_css=CSS, archive=fitz.Archive(_IMG_CACHE))
    writer = fitz.DocumentWriter(body_path)
    headings = []          # (level, text, body_page_number starting at 1)
    current = {"pg": 0}

    def _collect(pos):     # PyMuPDF requires exactly one positional argument
        if getattr(pos, "heading", 0) in (1, 2) and (getattr(pos, "open_close", 0) & 1):
            headings.append((pos.heading, (getattr(pos, "text", "") or "").strip(), current["pg"]))

    more = True
    while more:
        current["pg"] += 1
        if current["pg"] > MAX_PAGES:
            writer.close()
            raise RuntimeError(f"pagination did not terminate within {MAX_PAGES} pages - an element "
                               "does not fit a page")
        dev = writer.begin_page(page_rect)
        more, _ = story.place(where)
        story.element_positions(_collect, {"page": current["pg"]})
        story.draw(dev)
        writer.end_page()
    writer.close()

    body = fitz.open(body_path)
    n_body = len(body)

    # contents pages
    toc_html = "<h1 class='first'>Contents</h1><div class='toc'>"
    seen = set()
    for level, text, pg in headings:
        if not text or (level, text, pg) in seen:
            continue
        seen.add((level, text, pg))
        indent = "&nbsp;&nbsp;&nbsp;&nbsp;" if level == 2 else ""
        toc_html += f"<p>{indent}{text} &nbsp;·&nbsp; {pg}</p>"
    toc_html += "</div>"
    toc_path = out_path + ".toc.pdf"
    toc_story = fitz.Story(html=toc_html, user_css=CSS)
    tw = fitz.DocumentWriter(toc_path)
    more = True
    while more:
        dev = tw.begin_page(page_rect)
        more, _ = toc_story.place(where)
        toc_story.draw(dev)
        tw.end_page()
    tw.close()
    toc = fitz.open(toc_path)
    n_toc = len(toc)

    doc = fitz.open()
    tp = doc.new_page(width=page_rect.width, height=page_rect.height)
    tp.insert_textbox(fitz.Rect(60, 200, page_rect.width - 60, 300), title, fontsize=30, fontname="helv",
                      color=(0.07, 0.13, 0.2))
    tp.insert_textbox(fitz.Rect(60, 300, page_rect.width - 60, 340), subtitle, fontsize=15, fontname="helv",
                      color=(0.2, 0.27, 0.33))
    tp.insert_textbox(fitz.Rect(60, 420, page_rect.width - 60, 560),
                      f"MakeMyFigure version {__version__}\nDocumentation generated from commit {COMMIT}\n"
                      f"Date {DATE}\n\nBuilt from the current code and the running application. "
                      f"Screenshots and example figures use bundled synthetic data only.\n\n"
                      f"Page references in the Contents count from the first body page.",
                      fontsize=11, fontname="helv")
    doc.insert_pdf(toc)
    doc.insert_pdf(body)
    # page numbers on body pages (numbered from 1 at the first body page)
    for i in range(1 + n_toc, len(doc)):
        page = doc[i]
        num = i - n_toc
        page.insert_text(fitz.Point(page_rect.width / 2 - 8, page_rect.height - 28), str(num),
                         fontsize=9, fontname="helv", color=(0.35, 0.35, 0.35))
        page.insert_text(fitz.Point(48, page_rect.height - 28), f"{title} · v{__version__} · {COMMIT}",
                         fontsize=7.5, fontname="helv", color=(0.5, 0.5, 0.5))
    outline = [[lvl, txt, pg + n_toc + 1] for lvl, txt, pg in headings if txt]
    try:
        doc.set_toc(outline)
    except Exception:  # noqa: BLE001 - an outline is a nicety
        pass
    doc.save(out_path, garbage=3, deflate=True)
    n = len(doc)
    doc.close(); body.close(); toc.close()
    for tmp in (body_path, toc_path):
        try:
            os.remove(tmp)
        except OSError:
            pass
    return n


def build_pdf(md_path: str, title: str, subtitle: str) -> tuple:
    md_text = open(md_path, encoding="utf-8").read()
    html, headings, n_img = md_to_html(md_text, os.path.dirname(md_path))
    out = md_path[:-3] + ".pdf"
    n = render_story(html, title, subtitle, out)
    return out, n, n_img


def main() -> int:
    qs_md = stamp_quick_start()
    um_md = assemble_user_manual()
    results = []
    for md, title, sub in ((qs_md, "Make My Figure — Quick Start", "From installation to an exported figure"),
                           (um_md, "Make My Figure — User Manual", "Every workflow, control and file, as built")):
        docx = build_docx(md)
        pdf, pages, n_img = build_pdf(md, title, sub)
        results.append((os.path.relpath(md, ROOT), os.path.getsize(docx) // 1024, os.path.relpath(pdf, ROOT), pages, n_img))
    for md, kb, pdf, pages, n_img in results:
        print(f"{md}\n  DOCX {kb} KB · PDF {pdf} · {pages} pages · {n_img} figures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
