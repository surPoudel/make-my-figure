"""Render a review sheet of variants for one plot type so the author can judge it quickly.

    python .agents/makemyfigure-developer/scripts/render_plot_matrix.py dumbbell_plot
    python .agents/makemyfigure-developer/scripts/render_plot_matrix.py dumbbell_plot --out reports/agent_runs/dumbbell

Variants are derived GENERICALLY from the bundled example by editing the table: the grouping column
is the first mapped role whose column is NON-numeric (checked by dtype, in the order x, group,
condition, sample, subject, label, color, hue, stack) and the value column the first mapped role whose
column is numeric (y, value, response, estimate, score, measurement, time, x). Variants: default, few groups (2), many groups (8, groups duplicated with suffixes),
small n (3 per group), large n (60 per group, resampled with a fixed seed), long labels, missing
values (10 % NaN), extreme value, statistics on (if the renderer uses the statistics engine),
horizontal orientation (if declared as an option), and each shipped style preset found under
style_profiles/ (*.mmfpreset.json). Each variant is rendered at the PlotSpec's own physical width
and saved as PNG; a contact sheet (matrix.png) and a markdown report list warnings, exceptions,
figure size in mm, publication score (if available) and text-overlap QC (if available).
LOOK at the sheet: a render without exceptions is not a pass.
"""
from __future__ import annotations

import argparse
import copy
import glob
import json
import math
import os
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


CATEGORY_ROLE_ORDER = ("x", "label", "sample", "subject", "group", "condition", "hue", "color", "stack")
VALUE_ROLE_ORDER = ("y", "value", "response", "estimate", "score", "measurement", "value_a", "value_b", "lower", "upper",
                    "start", "end", "time", "x")


def _roles(spec: Dict[str, Any], df: pd.DataFrame, category_role: Optional[str] = None,
           value_role: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """(category column, numeric value column). Explicit roles win; otherwise the first mapped role in
    CATEGORY_ROLE_ORDER whose column is non-numeric, and the first in VALUE_ROLE_ORDER whose column is numeric.
    For plots where two categorical roles exist (e.g. item + condition), pass --category-role."""
    mapping = spec.get("mapping", {}) or {}
    cat = num = None
    for key in ((category_role,) if category_role else CATEGORY_ROLE_ORDER):
        col = mapping.get(key)
        if isinstance(col, str) and col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
            cat = col; break
    for key in ((value_role,) if value_role else VALUE_ROLE_ORDER):
        col = mapping.get(key)
        if isinstance(col, str) and col in df.columns and pd.api.types.is_numeric_dtype(df[col]) and col != cat:
            num = col; break
    return cat, num


def variants(spec: Dict[str, Any], df: pd.DataFrame, uses_stats: bool, has_orientation: bool,
             category_role: Optional[str] = None, value_role: Optional[str] = None) -> List[Tuple[str, Dict[str, Any], pd.DataFrame]]:
    cat, num = _roles(spec, df, category_role, value_role)
    rng = np.random.default_rng(7)
    out: List[Tuple[str, Dict[str, Any], pd.DataFrame]] = [("default", copy.deepcopy(spec), df)]
    if cat:
        levels = list(dict.fromkeys(df[cat].astype(str)))
        if len(levels) > 2:
            out.append(("few_groups", copy.deepcopy(spec), df[df[cat].astype(str).isin(levels[:2])].reset_index(drop=True)))
        parts = []
        for k in range(math.ceil(8 / max(1, len(levels)))):
            d = df.copy(); d[cat] = d[cat].astype(str) + (f" {k + 1}" if k else "")
            parts.append(d)
        many = pd.concat(parts, ignore_index=True)
        many = many[many[cat].astype(str).isin(list(dict.fromkeys(many[cat].astype(str)))[:8])].reset_index(drop=True)
        out.append(("many_groups", copy.deepcopy(spec), many))
        out.append(("small_n", copy.deepcopy(spec), df.groupby(cat, sort=False, group_keys=False).head(3).reset_index(drop=True)))
        big = pd.concat([g.sample(60, replace=True, random_state=7) for _, g in df.groupby(cat, sort=False)], ignore_index=True)
        if num:
            big[num] = big[num] + rng.normal(0, big[num].std() * 0.15 if big[num].std() else 0.1, len(big))
        out.append(("large_n", copy.deepcopy(spec), big))
        long = df.copy(); long[cat] = long[cat].astype(str) + " with a considerably longer label"
        out.append(("long_labels", copy.deepcopy(spec), long))
    if num:
        miss = df.copy(); idx = rng.choice(len(miss), max(1, len(miss) // 10), replace=False)
        miss.loc[miss.index[idx], num] = np.nan
        out.append(("missing_values", copy.deepcopy(spec), miss))
        ext = df.copy(); ext.loc[ext.index[0], num] = float(ext[num].max()) * 4 if ext[num].max() else 10.0
        out.append(("extreme_value", copy.deepcopy(spec), ext))
    if uses_stats:
        s = copy.deepcopy(spec); s["statistics"] = {**(s.get("statistics") or {}), "enabled": True}
        out.append(("statistics_on", s, df))
    if has_orientation:
        s = copy.deepcopy(spec); s["mapping"]["orientation"] = "horizontal"
        out.append(("horizontal", s, df))
    presets = C.optional_import("make_my_figure_core.presets")
    if presets:
        for path in sorted(glob.glob(os.path.join(C.ROOT, "style_profiles", "**", "*.mmfpreset.json"), recursive=True))[:4]:
            try:
                p = presets.load_preset(path)
                res = presets.apply_preset(p, copy.deepcopy(spec), columns=list(df.columns))
                out.append((f"preset_{os.path.basename(path).split('.')[0]}", res.spec, df))
            except Exception:  # noqa: BLE001
                continue
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plot_type")
    ap.add_argument("--out", help="output folder (default reports/agent_runs/<plot_type>_matrix)")
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--category-role", help="mapping role to treat as the grouping/item axis (default: first non-numeric of "
                                            + ", ".join(CATEGORY_ROLE_ORDER) + ")")
    ap.add_argument("--value-role", help="mapping role to treat as the numeric value (default: first numeric of " + ", ".join(VALUE_ROLE_ORDER) + ")")
    ap.add_argument("--catalog-figure", action="store_true",
                    help="also write docs/manuals/assets/figures/<plot_type>.png (default variant, 150 dpi) - the "
                         "manual catalogue image, produced through the app like every other gallery artefact")
    a = ap.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image

    reg = C.registry()
    if a.plot_type not in reg.available_plot_types():
        raise SystemExit(f"{a.plot_type} is not registered")
    ex = C.optional_import("make_my_figure_core.examples")
    info, aux_t, spec = ex.load_example(a.plot_type)
    df, aux = info.dataframe, ({k: v.dataframe for k, v in aux_t.items()} or None)
    src = open(os.path.join(C.ROOT, C.renderer_path_for(a.plot_type)), encoding="utf-8").read()
    ui = C.optional_import("make_my_figure_core.ui_hints")
    has_orient = bool(ui and any(o.key == "orientation" for o in ui.options(a.plot_type)))
    out_dir = a.out or os.path.join(C.ROOT, "reports", "agent_runs", f"{a.plot_type}_matrix")
    os.makedirs(out_dir, exist_ok=True)
    score_mod = C.optional_import("make_my_figure_core.qc.publication_score")
    layout_mod = C.optional_import("make_my_figure_core.qc.text_layout_qc")

    rows = []; images = []
    cat_col, val_col = _roles(spec, df, a.category_role, a.value_role)
    print(f"variants built on category column {cat_col!r} and value column {val_col!r} "
          f"(override with --category-role / --value-role)")
    for name, s, d in variants(spec, df, "run_and_annotate" in src or "run_statistics" in src, has_orient,
                               a.category_role, a.value_role):
        row: Dict[str, Any] = {"variant": name, "rows": len(d)}
        try:
            res = reg.render(s, d, aux=aux)
            fig = res.figure
            w, h = fig.get_size_inches()
            row.update({"status": "ok", "size_mm": f"{w * 25.4:.0f}x{h * 25.4:.0f}", "warnings": len(res.warnings),
                        "first_warning": (res.warnings[0][:90] if res.warnings else "")})
            if score_mod:
                try:
                    sc = score_mod.score_publication(result=res, figure=fig, spec=s)
                    row["pub_score"] = f"{getattr(sc, 'level', '')} {getattr(sc, 'score', '')}"
                except Exception:  # noqa: BLE001
                    row["pub_score"] = "n/a"
            if layout_mod:
                try:
                    q = layout_mod.check_text_layout(fig)
                    row["text_qc"] = f"overlap {q.n_overlapping_pairs}, clipped {q.n_clipped}"
                except Exception:  # noqa: BLE001
                    row["text_qc"] = "n/a"
            png = os.path.join(out_dir, f"{name}.png")
            open(png, "wb").write(reg.figure_to_bytes(fig, "png", dpi=a.dpi))
            if name == "default" and a.catalog_figure:
                cat = os.path.join(C.ROOT, "docs", "manuals", "assets", "figures", f"{a.plot_type}.png")
                os.makedirs(os.path.dirname(cat), exist_ok=True)
                open(cat, "wb").write(reg.figure_to_bytes(fig, "png", dpi=150))
                print(f"catalogue figure written: {os.path.relpath(cat, C.ROOT)}")
            images.append((name, png)); plt.close(fig)
        except Exception as e:  # noqa: BLE001
            row.update({"status": "EXCEPTION", "first_warning": f"{type(e).__name__}: {str(e)[:120]}"})
        rows.append(row)

    if images:
        ims = [Image.open(p).convert("RGB") for _, p in images]
        cell_w = max(i.width for i in ims); cell_h = max(i.height for i in ims) + 28
        cols = 3; nrows = math.ceil(len(ims) / cols)
        sheet = Image.new("RGB", (cell_w * cols, cell_h * nrows), "white")
        from PIL import ImageDraw
        draw = ImageDraw.Draw(sheet)
        for i, ((name, _), im) in enumerate(zip(images, ims)):
            x, y = (i % cols) * cell_w, (i // cols) * cell_h
            draw.text((x + 6, y + 6), name, fill="black")
            sheet.paste(im, (x, y + 28))
        sheet.save(os.path.join(out_dir, "matrix.png"))
    cols_out = ["variant", "rows", "status", "size_mm", "warnings", "pub_score", "text_qc", "first_warning"]
    md = (f"# Render matrix: `{a.plot_type}` ({reg.display_name(a.plot_type)})\n\n"
          f"checkout {C.git('rev-parse', '--abbrev-ref', 'HEAD')} {C.git('rev-parse', '--short', 'HEAD')}; example {ex.entry(a.plot_type)['files']['csv']}\n\n"
          + f"variants built on category column {cat_col!r} and value column {val_col!r}\n\n"
          + C.table(rows, cols_out) + "\n\nContact sheet: matrix.png. Inspect every panel: font sizes, marker sizes, line widths, "
          "contrast, axis and tick labels, legend placement, whitespace, clipping, overlap, long labels, brackets, physical size.\n"
          + ("" if layout_mod else "NOTE: this checkout has no text-layout QC module, so the pub_score column does NOT detect "
             "overlapping or clipped text; only your eyes do.\n"))
    open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8").write(md)
    print(md); print(f"written: {out_dir if not os.path.abspath(out_dir).startswith(C.ROOT) else os.path.relpath(out_dir, C.ROOT)}")
    return 1 if any(r["status"] != "ok" for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
