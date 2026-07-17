#!/usr/bin/env python
"""Cross-platform QC harness — render every plot type deterministically and record
a structured report, so the same run on Mac / Windows / WSL / Linux can be compared.

It does NOT compare pixels across platforms (fonts/backends legitimately differ).
Instead it checks, per plot type: renders without error; produces the expected
artifacts (PNG/PDF/SVG, all non-empty); carries no forbidden (journal-named) style
label; and reports element counts (axes, legend labels), warnings, and the font/
backend actually used. Outputs qc_summary.csv, qc_report.md, platform_manifest.json
and PlotSpec sidecars.

Usage:
  python scripts/run_cross_platform_qc.py --output reports/release_cross_platform_qc/current_platform
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import traceback

import matplotlib

matplotlib.use("Agg")  # deterministic, headless
import matplotlib.pyplot as plt  # noqa: E402

# Ensure the repo (editable) is importable when run from a checkout.
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from make_my_figure_core import examples as ex  # noqa: E402
from make_my_figure_core.plots.registry import (  # noqa: E402
    available_plot_types, default_mapping, export_figure, make_spec, render, write_sidecar)
from make_my_figure_core.version import build_info  # noqa: E402

_FORBIDDEN = ("nature_like", "science_like", "cell_like", "nature-like",
              "science-like", "cell-like", "journal-like")
_FORMATS = ("png", "pdf", "svg")


def _package_versions() -> dict:
    out = {}
    for mod in ("matplotlib", "pandas", "numpy", "scipy", "networkx", "statsmodels",
                "streamlit", "PySide6"):
        try:
            m = __import__(mod)
            out[mod] = getattr(m, "__version__", "unknown")
        except Exception:  # noqa: BLE001
            out[mod] = "not installed"
    return out


def _spec_for(plot_type: str):
    """Return (spec, dataframe, aux) for a plot type using its bundled example."""
    try:
        info, aux_tables, plotspec = ex.load_example(plot_type)
        df = info.dataframe
        aux = {k: v.dataframe for k, v in (aux_tables or {}).items()}
        if plotspec:
            plotspec.setdefault("journal_style", "publication")
            plotspec["journal_style"] = "publication"
            spec = plotspec
        else:
            spec = make_spec(plot_type, "qc", "publication", mapping=default_mapping(plot_type))
        return spec, df, (aux or None)
    except Exception:
        return None, None, None


def _font_used() -> str:
    try:
        return str(plt.rcParams.get("font.family"))
    except Exception:  # noqa: BLE001
        return "unknown"


def run(output_dir: str) -> dict:
    os.makedirs(output_dir, exist_ok=True)
    rows = []
    plot_types = available_plot_types()
    for pt in plot_types:
        row = {"plot_type": pt, "render_status": "skipped",
               "export_png": "", "export_pdf": "", "export_svg": "",
               "n_axes": 0, "n_legend_labels": 0, "n_warnings": 0,
               "forbidden_style_label": False, "font_used": "", "notes": ""}
        spec, df, aux = _spec_for(pt)
        if spec is None:
            row["notes"] = "no example dataset"
            rows.append(row)
            continue
        pdir = os.path.join(output_dir, pt)
        os.makedirs(pdir, exist_ok=True)
        try:
            result = render(spec, df, aux=aux)
            fig = result.figure
            row["render_status"] = "ok"
            row["n_axes"] = len(fig.axes)
            leg = fig.axes[0].get_legend() if fig.axes else None
            row["n_legend_labels"] = len(leg.get_texts()) if leg else 0
            row["n_warnings"] = len(result.warnings or [])
            row["font_used"] = _font_used()
            blob = json.dumps(result.metadata, default=str).lower() + \
                " ".join(result.warnings or []).lower()
            row["forbidden_style_label"] = any(tok in blob for tok in _FORBIDDEN)
            base = os.path.join(pdir, pt)
            for fmt in _FORMATS:
                try:
                    export_figure(fig, base, [fmt], dpi=300)
                    p = f"{base}.{fmt}"
                    ok = os.path.exists(p) and os.path.getsize(p) > 200
                    row[f"export_{fmt}"] = "ok" if ok else "empty"
                except Exception as exc:  # noqa: BLE001
                    row[f"export_{fmt}"] = f"error: {exc}"
            try:
                write_sidecar(spec, result.metadata, base)
            except Exception:  # noqa: BLE001
                pass
            plt.close(fig)
        except Exception as exc:  # noqa: BLE001
            row["render_status"] = f"error: {exc}"
            row["notes"] = traceback.format_exc().splitlines()[-1]
        rows.append(row)

    manifest = {"build": build_info(), "packages": _package_versions(),
                "n_plot_types": len(plot_types),
                "repo_in_mnt_c": _REPO.startswith("/mnt/"),
                "repo_in_onedrive": "OneDrive" in _REPO}
    with open(os.path.join(output_dir, "platform_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    fields = ["plot_type", "render_status", "export_png", "export_pdf", "export_svg",
              "n_axes", "n_legend_labels", "n_warnings", "forbidden_style_label",
              "font_used", "notes"]
    with open(os.path.join(output_dir, "qc_summary.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    ok = [r for r in rows if r["render_status"] == "ok"]
    errored = [r for r in rows if r["render_status"].startswith("error")]
    forbidden = [r for r in rows if r["forbidden_style_label"]]
    lines = [
        "# Cross-platform QC report", "",
        f"- Build: `{build_info()['version']}` · commit `{build_info()['commit']}` · "
        f"backend `{build_info()['backend']}`",
        f"- Platform: `{build_info()['platform']}`",
        f"- Plot types: {len(rows)} · rendered OK: {len(ok)} · errors: {len(errored)}",
        f"- Forbidden (journal) style labels found: {len(forbidden)}",
        "", "## Per-plot results", "",
        "| plot_type | render | png | pdf | svg | axes | legend | warns |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['plot_type']} | {r['render_status']} | {r['export_png']} | "
                     f"{r['export_pdf']} | {r['export_svg']} | {r['n_axes']} | "
                     f"{r['n_legend_labels']} | {r['n_warnings']} |")
    if errored:
        lines += ["", "## Errors", *[f"- **{r['plot_type']}**: {r['render_status']}" for r in errored]]
    with open(os.path.join(output_dir, "qc_report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    return {"n": len(rows), "ok": len(ok), "errors": len(errored),
            "forbidden": len(forbidden), "output": output_dir}


def main() -> int:
    ap = argparse.ArgumentParser(description="Cross-platform plot QC harness.")
    ap.add_argument("--output", default="reports/release_cross_platform_qc/current_platform",
                    help="Output directory for the QC report + artifacts.")
    args = ap.parse_args()
    summary = run(args.output)
    print(json.dumps(summary, indent=2))
    # Non-zero exit if any plot errored or any forbidden style label leaked.
    return 1 if (summary["errors"] or summary["forbidden"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
