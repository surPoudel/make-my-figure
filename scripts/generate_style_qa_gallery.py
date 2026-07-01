"""Render a visual QA gallery: every example plot in every style profile.

Outputs to ``outputs/style_qa_gallery/`` (git-ignored — regenerate any time)
with a Markdown index for quick visual inspection of publication-readiness.

Usage:
    python scripts/generate_style_qa_gallery.py            # PNG for all profiles
    python scripts/generate_style_qa_gallery.py --formats png,svg,pdf
    python scripts/generate_style_qa_gallery.py --profiles publication,nature_like
"""

from __future__ import annotations

import argparse
import os
import sys

import matplotlib

matplotlib.use("Agg")

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from make_my_figure_core import examples  # noqa: E402
from make_my_figure_core.plots.registry import (  # noqa: E402
    available_plot_types,
    display_name,
    make_spec,
    render,
    export_figure,
)
from make_my_figure_core.styles.engine import list_profiles  # noqa: E402

OUT = os.path.join(_ROOT, "outputs", "style_qa_gallery")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--formats", default="png")
    ap.add_argument("--profiles", default="")
    args = ap.parse_args()
    formats = [f.strip() for f in args.formats.split(",") if f.strip()]

    all_profiles = list_profiles()
    if args.profiles:
        profiles = [p for p in args.profiles.split(",") if p in all_profiles]
    else:
        # publication + the three starter profiles + any learned profiles.
        profiles = [p for p in all_profiles
                    if p in ("publication", "nature_like", "science_like", "cell_like")
                    or p.endswith("_learned")]

    os.makedirs(OUT, exist_ok=True)
    import matplotlib.pyplot as plt

    index: dict = {}
    n_ok = n_warn = 0
    for pt in available_plot_types():
        info, aux, _spec = examples.load_example(pt)
        aux_dfs = {k: v.dataframe for k, v in aux.items()} or None
        index[pt] = {}
        for prof in profiles:
            spec = make_spec(pt, "data.csv", prof)
            try:
                result = render(spec, info.dataframe, aux=aux_dfs)
            except Exception as exc:  # keep going
                index[pt][prof] = {"error": str(exc)}
                continue
            base = os.path.join(OUT, f"{pt}__{prof}")
            files = export_figure(result.figure, base, formats,
                                  dpi=spec["output"].get("dpi", 300))
            plt.close(result.figure)
            check = result.metadata.get("publication_check", {})
            n_ok += bool(check.get("passed"))
            n_warn += (not check.get("passed", True))
            index[pt][prof] = {
                "png": os.path.basename(files[0]) if files else None,
                "check": check.get("summary", ""),
            }

    _write_index(index, profiles)
    print(f"Wrote QA gallery for {len(available_plot_types())} plot types x "
          f"{len(profiles)} profiles to {os.path.relpath(OUT, _ROOT)}")
    print(f"Publication check: {n_ok} passed, {n_warn} with warnings.")
    return 0


def _write_index(index: dict, profiles: list) -> None:
    lines = [
        "# Style QA Gallery",
        "",
        "Visual QA of every example plot rendered in every style profile. "
        "Regenerate with `python scripts/generate_style_qa_gallery.py`.",
        "",
        "> Journal-like / publication-style aesthetics only — not official journal "
        "compliance. Example data are synthetic.",
        "",
    ]
    for pt, per_prof in index.items():
        lines.append(f"## {display_name(pt)} (`{pt}`)")
        lines.append("")
        for prof in profiles:
            entry = per_prof.get(prof, {})
            if entry.get("error"):
                lines.append(f"- **{prof}** — error: {entry['error']}")
                continue
            png = entry.get("png")
            if png:
                lines.append(f"### {prof} — {entry.get('check','')}")
                lines.append(f"![{pt} {prof}]({png})")
                lines.append("")
    with open(os.path.join(OUT, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
