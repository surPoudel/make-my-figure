"""Scaffold a new plot type from the templates and print the exact integration checklist.

    python .agents/makemyfigure-developer/scripts/scaffold_plot.py dumbbell_plot \
        --display "Dumbbell plot (paired change)" --module dumbbell --roles x,y,group --slug dumbbell

Creates (never overwrites): make_my_figure_core/plots/<module>.py, tests/test_<module>.py,
.agents/makemyfigure-developer/inventory/scaffold_<plot_type>.md (the checklist + snippets for
the example builder and the manual section). With --wire it also appends the registry entries
(import, _RENDERERS, _DEFAULT_MAPPINGS, _DISPLAY_NAMES) and the ui_hints COLUMN_FIELDS/OPTIONS
rows by text insertion before the closing brace of each table; review the diff afterwards.
Everything else (example builder, capabilities, catalogue dicts, docs, recommendations) is
listed with file paths for the developer to edit by hand, because those need judgement.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

TPL = os.path.join(C.AGENT_DIR, "templates")


def _fill(text: str, subs: dict) -> str:
    for k, v in subs.items():
        text = text.replace(f"__{k}__", v)
    return text


def _write_new(path: str, content: str) -> str:
    if os.path.exists(path):
        return f"exists, left untouched: {os.path.relpath(path, C.ROOT)}"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return f"created: {os.path.relpath(path, C.ROOT)}"


def _insert_before_table_close(src: str, table_name: str, line: str) -> str:
    """Insert ``line`` before the ``}`` that closes the dict literal ``table_name = {``."""
    m = re.search(rf"^{re.escape(table_name)}\b[^\n]*=\s*\{{", src, re.M)
    if not m:
        raise SystemExit(f"table {table_name} not found")
    i = m.end(); depth = 1
    while depth and i < len(src):
        ch = src[i]
        depth += ch == "{"
        depth -= ch == "}"
        i += 1
    close = i - 1
    # back up to the start of the closing line
    ls = src.rfind("\n", 0, close) + 1
    return src[:ls] + line + "\n" + src[ls:]


def wire(plot_type: str, module: str, display: str, roles: list) -> list:
    notes = []
    reg_path = os.path.join(C.ROOT, "make_my_figure_core", "plots", "registry.py")
    src = open(reg_path, encoding="utf-8").read()
    if f"{module}.PLOT_TYPE" in src:
        notes.append("registry: already wired")
    else:
        src = re.sub(r"(from make_my_figure_core\.plots import \()", rf"\1\n    {module},", src, count=1)
        src = _insert_before_table_close(src, "_RENDERERS", f"    {module}.PLOT_TYPE: {module}.render,")
        mapping = ", ".join(f'"{r}": "{r}"' for r in roles)
        src = _insert_before_table_close(src, "_DEFAULT_MAPPINGS", f"    {module}.PLOT_TYPE: {{{mapping}}},")
        src = _insert_before_table_close(src, "_DISPLAY_NAMES", f'    {module}.PLOT_TYPE: "{display}",')
        open(reg_path, "w", encoding="utf-8").write(src)
        notes.append("registry: import + _RENDERERS + _DEFAULT_MAPPINGS + _DISPLAY_NAMES appended (fix the default column names!)")
    ui_path = os.path.join(C.ROOT, "make_my_figure_core", "ui_hints.py")
    ui = open(ui_path, encoding="utf-8").read()
    if f'"{plot_type}"' in ui:
        notes.append("ui_hints: already declared")
    else:
        ui = _insert_before_table_close(ui, "COLUMN_FIELDS", f'    "{plot_type}": {list(roles)!r},'.replace("'", '"'))
        ui = _insert_before_table_close(ui, "OPTIONS", f'    "{plot_type}": [_X_TICK_ROTATION],  # add this plot\'s Option(...) entries with explicit scope=')
        open(ui_path, "w", encoding="utf-8").write(ui)
        notes.append("ui_hints: COLUMN_FIELDS + OPTIONS rows appended (add the plot's real Option entries, each with scope=)")
    m = re.search(r"^OPTIONS\b[^\n]*=\s*\{(.*?)^\}", ui, re.M | re.S)          # scan the OPTIONS body only
    body = m.group(1) if m else ""
    keys = re.findall(r'^\s{4}"([a-z_0-9]+)":\s*\[', body, re.M)
    dup = sorted({k for k in keys if keys.count(k) > 1})
    if dup:
        notes.append(f"WARNING ui_hints.OPTIONS has duplicate keys (later wins): {sorted(set(dup))}; do not add a second entry for a key")
    return notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plot_type", help="registry key, snake_case, e.g. dumbbell_plot")
    ap.add_argument("--display", required=True, help="human name shown in the UI")
    ap.add_argument("--module", help="renderer module name (default: plot_type without _plot)")
    ap.add_argument("--roles", default="x,y", help="comma-separated column roles (required first)")
    ap.add_argument("--slug", help="example folder slug (default: module)")
    ap.add_argument("--purpose", default="TODO one-line purpose", help="one-line scientific purpose")
    ap.add_argument("--wire", action="store_true", help="also append registry + ui_hints entries")
    a = ap.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9_]+", a.plot_type):
        ap.error("plot_type must be snake_case")
    if a.plot_type in C.plot_types():
        raise SystemExit(f"{a.plot_type} is already registered; extend it instead of scaffolding.")
    module = a.module or re.sub(r"_plot$", "", a.plot_type)
    slug = a.slug or module
    roles = [r.strip() for r in a.roles.split(",") if r.strip()]
    subs = {"PLOT_TYPE": a.plot_type, "DISPLAY_NAME": a.display, "SLUG": slug, "SHEET": slug[:31].title(),
            "ONE_LINE_PURPOSE": a.purpose, "WHAT_THE_PLOT_ANSWERS": "TODO", "UNIT_OF_OBSERVATION": "observation",
            "REQUIRED_ROLES": ", ".join(f"`{r}`" for r in roles[:2]), "OPTIONAL_ROLES": ", ".join(f"`{r}`" for r in roles[2:]) or "none",
            "OPTIONS_TABLE": "TODO", "STATISTICS_SENTENCE": "TODO"}
    out = []
    out.append(_write_new(os.path.join(C.ROOT, "make_my_figure_core", "plots", f"{module}.py"),
                          _fill(open(os.path.join(TPL, "renderer_template.py"), encoding="utf-8").read(), subs)))
    out.append(_write_new(os.path.join(C.ROOT, "tests", f"test_{a.plot_type}.py"),
                          _fill(open(os.path.join(TPL, "test_template.py"), encoding="utf-8").read(), subs)))
    checklist = f"""# Scaffold checklist for `{a.plot_type}` ({a.display})

Generated by scaffold_plot.py. Tick every line; `validate_plot_integration.py {a.plot_type}` checks most of them.

## Code
- [ ] `make_my_figure_core/plots/{module}.py`: replace the TODO marks with the plot's geometry; keep the contract.
- [ ] `make_my_figure_core/plots/registry.py`: import, `_RENDERERS`, `_DEFAULT_MAPPINGS` (must name the EXAMPLE's columns), `_DISPLAY_NAMES`.
- [ ] `make_my_figure_core/ui_hints.py`: `COLUMN_FIELDS["{a.plot_type}"]` (roles in UI order) and `OPTIONS["{a.plot_type}"]` (each with scope style|config).
- [ ] `make_my_figure_core/styles/capabilities.py`: ALWAYS regenerate after adding a renderer: `python scripts/audit_style_capabilities.py --write` (tests/test_style_capabilities_audit.py fails on drift); hand-edit only if the audited flags are wrong.
- [ ] statistics (StatsSpec = the plain dict `spec["statistics"]`, statistics/schemas.py): if scientifically relevant call `stats_integration.run_and_annotate` AFTER `fig.tight_layout()`; add a `resolve_columns` branch in statistics/runner.py when the roles differ in meaning from bar/box (every x-numeric plot does) and a `recommend_tests` branch in statistics/test_registry.py.
- [ ] recommendations: add an advisory rule in `make_my_figure_core/recommendations/plot_recommender.py` ONLY with an explicit data-shape justification; add a false-positive test.

## Example data (offline, deterministic)
- [ ] `scripts/generate_example_data.py`: add builder `b_{slug}` and an `Example(...)` entry (snippet below), then run
      `python .agents/makemyfigure-developer/scripts/generate_example.py {a.plot_type}`.

## Tests
- [ ] `tests/test_{a.plot_type}.py`: adapt role names and options; add statistics tests if used.
- [ ] bump the tests that pin the plot count (`inspect_registry.py` lists them, e.g. tests/test_renderers_m2.py, tests/test_desktop_controller.py).
- [ ] `python .agents/makemyfigure-developer/scripts/run_plot_tests.py {a.plot_type}` (focused + related + registry-wide suites).

## Documentation (generated THROUGH the app, never hand-drawn)
- [ ] `scripts/build_plot_catalog_part.py`: add `PURPOSE["{a.plot_type}"]`, `LIMITS["{a.plot_type}"]` and, if statistics, `STATS_PLOTS["{a.plot_type}"]`.
- [ ] catalogue figure: `python .agents/makemyfigure-developer/scripts/render_plot_matrix.py {a.plot_type} --catalog-figure` writes `docs/manuals/assets/figures/{a.plot_type}.png` through the app.
- [ ] rebuild: `python scripts/build_plot_catalog_part.py` then `python scripts/build_manuals.py`; update the plot count in `scripts/build_manual_diagrams.py` (label text) and rerun it; `docs/manuals/audit/current_capabilities.md`; README badge + "N plot types" line.
- [ ] preset QC matrix: `python scripts/build_figure_preset_qc.py` regenerates `reports/figure_preset_qc/all_plot_preset_matrix.csv` (tests/test_figure_preset_qc.py requires a PASS row for every registered plot).
- [ ] Quick Start: mention only if the plot changes a common workflow. CHANGELOG.md `## Unreleased`: one entry.
- [ ] `python .agents/makemyfigure-developer/scripts/render_plot_matrix.py {a.plot_type}` and LOOK at the sheet.

## Gate
- [ ] `validate_plot_integration.py {a.plot_type}` all PASS; `audit_roundtrip.py {a.plot_type}` all PASS; full suite; local build; STOP: READY FOR AUTHOR TESTING.

## Snippets
```python
{_fill(open(os.path.join(TPL, "example_template.py"), encoding="utf-8").read(), subs)}
```

```markdown
{_fill(open(os.path.join(TPL, "manual_template.md"), encoding="utf-8").read(), subs)}
```
"""
    out.append(_write_new(os.path.join(C.AGENT_DIR, "inventory", f"scaffold_{a.plot_type}.md"), checklist))
    if a.wire:
        out += wire(a.plot_type, module, a.display, roles)
    print("\n".join(out))
    print(f"\nNext: edit the renderer, then `python .agents/makemyfigure-developer/scripts/validate_plot_integration.py {a.plot_type}`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
