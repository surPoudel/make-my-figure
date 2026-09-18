"""Machine-readable inventory of every registered plot type in THIS checkout.

Run this first in every development task; never trust a remembered plot count.

    python .agents/makemyfigure-developer/scripts/inspect_registry.py            # summary table
    python .agents/makemyfigure-developer/scripts/inspect_registry.py --json     # full JSON to stdout
    python .agents/makemyfigure-developer/scripts/inspect_registry.py --write    # writes inventory/plot_inventory.{json,md}
    python .agents/makemyfigure-developer/scripts/inspect_registry.py --plot raincloud_plot

For each plot type: display name, renderer module/path, default mapping (column roles and
option defaults), declared column roles (ui_hints), options (key/kind/scope/default), style
capabilities, statistics support (renderer uses the shared statistics integration), bundled
example (files, aux tables), tests / docs / recommendation rules / manual catalogue that mention
it, and preset-QC status when a report exists. Also reports which optional components exist.
"""
from __future__ import annotations

import argparse
import csv
import inspect
import json
import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402


def _stats_support(plot_type: str) -> Dict[str, Any]:
    mod = C.renderer_module_for(plot_type)
    if not mod:
        return {"uses_statistics_engine": False}
    try:
        src = inspect.getsource(sys.modules[mod])
    except Exception:  # noqa: BLE001
        return {"uses_statistics_engine": False}
    return {
        "uses_statistics_engine": ("stats_integration" in src or "run_and_annotate" in src
                                   or "run_statistics" in src),
        "draws_brackets": "annotate_pairwise" in src or "run_and_annotate" in src,
        "corner_panel": "annotate_corner" in src or 'mode="corner"' in src,
    }


def _options(plot_type: str) -> List[Dict[str, Any]]:
    ui = C.optional_import("make_my_figure_core.ui_hints")
    if not ui:
        return []
    out = []
    for o in ui.options(plot_type):
        out.append({"key": o.key, "label": o.label, "kind": o.kind, "default": o.default,
                    "choices": o.choices, "scope": getattr(o, "scope", None)})
    return out


def _capabilities(plot_type: str) -> Dict[str, Any]:
    caps = C.optional_import("make_my_figure_core.styles.capabilities")
    if not caps:
        return {}
    c = caps.get_style_capabilities(plot_type)
    d = {k: v for k, v in vars(c).items() if k.startswith("supports_")}
    d["explicitly_declared"] = plot_type in getattr(caps, "_CAPABILITIES", {}) or \
        plot_type in getattr(caps, "CAPABILITIES", {}) or _declared_in_source(caps, plot_type)
    return d


def _declared_in_source(module, plot_type: str) -> bool:
    try:
        return f'"{plot_type}"' in inspect.getsource(module)
    except Exception:  # noqa: BLE001
        return False


def _example(plot_type: str) -> Dict[str, Any]:
    ex = C.optional_import("make_my_figure_core.examples")
    if not ex or not ex.has_example(plot_type):
        return {"present": False}
    e = ex.entry(plot_type)
    return {"present": True, "slug": e.get("slug"), "files": e.get("files", {}),
            "aux_tables": e.get("aux_tables", {}), "required_columns": e.get("required_columns"),
            "optional_columns": e.get("optional_columns"), "n_rows": e.get("n_rows")}


def _preset_qc(plot_type: str) -> Dict[str, Any]:
    path = os.path.join(C.ROOT, "reports", "figure_preset_qc", "all_plot_preset_matrix.csv")
    if not os.path.exists(path):
        return {"report": None}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("plot_type") == plot_type:
                return {"report": os.path.relpath(path, C.ROOT), "status": row.get("status"),
                        "notes": row.get("notes", "")[:200]}
    return {"report": os.path.relpath(path, C.ROOT), "status": "missing row"}


def inventory_for(plot_type: str) -> Dict[str, Any]:
    reg = C.registry()
    ui = C.optional_import("make_my_figure_core.ui_hints")
    mentions = {
        "tests": C.grep_files(plot_type, ["tests"]),
        "docs": C.grep_files(plot_type, ["docs"], exts=(".md",)),
        "recommendations": C.grep_files(plot_type, ["make_my_figure_core/recommendations"]),
        "manual_catalog_builder": C.grep_files(plot_type, ["scripts/build_plot_catalog_part.py"]),
        "example_generator": C.grep_files(plot_type, ["scripts/generate_example_data.py"]),
        "ui_hints": C.grep_files(plot_type, ["make_my_figure_core/ui_hints.py"]),
        "capabilities": C.grep_files(plot_type, ["make_my_figure_core/styles/capabilities.py"]),
        "frontends": C.grep_files(plot_type, ["apps"]),
    }
    return {
        "plot_type": plot_type,
        "display_name": reg.display_name(plot_type),
        "renderer_module": C.renderer_module_for(plot_type),
        "renderer_path": C.renderer_path_for(plot_type),
        "default_mapping": reg.default_mapping(plot_type),
        "column_roles": list(ui.column_fields(plot_type)) if ui else [],
        "options": _options(plot_type),
        "style_capabilities": _capabilities(plot_type),
        "statistics": _stats_support(plot_type),
        "example": _example(plot_type),
        "preset_qc": _preset_qc(plot_type),
        "mentions": mentions,
    }


def _pinned_counts() -> List[str]:
    """tests that assert an exact plot count; they must be bumped when a plot type is added."""
    import re
    out = []
    for rel in C.grep_files("plot_types()", ["tests"], exts=(".py",)):
        for i, line in enumerate(open(os.path.join(C.ROOT, rel), encoding="utf-8"), 1):
            if re.search(r"plot_types\(\)\)\s*==\s*\d+", line):
                out.append(f"{rel}:{i}: {line.strip()}")
    return out


def build_inventory() -> Dict[str, Any]:
    pts = C.plot_types()
    return {
        "checkout": C.ROOT,
        "branch": C.git("rev-parse", "--abbrev-ref", "HEAD"),
        "commit": C.git("rev-parse", "--short", "HEAD"),
        "app_version": C.version(),
        "plot_count": len(pts),
        "features": C.features(),
        "tests_pinning_plot_count": _pinned_counts(),
        "plots": [inventory_for(p) for p in pts],
    }


def summary_rows(inv: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for p in inv["plots"]:
        rows.append({
            "plot_type": p["plot_type"],
            "renderer": os.path.basename(p["renderer_path"] or "?"),
            "roles": ",".join(p["column_roles"]) or "-",
            "options": len(p["options"]),
            "stats": "yes" if p["statistics"].get("uses_statistics_engine") else "no",
            "example": "yes" if p["example"]["present"] else "NO",
            "tests": len(p["mentions"]["tests"]),
            "docs": len(p["mentions"]["docs"]),
            "catalog": "yes" if p["mentions"]["manual_catalog_builder"] else "NO",
            "preset_qc": p["preset_qc"].get("status") or "-",
        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="print the full inventory as JSON")
    ap.add_argument("--write", action="store_true", help="write inventory/plot_inventory.json and .md")
    ap.add_argument("--plot", help="only this plot type (JSON)")
    a = ap.parse_args()
    if a.plot:
        if a.plot not in C.plot_types():
            print(f"{a.plot!r} is not registered. Registered: {', '.join(C.plot_types())}")
            return 2
        print(json.dumps(inventory_for(a.plot), indent=1, default=str))
        return 0
    inv = build_inventory()
    if a.json:
        print(json.dumps(inv, indent=1, default=str))
        return 0
    rows = summary_rows(inv)
    head = (f"MakeMyFigure {inv['app_version']} @ {inv['branch']} {inv['commit']}: "
            f"{inv['plot_count']} registered plot types\n"
            f"features: {', '.join(k for k, v in inv['features'].items() if v)}\n"
            f"absent:   {', '.join(k for k, v in inv['features'].items() if not v) or 'none'}\n"
            + ("tests pinning the plot count (bump when adding a plot): " + "; ".join(inv["tests_pinning_plot_count"]) + "\n"
               if inv["tests_pinning_plot_count"] else ""))
    md = head + "\n" + C.table(rows, list(rows[0].keys())) if rows else head
    print(md)
    if a.write:
        C.dump_json(inv, os.path.join(C.AGENT_DIR, "inventory", "plot_inventory.json"))
        with open(os.path.join(C.AGENT_DIR, "inventory", "plot_inventory.md"), "w", encoding="utf-8") as fh:
            fh.write("# Plot inventory (generated by scripts/inspect_registry.py; do not edit)\n\n" + md + "\n")
        print(f"\nwritten: {os.path.relpath(os.path.join(C.AGENT_DIR, 'inventory'), C.ROOT)}/plot_inventory.{{json,md}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
