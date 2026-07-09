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


def _is_num(v) -> bool:
    return v is not None and isinstance(v, (int, float)) and v == v  # not None / NaN


def stat_symbol(r: StatResult) -> str:
    """Display symbol for a test statistic (mathtext where needed)."""
    name = (r.statistic_name or "").lower()
    table = {
        "t": "t", "f": "F", "u": "U", "w": "W", "z": "z", "h": "H",
        "r": "r", "rho": r"$\rho$", "slope": "slope", "chi2": r"$\chi^2$",
    }
    return table.get(name, r.statistic_name or "stat")


def effect_symbol(name: Optional[str]) -> str:
    """Compact symbol for an effect-size name (mathtext for squared terms)."""
    if not name:
        return "effect"
    table = {
        "Cohen's d": "d", "Cohen's dz": "dz", "Hedges' g": "g",
        "rank-biserial": "r", "Cliff's delta (rank-biserial)": r"$\delta$",
        "Cliff's delta": r"$\delta$",
        "eta-squared": r"$\eta^2$", "omega-squared": r"$\omega^2$",
        "epsilon-squared": r"$\epsilon^2$", "R-squared": r"$R^2$",
        "Cramer's V": "V", "odds ratio": "OR", "hazard ratio": "HR",
        "Spearman rho": r"$\rho$", "Pearson r": "r",
    }
    return table.get(name, name)


# Back-compat private alias.
_effect_symbol = effect_symbol


def format_p_adj(p: Optional[float], *, digits: int = 3, sci_threshold: float = 1e-3,
                 p_less_than: bool = True) -> str:
    """Adjusted p-value as ``q = ...`` (shares p-value formatting rules)."""
    body = format_p(p, digits=digits, sci_threshold=sci_threshold if p_less_than else 0.0)
    return body.replace("p ", "q ", 1)


def _fmt_num(v: Optional[float], digits: int) -> str:
    return f"{v:.{digits}g}" if _is_num(v) else "n/a"


def format_p_bare(p: Optional[float], *, digits: int = 3, sci_threshold: float = 1e-3,
                  p_less_than: bool = True) -> str:
    """Bare p-value string (no ``p =`` prefix): ``0.023`` / ``<0.001`` / ``1.2e-05``."""
    if not _is_num(p):
        return "n/a"
    if p_less_than and p < sci_threshold:
        smallest = float(f"1e-{digits}")
        if p < smallest:
            return f"<{smallest:g}"
        return f"{p:.{max(1, digits)}e}"
    return f"{p:.{digits}f}"


def annotation_tokens(r: StatResult, cfg: Optional[dict] = None) -> dict:
    """Build the token dict for a comparison, reading only stored values.

    All value tokens are BARE (no ``p =`` / symbol prefixes), so a user template
    like ``p = {p}`` or ``{effect_symbol} = {effect}`` composes cleanly. Tokens:
    p, p_adj, stars, stat_symbol, stat, effect_symbol, effect, ci, test_short,
    n, comparison. Nothing is recomputed here.
    """
    cfg = cfg or {}
    digits = int(cfg.get("digits", 3))
    sci = float(cfg.get("sci_threshold", 1e-3))
    plt_style = bool(cfg.get("p_less_than_style", True))
    sdig = int(cfg.get("stat_digits", 2))
    edig = int(cfg.get("effect_digits", 2))
    star = stars_for_p(r.display_p)
    if star == "ns" and cfg.get("use_ns", True):
        star = "n.s."
    n_total = r.n_total if r.n_total is not None else (sum((r.n_by_group or {}).values()) or None)
    ci = ""
    if _is_num(r.confidence_interval_low) and _is_num(r.confidence_interval_high):
        ci = f"[{r.confidence_interval_low:.{edig}g}, {r.confidence_interval_high:.{edig}g}]"
    return {
        "p": format_p_bare(r.p_value, digits=digits, sci_threshold=sci, p_less_than=plt_style),
        "p_adj": format_p_bare(r.adjusted_p_value, digits=digits, sci_threshold=sci, p_less_than=plt_style),
        "stars": star,
        "stat_symbol": stat_symbol(r),
        "stat": _fmt_num(r.statistic, sdig),
        "effect_symbol": effect_symbol(r.effect_size_name),
        "effect": _fmt_num(r.effect_size, edig),
        "ci": ci,
        "test_short": _test_short(r),
        "n": "" if n_total is None else str(int(n_total)),
        "comparison": r.comparison_label,
    }


def _p_kv(bare: str) -> str:
    """Turn a bare p string into ``p = 0.023`` / ``p < 0.001``."""
    return f"p < {bare[1:]}" if bare.startswith("<") else f"p = {bare}"


def _q_kv(bare: str) -> str:
    return f"q < {bare[1:]}" if bare.startswith("<") else f"q = {bare}"


def _test_short(r: StatResult) -> str:
    # Names deliberately omit the statistic letter (t/F/U/...) so 'full' mode can
    # append '{stat_symbol} = {stat}' without duplicating it (e.g. 'Welch t = ...').
    short = {
        "students_t": "Student's", "welch_t": "Welch", "mann_whitney": "Mann-Whitney",
        "paired_t": "paired", "wilcoxon": "Wilcoxon", "one_way_anova": "one-way ANOVA",
        "two_way_anova": "two-way ANOVA", "rm_anova": "RM-ANOVA",
        "kruskal_wallis": "Kruskal-Wallis", "dunn": "Dunn", "chi_square": "chi-square",
        "fishers_exact": "Fisher's exact", "logrank": "log-rank", "cox_ph": "Cox",
        "pearson": "Pearson", "spearman": "Spearman", "linear_regression": "OLS",
    }
    return short.get(r.test_id, r.test_name)


def render_annotation(r: StatResult, cfg: Optional[dict] = None) -> str:
    """Render the on-figure label for one comparison from stored values only.

    Honors ``cfg['content']`` (see ANNOTATION_CONTENTS) or a custom template
    ``cfg['template']``. Returns "" when the annotation should be hidden
    (nonsignificant + hide_nonsignificant).
    """
    cfg = cfg or {}
    content = cfg.get("content") or {"stars": "stars", "p": "p", "both": "p_stars"}.get(
        cfg.get("mode", "stars"), "stars")
    if cfg.get("hide_nonsignificant") and not bool(r.reject_null):
        return ""
    tok = annotation_tokens(r, cfg)
    has_stat = _is_num(r.statistic)
    has_effect = _is_num(r.effect_size)
    stat_kv = f"{tok['stat_symbol']} = {tok['stat']}" if has_stat else ""
    effect_kv = f"{tok['effect_symbol']} = {tok['effect']}" if has_effect else ""
    p_kv = _p_kv(tok["p"])
    q_kv = _q_kv(tok["p_adj"])

    if content == "stars":
        return tok["stars"]
    if content == "p":
        return p_kv
    if content == "p_adj":
        return q_kv if r.adjusted_p_value is not None else p_kv
    if content == "p_stars":
        return f"{p_kv} ({tok['stars']})"
    if content == "stat":
        return stat_kv or tok["stars"]
    if content == "effect":
        return effect_kv or tok["stars"]
    if content == "p_stat":
        return ", ".join([b for b in (stat_kv, p_kv) if b])
    if content == "p_effect":
        return ", ".join([b for b in (effect_kv, p_kv) if b])
    if content == "full":
        bits = []
        if has_stat:
            # test_short conveys the test; append the statistic symbol + value.
            bits.append(f"{tok['test_short']} {tok['stat_symbol']} = {tok['stat']}")
        if has_effect:
            bits.append(effect_kv)
        bits.append(p_kv)
        return ", ".join(bits)
    if content == "custom":
        try:
            return (cfg.get("template") or "{stars}").format(**tok).strip()
        except Exception:
            return tok["stars"]
    if content == "flags":
        parts = []
        if cfg.get("show_test_name"):
            parts.append(tok["test_short"])
        if cfg.get("show_stat") and has_stat:
            parts.append(stat_kv)
        if cfg.get("show_effect") and has_effect:
            parts.append(effect_kv)
        if cfg.get("show_ci") and tok["ci"]:
            parts.append(tok["ci"])
        if cfg.get("show_p"):
            parts.append(p_kv)
        if cfg.get("show_p_adj") and r.adjusted_p_value is not None:
            parts.append(q_kv)
        if cfg.get("show_stars"):
            parts.append(tok["stars"])
        if cfg.get("show_n") and tok["n"]:
            parts.append(f"n = {tok['n']}")
        return ", ".join(parts) if parts else tok["stars"]
    return tok["stars"]


def annotation_text(r: StatResult, *, mode: str = "stars", digits: int = 3,
                    show_effect: bool = False, sci_threshold: float = 1e-3,
                    cfg: Optional[dict] = None) -> str:
    """Back-compatible wrapper around :func:`render_annotation`."""
    if cfg is not None:
        return render_annotation(r, cfg)
    base = {"mode": mode, "content": {"stars": "stars", "p": "p", "both": "p_stars"}.get(mode, "stars"),
            "digits": digits, "sci_threshold": sci_threshold, "show_effect": show_effect}
    text = render_annotation(r, base)
    if show_effect and _is_num(r.effect_size):
        text += f", {effect_symbol(r.effect_size_name)} = {r.effect_size:.2g}"
    return text
