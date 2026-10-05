"""TEST THE WHEEL: install it into a fresh virtual environment and exercise it from OUTSIDE the repo.

    python .agents/makemyfigure-release-manager/scripts/smoke_test_install.py [--version X.Y.Z] [--desktop] [--keep]

The venv is created in a temporary directory and the test script runs with that directory as
its working directory, so `import make_my_figure_core` cannot resolve to the checkout. Checks:
import, __version__ == expected, plot registry loads (count recorded), bundled resources present
(schemas/style_profiles/mock_data/examples via resources.missing_bundled_dirs), a bundled example
renders and exports PNG + PDF bytes, one statistical test runs. With --desktop it also installs
PySide6 and imports the desktop controller (the GUI itself is not part of the wheel: the wheel
ships make_my_figure_core only; apps/ is part of the source tree and the PyInstaller bundle).
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

PROBE = r'''
import json, os, sys, traceback
os.environ["MPLBACKEND"] = "Agg"
out = {"cwd": os.getcwd(), "checks": {}}
def check(name, fn):
    try:
        out["checks"][name] = {"ok": True, "value": fn()}
    except Exception as exc:
        out["checks"][name] = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()[-600:]}
import make_my_figure_core
out["module_file"] = make_my_figure_core.__file__
check("version", lambda: __import__("make_my_figure_core.version", fromlist=["x"]).__version__)
from make_my_figure_core.plots.registry import available_plot_types, make_spec, render, figure_to_bytes
check("plot_types", lambda: len(available_plot_types()))
from make_my_figure_core import resources
check("bundled_dirs_missing", lambda: resources.missing_bundled_dirs())
from make_my_figure_core import examples
def render_example():
    pt = "boxplot_or_violin_with_points"
    info, aux, plotspec = examples.load_example(pt)
    df = info.dataframe
    mapping = plotspec.get("mapping") or None
    spec = make_spec(pt, "example.csv", plotspec.get("journal_style", "publication"), mapping=mapping)
    res = render(spec, df, aux={k: t.dataframe for k, t in aux.items()} or None)
    png = figure_to_bytes(res.figure, "png", dpi=100); pdf = figure_to_bytes(res.figure, "pdf")
    return {"png_bytes": len(png), "pdf_bytes": len(pdf), "rows": int(len(df))}
check("render_example", render_example)
def stats():
    import numpy as np, pandas as pd
    from make_my_figure_core.plots import registry
    rng = np.random.default_rng(0)
    df = pd.DataFrame([{"g": g, "y": float(rng.normal(m, 0.3))} for g, m in [("A", 1.0), ("B", 2.0)] for _ in range(8)])
    spec = make_spec("barplot_with_error_bar", "t.csv", "publication", mapping={"x": "g", "y": "y"},
                     statistics={"enabled": True, "test": "welch_t", "comparison_mode": "all_pairs"})
    res = render(spec, df)
    return {"n_results": len(res.stats_report.results), "test": res.stats_report.results[0].test_name}
check("statistics", stats)
if "--desktop" in sys.argv:
    def desktop():
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        import PySide6
        return {"PySide6": PySide6.__version__}
    check("desktop_import", desktop)
print("PROBE_JSON " + json.dumps(out))
'''


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", help="expected version (default: version.py)")
    ap.add_argument("--desktop", action="store_true", help="also install PySide6 and import it")
    ap.add_argument("--keep", action="store_true", help="keep the temporary venv")
    ap.add_argument("--json", default=os.path.join(C.REPORTS_DIR, "wheel_smoke_test.json"))
    a = ap.parse_args()
    v = (a.version or C.version_py()).lstrip("v")
    wheels = glob.glob(os.path.join(C.STAGING_ROOT, v, "python", "*.whl"))
    if not wheels:
        print(f"FAIL: no wheel in release_staging/{v}/python - run build_python_dist.py first"); return 1
    wheel = wheels[0]
    tmp = tempfile.mkdtemp(prefix="mmf_wheel_venv_")
    venv = os.path.join(tmp, "venv")
    py = os.path.join(venv, "Scripts" if os.name == "nt" else "bin", "python" + (".exe" if os.name == "nt" else ""))
    rec = {"generated": C.now_iso(), "version": v, "wheel": os.path.basename(wheel), "venv": venv, "ok": False}
    try:
        subprocess.run([sys.executable, "-m", "venv", venv], check=True)
        subprocess.run([py, "-m", "pip", "install", "-q", "--upgrade", "pip"], check=True)
        pkgs = [wheel] + (["PySide6>=6.5,<7"] if a.desktop else [])
        r = subprocess.run([py, "-m", "pip", "install", "-q", *pkgs], text=True, capture_output=True, timeout=1800)
        rec["pip_install_returncode"] = r.returncode
        if r.returncode != 0:
            rec["pip_error"] = r.stderr[-1500:]; raise SystemExit("pip install failed")
        probe = os.path.join(tmp, "probe.py")
        open(probe, "w", encoding="utf-8").write(PROBE)
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        if a.desktop and os.environ.get("LD_LIBRARY_PATH"):
            env["LD_LIBRARY_PATH"] = os.environ["LD_LIBRARY_PATH"]
        r = subprocess.run([py, probe] + (["--desktop"] if a.desktop else []), cwd=tmp, text=True, capture_output=True, env=env, timeout=900)
        line = [l for l in (r.stdout or "").splitlines() if l.startswith("PROBE_JSON ")]
        if not line:
            rec["probe_error"] = (r.stderr or r.stdout)[-1500:]; raise SystemExit("probe produced no result")
        import json
        probe_out = json.loads(line[0][len("PROBE_JSON "):])
        rec.update(probe_out)
        checks = probe_out["checks"]
        rec["imported_from_venv"] = venv in probe_out.get("module_file", "") or "site-packages" in probe_out.get("module_file", "")
        rec["version_ok"] = checks.get("version", {}).get("value") == v
        rec["ok"] = all(c["ok"] for c in checks.values()) and rec["imported_from_venv"] and rec["version_ok"] \
            and not checks.get("bundled_dirs_missing", {}).get("value")
    except SystemExit as exc:
        rec["error"] = str(exc)
    finally:
        C.write_json(a.json, rec)
        if not a.keep:
            shutil.rmtree(tmp, ignore_errors=True)
    print(f"wheel smoke test for {rec['wheel']}")
    print(f"  imported from venv: {rec.get('imported_from_venv')}  ({rec.get('module_file', '')})")
    for name, c in rec.get("checks", {}).items():
        print(f"  {'ok ' if c['ok'] else '!! '}{name}: {c.get('value') if c['ok'] else c.get('error')}")
    if rec.get("error"):
        print("  error:", rec["error"], rec.get("pip_error", rec.get("probe_error", ""))[:600])
    print("RESULT:", "PASS" if rec["ok"] else "FAIL", "->", os.path.relpath(a.json, C.ROOT))
    return 0 if rec["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
