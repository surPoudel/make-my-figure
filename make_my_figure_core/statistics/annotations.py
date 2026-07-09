"""Annotation model: turn stored StatResults into figure annotation items.

An :class:`AnnotationItem` is the *only* thing a renderer's overlay engine draws.
Each item is derived from exactly one :class:`StatResult`, so every p-value or
star shown on a figure is backed by a stored result with its test, groups, n,
correction, and method sentence. Renderers never format p-values themselves.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from make_my_figure_core.statistics import method_reporting as report
from make_my_figure_core.statistics.models import StatResult


@dataclass
class AnnotationItem:
    """A single comparison to draw (bracket + label) between two categories."""

    group_a: str
    group_b: str
    text: str
    p_value: Optional[float]
    display_p: Optional[float]
    significant: Optional[bool]
    x_level: Optional[str] = None      # for within-x (grouped) comparisons
    within_x: bool = False
    result_id: str = ""                # test_id of the backing StatResult
    source: Dict[str, Any] = field(default_factory=dict)  # small provenance echo


def build_pairwise_annotations(results: List[StatResult], annotation_cfg: Dict[str, Any]
                               ) -> List[AnnotationItem]:
    """Build bracket annotation items from two-group StatResults.

    Only ``two_group`` comparisons produce brackets; omnibus/correlation/survival
    results are surfaced as text panels elsewhere. Non-significant comparisons are
    included only if ``show_nonsignificant`` is set.
    """
    cfg = annotation_cfg or {}
    # `hide_nonsignificant` (new) and `show_nonsignificant` (legacy) both drop
    # non-significant comparisons from the figure.
    show_ns = bool(cfg.get("show_nonsignificant", True)) and not bool(cfg.get("hide_nonsignificant", False))

    items: List[AnnotationItem] = []
    for r in results:
        if r.comparison_type != "two_group":
            continue
        if r.p_value is None or r.p_value != r.p_value:
            continue  # skip failed/blank comparisons
        significant = r.reject_null
        if not significant and not show_ns:
            continue
        text = report.render_annotation(r, cfg)
        if not text:
            continue
        items.append(AnnotationItem(
            group_a=str(r.group_a), group_b=str(r.group_b), text=text,
            p_value=r.p_value, display_p=r.display_p, significant=significant,
            x_level=(r.extra or {}).get("x_level"),
            within_x=bool((r.extra or {}).get("within_x", False)),
            result_id=r.test_id,
            source={"test": r.test_name, "n": r.n_by_group,
                    "correction": r.correction_method,
                    "effect_size": r.effect_size, "effect_size_name": r.effect_size_name},
        ))
    return items


def stat_text_panel(results: List[StatResult], *, digits: int = 3,
                    show_ci: bool = True) -> List[str]:
    """Lines of text for corner/panel annotations (correlation, survival, omnibus)."""
    lines: List[str] = []
    for r in results:
        if r.comparison_type == "two_group":
            continue
        if r.comparison_type == "correlation":
            label = "r" if r.test_id == "pearson" else "rho"
            grp = f"{r.group_a}: " if r.group_a else ""
            txt = f"{grp}{label} = {r.statistic:.2f}, {report.format_p(r.display_p, digits=digits)}"
            if r.test_id == "pearson" and r.effect_size == r.effect_size:
                txt += f", R² = {r.effect_size:.2f}"
            lines.append(txt)
        elif r.comparison_type == "regression":
            grp = f"{r.group_a}: " if r.group_a else ""
            txt = f"{grp}slope = {r.statistic:.3g}, {report.format_p(r.display_p, digits=digits)}"
            if r.effect_size == r.effect_size:
                txt += f", R² = {r.effect_size:.2f}"
            lines.append(txt)
        elif r.comparison_type == "survival" and r.test_id == "logrank":
            lines.append(f"Log-rank {report.format_p(r.display_p, digits=digits)}")
        elif r.comparison_type == "survival" and r.test_id == "cox_ph":
            ci = ""
            if r.confidence_interval_low == r.confidence_interval_low:
                ci = f" (95% CI {r.confidence_interval_low:.2g}-{r.confidence_interval_high:.2g})"
            lines.append(f"HR {r.group_a} vs {r.group_b} = {r.estimate:.2g}{ci}, "
                         f"{report.format_p(r.display_p, digits=digits)}")
        elif r.comparison_type == "categorical":
            lines.append(f"{r.test_name}: {report.format_p(r.display_p, digits=digits)}")
        elif r.comparison_type == "omnibus":
            sn = r.statistic_name or "stat"
            if r.test_id == "two_way_anova":
                # Compact: one header, then term-only lines (genotype / treatment
                # / interaction) so the panel does not repeat "Two-way ANOVA".
                if not any(ln == "Two-way ANOVA:" for ln in lines):
                    lines.append("Two-way ANOVA:")
                term = (r.group_a or "").split(" x ")
                label = "interaction" if len(term) == 2 else (r.group_a or "term")
                lines.append(f"  {label}: {sn} = {r.statistic:.3g}, "
                             f"{report.format_p(r.display_p, digits=digits)}")
            else:
                lines.append(f"{r.test_name}: {sn} = {r.statistic:.3g}, "
                             f"{report.format_p(r.display_p, digits=digits)}")
    return lines
