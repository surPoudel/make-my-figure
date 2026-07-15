"""Assemble the recreated panels into a labelled multi-panel figure (Figure Builder)."""
import os
import _lib

if __name__ == "__main__":
    fs = _lib.assemble_figure()
    ok = {e: os.path.exists(os.path.join(_lib.FB_DIR, f"assembled_figure.{e}"))
          and os.path.getsize(os.path.join(_lib.FB_DIR, f"assembled_figure.{e}")) > 0
          for e in ("png", "svg", "pdf")}
    with open(os.path.join(_lib.FB_DIR, "assembled_figure_qc.md"), "w", encoding="utf-8") as fh:
        fh.write("# Assembled figure QC\n\n"
                 "Panels A/B/C assembled via Make My Figure's Figure Builder "
                 "(`make_my_figure_core.panels.build_figure`) into a 2x2 grid, "
                 "uppercase labels, 180x160 mm, panel content rasterized at 300 dpi with "
                 "vector labels.\n\n"
                 f"- FigureSpec: `figure_builder/figure_spec.json`\n"
                 f"- Exports non-empty: {ok}\n\n"
                 "This demonstrates assembly of recreated Publication-style panels into a "
                 "manuscript-ready layout; it is not a copy of any published composite figure.\n")
    print("Figure Builder assembled ->", fs, "exports:", ok)
