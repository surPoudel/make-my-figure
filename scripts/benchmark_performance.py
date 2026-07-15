#!/usr/bin/env python
"""Performance benchmarks for Make My Figure (v0.6).

Measures the timings that matter for interactive responsiveness — cold import
(startup), example loading, common/heavy plot rendering, export, and figure
recommendation — and writes a Markdown report.

Run (Mac / Linux):
    python scripts/benchmark_performance.py --quick
    python scripts/benchmark_performance.py --out outputs/performance/v0_6_performance_report.md

Run (Windows PowerShell):
    python scripts\\benchmark_performance.py --quick

All measurements are local to the current machine/OS; treat them as relative,
not absolute. Rendering uses the headless Agg backend and runs fully offline.
"""

from __future__ import annotations

import argparse
import os
import statistics as _stats
import subprocess
import sys
import time
from typing import Callable, Dict, List, Optional

import matplotlib

matplotlib.use("Agg")

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

COMMON_PLOTS = ["barplot_with_error_bar", "scatterplot_with_regression",
                "boxplot_or_violin_with_points", "volcano_plot"]
HEAVY_PLOTS = ["heatmap_clustered_matrix", "pca_scatter_from_matrix"]


def _timeit(fn: Callable[[], object], repeats: int = 3) -> Dict[str, float]:
    """Return best/median wall-clock seconds over ``repeats`` runs."""
    samples: List[float] = []
    for _ in range(max(1, repeats)):
        t0 = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - t0)
    return {"best": min(samples), "median": _stats.median(samples), "runs": len(samples)}


def _cold_import_seconds(module: str) -> Optional[float]:
    """Time a fresh interpreter importing ``module`` (real startup cost)."""
    env = dict(os.environ)
    env["MPLBACKEND"] = "Agg"
    env["PYTHONPATH"] = _ROOT + os.pathsep + env.get("PYTHONPATH", "")
    code = (f"import time,importlib;"
            f"t=time.perf_counter();importlib.import_module('{module}');"
            f"print(time.perf_counter()-t)")
    try:
        out = subprocess.run([sys.executable, "-c", code], capture_output=True,
                             text=True, env=env, cwd=_ROOT, timeout=180)
        if out.returncode == 0 and out.stdout.strip():
            return float(out.stdout.strip().splitlines()[-1])
    except (subprocess.SubprocessError, ValueError):
        return None
    return None


def _render_spec(controller, plot_type: str):
    data = controller.load_example(plot_type)
    spec = controller.build_spec(plot_type, "publication", data.table_name,
                                 controller.default_mapping(plot_type))
    return spec, data


def run_benchmarks(quick: bool = False, repeats: int = 3) -> Dict[str, object]:
    """Run the benchmark battery and return a nested timings dict."""
    import matplotlib.pyplot as plt

    from apps.desktop_app.controller import DesktopController
    from make_my_figure_core.recommendations import recommend_for_table

    controller = DesktopController()
    results: Dict[str, object] = {"quick": quick, "repeats": repeats}

    # (a) cold import / startup
    results["cold_import"] = {
        "make_my_figure_core": _cold_import_seconds("make_my_figure_core"),
        "apps.desktop_app.controller": _cold_import_seconds("apps.desktop_app.controller"),
    }

    common = COMMON_PLOTS[:2] if quick else COMMON_PLOTS
    heavy = HEAVY_PLOTS[:1] if quick else HEAVY_PLOTS

    # (b) example load
    load_times: Dict[str, Dict[str, float]] = {}
    for pt in common + heavy:
        load_times[pt] = _timeit(lambda pt=pt: controller.load_example(pt), repeats)
    results["example_load"] = load_times

    # (c) render (common + heavy)
    render_times: Dict[str, Dict[str, float]] = {}
    for pt in common + heavy:
        def _do(pt=pt):
            spec, data = _render_spec(controller, pt)
            res = controller.render(spec, data)
            plt.close(res.figure)
        try:
            render_times[pt] = _timeit(_do, repeats)
        except Exception as exc:  # noqa: BLE001 - record, don't abort the battery
            render_times[pt] = {"error": str(exc)}
    results["render"] = render_times

    # (d) export (one common figure to svg+png+pdf)
    from make_my_figure_core.plots.registry import export_figure

    def _export():
        spec, data = _render_spec(controller, common[0])
        res = controller.render(spec, data)
        base = os.path.join(_root_tmp(), "bench_export")
        export_figure(res.figure, base, ["svg", "png", "pdf"], dpi=300)
        plt.close(res.figure)
    try:
        results["export_svg_png_pdf"] = _timeit(_export, repeats)
    except Exception as exc:  # noqa: BLE001
        results["export_svg_png_pdf"] = {"error": str(exc)}

    # (e) recommendation time
    def _recommend():
        data = controller.load_example("boxplot_or_violin_with_points")
        recommend_for_table(data.info.dataframe, data.table_name)
    try:
        results["recommendation"] = _timeit(_recommend, repeats)
    except Exception as exc:  # noqa: BLE001
        results["recommendation"] = {"error": str(exc)}

    return results


def _root_tmp() -> str:
    d = os.path.join(_ROOT, "outputs", "performance", "_tmp")
    os.makedirs(d, exist_ok=True)
    return d


def _fmt(t: Optional[Dict[str, float]]) -> str:
    if not t:
        return "n/a"
    if "error" in t:
        return f"error: {t['error'][:60]}"
    return f"{t['best']*1000:.0f} ms (median {t['median']*1000:.0f} ms)"


def render_report(results: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# Make My Figure — v0.6 performance report\n")
    lines.append("_Measured locally on this machine/OS with the Agg backend; "
                 "timings are relative, not absolute, and run fully offline._\n")
    lines.append(f"- Platform: `{sys.platform}`  |  Python: `{sys.version.split()[0]}`")
    lines.append(f"- quick={results.get('quick')}  repeats={results.get('repeats')}\n")

    ci = results.get("cold_import", {}) or {}
    lines.append("## Cold import (startup cost)\n")
    lines.append("| Module | Time |")
    lines.append("|---|---|")
    for k, v in ci.items():
        lines.append(f"| `{k}` | {v*1000:.0f} ms |" if isinstance(v, (int, float)) else f"| `{k}` | n/a |")
    lines.append("")

    def _table(title: str, d: Dict[str, Dict[str, float]]):
        lines.append(f"## {title}\n")
        lines.append("| Item | Time |")
        lines.append("|---|---|")
        for k, v in d.items():
            lines.append(f"| `{k}` | {_fmt(v)} |")
        lines.append("")

    _table("Example load", results.get("example_load", {}))
    _table("Render", results.get("render", {}))

    lines.append("## Export & recommendation\n")
    lines.append("| Item | Time |")
    lines.append("|---|---|")
    lines.append(f"| export (svg+png+pdf) | {_fmt(results.get('export_svg_png_pdf'))} |")
    lines.append(f"| recommend_for_table | {_fmt(results.get('recommendation'))} |")
    lines.append("")

    lines.append("## Suspected bottlenecks\n")
    lines.append("- **Canvas rebuilt every render** (desktop): the Qt canvas + toolbar are "
                 "recreated on each preview instead of updating the existing canvas — flicker "
                 "and lag. v0.6 moves toward canvas reuse + debounced preview rendering.")
    lines.append("- **Synchronous GUI-thread work**: rendering / statistics / export ran on the "
                 "GUI thread. v0.6 adds a `QThreadPool` worker layer (`apps/desktop_app/workers.py`) "
                 "so long tasks report progress instead of freezing the window.")
    lines.append("- **Eager scipy import**: importing the statistics package pulls in scipy via the "
                 "test modules; deferring it shortens cold start.")
    lines.append("- **OneDrive / cloud-synced paths (Windows)**: file dialogs and first reads can be "
                 "slow when the working directory is under OneDrive/Dropbox/iCloud (cloud hydration).")
    lines.append("- **PyInstaller cold start (Windows)**: first launch pays Defender/SmartScreen scan "
                 "+ cold DLL/plugin load + matplotlib font-cache build.\n")

    lines.append("## Remaining limitations\n")
    lines.append("- Timings vary widely by machine; re-run locally to compare before/after.")
    lines.append("- Background rendering builds figures off-thread but canvas updates stay on the "
                 "GUI thread (matplotlib requirement).")
    lines.append("- First-launch delay on frozen Windows builds is largely outside app control; "
                 "documented in `docs/WINDOWS_PERFORMANCE.md`.\n")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Make My Figure performance benchmarks")
    ap.add_argument("--quick", action="store_true", help="smaller subset for a fast run")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--out", default=None, help="write the Markdown report to this path")
    args = ap.parse_args(argv)

    results = run_benchmarks(quick=args.quick, repeats=args.repeats)
    report = render_report(results)
    print(report)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"\nWrote report to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
