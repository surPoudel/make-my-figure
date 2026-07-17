"""Publication-grade network / interaction graph (v0.5).

Renders a node-link diagram from one of several inputs — an edge list, a square
adjacency matrix, or a correlation/co-expression table — using NetworkX for
graph construction, layout, and metrics, and Matplotlib for vector-safe output.

Supported layouts: spring (force-directed), kamada_kawai, circular, shell,
spectral, multipartite (needs a group/layer column), fixed (x/y columns), and
random (fallback). Layout randomness uses ``mapping['seed']`` so figures are
reproducible.

> A **correlation network** encodes statistical association, NOT a mechanistic
> interaction. This is stated in the figure caption when correlation mode is used.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from make_my_figure_core.clustering import CLUSTER_PALETTE
from make_my_figure_core.plots._v04_shared import numeric_matrix, ordered_unique, pick_column
from make_my_figure_core.plots.base import (
    RenderError,
    RenderResult,
    base_metadata,
    figure_size,
    get_mapping,
    place_legend,
    require_columns,
)
from make_my_figure_core.styles.engine import StyleProfile

PLOT_TYPE = "network_graph"

_LAYOUTS = ("spring", "kamada_kawai", "circular", "shell", "spectral",
            "multipartite", "fixed", "random")
_DENSE_NODES = 300
_DENSE_EDGES = 1500


def _build_edges(spec: Dict[str, Any], df: pd.DataFrame) -> Tuple[pd.DataFrame, str, List[str]]:
    """Return (edge_df with source/target/weight[/sign], mode, warnings)."""
    warnings: List[str] = []
    mode = str(get_mapping(spec, "mode", "edge_list")).lower()

    if mode == "adjacency":
        labels, cols, matrix, w = numeric_matrix(df, get_mapping(spec, "row_id", None),
                                                 context=PLOT_TYPE)
        warnings += w
        # Node names = row labels; columns should align to the same nodes.
        n = min(len(labels), matrix.shape[1])
        min_w = float(get_mapping(spec, "min_weight", 0.0) or 0.0)
        rows = []
        for i in range(n):
            for j in range(i + 1, n):
                wv = matrix[i, j]
                if np.isfinite(wv) and abs(wv) > 0 and abs(wv) >= min_w:
                    rows.append({"source": labels[i], "target": labels[j], "weight": float(wv)})
        edges = pd.DataFrame(rows, columns=["source", "target", "weight"])
        return edges, mode, warnings

    # edge_list or correlation
    src = get_mapping(spec, "source", "source")
    tgt = get_mapping(spec, "target", "target")
    require_columns(df, [src, tgt], context=PLOT_TYPE)
    work = df.copy()
    edges = pd.DataFrame({"source": work[src].astype(str), "target": work[tgt].astype(str)})

    corr_col = get_mapping(spec, "correlation", None) or pick_column(work, ["correlation", "corr", "rho", "r"])
    weight_col = get_mapping(spec, "weight", None) or pick_column(work, ["weight", "score", "combined_score"])
    if mode == "correlation" or corr_col:
        if not corr_col or corr_col not in work.columns:
            raise RenderError(f"{PLOT_TYPE}: correlation mode needs a correlation column.")
        edges["weight"] = pd.to_numeric(work[corr_col], errors="coerce")
        edges["sign"] = np.where(edges["weight"] >= 0, "positive", "negative")
        mode = "correlation"
    elif weight_col and weight_col in work.columns:
        edges["weight"] = pd.to_numeric(work[weight_col], errors="coerce")
    else:
        edges["weight"] = 1.0
    for opt in ("interaction_type", "edge_type", "sign", "group", "pathway"):
        c = get_mapping(spec, opt, None)
        if c and c in work.columns and opt not in edges:
            edges[opt] = work[c].astype(str)
    p_col = get_mapping(spec, "p_value", None) or get_mapping(spec, "adjusted_p_value", None)
    if p_col and p_col in work.columns:
        edges["_p"] = pd.to_numeric(work[p_col], errors="coerce")
    return edges.dropna(subset=["weight"]), mode, warnings


def _filter_edges(spec: Dict[str, Any], edges: pd.DataFrame, mode: str,
                  warnings: List[str]) -> pd.DataFrame:
    e = edges.copy()
    if mode == "correlation":
        cutoff = float(get_mapping(spec, "corr_cutoff", 0.3) or 0.0)
        sign = str(get_mapping(spec, "sign_filter", "both")).lower()
        e = e[e["weight"].abs() >= cutoff]
        if sign == "positive":
            e = e[e["weight"] > 0]
        elif sign == "negative":
            e = e[e["weight"] < 0]
    min_w = get_mapping(spec, "min_weight", None)
    if min_w is not None and "weight" in e:
        e = e[e["weight"].abs() >= float(min_w)]
    p_cut = get_mapping(spec, "p_cutoff", None)
    if p_cut is not None and "_p" in e:
        e = e[e["_p"] <= float(p_cut)]
    top_n = get_mapping(spec, "top_n_edges", None)
    if top_n:
        e = e.reindex(e["weight"].abs().sort_values(ascending=False).index).head(int(top_n))
    return e.reset_index(drop=True)


def _node_table(aux: Optional[Dict[str, Any]]) -> Optional[pd.DataFrame]:
    if not aux:
        return None
    for key in ("nodes", "node_attributes", "node_table"):
        if key in aux and aux[key] is not None:
            return aux[key]
    return None


def render(spec: Dict[str, Any], df, style: StyleProfile, aux=None) -> RenderResult:
    edges, mode, warnings = _build_edges(spec, df)
    edges = _filter_edges(spec, edges, mode, warnings)
    if edges.empty:
        raise RenderError(f"{PLOT_TYPE}: no edges left after filtering — relax thresholds.")

    import networkx as nx

    directed = bool(get_mapping(spec, "directed", False))
    G = nx.DiGraph() if directed else nx.Graph()
    # Carry categorical edge attributes onto the graph so edges can be colored by
    # them (e.g. interaction_type / edge_type / pathway), not just weight/sign.
    _edge_cat_cols = [c for c in ("interaction_type", "edge_type", "sign", "pathway")
                      if c in edges.columns]
    for _, r in edges.iterrows():
        attrs = {"weight": float(r.get("weight", 1.0))}
        for c in _edge_cat_cols:
            attrs[c] = str(r[c])
        G.add_edge(str(r["source"]), str(r["target"]), **attrs)

    # Node attributes from an aux 'nodes' table.
    nodes_df = _node_table(aux)
    node_attr: Dict[str, Dict[str, Any]] = {}
    if nodes_df is not None and len(nodes_df):
        ncol = pick_column(nodes_df, ["node", "id", "name", "gene", "gene_symbol"],
                           default=nodes_df.columns[0])
        gcol = pick_column(nodes_df, ["group", "module", "community", "category", "type", "class"])
        vcol = pick_column(nodes_df, ["size", "value", "degree", "fold_change", "color_value"])
        for _, r in nodes_df.iterrows():
            rec: Dict[str, Any] = {}
            if gcol:
                rec["group"] = str(r[gcol])
            if vcol:
                rec["value"] = pd.to_numeric(pd.Series([r[vcol]]), errors="coerce").iloc[0]
            node_attr[str(r[ncol])] = rec

    # Node-degree filtering / top-N nodes / isolates.
    min_deg = get_mapping(spec, "min_degree", None)
    if min_deg is not None:
        G.remove_nodes_from([n for n, d in dict(G.degree()).items() if d < int(min_deg)])
    top_nodes = get_mapping(spec, "top_n_nodes", None)
    if top_nodes:
        keep = [n for n, _ in sorted(G.degree(), key=lambda kv: kv[1], reverse=True)][:int(top_nodes)]
        G = G.subgraph(keep).copy()
    if bool(get_mapping(spec, "remove_isolates", True)):
        G.remove_nodes_from(list(nx.isolates(G)))
    if G.number_of_nodes() == 0:
        raise RenderError(f"{PLOT_TYPE}: no nodes left after filtering — relax thresholds.")

    n_nodes, n_edges = G.number_of_nodes(), G.number_of_edges()
    density = nx.density(G)
    if n_nodes > _DENSE_NODES or n_edges > _DENSE_EDGES or density > 0.5:
        warnings.append(f"Dense network ({n_nodes} nodes, {n_edges} edges, density={density:.2f}); "
                        "consider stronger filtering (top_n_edges / min_degree / min_weight).")

    # --- layout ---
    seed = int(get_mapping(spec, "seed", 42))
    layout = str(get_mapping(spec, "layout", "spring")).lower()
    if layout not in _LAYOUTS:
        layout = "spring"
    try:
        if layout == "spring":
            pos = nx.spring_layout(G, seed=seed, k=None)
        elif layout == "kamada_kawai":
            pos = nx.kamada_kawai_layout(G)
        elif layout == "circular":
            pos = nx.circular_layout(G)
        elif layout == "shell":
            pos = nx.shell_layout(G)
        elif layout == "spectral":
            pos = nx.spectral_layout(G)
        elif layout == "random":
            pos = nx.random_layout(G, seed=seed)
        elif layout == "multipartite":
            for n in G.nodes():
                G.nodes[n]["_layer"] = node_attr.get(n, {}).get("group", "0")
            pos = nx.multipartite_layout(G, subset_key="_layer")
        elif layout == "fixed":
            xcol = get_mapping(spec, "x", "x"); ycol = get_mapping(spec, "y", "y")
            if nodes_df is not None and xcol in nodes_df.columns and ycol in nodes_df.columns:
                ncol = pick_column(nodes_df, ["node", "id", "name"], default=nodes_df.columns[0])
                pos = {str(r[ncol]): (float(r[xcol]), float(r[ycol])) for _, r in nodes_df.iterrows()
                       if str(r[ncol]) in G}
                pos = {n: pos.get(n, (0.0, 0.0)) for n in G.nodes()}
            else:
                warnings.append("Fixed layout needs node x/y columns; fell back to spring.")
                pos = nx.spring_layout(G, seed=seed)
        else:
            pos = nx.spring_layout(G, seed=seed)
    except Exception as exc:  # pragma: no cover - layout robustness
        warnings.append(f"Layout '{layout}' failed ({exc}); used spring.")
        pos = nx.spring_layout(G, seed=seed)

    # --- node sizing (fixed | by degree | by value) ---
    degrees = dict(G.degree())
    size_by = str(get_mapping(spec, "size_by", "degree")).lower()
    if size_by == "fixed":
        node_sizes = np.full(G.number_of_nodes(),
                             float(get_mapping(spec, "node_size", 300.0) or 300.0))
    else:
        if size_by == "value" and any("value" in node_attr.get(n, {}) for n in G):
            raw = np.array([float(node_attr.get(n, {}).get("value", np.nan)) for n in G], dtype=float)
            raw = np.nan_to_num(raw, nan=np.nanmedian(raw[~np.isnan(raw)]) if np.isfinite(raw).any() else 1.0)
        else:
            raw = np.array([degrees[n] for n in G], dtype=float)
        lo, hi = float(np.min(raw)), float(np.max(raw))
        norm = (raw - lo) / (hi - lo) if hi > lo else np.zeros_like(raw)
        node_sizes = 120 + norm * 680  # ~120..800 pt^2

    # --- node coloring (group | value | fixed) ---
    groups = [node_attr.get(n, {}).get("group") for n in G]
    has_groups = any(g is not None for g in groups)
    color_value = [node_attr.get(n, {}).get("value") for n in G]
    color_by = str(get_mapping(spec, "color_by", "group" if has_groups else "none")).lower()

    # A custom category->color map (dict or JSON string) overrides the palette.
    node_color_map = get_mapping(spec, "node_color_map", None) or {}
    if isinstance(node_color_map, str):
        import json
        try:
            node_color_map = json.loads(node_color_map)
        except Exception:  # noqa: BLE001
            node_color_map = {}

    node_colors: Any
    legend_handles = None
    cmap_obj = None
    if color_by == "group" and has_groups:
        levels = ordered_unique([g for g in groups if g is not None])
        # Honor the active Publication palette for group node colors (falls back to the
        # clustering palette); a user-supplied node_color_map wins per category.
        palette = list(getattr(style, "palette", None) or []) or list(CLUSTER_PALETTE)
        cmap_lv = {lv: str(node_color_map.get(str(lv), palette[i % len(palette)]))
                   for i, lv in enumerate(levels)}
        node_colors = [cmap_lv.get(g, "#BBBBBB") for g in groups]
        from matplotlib.patches import Patch

        legend_handles = [Patch(facecolor=cmap_lv[lv], edgecolor="black", label=str(lv))
                          for lv in levels]
    elif color_by == "value" and any(v is not None for v in color_value):
        vals = np.array([float(v) if v is not None else np.nan for v in color_value], dtype=float)
        vals = np.nan_to_num(vals, nan=np.nanmedian(vals[~np.isnan(vals)]) if np.isfinite(vals).any() else 0.0)
        node_colors = vals
        _nc = get_mapping(spec, "node_cmap", None)
        cmap_obj = str(_nc) if (_nc and str(_nc) != "(default)") else str(style.sequential_cmap)
    else:
        # Fixed single node color: explicit node_color wins, else the palette's first
        # color. Sentinels ("(default)"/"(palette)"/"") mean "use the palette".
        nc = get_mapping(spec, "node_color", None)
        node_colors = str(nc) if (nc and str(nc) not in ("(default)", "(palette)", "")) \
            else str(style.color_for(0))

    # --- edge widths (by weight | fixed) ---
    weights = np.array([abs(G[u][v].get("weight", 1.0)) for u, v in G.edges()], dtype=float)
    edge_width_by = str(get_mapping(spec, "edge_width_by", "weight")).lower()
    if edge_width_by == "fixed":
        ew = np.full(weights.shape, float(get_mapping(spec, "edge_width", 1.5) or 1.5))
    elif weights.size and np.ptp(weights) > 0:
        ew = 0.5 + 2.5 * (weights - weights.min()) / np.ptp(weights)
    else:
        ew = np.full(weights.shape, 1.0)

    # --- edge colors (by category | by sign in correlation mode | fixed) ---
    edge_legend_handles = None
    # Auto-detect: if the edge table carries interaction_type/edge_type, color by it
    # unless the user picked otherwise. This restores the "hue by interaction_type".
    default_ecb = next((c for c in ("interaction_type", "edge_type", "pathway")
                        if c in _edge_cat_cols), None)
    edge_color_by = get_mapping(spec, "edge_color_by", None)
    if edge_color_by is None or str(edge_color_by).lower() in ("(auto)", "auto", ""):
        edge_color_by = default_ecb                       # auto: use a category if present
    elif str(edge_color_by).lower() == "none":
        edge_color_by = None                              # user explicitly disabled

    if edge_color_by and edge_color_by in _edge_cat_cols:
        cats = ordered_unique([str(G[u][v].get(edge_color_by)) for u, v in G.edges()])
        e_palette = list(getattr(style, "palette", None) or []) or list(CLUSTER_PALETTE)
        e_map = {c: e_palette[i % len(e_palette)] for i, c in enumerate(cats)}
        edge_colors = [e_map[str(G[u][v].get(edge_color_by))] for u, v in G.edges()]
        from matplotlib.patches import Patch

        edge_legend_handles = [Patch(facecolor=e_map[c], edgecolor="none", label=str(c))
                               for c in cats]
    elif mode == "correlation":
        pos_c = str(get_mapping(spec, "edge_color_positive", "#B2182B"))
        neg_c = str(get_mapping(spec, "edge_color_negative", "#2166AC"))
        edge_colors = [pos_c if G[u][v].get("weight", 0) >= 0 else neg_c for u, v in G.edges()]
    else:
        edge_colors = str(get_mapping(spec, "edge_color", "#888888"))

    # --- draw ---
    with style.apply():
        w_in, h_in = figure_size(spec, style, aspect=0.9)
        fig, ax = plt.subplots(figsize=(max(w_in, 5.2), max(h_in, 4.6)))
        nx.draw_networkx_edges(G, pos, ax=ax, width=list(ew), edge_color=edge_colors,
                               alpha=0.35, arrows=directed)
        nodes_art = nx.draw_networkx_nodes(
            G, pos, ax=ax, node_size=list(node_sizes), node_color=node_colors,
            cmap=cmap_obj, edgecolors="black", linewidths=0.7)
        nodes_art.set_zorder(3)

        # Labels: all if few nodes, else top-N by degree.
        show_labels = bool(get_mapping(spec, "node_labels", True))
        if show_labels:
            max_lab = int(get_mapping(spec, "max_labels", 30))
            if n_nodes <= max_lab:
                lab_nodes = list(G.nodes())
            else:
                lab_nodes = [n for n, _ in sorted(degrees.items(), key=lambda kv: kv[1],
                                                  reverse=True)[:max_lab]]
                warnings.append(f"{n_nodes} nodes: labeled the top {max_lab} by degree for legibility.")
            # Draw labels as haloed text and de-overlap them (repel + thin leader
            # lines) so dense graphs stay legible instead of stacking labels.
            import matplotlib.patheffects as pe

            fs = float(get_mapping(spec, "label_font_size", 0) or 0) or max(7.5, style.annotation_pt - 1)
            lab_color = str(get_mapping(spec, "label_color", None) or style.text_color)
            texts = []
            for nlab in lab_nodes:
                x_n, y_n = pos[nlab]
                texts.append(ax.text(x_n, y_n, str(nlab), fontsize=fs, ha="center",
                                     va="center", zorder=6, color=lab_color,
                                     path_effects=[pe.withStroke(linewidth=2.5,
                                                                 foreground="white")]))
            try:
                from adjustText import adjust_text

                adjust_text(texts, ax=ax, only_move={"text": "xy"},
                            expand_text=(1.1, 1.25), expand_points=(1.1, 1.25),
                            arrowprops=dict(arrowstyle="-", color="0.6", lw=0.5),
                            force_text=(0.3, 0.5))
            except Exception:
                pass

        if cmap_obj is not None:
            sm = plt.cm.ScalarMappable(cmap=cmap_obj)
            sm.set_array(np.asarray(node_colors, dtype=float))
            cb = fig.colorbar(sm, ax=ax, fraction=0.045, pad=0.02)
            cb.set_label(str(get_mapping(spec, "color_label", "node value")),
                         fontsize=style.axis_font_pt)

        title = spec.get("layout", {}).get("title") or (
            "Correlation network" if mode == "correlation" else "Network graph")
        if mode == "correlation":
            title += "\n(association, not a mechanistic interaction)"
            ax.set_title(title, fontsize=style.title_font_pt)
        else:
            ax.set_title(title, fontsize=style.title_font_pt)
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.margins(0.10)
        ax._colorbar = True  # network is a diagram: skip axis-label QA check
        show_legend = bool(get_mapping(spec, "show_legend", True))
        placed = False
        if legend_handles and show_legend:
            place_legend(ax, style, title=str(get_mapping(spec, "color_by", "group")),
                         handles=legend_handles, labels=[h.get_label() for h in legend_handles],
                         force_outside=True)
            placed = True
        if edge_legend_handles and show_legend:
            # Edge-category legend. If a node legend already occupies the outside slot,
            # add this as a second legend (lower-left) via add_artist so both show.
            edge_leg = ax.legend(handles=edge_legend_handles,
                                 title=str(edge_color_by), loc="lower left",
                                 fontsize=style.legend_pt, frameon=False)
            if placed:
                ax.add_artist(edge_leg)
            placed = True
        if not placed:
            fig.tight_layout()

    # --- metrics / summary ---
    comps = list(nx.weakly_connected_components(G) if directed else nx.connected_components(G))
    summary: Dict[str, Any] = {
        "n_nodes": int(n_nodes), "n_edges": int(n_edges), "density": round(float(density), 4),
        "n_connected_components": len(comps),
        "largest_component_size": int(max((len(c) for c in comps), default=0)),
        "directed": directed, "layout": layout, "seed": seed, "mode": mode,
    }
    node_metrics: List[Dict[str, Any]] = []
    wdeg = dict(G.degree(weight="weight"))
    betw = clos = eig = {}
    if n_nodes <= 500:
        try:
            betw = nx.betweenness_centrality(G)
            clos = nx.closeness_centrality(G)
        except Exception:
            betw = clos = {}
        try:
            eig = nx.eigenvector_centrality_numpy(G)
        except Exception:
            eig = {}
    if bool(get_mapping(spec, "detect_communities", False)):
        try:
            from networkx.algorithms.community import greedy_modularity_communities

            comm = greedy_modularity_communities(G.to_undirected())
            cmap_comm = {n: i + 1 for i, cset in enumerate(comm) for n in cset}
            summary["n_communities"] = len(comm)
            summary["community_method"] = "greedy_modularity (heuristic)"
        except Exception:
            cmap_comm = {}
    else:
        cmap_comm = {}
    for n in G.nodes():
        node_metrics.append({
            "node": n, "degree": int(degrees[n]), "weighted_degree": round(float(wdeg[n]), 4),
            "betweenness": round(float(betw.get(n, 0.0)), 5) if betw else None,
            "closeness": round(float(clos.get(n, 0.0)), 5) if clos else None,
            "eigenvector": round(float(eig.get(n, 0.0)), 5) if eig else None,
            "group": node_attr.get(n, {}).get("group"),
            "community": cmap_comm.get(n),
        })

    meta = base_metadata(spec, style, edges, used_columns=["source", "target"])
    meta["network_summary"] = summary
    meta["node_metrics"] = node_metrics
    meta["filtered_edges"] = edges.to_dict(orient="records")
    meta.update(summary)
    return RenderResult(figure=fig, metadata=meta, warnings=warnings)
