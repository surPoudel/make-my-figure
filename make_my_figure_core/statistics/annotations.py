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


def _omnibus_value(r: StatResult, cfg: Dict[str, Any], digits: int) -> str:
    """The text after an omnibus term's name, as the "Annotation shows" control asks.

    Before, an ANOVA always printed "F(3, 108) = 242, p < 0.001" whatever the
    control said, and "Show effect size" and "Hide non-significant" did nothing
    to it. Returns "" when the term is to be hidden.
    """
    if cfg.get("hide_nonsignificant") and not bool(r.reject_null):
        return ""
    sn = r.statistic_name or "stat"
    has_df2 = r.df is not None and r.df2 is not None and r.df == r.df and r.df2 == r.df2
    stat = (f"{sn}({r.df:g}, {r.df2:g}) = {r.statistic:.3g}" if has_df2 and r.test_id == "factorial_anova"
            else f"{sn} = {r.statistic:.3g}") if r.statistic == r.statistic and r.statistic is not None else ""
    p = report.format_p(r.display_p, digits=digits)
    tok = report.annotation_tokens(r, cfg)
    stars = tok["stars"]
    effect = (f"{tok['effect_symbol']} = {r.effect_size:.2f}"
              if r.effect_size is not None and r.effect_size == r.effect_size else "")
    content = cfg.get("content") or {"stars": "stars", "p": "p", "both": "p_stars"}.get(
        cfg.get("mode", "stars"), "stars")
    if content == "custom":
        try:
            return (cfg.get("template") or "{stars}").format(**tok).strip()
        except Exception:  # noqa: BLE001
            return stars
    if content == "flags":
        parts = [b for flag, b in (("show_stat", stat), ("show_effect", effect), ("show_p", p),
                                   ("show_p_adj", p), ("show_stars", stars)) if cfg.get(flag) and b]
        return ", ".join(dict.fromkeys(parts)) or stars
    parts = {"stars": [stars] if cfg.get("omnibus_stars") else [stat, p], "p": [p], "p_adj": [p], "p_stars": [f"{p} ({stars})"],
             "stat": [stat or stars], "effect": [effect or stars], "p_stat": [stat, p],
             "p_effect": [effect, p], "full": [stat, effect, p]}.get(content, [stars])
    if cfg.get("show_effect") and effect and effect not in parts:
        parts.append(effect)
    return ", ".join(b for b in parts if b)


def _omnibus_follows_cfg(cfg: Optional[Dict[str, Any]]) -> bool:
    """Whether omnibus lines take their form from the annotation settings.

    Not under the default "Stars only": an ANOVA is reported with its statistic,
    and every figure saved with default statistics shows "F = 77.9, p < 0.001",
    which must not turn into "****". Any other content choice, the effect size,
    hiding non-significant terms or ``omnibus_stars`` (stars for ANOVA terms too,
    opt-in) is an explicit request and is honoured.
    """
    if cfg is None:
        return False
    content = cfg.get("content") or {"stars": "stars", "p": "p", "both": "p_stars"}.get(
        cfg.get("mode", "stars"), "stars")
    return (content != "stars" or bool(cfg.get("show_effect")) or bool(cfg.get("hide_nonsignificant"))
            or bool(cfg.get("omnibus_stars")))


def stat_text_panel(results: List[StatResult], *, digits: int = 3,
                    show_ci: bool = True, cfg: Optional[Dict[str, Any]] = None) -> List[str]:
    """Lines of text for corner/panel annotations (correlation, survival, omnibus).

    With ``cfg`` (the StatsSpec annotation block) omnibus lines follow its
    content, effect-size and hide-non-significant settings; without it they keep
    the fixed "statistic, p" form.
    """
    lines: List[str] = []
    for r in results:
        if r.comparison_type == "two_group":
            continue
        if r.comparison_type == "omnibus" and _omnibus_follows_cfg(cfg):
            value = _omnibus_value(r, cfg, digits)
            if not value:
                continue
            if r.test_id in ("two_way_anova", "factorial_anova"):
                head = "Two-way ANOVA:" if r.test_id == "two_way_anova" else f"{r.test_name}:"
                if head not in lines:
                    lines.append(head)
                lines.append(f"  {r.group_a or 'term'}: {value}")
            else:
                lines.append(f"{r.test_name}: {value}")
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
            elif r.test_id == "factorial_anova":
                head = f"{r.test_name}:"
                if head not in lines:
                    lines.append(head)
                lines.append(f"  {r.group_a}: {sn}({r.df:g}, {r.df2:g}) = {r.statistic:.3g}, "
                             f"{report.format_p(r.display_p, digits=digits)}")
            else:
                lines.append(f"{r.test_name}: {sn} = {r.statistic:.3g}, "
                             f"{report.format_p(r.display_p, digits=digits)}")
    return lines
