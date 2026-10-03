"""Render every plot type under Publication defaults and every experimental preset, plus the
group-comparison test designs under every box/violin/bar variant, and write a geometry fingerprint.

Usage:  python scripts/render_fingerprint_all_plots.py <repo_root> <out.json>
        python scripts/render_fingerprint_all_plots.py --compare a.json b.json

Run it with two Python environments that differ only in the matplotlib (or numpy/pandas) version
and compare the two JSON files: every render must succeed in both, and the data artists (lines,
patches, collections), axis limits, tick labels and label strings must be identical. Only the
positions of repelled text labels (adjustText: volcano, MA, lollipop, network) may move.
See reports/journal_presets/matplotlib_compat_check.md for the 2026-09-17 run."""
import glob, hashlib, json, os, sys, traceback, warnings
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, pandas as pd


def compare(path_a, path_b):
    a = json.load(open(path_a)); b = json.load(open(path_b))
    ra, rb = a["results"], b["results"]
    assert ra.keys() == rb.keys(), "different render sets"
    fails = [k for k in ra if not ra[k]["ok"]] + [k for k in rb if not rb[k]["ok"]]
    data_diff, label_diff = [], []
    for k in ra:
        if not (ra[k]["ok"] and rb[k]["ok"]):
            continue
        fa, fb = ra[k]["fp"], rb[k]["fp"]
        if fa["size_in"] != fb["size_in"] or len(fa["axes"]) != len(fb["axes"]):
            data_diff.append(k); continue
        for xa, xb in zip(fa["axes"], fb["axes"]):
            for f in ("xlim", "ylim", "lines", "collections", "xticklabels", "yticklabels", "xlabel", "ylabel", "title"):
                if xa[f] != xb[f]:
                    data_diff.append(k); break
            # Empty-string texts are adjustText connector annotations (their number depends on the
            # adjustText release); real labels must be the same multiset of strings.
            if sorted(t[0] for t in xa["texts"] if t[0]) != sorted(t[0] for t in xb["texts"] if t[0]):
                data_diff.append(k)
            elif xa["texts"] != xb["texts"] or xa["patches"] != xb["patches"]:
                label_diff.append(k)
    print(f"{a['matplotlib']} vs {b['matplotlib']}: {len(ra)} renders; failed {len(set(fails))}; "
          f"data/limits/tick-or-label text differ {len(set(data_diff))}; label position only {len(set(label_diff))}")
    for k in sorted(set(fails)): print("  FAILED", k)
    for k in sorted(set(data_diff)): print("  DATA DIFFERS", k)
    for k in sorted(set(label_diff)): print("  label placement", k)
    return 1 if (fails or data_diff) else 0

if sys.argv[1] == "--compare":
    sys.exit(compare(sys.argv[2], sys.argv[3]))
ROOT = sys.argv[1]; OUT = sys.argv[2]
sys.path.insert(0, ROOT)
from make_my_figure_core.plots import registry
from make_my_figure_core import preset_preview as pv, experimental_presets as xp

def h(a):
    a = np.asarray(a, dtype=float)
    return hashlib.md5(np.round(a, 6).tobytes()).hexdigest()[:12]

def fp(fig):
    out = []
    for ax in fig.axes:
        d = {"xlim": [round(v, 6) for v in ax.get_xlim()], "ylim": [round(v, 6) for v in ax.get_ylim()],
             "lines": [h(np.c_[l.get_xdata(), l.get_ydata()]) for l in ax.lines],
             "patches": [h(p.get_path().vertices) for p in ax.patches],
             "collections": [h(c.get_offsets()) if len(c.get_offsets()) else
                             h(np.concatenate([p.vertices for p in c.get_paths()]) if c.get_paths() else [0])
                             for c in ax.collections],
             "texts": [(t.get_text(), round(float(t.get_position()[0]), 5), round(float(t.get_position()[1]), 5))
                       for t in ax.texts],
             "xticklabels": [t.get_text() for t in ax.get_xticklabels()],
             "yticklabels": [t.get_text() for t in ax.get_yticklabels()],
             "xlabel": ax.get_xlabel(), "ylabel": ax.get_ylabel(), "title": ax.get_title()}
        out.append(d)
    return {"size_in": [round(v, 4) for v in fig.get_size_inches()], "axes": out}

results = {}
def run(key, spec, df, aux):
    warnings.simplefilter("ignore")
    try:
        res = registry.render(spec, df, aux=aux)
        results[key] = {"ok": True, "fp": fp(res.figure), "warnings": list(res.warnings or []),
                        "metadata_keys": sorted((res.metadata or {}).keys()) if hasattr(res, "metadata") else []}
        plt.close(res.figure)
    except Exception as e:
        results[key] = {"ok": False, "error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-800:]}

presets = [e for e in xp.list_experimental_presets()]
for pt in registry.available_plot_types():
    spec, df, aux = pv.synthetic_spec(pt)
    run(f"{pt}|defaults", spec, df, aux)
    for e in presets:
        p = xp.load_experimental_preset(e.preset_id)
        try:
            r = pv.apply_with_guard(p, spec, columns=list(df.columns))
            run(f"{pt}|{e.preset_id}", r.spec, df, aux)
        except Exception as ex:
            results[f"{pt}|{e.preset_id}"] = {"ok": False, "error": f"apply: {type(ex).__name__}: {ex}"}

# group-comparison designs x renderer variants
gcdir = os.path.join(ROOT, "examples", "group_comparison_test_data")
man = json.load(open(os.path.join(gcdir, "manifest.json")))
for d in man["datasets"]:
    path = os.path.join(ROOT, d["file"]); f = os.path.basename(path)
    df = pd.read_csv(path)
    cols = list(d["columns"]); x = cols[0]
    y = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])][-1]
    hue = next((c for c in cols if c not in (x, y)), None) if d.get("subgroups") else None
    base = {"x": x, "y": y, **({"hue": hue} if hue else {})}
    for kind in ["box", "violin", "box+violin", "summary"]:
        for orient in ["vertical", "horizontal"]:
            for arr in ["jitter", "centered", "beeswarm"]:
                spec = registry.make_spec("boxplot_or_violin_with_points", f, "publication",
                                          mapping={**base, "kind": kind, "orientation": orient, "points": True,
                                                   "arrangement": arr, "show_n": "below"},
                                          statistics={"enabled": True})
                run(f"gc:{f}|boxviolin|{kind}|{orient}|{arr}", spec, df, None)
    for orient in ["vertical", "horizontal"]:
        for summ, err in [("mean", "sem"), ("mean", "sd"), ("mean", "ci95_t"), ("median", "iqr")]:
            spec = registry.make_spec("barplot_with_error_bar", f, "publication",
                                      mapping={**base, "summary": summ, "error": err, "points": True,
                                               "orientation": orient, "show_n": "below"},
                                      statistics={"enabled": True})
            run(f"gc:{f}|bar|{summ}|{err}|{orient}", spec, df, None)

try:
    import adjustText as _adj; _adj_v = getattr(_adj, "__version__", "?")
except Exception:  # pragma: no cover
    _adj_v = "absent"
json.dump({"matplotlib": matplotlib.__version__, "numpy": np.__version__, "pandas": pd.__version__,
           "adjustText": _adj_v, "results": results}, open(OUT, "w"), indent=0)
n_fail = sum(1 for v in results.values() if not v["ok"])
print(f"mpl {matplotlib.__version__}: {len(results)} renders, {n_fail} failed")
for k, v in results.items():
    if not v["ok"]: print("  FAIL", k, "->", v["error"])
