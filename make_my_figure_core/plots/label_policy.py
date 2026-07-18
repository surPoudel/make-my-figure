"""Shared duplicate-label handling for point-labelled plots (Volcano + MA).

A differential-result table often maps several plotted rows (peptides, transcripts,
probes, isoforms) to the **same** gene symbol. Historically the renderers collapsed
labels by text (``seen = {t for ...}`` / dicts keyed by label text), so only one of
three ``Mbp`` peptides was ever labelled — silently discarding valid feature-level
results.

This module makes that behaviour user-configurable and keeps **point identity** for
every plotted row so duplicate-symbol points stay independently selectable, movable,
and unlabelable.

Policies (``duplicate_label_policy``):
  * ``all``    — label every selected point (default; duplicates allowed).
  * ``unique`` — one representative point per unique label value.
  * ``count``  — one representative per label, text suffixed ``(n=k)`` where ``k`` is
                 the number of *plotted* rows sharing that label.

Representative rule (``duplicate_label_representative_rule``) picks the representative
row deterministically for ``unique``/``count``:
  ``pvalue`` (smallest p), ``padj`` (smallest FDR), ``effect`` (largest |effect|),
  ``statistic`` (largest |statistic|), ``first`` (first row in source order).
A rule whose column is absent falls back to ``first`` (and the UI disables it).

Pure pandas — no Matplotlib, no GUI. Both renderers call :func:`build_label_points`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import pandas as pd

DUPLICATE_POLICIES = ("all", "unique", "count")
REPRESENTATIVE_RULES = ("pvalue", "padj", "effect", "statistic", "first")
DEFAULT_POLICY = "all"
DEFAULT_RULE = "pvalue"

# Human-readable labels for the GUIs (kept here so both frontends stay in sync).
POLICY_LABELS = {
    "all": "Label every selected point",
    "unique": "Label one point per unique label",
    "count": "Label unique label with count",
}
RULE_LABELS = {
    "pvalue": "smallest p-value",
    "padj": "smallest adjusted p-value/FDR",
    "effect": "largest absolute effect size",
    "statistic": "highest absolute statistic",
    "first": "first source row",
}


@dataclass
class LabelPoint:
    """One label anchored to a specific plotted point (never keyed by text)."""

    point_id: str
    source_row_id: Any
    label_text: str
    anchor_x: float
    anchor_y: float
    offset: Optional[Tuple[float, float]] = None   # (dx, dy) in points; None => auto


def normalize_policy(value: Any) -> str:
    v = str(value or "").strip().lower()
    # Back-compat aliases.
    if v in ("every", "all_points", "all-point", "allpoints"):
        v = "all"
    if v in ("one", "representative", "dedupe", "deduplicate"):
        v = "unique"
    return v if v in DUPLICATE_POLICIES else DEFAULT_POLICY


def normalize_rule(value: Any) -> str:
    v = str(value or "").strip().lower()
    aliases = {
        "p": "pvalue", "p_value": "pvalue", "pval": "pvalue", "smallest_p": "pvalue",
        "fdr": "padj", "adj_p": "padj", "adjusted": "padj", "qvalue": "padj",
        "logfc": "effect", "lfc": "effect", "fold_change": "effect",
        "stat": "statistic", "t": "statistic", "z": "statistic",
        "source": "first", "row": "first", "first_row": "first",
    }
    v = aliases.get(v, v)
    return v if v in REPRESENTATIVE_RULES else DEFAULT_RULE


def point_id_for(work: pd.DataFrame, idx: Any, id_col: Optional[str]) -> str:
    """Stable point id for a plotted row: feature id if present, else positional row id.

    Positional (``row_<pos>``) matches the click-identify point order, so a clicked
    point maps back to the same id the renderer uses.
    """
    if id_col and id_col in work.columns:
        try:
            v = work.at[idx, id_col]
            if pd.notna(v) and str(v).strip():
                return str(v).strip()
        except Exception:  # noqa: BLE001
            pass
    try:
        return f"row_{work.index.get_loc(idx)}"
    except Exception:  # noqa: BLE001
        return f"row_{idx}"


def parse_offsets(raw: Any) -> Dict[str, Any]:
    """Parse a JSON/dict offsets map ({key: [dx, dy]}); tolerant of bad input."""
    if not raw:
        return {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:  # noqa: BLE001
            return {}
    return raw if isinstance(raw, dict) else {}


def _representatives(work: pd.DataFrame, candidate_idx: Sequence[Any],
                     label_series: pd.Series, rule: str,
                     rep_columns: Dict[str, Optional[str]]) -> Dict[str, Any]:
    """Deterministic {label -> representative index} over the candidate rows."""
    groups: Dict[str, List[Any]] = {}
    for i in candidate_idx:
        lab = str(label_series.loc[i])
        groups.setdefault(lab, []).append(i)

    col = rep_columns.get(rule)
    reps: Dict[str, Any] = {}
    for lab, members in groups.items():
        # source order for tie-breaks and the "first" rule
        members = sorted(members, key=lambda j: work.index.get_loc(j))
        if rule == "first" or not col or col not in work.columns:
            reps[lab] = members[0]
            continue
        vals = pd.to_numeric(work.loc[members, col], errors="coerce")
        if vals.notna().sum() == 0:
            reps[lab] = members[0]
            continue
        best = vals.idxmin() if rule in ("pvalue", "padj") else vals.abs().idxmax()
        reps[lab] = members[0] if pd.isna(best) else best
    return reps


def build_label_points(
    work: pd.DataFrame,
    ranked_idx: Sequence[Any],
    *,
    label_series: pd.Series,
    text_fn: Callable[[Any], str],
    x_col: str,
    y_col: str,
    id_col: Optional[str] = None,
    policy: str = DEFAULT_POLICY,
    representative_rule: str = DEFAULT_RULE,
    show_count: bool = False,
    rep_columns: Optional[Dict[str, Optional[str]]] = None,
    limit: Optional[int] = None,
    total_counts: Optional[Dict[str, int]] = None,
) -> List[LabelPoint]:
    """Turn ranked candidate rows into final label points, applying the policy.

    ``ranked_idx`` is the candidate rows already ordered by the active label mode
    (most-important first). For ``all`` this yields one label per row (capped at
    ``limit`` rows). For ``unique``/``count`` the labels are chosen in ranked order,
    one representative per label value (so ``limit`` counts *unique labels*).
    """
    policy = normalize_policy(policy)
    rule = normalize_rule(representative_rule)
    rep_columns = rep_columns or {}
    out: List[LabelPoint] = []

    if policy == "all":
        seen_pid: set = set()
        for i in ranked_idx:
            txt = text_fn(i)
            if not txt:
                continue
            pid = point_id_for(work, i, id_col)
            if pid in seen_pid:
                continue
            seen_pid.add(pid)
            out.append(LabelPoint(
                point_id=pid, source_row_id=i, label_text=txt,
                anchor_x=float(work.at[i, x_col]), anchor_y=float(work.at[i, y_col])))
            if limit is not None and len(out) >= limit:
                break
        return out

    # unique / count: pick one representative per label value, in ranked order.
    reps = _representatives(work, ranked_idx, label_series, rule, rep_columns)
    ordered_labels: List[str] = []
    seen_lab: set = set()
    for i in ranked_idx:
        lab = str(label_series.loc[i])
        if lab and lab not in seen_lab:
            seen_lab.add(lab)
            ordered_labels.append(lab)

    add_count = policy == "count" or bool(show_count)
    for lab in ordered_labels:
        i = reps.get(lab)
        if i is None:
            continue
        txt = text_fn(i)
        if not txt:
            continue
        if add_count:
            n = int(total_counts.get(lab, 1)) if total_counts else 1
            txt = f"{txt} (n={n})"
        out.append(LabelPoint(
            point_id=point_id_for(work, i, id_col), source_row_id=i, label_text=txt,
            anchor_x=float(work.at[i, x_col]), anchor_y=float(work.at[i, y_col])))
        if limit is not None and len(out) >= limit:
            break
    return out


def total_label_counts(label_series: pd.Series) -> Dict[str, int]:
    """Count plotted rows per label value (for the ``count`` policy suffix)."""
    s = label_series.astype(str).str.strip()
    s = s[s.ne("") & s.ne("nan")]
    return {str(k): int(v) for k, v in s.value_counts().items()}


def available_rules(rep_columns: Dict[str, Optional[str]],
                    df_columns: Sequence[str]) -> List[str]:
    """Rules that can be computed given the present columns ('first' always available)."""
    cols = set(map(str, df_columns))
    ok = ["first"]
    for rule in ("pvalue", "padj", "effect", "statistic"):
        col = rep_columns.get(rule)
        if col and str(col) in cols:
            ok.append(rule)
    # Stable, UI-friendly order.
    order = {r: n for n, r in enumerate(REPRESENTATIVE_RULES)}
    return sorted(ok, key=lambda r: order.get(r, 99))
