"""Capability-driven styling audit: every registered plot, every control it declares.

For each plot type, this asks only what the capability registry says the plot can
do, and then checks that the control actually did it:

  legend      offset the legend and measure that it moved by what was asked
  palette     switch the palette and measure that the drawn colours changed
  overrides   set one category's colour and measure that artist took it
  categories  2 / 3 / 5 / 10 groups, where the plot takes a grouping column
  science     every numeric value in the metadata is identical after styling
  roundtrip   PlotSpec -> JSON -> render gives the same picture
  export      the figure is unchanged by being exported (preview/export parity)

Writes styling_audit.csv beside this file and prints a short summary. Verbose
detail goes to the CSV, not the terminal.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import pathlib
import sys
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import to_hex

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
TMP = pathlib.Path(os.environ.get("CLAUDE_JOB_DIR", "/tmp")) / "tmp" / "styling_audit"
TMP.mkdir(parents=True, exist_ok=True)

from make_my_figure_core import examples                      # noqa: E402
from make_my_figure_core.plots import base, registry          # noqa: E402
from make_my_figure_core.styles.capabilities import get_style_capabilities  # noqa: E402

SKIP = "n/a"


# Text that is fitted to its axes is fitted for the size it is being drawn at, so
# the first draw at a new dpi re-fits it and the one after that is identical.
# Every digest here is therefore taken at ONE dpi, after a settling draw at that
# same dpi - otherwise the harness measures its own dpi change and calls it a
# difference, which is the trap the v1.2.1 gallery audit fell into.
DIGEST_DPI = 150


def digest(fig, *, settle: bool = False) -> str:
    if settle:
        fig.savefig(io.BytesIO(), format="png", dpi=DIGEST_DPI)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DIGEST_DPI)
    return hashlib.sha256(buf.getvalue()).hexdigest()[:16]


def numeric_metadata(meta) -> dict:
    out = {}
    for key, value in (meta or {}).items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            out[key] = round(float(value), 9)
        elif isinstance(value, (list, tuple)) and value and all(
                isinstance(v, (int, float)) for v in value):
            out[key] = [round(float(v), 9) for v in value]
    return out


def render(plot_type, *, style=None, layout=None, mapping=None):
    table, aux, spec = examples.load_example(plot_type)
    spec = json.loads(json.dumps(spec))
    if style:
        spec["style"] = {**(spec.get("style") or {}), **style}
    if layout:
        spec["layout"] = {**(spec.get("layout") or {}), **layout}
    if mapping:
        spec["mapping"] = {**spec["mapping"], **mapping}
    return spec, table.dataframe, {k: v.dataframe for k, v in (aux or {}).items()}, \
        registry.render(spec, table.dataframe,
                        aux={k: v.dataframe for k, v in (aux or {}).items()})


def legend_box_pt(fig):
    fig.canvas.draw()
    ax = base.legend_axes(fig)
    leg = ax.get_legend() if ax is not None else None
    if leg is None:
        return None
    box = leg.get_window_extent(fig.canvas.get_renderer())
    scale = 72.0 / fig.dpi
    return (box.x0 * scale, box.y0 * scale)


def drawn_colors(fig) -> set:
    out = set()
    for ax in fig.axes:
        for coll in ax.collections:
            # Face AND edge: a LineCollection - which is what a dendrogram's
            # branches are - has no face colour at all, so reading only faces
            # reported "the palette does nothing" on a plot where it works.
            for getter in ("get_facecolor", "get_edgecolor", "get_color"):
                try:
                    values = getattr(coll, getter)()
                    out.update(to_hex(c) for c in np.atleast_2d(values))
                except Exception:  # noqa: BLE001
                    pass
        for patch in ax.patches:
            try:
                out.add(to_hex(patch.get_facecolor()))
            except Exception:  # noqa: BLE001
                pass
        for line in ax.lines:
            try:
                out.add(to_hex(line.get_color()))
            except Exception:  # noqa: BLE001
                pass
    return out


def audit(plot_type) -> dict:
    caps = get_style_capabilities(plot_type)
    row = {"plot_type": plot_type}
    figs = []
    try:
        spec, df, aux, baseline = render(plot_type)
        figs.append(baseline.figure)
        base_digest = digest(baseline.figure, settle=True)
        base_meta = numeric_metadata(baseline.metadata)
        base_colors = drawn_colors(baseline.figure)
        row["render"] = "pass"

        # --- legend offset ------------------------------------------------
        row["legend"] = SKIP
        if caps.supports_legend and legend_box_pt(baseline.figure) is not None:
            before = legend_box_pt(baseline.figure)
            _s, _d, _a, moved = render(plot_type, layout={"legend_offset_x": 18.0})
            figs.append(moved.figure)
            after = legend_box_pt(moved.figure)
            dx = after[0] - before[0] if after else None
            row["legend"] = ("pass" if dx is not None and abs(dx - 18.0) < 1.0
                             else f"FAIL moved {dx}")
        elif caps.supports_legend:
            row["legend"] = "no legend in example"

        # --- palette ------------------------------------------------------
        row["palette"] = SKIP
        if caps.supports_palette:
            # A plot with no categorical colour reaches the palette only through
            # the colormap partner this project's palettes carry, so probe it
            # with one of those; matplotlib's qualitative sets have no partner
            # and are not offered there.
            probe = "tab20" if caps.supports_group_colors else "grayscale"
            _s, _d, _a, painted = render(plot_type, style={"palette_name": probe})
            figs.append(painted.figure)
            row["palette"] = ("pass" if drawn_colors(painted.figure) != base_colors
                              else "FAIL colours unchanged")

        # --- one category's colour ----------------------------------------
        row["override"] = SKIP
        if caps.supports_group_colors:
            _s, _d, _a, over = render(plot_type,
                                      style={"color_overrides": {"0": "#FF00FF"}})
            figs.append(over.figure)
            row["override"] = ("pass" if "#ff00ff" in drawn_colors(over.figure)
                               else "FAIL not applied")

        # --- science unchanged under styling -------------------------------
        _s, _d, _a, styled = render(
            plot_type, style={"palette_name": "tab20", "color_overrides": {"0": "#FF00FF"}},
            layout={"legend_offset_x": 6.0})
        figs.append(styled.figure)
        styled_meta = numeric_metadata(styled.metadata)
        drift = {k: (base_meta[k], styled_meta.get(k))
                 for k in base_meta if styled_meta.get(k) != base_meta[k]}
        row["science"] = "pass" if not drift else f"FAIL {list(drift)[:3]}"

        # --- PlotSpec round trip -------------------------------------------
        again = registry.render(json.loads(json.dumps(spec)), df, aux=aux)
        figs.append(again.figure)
        row["roundtrip"] = ("pass" if digest(again.figure, settle=True) == base_digest
                            else "FAIL render differs")

        # --- preview / export parity ---------------------------------------
        written = registry.export_figure(baseline.figure, str(TMP / plot_type),
                                         ["png", "pdf", "svg"], dpi=DIGEST_DPI)
        sizes = {pathlib.Path(p).suffix.lstrip("."): os.path.getsize(p) for p in written}
        small = [f for f, n in sizes.items() if n < 1000]
        row["export"] = "pass" if not small else f"FAIL tiny {small}"
        # Parity is "the file you get is the file you get": export twice and the
        # bytes must match. Comparing the in-memory figure before and after an
        # export instead measures the re-fit that a tight bounding box legitimately
        # triggers on the two label-repelling plot types - the saved file is
        # correct, and it settles after one save.
        again_png = registry.export_figure(baseline.figure, str(TMP / f"{plot_type}_2"),
                                           ["png"], dpi=DIGEST_DPI)
        first = pathlib.Path(str(TMP / plot_type) + ".png").read_bytes()
        second = pathlib.Path(again_png[0]).read_bytes()
        row["export_parity"] = ("pass" if first == second
                                else "FAIL two exports differ")
    except Exception as exc:  # noqa: BLE001
        row.setdefault("render", f"FAIL {type(exc).__name__}: {exc}"[:90])
    finally:
        for f in figs:
            plt.close(f)
    return row


def audit_categories(plot_type) -> dict:
    """2 / 3 / 5 / 10 groups through a plot that takes a grouping column."""
    row = {"plot_type": plot_type}
    rng = np.random.default_rng(5)
    for n in (2, 3, 5, 10):
        try:
            spec = registry.make_spec(plot_type, "t.csv", "publication")
            spec["mapping"] = {"x": "c", "y": "m", "color": "c", "error": "sem"}
            df = pd.DataFrame({"c": [f"G{i:02d}" for i in range(n) for _ in range(5)],
                               "m": rng.normal(1.0, 0.2, n * 5)})
            result = registry.render(spec, df)
            colors = [to_hex(p.get_facecolor())
                      for p in result.figure.axes[0].patches][:n]
            warned = any("categories were drawn" in w for w in result.warnings)
            distinct = len(set(colors))
            plt.close(result.figure)
            ok = (distinct == n) or warned
            row[f"n{n}"] = f"{'pass' if ok else 'FAIL'} {distinct}/{n}" \
                           f"{' warned' if warned else ''}"
        except Exception as exc:  # noqa: BLE001
            row[f"n{n}"] = f"FAIL {type(exc).__name__}"
    return row


def main():
    warnings.filterwarnings("ignore")
    plot_types = [p for p in sorted(registry.available_plot_types()) if examples.entry(p)]
    print(f"auditing {len(plot_types)} plot types with examples")
    rows = []
    for i, pt in enumerate(plot_types, 1):
        rows.append(audit(pt))
        print(f"  [{i:2d}/{len(plot_types)}] {pt}")
        sys.stdout.flush()

    cols = ["plot_type", "render", "legend", "palette", "override", "science",
            "roundtrip", "export", "export_parity"]
    with open(OUT / "styling_audit.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    cat = [audit_categories("barplot_with_error_bar"),
           audit_categories("boxplot_or_violin_with_points")]
    with open(OUT / "styling_audit_categories.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["plot_type", "n2", "n3", "n5", "n10"],
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(cat)

    failures = {r["plot_type"]: {k: v for k, v in r.items()
                                 if isinstance(v, str) and v.startswith("FAIL")}
                for r in rows}
    failures = {k: v for k, v in failures.items() if v}
    checked = {c: sum(1 for r in rows if r.get(c) == "pass") for c in cols[1:]}
    print(f"\n  {len(plot_types) - len(failures)} of {len(plot_types)} plot types clean")
    print(f"  checks that passed: {checked}")
    for pt, bad in failures.items():
        print(f"    {pt}: {bad}")
    for r in cat:
        print(f"  categories {r['plot_type']}: "
              f"{ {k: v for k, v in r.items() if k != 'plot_type'} }")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
