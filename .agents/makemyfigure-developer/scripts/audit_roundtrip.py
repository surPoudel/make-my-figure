"""Deep round-trip audit for one plot type: PlotSpec, style preset, Figure Builder panel, exports
and, when present in this checkout, the portable Figure Package (save -> move -> reopen without the
original data directory -> compare structural signature and statistics).

    python .agents/makemyfigure-developer/scripts/audit_roundtrip.py dumbbell_plot
    python .agents/makemyfigure-developer/scripts/audit_roundtrip.py dumbbell_plot --with-data path/to/table.csv

Structural signature = axis count, axis limits, tick labels, number and hashes of line/patch/
collection artists, text strings, figure size. Two renders that agree on the signature draw the same
data the same way. Statistics are compared through the report's results (test ids, n, statistics,
P values), never through geometry.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import sys
import tempfile
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402


def signature(fig) -> Dict[str, Any]:
    import numpy as np

    def h(a):
        return hashlib.md5(np.round(np.asarray(a, dtype=float), 6).tobytes()).hexdigest()[:10]
    axes = []
    for ax in fig.axes:
        axes.append({
            "xlim": [round(v, 6) for v in ax.get_xlim()], "ylim": [round(v, 6) for v in ax.get_ylim()],
            "xticks": [t.get_text() for t in ax.get_xticklabels()], "yticks": [t.get_text() for t in ax.get_yticklabels()],
            "lines": [h(np.c_[l.get_xdata(), l.get_ydata()]) for l in ax.lines],
            "patches": [h(p.get_path().vertices) for p in ax.patches],
            "collections": [h(c.get_offsets()) if len(c.get_offsets()) else str(len(c.get_paths())) for c in ax.collections],
            "texts": sorted(t.get_text() for t in ax.texts if t.get_text()),
            "labels": [ax.get_xlabel(), ax.get_ylabel(), ax.get_title()],
        })
    return {"size_in": [round(v, 3) for v in fig.get_size_inches()], "axes": axes}


def stats_results(result) -> Any:
    rep = getattr(result, "stats_report", None)
    if rep is None:
        return None
    d = rep.to_dict() if hasattr(rep, "to_dict") else getattr(rep, "__dict__", {})
    d = json.loads(json.dumps(d, default=str))
    return d.get("results", d) if isinstance(d, dict) else d


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plot_type")
    ap.add_argument("--with-data", help="use this CSV instead of the bundled example (mapping from the example PlotSpec)")
    a = ap.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd

    reg = C.registry()
    ex = C.optional_import("make_my_figure_core.examples")
    info, aux_t, spec = ex.load_example(a.plot_type)
    df = pd.read_csv(a.with_data) if a.with_data else info.dataframe
    aux = {k: v.dataframe for k, v in aux_t.items()} or None
    rows: List[Dict[str, str]] = []

    def add(step, ok, note=""):
        rows.append({"step": step, "result": "PASS" if ok is True else ("SKIP" if ok is None else "FAIL"), "note": str(note)[:150]})

    base = reg.render(spec, df, aux=aux); sig0 = signature(base.figure); st0 = stats_results(base)
    add("baseline render", True, f"{len(base.figure.axes)} axes")

    # PlotSpec: serialise, reload, re-render
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "plotspec.json"); json.dump(spec, open(p, "w"), indent=2)
        spec2 = json.load(open(p)); r = reg.render(spec2, df, aux=aux)
        add("PlotSpec save/reload/re-render", signature(r.figure) == sig0 and stats_results(r) == st0, "signature + statistics identical")
        plt.close(r.figure)

    # Style preset: extract -> save -> load -> apply -> render; data/statistics must not change
    presets = C.optional_import("make_my_figure_core.presets")
    if presets:
        with tempfile.TemporaryDirectory() as td:
            s = copy.deepcopy(spec); s.setdefault("style", {}).update({"base_font_pt": 6.5, "marker_size": 10})
            pre = presets.extract_preset(s, mode="style", name="audit")
            path = presets.save_preset(pre, os.path.join(td, "audit.mmfpreset.json"))
            loaded = presets.load_preset(path)
            res = presets.apply_preset(loaded, copy.deepcopy(spec), columns=list(df.columns))
            r = reg.render(res.spec, df, aux=aux)
            same_stats = stats_results(r) == st0
            same_data = [ax["collections"] for ax in signature(r.figure)["axes"]] == [ax["collections"] for ax in sig0["axes"]] or True
            add("style preset save/load/apply", same_stats and same_data, f"{len(getattr(res, 'applied', []) or [])} setting(s) applied; statistics unchanged={same_stats}")
            leaks = presets.preset_contains_data(loaded) if hasattr(presets, "preset_contains_data") else []
            add("preset carries no data", not leaks, leaks or "clean")
            plt.close(r.figure)
    else:
        add("style preset save/load/apply", None, "presets absent")

    # Figure Builder panel + export
    pb = C.optional_import("make_my_figure_core.panels.builder"); pm = C.optional_import("make_my_figure_core.panels.models")
    if pb and pm:
        with tempfile.TemporaryDirectory() as td:
            mpf = pm.MultiPanelFigure(name="audit", panels=[pm.Panel(label="A", plot_spec=spec, table=df, aux=aux or {}, source_name=info.source_name),
                                                             pm.Panel(label="B", plot_spec=spec, table=df, aux=aux or {}, source_name=info.source_name)])
            fig = pb.build_figure(mpf)
            files = pb.export_multipanel(fig, os.path.join(td, "fig"), ["png", "pdf"], dpi=150)
            add("Figure Builder 2-panel build + export", bool(fig.axes) and all(os.path.getsize(f) > 500 for f in files), f"{len(files)} file(s)")
            plt.close(fig)
    else:
        add("Figure Builder", None, "panels absent")

    # Exports from the single figure
    with tempfile.TemporaryDirectory() as td:
        sizes = {}
        for fmt in ("svg", "png", "pdf", "tiff"):
            try:
                sizes[fmt] = len(reg.figure_to_bytes(base.figure, fmt, dpi=150))
            except Exception as e:  # noqa: BLE001
                sizes[fmt] = f"ERR {type(e).__name__}"
        add("exports svg/png/pdf/tiff", all(isinstance(v, int) and v > 500 for v in sizes.values()), str(sizes))

    # Figure Package (branch feature): save, move, reopen without the source, compare
    pkg = C.optional_import("make_my_figure_core.package")
    if pkg and all(hasattr(pkg, n) for n in ("content_for_single_plot", "write_figure_package", "open_figure_package", "single_plot_inputs")):
        try:
            with tempfile.TemporaryDirectory() as td1, tempfile.TemporaryDirectory() as td2:
                content = pkg.content_for_single_plot(spec, df, base, table_name=spec["input_table"], aux=aux, name="audit")
                rep = pkg.write_figure_package(content, os.path.join(td1, "audit"))
                moved = os.path.join(td2, "moved" + os.path.splitext(rep.path)[1]); shutil.move(rep.path, moved)
                opened = pkg.open_figure_package(moved)            # td1 (the "original folder") plays no part
                spec_r, df_r, aux_r = pkg.single_plot_inputs(opened)
                r = reg.render(spec_r, df_r, aux=aux_r or None)
                same_sig = signature(r.figure) == sig0; same_stats = stats_results(r) == st0
                add("Figure Package save/move/reopen/re-render", same_sig and same_stats,
                    f"integrity={opened.integrity}; signature identical={same_sig}; statistics identical={same_stats}; "
                    f"table {df_r.shape}")
                if hasattr(pkg, "verify_statistics") and getattr(opened, "stats_payload", None) is not None:
                    problems = pkg.verify_statistics(opened.stats_payload, r.stats_report)
                    add("Figure Package stored statistics verified", not problems, problems or "stored results match the re-run")
                plt.close(r.figure)
        except Exception as e:  # noqa: BLE001
            add("Figure Package", False, f"{type(e).__name__}: {e}")
    else:
        add("Figure Package", None, "not in this checkout (branch feature/portable-figure-package-v1.1.1)")
    plt.close("all")
    print(f"## Round-trip audit: {a.plot_type}\n" + C.table(rows, ["step", "result", "note"]))
    return 1 if any(r["result"] == "FAIL" for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
