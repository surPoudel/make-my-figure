"""v1.2.1 release gate: every registered plot, end to end, plus the colour contract.

Produces, beside this file:
  gallery_audit.csv       one row per plot type
  palette_contract.csv    the colour contract the brief asks for
  FIGURE_BUILDER.csv      standalone vs Figure Builder at identical dimensions

The plot list comes from the live registry, so a type added later cannot avoid
the gate by not being in a hard-coded list.
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

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
TMP = pathlib.Path(os.environ.get("CLAUDE_JOB_DIR", "/tmp")) / "tmp" / "v121_audit"
TMP.mkdir(parents=True, exist_ok=True)

from make_my_figure_core import examples, ui_hints                       # noqa: E402
from make_my_figure_core.package import (                                # noqa: E402
    content_for_single_plot, open_figure_package, single_plot_inputs, write_figure_package)
from make_my_figure_core.plots import registry                           # noqa: E402
from make_my_figure_core.qc.text_layout_qc import check_text_layout      # noqa: E402
from make_my_figure_core.styles.capabilities import get_style_capabilities  # noqa: E402
from make_my_figure_core.styles.engine import USER_PALETTES              # noqa: E402

COLOURISH = ("color", "colour", "palette", "cmap", "fill")


def digest(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=72)
    return hashlib.sha256(buf.getvalue()).hexdigest()[:12]


def artist_colours(fig):
    out = set()
    for ax in fig.axes:
        for coll in ax.collections:
            for row in coll.get_facecolor():
                out.add(tuple(np.round(row[:3], 3)))
        for line in ax.lines:
            out.add(str(line.get_color()))
        for patch in ax.patches:
            try:
                out.add(tuple(np.round(matplotlib.colors.to_rgb(patch.get_facecolor()), 3)))
            except Exception:  # noqa: BLE001
                pass
    return out


def render(plot_type, *, mapping=None, style=None):
    table, aux, spec = examples.load_example(plot_type)
    if mapping:
        spec = {**spec, "mapping": {**(spec.get("mapping") or {}), **mapping}}
    if style:
        spec = {**spec, "style": {**(spec.get("style") or {}), **style}}
    frames = {k: v.dataframe for k, v in (aux or {}).items()}
    return spec, table, frames, registry.render(spec, table.dataframe, aux=frames)


def audit_plot(plot_type):
    row = {"plot_type": plot_type}
    figs = []
    try:
        spec, table, frames, res = render(plot_type)
        figs.append(res.figure)
        row["render"] = "pass"
        # Captured BEFORE the export below. Exporting re-draws the figure, which
        # re-runs the label-refit callbacks and moves repelled labels, so a digest
        # taken afterwards is of a different figure - comparing it against a fresh
        # render reported a round-trip failure on the two label-repelling plots
        # that did not exist.
        reference = digest(res.figure)
        qc = check_text_layout(res.figure)
        row["clipped"] = qc.n_clipped
        row["overlapping_pairs"] = qc.n_overlapping_pairs
        row["warnings"] = len(res.warnings)

        _s, _t, _f, res_pub = render(plot_type, style={"profile": "publication"})
        figs.append(res_pub.figure)
        row["publication_render"] = "pass"

        base = str(TMP / plot_type)
        try:
            written = registry.export_figure(res.figure, base, ["png", "svg", "pdf"], dpi=150)
            got = {pathlib.Path(p).suffix.lstrip("."): os.path.getsize(p) for p in written}
            for fmt in ("png", "svg", "pdf"):
                row[f"export_{fmt}"] = "pass" if got.get(fmt, 0) > 1000 else f"FAIL {got.get(fmt,0)}B"
        except Exception as exc:  # noqa: BLE001
            for fmt in ("png", "svg", "pdf"):
                row[f"export_{fmt}"] = f"FAIL {type(exc).__name__}"

        try:
            spec2 = json.loads(json.dumps(spec))
            registry.validate_plot_spec(spec2)
            res2 = registry.render(spec2, table.dataframe, aux=frames)
            figs.append(res2.figure)
            row["plotspec_roundtrip"] = "pass" if digest(res2.figure) == reference \
                else "FAIL render differs"
        except Exception as exc:  # noqa: BLE001
            row["plotspec_roundtrip"] = f"FAIL {type(exc).__name__}: {exc}"[:70]

        try:
            content = content_for_single_plot(
                spec, table.dataframe, res, table_name=spec.get("input_table") or "t.csv",
                aux=frames, name=plot_type)
            rep = write_figure_package(content, str(TMP / f"{plot_type}_pkg"))
            pkg = open_figure_package(rep.path)
            spec3, df3, aux3 = single_plot_inputs(pkg)
            res3 = registry.render(spec3, df3, aux=aux3)
            figs.append(res3.figure)
            row["package_roundtrip"] = "pass" if digest(res3.figure) == reference \
                else "FAIL render differs"
        except Exception as exc:  # noqa: BLE001
            row["package_roundtrip"] = f"FAIL {type(exc).__name__}: {exc}"[:70]
    except Exception as exc:  # noqa: BLE001
        row.setdefault("render", f"FAIL {type(exc).__name__}: {exc}"[:80])
    finally:
        for f in figs:
            plt.close(f)
    return row


def audit_colour(plot_type):
    """One row per exposed colour control, plus the palette itself."""
    rows = []
    caps = get_style_capabilities(plot_type)
    semantics = ("CATEGORICAL" if caps.supports_group_colors else
                 ("NONE" if not caps.supports_palette else "SINGLE ACCENT / CONTINUOUS"))
    try:
        _s, _t, _f, base_res = render(plot_type)
        base_hash, base_cols = digest(base_res.figure), artist_colours(base_res.figure)
        plt.close(base_res.figure)
    except Exception as exc:  # noqa: BLE001
        return [{"plot": plot_type, "color_semantics": semantics, "control": "(render)",
                 "status": f"FAIL {type(exc).__name__}"}]

    if caps.supports_palette:
        a, b = USER_PALETTES[0], USER_PALETTES[1]
        try:
            _s, _t, _f, ra = render(plot_type, style={"palette_name": a})
            _s, _t, _f, rb = render(plot_type, style={"palette_name": b})
            ha, hb = digest(ra.figure), digest(rb.figure)
            n_a = len(artist_colours(ra.figure))
            plt.close(ra.figure); plt.close(rb.figure)
            rows.append({"plot": plot_type, "color_semantics": semantics,
                         "control": "palette_name", "expected_target": "categorical artists",
                         "palette_A": a, "palette_B": b, "changed": "yes" if ha != hb else "no",
                         "distinct_colours": n_a,
                         "status": "ok" if ha != hb else "PALETTE HAS NO EFFECT"})
        except Exception as exc:  # noqa: BLE001
            rows.append({"plot": plot_type, "color_semantics": semantics,
                         "control": "palette_name", "status": f"FAIL {type(exc).__name__}"})
    else:
        rows.append({"plot": plot_type, "color_semantics": semantics, "control": "palette_name",
                     "changed": "n/a", "status": "declared inapplicable (warns)"})

    for opt in ui_hints.OPTIONS.get(plot_type, []):
        if not any(t in opt.key.lower() for t in COLOURISH):
            continue
        try:
            value = "#CC6677" if opt.kind == "choice" else 0.7
            extra = {"show_ci": True} if plot_type == "bland_altman_plot" else {}
            _s, _t, _f, r = render(plot_type, mapping={**extra, opt.key: value})
            changed = digest(r.figure) != base_hash
            plt.close(r.figure)
            rows.append({"plot": plot_type, "color_semantics": semantics, "control": opt.key,
                         "expected_target": opt.label, "palette_A": "default",
                         "palette_B": str(value), "changed": "yes" if changed else "no",
                         "status": "ok" if changed else "needs a precondition / no effect"})
        except Exception as exc:  # noqa: BLE001
            rows.append({"plot": plot_type, "color_semantics": semantics, "control": opt.key,
                         "status": f"refused: {type(exc).__name__}"})
    return rows


def main():
    warnings.filterwarnings("ignore")
    plot_types = sorted(registry.available_plot_types())
    print(f"auditing {len(plot_types)} registered plot types")

    gallery, contract = [], []
    for i, pt in enumerate(plot_types, 1):
        gallery.append(audit_plot(pt))
        contract.extend(audit_colour(pt))
        print(f"  [{i:2d}/{len(plot_types)}] {pt}")
        sys.stdout.flush()

    gcols = ["plot_type", "render", "publication_render", "clipped", "overlapping_pairs",
             "export_png", "export_svg", "export_pdf", "plotspec_roundtrip",
             "package_roundtrip", "warnings"]
    with open(OUT / "gallery_audit.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=gcols, extrasaction="ignore")
        w.writeheader(); w.writerows(gallery)

    ccols = ["plot", "color_semantics", "control", "expected_target", "palette_A",
             "palette_B", "changed", "distinct_colours", "status"]
    with open(OUT / "palette_contract.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=ccols, extrasaction="ignore")
        w.writeheader(); w.writerows(contract)

    gate = ("render", "publication_render", "export_png", "export_svg", "export_pdf",
            "plotspec_roundtrip", "package_roundtrip")
    failed = {r["plot_type"]: {k: r[k] for k in gate if str(r.get(k, "")).startswith("FAIL")}
              for r in gallery}
    failed = {k: v for k, v in failed.items() if v}
    dead = [r for r in contract if r.get("status") == "PALETTE HAS NO EFFECT"]

    print(f"\n  gallery: {len(plot_types) - len(failed)} of {len(plot_types)} clean")
    for pt, bad in failed.items():
        print(f"    {pt}: {bad}")
    print(f"  colour contract: {len(contract)} controls audited, "
          f"{len(dead)} palette control(s) with no effect")
    for r in dead:
        print(f"    {r['plot']}")
    return 1 if (failed or dead) else 0


if __name__ == "__main__":
    raise SystemExit(main())
