"""Check that a plot type is integrated with every part of the application that exists in this
checkout. Exit code 1 when any REQUIRED check fails.

    python .agents/makemyfigure-developer/scripts/validate_plot_integration.py dumbbell_plot
    python .agents/makemyfigure-developer/scripts/validate_plot_integration.py --all          # every registered plot

Checks (each reports PASS / FAIL / SKIP with a reason; optional components are SKIPped when absent):
registry (renderer, display name, default mapping), ui_hints roles + options with valid scopes,
style capabilities resolve, bundled example loads and renders with the example PlotSpec,
schema validation, JSON round trip re-renders to identical metadata, scientific freeze (input
table unchanged by rendering), export to svg/png/pdf, style preset extract -> apply -> render
leaves data/statistics identical, Figure Builder panel builds, Figure Package round trip (if the
package module exists), statistics engine used when a statistics block is honoured, focused tests
exist, manual catalogue dictionaries have entries, docs mention the plot, CHANGELOG mentions it
(advisory), recommendation rules mention it (informational only).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import tempfile
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

REQUIRED = {"registry", "display_name", "default_mapping", "ui_roles", "ui_options", "capabilities", "example", "figure_package",
            "catalog_figure", "preset_qc_row",
            "render", "schema", "plotspec_roundtrip", "scientific_freeze", "export", "preset_style_safe",
            "builder_panel", "tests_exist", "catalog_purpose", "docs_mention"}


def _digest(df) -> str:
    import pandas as pd
    return hashlib.sha256(pd.util.hash_pandas_object(df, index=True).to_numpy().tobytes()).hexdigest()


def _meta_key(result) -> str:
    return json.dumps(result.metadata, sort_keys=True, default=str)


PRESENTATION_META = {"spec", "export_dimensions", "style_profile", "layout_qc", "publication_check", "disclaimer",
                     "components", "annotation", "figure_size_in", "style"}


def _style_option_keys(plot_type: str) -> set:
    ui = C.optional_import("make_my_figure_core.ui_hints")
    return {o.key for o in ui.options(plot_type) if getattr(o, "scope", "config") == "style"} if ui else set()


def _sci_key(result, plot_type: str) -> str:
    """Scientific content of a render: analytical parts of the spec (roles, config options, test
    choice), data-derived metadata (n, groups, columns used) and statistics results. Presentation
    (style tokens, style-scoped options, annotation geometry, export size, QC scores) is excluded."""
    meta = copy.deepcopy(result.metadata or {})
    spec = meta.get("spec") or {}
    style_opts = _style_option_keys(plot_type)
    analytical = {
        "plot_type": spec.get("plot_type"), "input_table": spec.get("input_table"),
        "mapping": {k: v for k, v in (spec.get("mapping") or {}).items() if k not in style_opts},
        "statistics": {k: v for k, v in (spec.get("statistics") or {}).items() if k != "annotation"},
        "aux_tables": spec.get("aux_tables"),
    }
    data_meta = {k: v for k, v in meta.items() if k not in PRESENTATION_META}
    if isinstance(data_meta.get("statistics"), dict):
        data_meta["statistics"] = {k: v for k, v in data_meta["statistics"].items() if k != "annotation"}
    rep = getattr(result, "stats_report", None)
    stats = None
    if rep is not None:
        d = rep.to_dict() if hasattr(rep, "to_dict") else getattr(rep, "__dict__", str(rep))
        stats = json.loads(json.dumps(d, default=str))
        if isinstance(stats, dict):
            stats.pop("config", None)                    # annotation geometry/style lives here
    return json.dumps({"analytical": analytical, "meta": data_meta, "stats": stats}, sort_keys=True, default=str)


def check(plot_type: str) -> List[Dict[str, Any]]:
    import matplotlib.pyplot as plt
    rows: List[Dict[str, Any]] = []

    def add(name, status, note=""):
        rows.append({"check": name, "status": status, "note": str(note)[:160]})

    reg = C.registry()
    if plot_type not in reg.available_plot_types():
        add("registry", "FAIL", "not in available_plot_types()"); return rows
    add("registry", "PASS", C.renderer_path_for(plot_type))
    add("display_name", "PASS" if reg.display_name(plot_type) != plot_type else "FAIL", reg.display_name(plot_type))
    dm = reg.default_mapping(plot_type)
    add("default_mapping", "PASS" if dm else "FAIL", ", ".join(f"{k}={v}" for k, v in list(dm.items())[:5]))

    ui = C.optional_import("make_my_figure_core.ui_hints")
    if ui:
        roles = ui.column_fields(plot_type)
        add("ui_roles", "PASS" if roles else "FAIL", ",".join(roles) or "COLUMN_FIELDS has no entry")
        opts = ui.options(plot_type)
        bad = [o.key for o in opts if getattr(o, "scope", "config") not in ("style", "config")]
        add("ui_options", "FAIL" if bad else "PASS", f"{len(opts)} option(s)" + (f"; bad scope: {bad}" if bad else ""))
        mapped_roles = [r for r in roles if r in dm]
        if roles and not mapped_roles:
            add("roles_in_default_mapping", "FAIL", "no declared role appears in the default mapping")
    else:
        add("ui_roles", "SKIP", "ui_hints absent"); add("ui_options", "SKIP", "ui_hints absent")

    caps = C.optional_import("make_my_figure_core.styles.capabilities")
    if caps:
        c = caps.get_style_capabilities(plot_type)
        add("capabilities", "PASS", "explicit" if f'"{plot_type}"' in open(caps.__file__, encoding="utf-8").read() else "defaults")
    else:
        add("capabilities", "SKIP", "capabilities module absent")

    ex = C.optional_import("make_my_figure_core.examples")
    if not ex or not ex.has_example(plot_type):
        add("example", "FAIL", "no bundled example (scripts/generate_example_data.py)"); return rows
    info, aux_t, spec = ex.load_example(plot_type)
    df = info.dataframe; aux = {k: v.dataframe for k, v in aux_t.items()} or None
    add("example", "PASS", f"{ex.entry(plot_type)['files']['csv']} ({len(df)} rows)")

    d0 = _digest(df)
    try:
        r1 = reg.render(spec, df, aux=aux)
        add("render", "PASS", f"{len(r1.figure.axes)} axes; {len(r1.warnings)} warning(s)")
    except Exception as e:  # noqa: BLE001
        add("render", "FAIL", f"{type(e).__name__}: {e}"); return rows
    add("scientific_freeze", "PASS" if _digest(df) == d0 else "FAIL", "input table unchanged by render")

    try:
        from make_my_figure_core.spec.validate import validate_plot_spec
        validate_plot_spec(spec); add("schema", "PASS")
    except Exception as e:  # noqa: BLE001
        add("schema", "FAIL", f"{type(e).__name__}: {e}")

    spec2 = json.loads(json.dumps(spec))
    r2 = reg.render(spec2, df, aux=aux)
    add("plotspec_roundtrip", "PASS" if _meta_key(r1) == _meta_key(r2) else "FAIL", "metadata identical after JSON round trip")

    with tempfile.TemporaryDirectory() as td:
        try:
            for fmt in ("svg", "png", "pdf"):
                data = reg.figure_to_bytes(r1.figure, fmt, dpi=150)
                open(os.path.join(td, f"f.{fmt}"), "wb").write(data)
            sizes = {f: os.path.getsize(os.path.join(td, f"f.{f}")) for f in ("svg", "png", "pdf")}
            add("export", "PASS" if all(v > 500 for v in sizes.values()) else "FAIL", str(sizes))
        except Exception as e:  # noqa: BLE001
            add("export", "FAIL", f"{type(e).__name__}: {e}")

    presets = C.optional_import("make_my_figure_core.presets")
    if presets:
        try:
            demanding = copy.deepcopy(spec)
            demanding.setdefault("style", {}).update({"base_font_pt": 6.0, "palette_name": "colorblind", "marker_size": 12})
            preset = presets.extract_preset(demanding, mode="style", name="validator")
            presets.validate_preset(preset)
            res = presets.apply_preset(preset, spec, columns=list(df.columns))
            r3 = reg.render(res.spec, df, aux=aux)
            add("preset_style_safe", "PASS" if _sci_key(r1, plot_type) == _sci_key(r3, plot_type) else "FAIL",
                "style preset changes no scientific metadata/statistics")
        except Exception as e:  # noqa: BLE001
            add("preset_style_safe", "FAIL", f"{type(e).__name__}: {e}")
    else:
        add("preset_style_safe", "SKIP", "presets module absent")

    panels = C.optional_import("make_my_figure_core.panels.builder")
    models = C.optional_import("make_my_figure_core.panels.models")
    if panels and models:
        try:
            p = models.Panel(label="A", plot_spec=spec, table=df, aux=aux or {}, source_name=info.source_name)
            mpf = models.MultiPanelFigure(name="validator", panels=[p])
            fig = panels.build_figure(mpf)
            add("builder_panel", "PASS" if fig.axes else "FAIL", f"{len(fig.axes)} axes in composite")
            plt.close(fig)
        except Exception as e:  # noqa: BLE001
            add("builder_panel", "FAIL", f"{type(e).__name__}: {e}")
    else:
        add("builder_panel", "SKIP", "panels module absent")

    pkg = C.optional_import("make_my_figure_core.package")
    if pkg and all(hasattr(pkg, n) for n in ("content_for_single_plot", "write_figure_package", "open_figure_package", "single_plot_inputs")):
        try:
            with tempfile.TemporaryDirectory() as td:
                content = pkg.content_for_single_plot(spec, df, r1, table_name=spec["input_table"], aux=aux, name="validator")
                rep = pkg.write_figure_package(content, os.path.join(td, "validator"))
                opened = pkg.open_figure_package(rep.path)
                spec_r, df_r, aux_r = pkg.single_plot_inputs(opened)
                r4 = reg.render(spec_r, df_r, aux=aux_r or None)
                same = _sci_key(r1, plot_type) == _sci_key(r4, plot_type) and df_r.shape == df.shape
                add("figure_package", "PASS" if same else "FAIL",
                    f"integrity={opened.integrity}; reopened table {df_r.shape}; scientific content identical={same}")
        except Exception as e:  # noqa: BLE001
            add("figure_package", "FAIL", f"{type(e).__name__}: {e}")
    else:
        add("figure_package", "SKIP", "Figure Package not in this checkout")

    src = open(os.path.join(C.ROOT, C.renderer_path_for(plot_type)), encoding="utf-8").read()
    uses_stats = "run_and_annotate" in src or "run_statistics" in src
    add("statistics_engine", "PASS" if uses_stats else "SKIP",
        "renderer uses the shared statistics engine" if uses_stats else "no statistics (fine if not scientifically relevant)")
    import re as _re
    inferential = _re.findall(r"\b(ttest_\w+|mannwhitneyu|kruskal|f_oneway|wilcoxon|chi2_contingency|fisher_exact|pearsonr|spearmanr|linregress|logrank\w*)\b", src)
    if inferential and not uses_stats:
        add("statistics_engine", "WARN", f"renderer calls {sorted(set(inferential))} directly; inferential tests belong in StatsSpec "
            "(scatter's fit-statistics box is the documented exception, see references/statistics.md)")

    tests = C.grep_files(plot_type, ["tests"], exts=(".py",))
    wide = set(C.grep_files("available_plot_types()", ["tests"], exts=(".py",)))
    named_only = [t for t in tests if t not in wide]
    add("tests_exist", "PASS" if tests else "FAIL",
        f"{len(tests)} test module(s) name it ({len(named_only)} dedicated, {len(tests) - len(named_only)} also enumerate all types)")

    cat = os.path.join(C.ROOT, "scripts", "build_plot_catalog_part.py")
    if os.path.exists(cat):
        cs = open(cat, encoding="utf-8").read()

        def _in_dict(name: str) -> bool:
            m = re.search(rf"^{name}\s*=\s*\{{(.*?)^\}}", cs, re.M | re.S)
            return bool(m and f'"{plot_type}"' in m.group(1))
        add("catalog_purpose", "PASS" if _in_dict("PURPOSE") else "FAIL", "PURPOSE entry in scripts/build_plot_catalog_part.py")
        if uses_stats:
            add("catalog_stats_text", "PASS" if _in_dict("STATS_PLOTS") else "WARN", "STATS_PLOTS entry (renderer uses statistics)")
        add("catalog_limits", "PASS" if _in_dict("LIMITS") else "INFO", "LIMITS entry (optional)")
    else:
        add("catalog_purpose", "SKIP", "catalogue builder absent")
    fig_dir = os.path.join(C.ROOT, "docs", "manuals", "assets", "figures")
    if os.path.isdir(fig_dir):
        png = os.path.join(fig_dir, f"{plot_type}.png")
        add("catalog_figure", "PASS" if os.path.exists(png) else "FAIL",
            os.path.relpath(png, C.ROOT) + ("" if os.path.exists(png) else "  (render_plot_matrix.py <pt> --catalog-figure)"))
    qc_csv = os.path.join(C.ROOT, "reports", "figure_preset_qc", "all_plot_preset_matrix.csv")
    if os.path.exists(qc_csv):
        import csv as _csv
        with open(qc_csv, newline="", encoding="utf-8") as fh:
            row = next((r for r in _csv.DictReader(fh) if r.get("plot_type") == plot_type), None)
        add("preset_qc_row", "PASS" if row and row.get("status") == "PASS" else "FAIL",
            (f"status {row.get('status')}" if row else "no row") + "  (regenerate: python scripts/build_figure_preset_qc.py; tests/test_figure_preset_qc.py requires it)")
    docs = C.grep_files(plot_type, ["docs"], exts=(".md",))
    add("docs_mention", "PASS" if docs else "FAIL", f"{len(docs)} doc file(s)")
    chg = open(os.path.join(C.ROOT, "CHANGELOG.md"), encoding="utf-8").read() if os.path.exists(os.path.join(C.ROOT, "CHANGELOG.md")) else ""
    add("changelog_mention", "PASS" if plot_type in chg or reg.display_name(plot_type) in chg else "WARN", "advisory")
    rec = C.grep_files(plot_type, ["make_my_figure_core/recommendations"], exts=(".py",))
    add("recommendation_rule", "INFO", "has rule(s)" if rec else "no rule (only add one with an explicit data-shape justification)")
    plt.close("all")
    return rows


def repo_level_rows() -> List[Dict[str, Any]]:
    """Checks that concern the whole registry, printed once."""
    import re as _re
    rows = []
    n = len(C.plot_types())
    stale, ok = [], []
    for rel in C.grep_files("plot_types()", ["tests"], exts=(".py",)):
        for i, line in enumerate(open(os.path.join(C.ROOT, rel), encoding="utf-8"), 1):
            m = _re.search(r"plot_types\(\)\)\s*==\s*(\d+)", line)
            if m:
                (ok if int(m.group(1)) == n else stale).append(f"{rel}:{i} ({m.group(1)})")
    rows.append({"check": "tests_pin_plot_count", "status": "FAIL" if stale else "PASS",
                 "note": (f"registry has {n}; stale: " + ", ".join(stale)) if stale else
                         (f"{len(ok)} test(s) pin {n}; bump them when adding a plot: " + ", ".join(ok) if ok else "none")})
    for rel, label in (("README.md", "README"), ("scripts/build_manual_diagrams.py", "manual diagram")):
        path = os.path.join(C.ROOT, rel)
        if os.path.exists(path):
            nums = {int(x) for x in _re.findall(r"(\d+)\s*(?:plot\s*types|types\)|renderers)", open(path, encoding="utf-8").read()) }
            nums |= {int(x) for x in _re.findall(r"plot%20types-(\d+)", open(path, encoding="utf-8").read())}
            bad = sorted(x for x in nums if x != n and 10 <= x <= 500)
            rows.append({"check": f"{label}_plot_count", "status": "WARN" if bad else "PASS",
                         "note": f"mentions {bad} but registry has {n}" if bad else f"counts agree with {n}"})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plot_type", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    pts = C.plot_types() if a.all else ([a.plot_type] if a.plot_type else [])
    if not pts:
        ap.error("give a plot type or --all")
    exit_code = 0
    all_rows = {"_repo": repo_level_rows()}
    if not a.json:
        print("## repository-level\n" + C.table(all_rows["_repo"], ["check", "status", "note"]))
    for pt in pts:
        rows = check(pt)
        all_rows[pt] = rows
        fails = [r for r in rows if r["status"] == "FAIL" and r["check"] in REQUIRED]
        if fails:
            exit_code = 1
        if not a.json:
            print(f"\n## {pt}  ->  {'FAIL' if fails else 'PASS'} ({len(fails)} required failure(s))")
            print(C.table(rows, ["check", "status", "note"]))
    if a.json:
        print(json.dumps(all_rows, indent=1))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
