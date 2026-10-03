"""Preview a Figure Preset before applying it - on synthetic data, with a data-safety guard.

Applying a preset used to be immediate: pick, click *Apply*, and the controls changed. That is
fine for a preset you saved yourself; it is not fine for a preset you have never seen. This module
gives every frontend the same three pieces:

``preview_pair``
    Render the *current* configuration and the *preset-applied* configuration side by side on
    the bundled synthetic example table for the plot type (CC0, generated from code, never a
    user's data), and return both images plus the apply report. Nothing in the live session is
    touched.

``describe_changes``
    A plain list of what the preset would change, as ``(block, key, old, new)`` rows, so the
    dialog can show "tick labels 10 -> 7 pt" instead of "26 settings applied".

``assert_style_safe``
    The rule that makes a style preset trustworthy: it must never change the data, the column
    roles, the statistical test, the thresholds, transformations or feature selection. This
    compares the spec before and after ``apply_preset`` and returns every protected key that
    differs. For a ``style`` preset that list must be empty; frontends refuse to apply otherwise.

The preview uses the synthetic example data because a preset library ships without the user's
data and because the preview must be safe to render for a plot type the user has not yet
configured. It is a *style* preview: it shows how the preset draws, not what the user's figure
will contain.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

import matplotlib
import matplotlib.pyplot as plt

from make_my_figure_core import examples, presets
from make_my_figure_core.plots import registry
from make_my_figure_core.ui_hints import column_fields

# Keys of ``spec["statistics"]`` that describe the analysis rather than how it is drawn.
# Anything here is protected in style mode.
STATISTICS_ANALYSIS_KEYS = frozenset({
    # make_my_figure_core.statistics.schemas.default_stats_spec keys that define the analysis
    "enabled", "test", "method", "comparison_mode", "alternative", "paired", "correction", "alpha",
    "posthoc", "posthoc_test", "value_column", "group_column", "subgroup_column", "subject_column",
    "time_column", "event_column", "x_column", "y_column", "row_column", "col_column",
    "reference_group", "selected_pairs", "groups", "comparisons", "effect_size", "ci_level",
    "n_permutations", "seed",
})

# Mapping-option scopes that a style preset must leave alone (see ui_hints.Option.scope).
PROTECTED_OPTION_SCOPES = frozenset({"config", "data", "analysis"})

# Layout keys that describe the data, not geometry.
PROTECTED_LAYOUT_KEYS = frozenset(presets.LAYOUT_CONFIG_KEYS)


@dataclass
class ChangeRow:
    block: str
    key: str
    old: Any
    new: Any

    @property
    def label(self) -> str:
        return f"{self.block}.{self.key}"

    def as_text(self) -> str:
        return f"{self.label}: {self.old!r} -> {self.new!r}"


@dataclass
class PreviewResult:
    """Everything a preview dialog needs to show before the user decides."""

    plot_type: str
    preset_name: str
    before_png: bytes
    after_png: bytes
    changes: List[ChangeRow]
    apply_result: presets.PresetApplyResult
    protected_violations: List[str] = field(default_factory=list)
    render_warnings: List[str] = field(default_factory=list)
    synthetic_data_notice: str = (
        "Preview drawn on the bundled synthetic example data for this plot type (CC0, generated "
        "from code). Your data, columns, statistics and thresholds are not shown and not changed.")

    @property
    def safe_to_apply(self) -> bool:
        return not self.protected_violations


# ---------------------------------------------------------------------------------------------
# Data-safety guard
# ---------------------------------------------------------------------------------------------

def protected_keys(plot_type: str) -> Dict[str, Iterable[str]]:
    """The keys of a PlotSpec that a *style* preset must never write, by block."""
    roles = list(column_fields(plot_type)) if plot_type else []
    scopes = presets.option_scopes(plot_type) if plot_type else {}
    config_options = [k for k, s in scopes.items() if s in PROTECTED_OPTION_SCOPES]
    return {
        "input_table": ("input_table",),
        "source": ("source",),
        "mapping": tuple(roles) + tuple(config_options) + tuple(sorted(presets.MAPPING_DATA_KEYS)),
        "layout": tuple(sorted(PROTECTED_LAYOUT_KEYS)),
        "statistics": tuple(sorted(STATISTICS_ANALYSIS_KEYS)),
        "annotations": ("annotations",),
        "column_annotations": ("column_annotations",),
    }


def assert_style_safe(before: Dict[str, Any], after: Dict[str, Any]) -> List[str]:
    """Return every protected key whose value differs between ``before`` and ``after``.

    Empty means the change is purely visual. The comparison is by value, so a preset that
    rewrites a threshold to the same number is (correctly) not a violation.
    """
    plot_type = str(before.get("plot_type") or after.get("plot_type") or "")
    violations: List[str] = []
    prot = protected_keys(plot_type)
    if before.get("plot_type") != after.get("plot_type"):
        violations.append("plot_type")
    for top in ("input_table", "source", "annotations", "column_annotations"):
        if before.get(top) != after.get(top):
            violations.append(top)
    for block in ("mapping", "layout", "statistics"):
        b = before.get(block) or {}
        a = after.get(block) or {}
        for key in prot[block]:
            if b.get(key) != a.get(key):
                violations.append(f"{block}.{key}")
    return violations


# ---------------------------------------------------------------------------------------------
# Change description
# ---------------------------------------------------------------------------------------------

def describe_changes(before: Dict[str, Any], after: Dict[str, Any]) -> List[ChangeRow]:
    """Flat, ordered list of every key whose value the preset changed."""
    rows: List[ChangeRow] = []
    for block in ("journal_style",):
        if before.get(block) != after.get(block):
            rows.append(ChangeRow(block, "", before.get(block), after.get(block)))
    for block in ("style", "layout", "output", "mapping", "statistics"):
        b = before.get(block) or {}
        a = after.get(block) or {}
        for key in sorted(set(b) | set(a)):
            if b.get(key) != a.get(key):
                rows.append(ChangeRow(block, key, b.get(key), a.get(key)))
    return rows


# ---------------------------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------------------------

def synthetic_spec(plot_type: str) -> Tuple[Dict[str, Any], Any, Dict[str, Any]]:
    """``(spec, dataframe, aux_frames)`` for the bundled synthetic example of ``plot_type``."""
    info, aux, spec = examples.load_example(plot_type)
    spec = copy.deepcopy(spec) if spec else registry.make_spec(plot_type, info.source_name,
                                                                 "publication")
    spec["input_table"] = info.source_name
    spec.setdefault("journal_style", "publication")
    aux_frames = {name: t.dataframe for name, t in aux.items()} or None
    return spec, info.dataframe, aux_frames


def _render_png(spec: Dict[str, Any], df, aux, *, dpi: int) -> Tuple[bytes, List[str]]:
    with matplotlib.rc_context({"figure.max_open_warning": 0}):
        result = registry.render(spec, df, aux=aux)
    try:
        png = registry.figure_to_bytes(result.figure, "png", dpi=dpi)
    finally:
        plt.close(result.figure)
    return png, list(result.warnings or [])


def preview_pair(preset: Dict[str, Any], plot_type: str, *,
                 base_spec: Optional[Dict[str, Any]] = None,
                 data: Optional[Tuple[Any, Optional[Dict[str, Any]]]] = None,
                 dpi: int = 110) -> PreviewResult:
    """Render before/after and report what the preset would change.

    Without ``data`` the preview draws the bundled synthetic example of ``plot_type``;
    ``base_spec`` then contributes only its style, layout-geometry and output blocks so the
    "before" image shows the look the user has now. With ``data=(dataframe, aux_frames)`` the
    preview draws the user's *own* table with the user's full ``base_spec`` (their groups, their
    replicate counts, their statistics) - the images live in memory only, and neither the spec
    nor the data are modified. Style-mode presets are still checked with ``assert_style_safe``.
    """
    presets.validate_preset(preset)
    if data is not None:
        if not base_spec or not base_spec.get("plot_type"):
            raise presets.PresetError("previewing on data needs the current PlotSpec")
        df, aux = data
        spec = copy.deepcopy(base_spec)
        notice = ("Preview drawn on your current data and settings. Nothing is applied until you "
                  "confirm; your data, columns, statistics and thresholds are not changed.")
    else:
        spec, df, aux = synthetic_spec(plot_type)
        notice = None
    if base_spec and data is None:
        for block in ("style", "layout", "output", "journal_style"):
            if block == "journal_style":
                if base_spec.get(block):
                    spec[block] = base_spec[block]
                continue
            carried = {k: v for k, v in (base_spec.get(block) or {}).items()
                       if block != "layout" or k not in PROTECTED_LAYOUT_KEYS}
            if carried:
                spec[block] = {**(spec.get(block) or {}), **carried}
    before = copy.deepcopy(spec)
    result = presets.apply_preset(preset, spec, columns=list(df.columns),
                                  aux_columns=(list(next(iter(aux.values())).columns)
                                               if aux else None))
    after = result.spec
    violations = assert_style_safe(before, after) if preset.get("mode") == "style" else []
    before_png, w1 = _render_png(before, df, aux, dpi=dpi)
    after_png, w2 = _render_png(after, df, aux, dpi=dpi)
    out = PreviewResult(
        plot_type=plot_type,
        preset_name=str(preset.get("name", "")),
        before_png=before_png,
        after_png=after_png,
        changes=describe_changes(before, after),
        apply_result=result,
        protected_violations=violations,
        render_warnings=sorted(set(w1) | set(w2)),
    )
    if notice:
        out.synthetic_data_notice = notice
    return out


def preview_gallery(candidates: List[Dict[str, Any]], plot_type: str, *,
                    base_spec: Optional[Dict[str, Any]] = None,
                    data: Optional[Tuple[Any, Optional[Dict[str, Any]]]] = None,
                    dpi: int = 90) -> List[PreviewResult]:
    """Several presets side by side (e.g. the group-comparison styles) on the same data.

    Each entry is a full ``PreviewResult`` so the frontend can show every candidate with its
    change list and pick one to apply through the normal guarded path. Nothing is applied here.
    """
    return [preview_pair(p, plot_type, base_spec=base_spec, data=data, dpi=dpi) for p in candidates]


def apply_with_guard(preset: Dict[str, Any], spec: Dict[str, Any], *,
                     columns: Optional[Iterable[str]] = None,
                     aux_columns: Optional[Iterable[str]] = None) -> presets.PresetApplyResult:
    """``apply_preset`` that refuses a *style* preset touching anything analytical.

    Frontends call this instead of ``apply_preset`` after the user confirms a preview; the
    guard is the last line of defence against a hand-edited preset file.
    """
    result = presets.apply_preset(preset, spec, columns=columns, aux_columns=aux_columns)
    if preset.get("mode") == "style":
        violations = assert_style_safe(spec, result.spec)
        if violations:
            raise presets.PresetError(
                "this style preset would change analytical settings, which a style preset must "
                "never do: " + ", ".join(violations))
    return result
