"""Regenerate the bundled example dataset(s) deterministically and check the manifest.

    python .agents/makemyfigure-developer/scripts/generate_example.py                  # all plot types (same as scripts/generate_example_data.py)
    python .agents/makemyfigure-developer/scripts/generate_example.py dumbbell_plot     # verify one plot's example after regeneration

The example generator (scripts/generate_example_data.py) is the single authority: it writes
examples/by_plot_type/<slug>/{data.csv,tsv,xlsx,plotspec.json,README.md}, the combined workbook
and examples/example_data_manifest.json with a fixed seed. Because the manifest is one file,
regeneration is always for ALL plot types; this wrapper runs it, then verifies that every
registered plot type has an example whose PlotSpec renders, and reports rows/columns for the
plot type(s) named. It never touches anything outside examples/.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402


def regenerate() -> None:
    script = os.path.join(C.ROOT, "scripts", "generate_example_data.py")
    out = subprocess.run([sys.executable, script], cwd=C.ROOT, capture_output=True, text=True,
                         env={**os.environ, "MPLBACKEND": "Agg"})
    if out.returncode != 0:
        print(out.stdout[-2000:]); print(out.stderr[-3000:])
        raise SystemExit("generate_example_data.py failed")
    print(out.stdout.strip().splitlines()[-1] if out.stdout.strip() else "regenerated")


def verify(plot_types) -> int:
    import importlib
    ex = importlib.import_module("make_my_figure_core.examples")
    ex.load_manifest.cache_clear()
    reg = C.registry()
    failures = 0
    for pt in plot_types:
        if not ex.has_example(pt):
            print(f"FAIL {pt}: no example entry in examples/example_data_manifest.json "
                  f"(add an Example(...) to scripts/generate_example_data.py)")
            failures += 1
            continue
        info, aux, spec = ex.load_example(pt)
        try:
            res = reg.render(spec, info.dataframe, aux={k: v.dataframe for k, v in aux.items()} or None)
            import matplotlib.pyplot as plt
            plt.close(res.figure)
            print(f"PASS {pt}: {len(info.dataframe)} rows x {len(info.dataframe.columns)} cols "
                  f"({', '.join(map(str, info.dataframe.columns[:6]))}{'...' if len(info.dataframe.columns) > 6 else ''}); "
                  f"{len(res.warnings)} warning(s)")
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {pt}: example PlotSpec does not render: {type(e).__name__}: {e}")
            failures += 1
    return failures


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plot_type", nargs="*", help="plot type(s) to verify after regeneration (default: all)")
    ap.add_argument("--no-regenerate", action="store_true", help="only verify")
    a = ap.parse_args()
    if not a.no_regenerate:
        regenerate()
    pts = a.plot_type or C.plot_types()
    unknown = [p for p in pts if p not in C.plot_types()]
    if unknown:
        raise SystemExit(f"not registered: {unknown}")
    failures = verify(pts)
    changed = C.git("status", "--short", "--", "examples")
    if changed:
        print("\nexamples/ changed (review before committing):\n" + changed)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
