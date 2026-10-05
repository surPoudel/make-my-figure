"""Release gate for v1.2.0: every registered plot type, end to end.

Phases 5 and 6 of the release brief. The plot list comes from the live registry,
so a plot type added later cannot slip past this by not being in a hard-coded
list. For each type: render the bundled example at the default and publication
style, measure the drawn figure with the project's own layout QC, export to the
three shipped formats, and round-trip the PlotSpec and the Figure Package.

Writes gallery_audit.csv and gallery_audit.md next to this file. Exit code is 1
if any required check failed, so it can be used as a gate.
"""
from __future__ import annotations

import csv
import json
import os
import pathlib
import sys
import traceback
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = pathlib.Path(__file__).resolve().parent
TMP = pathlib.Path(os.environ.get("CLAUDE_JOB_DIR", "/tmp")) / "tmp" / "gallery_audit"
TMP.mkdir(parents=True, exist_ok=True)

from make_my_figure_core import examples                      # noqa: E402
from make_my_figure_core.package import (                     # noqa: E402
    content_for_single_plot, open_figure_package, single_plot_inputs,
    write_figure_package)
from make_my_figure_core.plots import registry                # noqa: E402
from make_my_figure_core.qc.text_layout_qc import check_text_layout  # noqa: E402

# A legend drawn over the data is a judgement call on a dense scatter, not a
# defect, so it is reported but does not fail the gate. Clipped text, overlapping
# text and a failed round-trip do fail it.
GATING = ("render_default", "render_publication", "clipped",
          "overlap", "export_png", "export_svg", "export_pdf",
          "plotspec_roundtrip", "package_roundtrip")

# `unnamed_scale` is reported, not gated. Whether a plot presents a readable axis
# at all is a design decision per plot type - a network graph clears both tick
# sets on purpose, and a tissue map gives a scale bar instead of coordinates in
# microns - so a mechanical check cannot tell a defect from an intended choice.
# What it *can* say is narrower and worth recording: this axes draws a scale and
# does not name it.


def _render(plot_type, profile=None):
    table, aux, spec = examples.load_example(plot_type)
    if profile:
        spec = {**spec, "style": {**(spec.get("style") or {}), "profile": profile}}
    aux_frames = {k: v.dataframe for k, v in (aux or {}).items()}
    return spec, table, aux_frames, registry.render(spec, table.dataframe, aux=aux_frames)


def audit_one(plot_type):
    row = {"plot_type": plot_type}
    figs = []
    try:
        # --- 1. default render + layout QC
        spec, table, aux, res = _render(plot_type)
        figs.append(res.figure)
        row["render_default"] = "pass"
        qc = check_text_layout(res.figure)
        row["n_text"] = qc.n_text
        row["clipped"] = "pass" if qc.n_clipped == 0 else f"FAIL {qc.n_clipped} clipped"
        row["overlap"] = "pass" if qc.n_overlapping_pairs == 0 else f"FAIL {qc.n_overlapping_pairs} pairs"
        row["legend_over_data"] = ("no" if not qc.legend_overlaps_data
                                   else f"yes {qc.legend_overlap_fraction:.0%}")
        row["min_font_pt"] = qc.min_font_pt
        row["size_mm"] = f"{qc.drawn_width_mm:.0f}x{qc.drawn_height_mm:.0f}"
        row["warnings"] = len(res.warnings)

        # --- 2. axis labels and title actually drawn
        unnamed = []
        for i, ax in enumerate(res.figure.axes):
            if not ax.axison:
                continue   # presents no axis; there is no scale to name
            for side, ticks, label in (("x", ax.get_xticklabels(), ax.get_xlabel()),
                                       ("y", ax.get_yticklabels(), ax.get_ylabel())):
                drawn = [t for t in ticks if t.get_visible() and t.get_text().strip()]
                if drawn and not label.strip():
                    unnamed.append(f"ax{i}.{side}")
        row["unnamed_scale"] = "none" if not unnamed else ",".join(unnamed)

        # --- 3. publication style
        _s, _t, _a, res_pub = _render(plot_type, profile="publication")
        figs.append(res_pub.figure)
        row["render_publication"] = "pass"
        qcp = check_text_layout(res_pub.figure)
        row["pub_clipped"] = qcp.n_clipped
        row["pub_overlap"] = qcp.n_overlapping_pairs

        # --- 4. exports
        base = str(TMP / plot_type)
        try:
            written = registry.export_figure(res.figure, base, ["png", "svg", "pdf"], dpi=200)
            got = {pathlib.Path(p).suffix.lstrip("."): os.path.getsize(p) for p in written}
            for fmt in ("png", "svg", "pdf"):
                row[f"export_{fmt}"] = ("pass" if got.get(fmt, 0) > 1000
                                        else f"FAIL {got.get(fmt, 0)}B")
        except Exception as exc:
            for fmt in ("png", "svg", "pdf"):
                row[f"export_{fmt}"] = f"FAIL {type(exc).__name__}"

        # --- 5. PlotSpec round-trip: serialise, validate, re-render
        try:
            spec2 = json.loads(json.dumps(spec))
            registry.validate_plot_spec(spec2)
            res2 = registry.render(spec2, table.dataframe, aux=aux)
            figs.append(res2.figure)
            same = (abs(res2.figure.get_size_inches()[0] - res.figure.get_size_inches()[0]) < 0.01
                    and abs(res2.figure.get_size_inches()[1] - res.figure.get_size_inches()[1]) < 0.01)
            row["plotspec_roundtrip"] = "pass" if same else "FAIL size differs"
        except Exception as exc:
            row["plotspec_roundtrip"] = f"FAIL {type(exc).__name__}: {exc}"[:90]

        # --- 6. Figure Package round-trip: write, reopen, re-render from frozen data
        try:
            content = content_for_single_plot(
                spec, table.dataframe, res, table_name=spec.get("input_table") or "table.csv",
                aux=aux, name=plot_type)
            rep = write_figure_package(content, str(TMP / f"{plot_type}_pkg"))
            pkg = open_figure_package(rep.path)
            spec3, df3, aux3 = single_plot_inputs(pkg)
            res3 = registry.render(spec3, df3, aux=aux3)
            figs.append(res3.figure)
            row["package_roundtrip"] = "pass"
            row["package_kb"] = os.path.getsize(rep.path) // 1024
        except Exception as exc:
            row["package_roundtrip"] = f"FAIL {type(exc).__name__}: {exc}"[:90]

    except Exception as exc:
        row.setdefault("render_default", f"FAIL {type(exc).__name__}: {exc}"[:90])
        row["traceback"] = traceback.format_exc(limit=2).replace("\n", " ")[:200]
    finally:
        for f in figs:
            plt.close(f)
    return row


def main():
    warnings.filterwarnings("ignore")
    plot_types = sorted(registry.available_plot_types())
    print(f"auditing {len(plot_types)} registered plot types "
          f"(from the live registry)\n")
    rows = []
    for i, pt in enumerate(plot_types, 1):
        row = audit_one(pt)
        rows.append(row)
        bad = [k for k in GATING if str(row.get(k, "")).startswith("FAIL")]
        print(f"  [{i:2d}/{len(plot_types)}] {pt:34s} " +
              ("OK" if not bad else "FAIL: " + ", ".join(bad)))
        sys.stdout.flush()

    cols = ["plot_type"] + [c for c in (
        "render_default", "render_publication", "clipped", "overlap", "unnamed_scale",
        "export_png", "export_svg", "export_pdf", "plotspec_roundtrip",
        "package_roundtrip", "legend_over_data", "min_font_pt", "n_text", "size_mm",
        "pub_clipped", "pub_overlap", "warnings", "package_kb", "traceback")]
    with open(OUT / "gallery_audit.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    failures = {}
    for row in rows:
        bad = {k: row[k] for k in GATING if str(row.get(k, "")).startswith("FAIL")}
        if bad:
            failures[row["plot_type"]] = bad

    legend_notes = [r["plot_type"] for r in rows
                    if str(r.get("legend_over_data", "no")).startswith("yes")]
    unnamed_notes = [(r["plot_type"], r["unnamed_scale"]) for r in rows
                     if r.get("unnamed_scale", "none") != "none"]

    with open(OUT / "gallery_audit.md", "w") as fh:
        fh.write("# v1.2.0 gallery audit (Phases 5-6)\n\n")
        fh.write(f"{len(plot_types)} registered plot types, read from the live registry.\n\n")
        fh.write("Per plot type: default render, publication-style render, layout QC "
                 "(clipped text, overlapping text, legend over data, minimum font), "
                 "PNG/SVG/PDF export, PlotSpec round-trip and Figure Package "
                 "round-trip re-rendered from the frozen data.\n\n")
        fh.write(f"**Result: {len(plot_types) - len(failures)} of {len(plot_types)} clean"
                 f"{'' if not failures else f'; {len(failures)} with failures'}.**\n\n")
        if failures:
            fh.write("## Failures\n\n")
            for pt, bad in failures.items():
                fh.write(f"- **{pt}**\n")
                for k, v in bad.items():
                    fh.write(f"  - `{k}`: {v}\n")
            fh.write("\n")
        if legend_notes:
            fh.write("## Reported, not gating: legend drawn over data\n\n"
                     "A key placed inside the axes can sit on the data; on a dense plot that is "
                     "a judgement call, so it is recorded rather than failed.\n\n")
            for pt in legend_notes:
                fh.write(f"- {pt}\n")
            fh.write("\n")
        if unnamed_notes:
            fh.write("## Reported, not gating: a drawn scale with no name\n\n"
                     "These axes draw tick labels but carry no axis label. Whether that is a "
                     "defect depends on the plot type, so it is recorded rather than failed.\n\n")
            for pt, where in unnamed_notes:
                fh.write(f"- {pt} ({where})\n")
            fh.write("\n")
        fh.write("Full per-plot measurements: `gallery_audit.csv`.\n")

    print(f"\n{len(plot_types) - len(failures)} of {len(plot_types)} clean")
    if failures:
        print(f"{len(failures)} with failures:")
        for pt, bad in failures.items():
            print(f"  {pt}: {bad}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
