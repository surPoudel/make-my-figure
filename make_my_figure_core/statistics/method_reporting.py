"""Transparent method reporting.

Turns :class:`StatResult` objects into (a) a per-result method sentence, (b) an
overall methods paragraph for a manuscript, and (c) a figure-legend sentence.
Also provides p-value / significance-star formatting used by both the text
reports and the on-figure annotations, so a star always means the same thing as
the reported p-value.
"""

from __future__ import annotations

from typing import List, Optional

from make_my_figure_core.statistics.models import StatResult
from make_my_figure_core.statistics.multiple_testing import DISPLAY_NAMES

# Significance-star thresholds (applied to the *displayed* p-value: adjusted if
# a correction was used, otherwise raw).
STAR_THRESHOLDS = [(0.0001, "****"), (0.001, "***"), (0.01, "**"), (0.05, "*")]


def stars_for_p(p: Optional[float]) -> str:
    """Return significance stars for a p-value ('ns' if not significant)."""
    if p is None or p != p:  # None or NaN
        return "n/a"
    for thr, star in STAR_THRESHOLDS:
        if p < thr:
            return star
    return "ns"


def format_p(p: Optional[float], *, digits: int = 3, sci_threshold: float = 1e-3,
             italic: bool = False) -> str:
    """Format a p-value for display, e.g. ``p = 0.023`` or ``p = 1.2e-05``.

    Very small p-values fall back to scientific notation; values below the
    smallest representable threshold are shown as ``p < 0.001``.
    """
    label = "p"
    if p is None or p != p:
        return f"{label} = n/a"
    if p < sci_threshold:
        smallest = float(f"1e-{digits}")
        if p < smallest:
            return f"{label} < {smallest:g}"
        return f"{label} = {p:.{max(1, digits)}e}"
    return f"{label} = {p:.{digits}f}"


def _pairing_phrase(r: StatResult) -> str:
    if r.paired:
        return "paired"
    if r.comparison_type == "two_group":
        return "unpaired"
    return ""


def method_sentence(r: StatResult, *, digits: int = 3) -> str:
    """A single, self-contained sentence describing one comparison."""
    alt = "two-sided" if r.alternative == "two-sided" else f"{r.alternative}"
    pieces: List[str] = []
    if r.comparison_type in ("two_group",):
        subj = f"'{r.group_a}' vs '{r.group_b}'" if r.group_a and r.group_b else "the groups"
        pairing = _pairing_phrase(r)
        pairing = f"{pairing} " if pairing else ""
        pieces.append(f"{subj} were compared with a {alt} {pairing}{r.test_name}")
    elif r.comparison_type in ("omnibus",):
        factors = " x ".join(r.grouping_columns) if r.grouping_columns else "the factor(s)"
        term = f" ({r.group_a})" if r.group_a else ""
        pieces.append(f"a {r.test_name} was performed on {r.value_column or 'the response'} "
                      f"across {factors}{term}")
    elif r.comparison_type == "correlation":
        grp = f" in group '{r.group_a}'" if r.group_a else ""
        pieces.append(f"the association between {r.grouping_columns[0] if r.grouping_columns else 'x'} "
                      f"and {r.value_column or 'y'}{grp} was assessed with {r.test_name}")
    elif r.comparison_type == "regression":
        grp = f" in group '{r.group_a}'" if r.group_a else ""
        pieces.append(f"{r.value_column or 'y'} was regressed on "
                      f"{r.grouping_columns[0] if r.grouping_columns else 'x'}{grp} by {r.test_name}")
    elif r.comparison_type == "survival":
        if r.test_id == "logrank":
            pieces.append(f"survival across {r.grouping_columns[0] if r.grouping_columns else 'groups'} "
                          f"was compared with a {alt} {r.test_name}")
        else:
            pieces.append(f"the hazard for '{r.group_a}' relative to '{r.group_b}' was estimated "
                          f"with a {r.test_name}")
    elif r.comparison_type == "categorical":
        cols = " and ".join(r.grouping_columns) if r.grouping_columns else "the categories"
        pieces.append(f"the association between {cols} was tested with {r.test_name}")
    else:
        pieces.append(f"a {r.test_name} was performed")

    # Statistic + p.
    stat_bits = []
    if r.statistic is not None and r.statistic_name:
        if r.df is not None and r.df2 is not None:
            stat_bits.append(f"{r.statistic_name}({r.df:g}, {r.df2:g}) = {r.statistic:.3g}")
        elif r.df is not None:
            stat_bits.append(f"{r.statistic_name}({r.df:g}) = {r.statistic:.3g}")
        else:
            stat_bits.append(f"{r.statistic_name} = {r.statistic:.3g}")
    pval = r.display_p
    stat_bits.append(format_p(pval, digits=digits))
    if r.adjusted_p_value is not None and r.correction_method and r.correction_method != "none":
        stat_bits.append(f"adjusted, {DISPLAY_NAMES.get(r.correction_method, r.correction_method)}")
    if r.effect_size is not None and r.effect_size == r.effect_size and r.effect_size_name:
        stat_bits.append(f"{r.effect_size_name} = {r.effect_size:.3g}")
    if (r.confidence_interval_low is not None and r.confidence_interval_high is not None
            and r.confidence_interval_low == r.confidence_interval_low):
        label = r.estimate_name or "estimate"
        stat_bits.append(f"{int(r.ci_level * 100)}% CI for {label} "
                         f"[{r.confidence_interval_low:.3g}, {r.confidence_interval_high:.3g}]")
    sentence = "; ".join([", ".join([pieces[0]] + stat_bits[:1])] + stat_bits[1:]) \
        if False else f"{pieces[0]} ({', '.join(stat_bits)})."
    return sentence[0].upper() + sentence[1:]


def methods_paragraph(results: List[StatResult], correction_method: Optional[str]) -> str:
    """A short methods paragraph covering the whole family of tests."""
    if not results:
        return ""
    test_names = []
    for r in results:
        if r.test_name not in test_names:
            test_names.append(r.test_name)
    lead = "Statistical analyses were performed with " + _software_phrase(results[0])
    tests = "; ".join(test_names)
    body = f"{lead}. Tests used: {tests}."
    n_corrected = sum(1 for r in results if r.adjusted_p_value is not None)
    if correction_method and correction_method != "none" and n_corrected > 1:
        body += (f" P-values were adjusted across {n_corrected} comparisons using "
                 f"{DISPLAY_NAMES.get(correction_method, correction_method)}.")
    body += (" Exact p-values are reported unless otherwise noted. Non-finite values were "
             "removed listwise before testing. Users are responsible for confirming that each "
             "test is appropriate for their experimental design.")
    return body


def legend_sentence(results: List[StatResult], correction_method: Optional[str]) -> str:
    """A concise sentence suitable for a figure legend."""
    if not results:
        return ""
    star_line = ("Significance: ****p<0.0001, ***p<0.001, **p<0.01, *p<0.05, ns not significant.")
    primary = results[0]
    base = primary.test_name
    if correction_method and correction_method != "none":
        base += f" with {DISPLAY_NAMES.get(correction_method, correction_method)}"
    return f"Comparisons by {base}. {star_line}"


def _software_phrase(r: StatResult) -> str:
    v = r.software_versions or {}
    bits = []
    for lib in ("scipy", "statsmodels", "numpy"):
        if lib in v and v[lib] not in ("not installed", None):
            bits.append(f"{lib} {v[lib]}")
    if not bits:
        return "Python/scipy"
    return "Python (" + ", ".join(bits) + ")"


def annotation_text(r: StatResult, *, mode: str = "stars", digits: int = 3,
                    show_effect: bool = False, sci_threshold: float = 1e-3) -> str:
    """The text placed on a figure for one comparison.

    ``mode``: ``stars`` | ``p`` | ``both``. When a correction was applied the
    displayed p-value is the adjusted one (consistent with the star).
    """
    pval = r.display_p
    star = stars_for_p(pval)
    if mode == "stars":
        text = star
    elif mode == "p":
        text = format_p(pval, digits=digits, sci_threshold=sci_threshold)
    else:  # both
        text = f"{star} ({format_p(pval, digits=digits, sci_threshold=sci_threshold)})"
    if show_effect and r.effect_size is not None and r.effect_size == r.effect_size:
        text += f"\n{r.effect_size_name} = {r.effect_size:.2g}"
    return text
