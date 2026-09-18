"""Find the existing renderers and shared components closest to a requested plot.

Offline keyword/role scoring over renderer docstrings, module names, display names, declared
column roles, options and the shared helper modules. Use it in STEP 3 of the new-plot workflow (AGENT.md)
before deciding NEW RENDERER vs EXTENSION.

    python .agents/makemyfigure-developer/scripts/find_related_renderers.py "half violin box jittered points groups"
    python .agents/makemyfigure-developer/scripts/find_related_renderers.py --roles x,y,group --top 8

Role names follow the registry's conventions (references/data-mapping.md): grouped comparisons use
x (categorical) + y (numeric); distribution plots over one numeric variable use x (NUMERIC) + group;
paired/longitudinal designs use subject + condition/time + value. Try the convention of the family.
"""
from __future__ import annotations

import argparse
import inspect
import os
import re
import sys
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

STOP = {"a", "an", "the", "and", "or", "of", "for", "with", "per", "by", "in", "on", "to", "as", "is", "are",
        "one", "two", "each", "at", "from", "that", "this", "its", "it", "be", "plot", "plots", "chart", "graph",
        "figure", "data", "value", "values", "shows", "show", "showing", "drawn", "draw", "draws", "axis", "axes"}

SYNONYMS = {
    "dumbbell": "paired segment connector two conditions before after change item", "connected": "paired segment connector",
    "cleveland": "dot segment category row", "before": "paired condition", "after": "paired condition",
    "pre": "paired condition", "post": "paired condition", "change": "difference",
    "segment": "line interval horizontal estimate", "interval": "ci estimate lower upper", "sorted": "sort order",
    "ecdf": "cumulative distribution step", "cumulative": "cumulative distribution",
    "connector": "line", "lines": "line",
    "boxplot": "box", "boxes": "box", "violins": "violin", "halfviolin": "violin half",
    "jittered": "jitter", "points": "point observations", "dots": "point dot", "strip": "strip dot",
    "swarm": "beeswarm", "bars": "bar", "barplot": "bar", "barchart": "bar", "errorbar": "error",
    "timecourse": "time line", "longitudinal": "time subject", "survival": "survival time event",
    "km": "kaplan meier survival", "heat": "heatmap", "matrix": "heatmap matrix", "cluster": "clustering dendrogram",
    "density": "density ridge kde", "distribution": "distribution histogram density",
    "de": "differential volcano ma", "expression": "expression", "gwas": "manhattan",
    "roc": "roc curve classifier", "pr": "precision recall", "agreement": "bland altman",
    "flow": "sankey alluvial", "set": "upset intersection", "network": "network graph node edge",
    "embedding": "umap tsne embedding", "pca": "pca embedding", "dose": "dose response",
    "forest": "forest estimate ci", "paired": "paired slope subject", "composition": "stacked fraction",
    "correlation": "scatter regression correlation", "regression": "scatter regression",
}

SHARED_COMPONENTS = {
    "make_my_figure_core/plots/base.py": "helpers every renderer uses (mapping, sizing, axes, legend, metadata)",
    "make_my_figure_core/plots/_v04_shared.py": "jitter, ordered_unique, small shared geometry helpers",
    "make_my_figure_core/plots/stats_integration.py": "run statistics through StatsSpec and annotate brackets",
    "make_my_figure_core/plots/stats_overlay.py": "bracket / above-bar / corner-panel annotation geometry",
    "make_my_figure_core/plots/label_policy.py": "label thinning and placement policy",
    "make_my_figure_core/plots/annotation_state.py": "annotation state carried between renders",
    "make_my_figure_core/plots/observations.py": "shared observations engine (jitter/centred/beeswarm, adaptive size) - branch feature",
    "make_my_figure_core/plots/_bar_shared.py": "shared bar summary/error/observation drawing - branch feature",
}


def _tokens(text: str) -> List[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_]+", text.lower())
    out: List[str] = []
    for w in words:
        if w in STOP:
            continue
        out.append(w)
        if w in SYNONYMS:
            out += SYNONYMS[w].split()
    return [w for w in out if w not in STOP]


def _corpus() -> Dict[str, Dict[str, str]]:
    reg = C.registry()
    ui = C.optional_import("make_my_figure_core.ui_hints")
    corpus: Dict[str, Dict[str, str]] = {}
    for pt in C.plot_types():
        mod = sys.modules.get(C.renderer_module_for(pt) or "")
        doc = (inspect.getdoc(mod) or "") if mod else ""
        roles = " ".join(ui.column_fields(pt)) if ui else ""
        opts = " ".join(o.key + " " + o.label for o in ui.options(pt)) if ui else ""
        mapping = " ".join(f"{k} {v}" for k, v in reg.default_mapping(pt).items())
        corpus[pt] = {"name": reg.display_name(pt), "doc": doc, "roles": roles, "options": opts,
                      "mapping": mapping, "path": C.renderer_path_for(pt) or ""}
    return corpus


def score(query: str, roles: List[str], top: int) -> List[Dict[str, object]]:
    q = set(_tokens(query))
    corpus = _corpus()
    rows = []
    for pt, c in corpus.items():
        name_t = set(_tokens(c["name"] + " " + pt))
        doc_t = set(_tokens(c["doc"]))
        opt_t = set(_tokens(c["options"] + " " + c["mapping"]))
        role_set = set(c["roles"].split())
        s = 3.0 * len(q & name_t) + 1.0 * len(q & doc_t) + 0.5 * len(q & opt_t)
        if roles:
            s += 2.0 * len(set(roles) & role_set)           # bonus only: plots with many roles are not penalised
        matched_roles = sorted(set(roles) & role_set)
        rows.append({"plot_type": pt, "score": round(s, 1), "display_name": c["name"], "path": c["path"],
                     "roles": c["roles"], "matched_roles": ",".join(matched_roles) or "-",
                     "matched": ",".join(sorted((q & (name_t | doc_t | opt_t)))[:8])})
    rows.sort(key=lambda r: -float(r["score"]))
    return rows[:top]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", nargs="?", default="", help="free-text description of the requested plot")
    ap.add_argument("--roles", default="", help="comma-separated column roles the plot needs (x,y,group,...)")
    ap.add_argument("--top", type=int, default=6)
    a = ap.parse_args()
    roles = [r.strip() for r in a.roles.split(",") if r.strip()]
    if not a.query and not roles:
        ap.error("give a query and/or --roles")
    rows = score(a.query, roles, a.top)
    print(C.table(rows, ["plot_type", "score", "display_name", "roles", "matched_roles", "path", "matched"]))
    print("\nShared components to reuse before writing new code:")
    for rel, why in SHARED_COMPONENTS.items():
        exists = os.path.exists(os.path.join(C.ROOT, rel))
        print(f"  {'[x]' if exists else '[ ]'} {rel}  -  {why}{'' if exists else '  (not in this checkout)'}")
    print("\nRead the top 2-5 renderers in full, then decide: NEW RENDERER or EXTENSION (see references/new-plot-workflow.md).")
    print("Contract-canonical renderers to copy habits from: make_my_figure_core/plots/barplot.py, box_violin.py "
          "(older renderers may use raw ax.legend or literal colours; copy their science, not those habits).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
