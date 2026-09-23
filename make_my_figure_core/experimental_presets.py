"""The experimental, evidence-derived publication preset library (read-only, opt-in).

These presets live in ``style_profiles/experimental_publication_presets/`` and are ordinary
Figure *style* presets (``.mmfpreset.json``, see :mod:`make_my_figure_core.presets`) with one
extra block, ``experimental``, that records where every value came from. They are:

* **not** part of the user's preset library (``PresetStore``) - they are bundled, read-only, and
  listed separately so nothing here changes the shipping library;
* **not** journal templates - they describe visual conventions measured in a corpus of
  published open-access figures plus the publishers' stated requirements, under neutral names;
  a preset never claims compliance, endorsement or acceptance;
* **style only** - a preset here can change typography, line and marker weights, palette, legend
  and axis geometry, and the target width. It can never change data, column roles, statistics,
  P values, transformations, normalisation, feature selection or thresholds; the loader refuses a
  file that tries (``validate_experimental_preset``).

Frontends show these under an "Experimental" heading, off by default, and always through the
preview-before-apply flow (:mod:`make_my_figure_core.preset_preview`).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from make_my_figure_core import presets
from make_my_figure_core.resources import resource_path

EXPERIMENTAL_DIR_PARTS = ("style_profiles", "experimental_publication_presets")
EXPERIMENTAL_BLOCK = "experimental"
ENV_FLAG = "MAKE_MY_FIGURE_EXPERIMENTAL_PRESETS"

NOTICE = (
    "Experimental presets describe visual conventions measured in published open-access figures "
    "and the publishers' stated artwork requirements. They are not official journal templates, "
    "carry no endorsement, and do not guarantee acceptance. They change only how a figure is "
    "drawn, never your data, statistics or thresholds. Preview before applying."
)

# Words that must not appear in a shipping preset name or description (neutral naming rule).
# ("official" is not listed: the mandatory disclaimer itself says "not an official template".)
_FORBIDDEN_NAME_WORDS = ("nature", "science", "cell", "lancet", "nejm", "jama", "plos",
                         "compliant", "approved", "ready", "endorsed", "guaranteed")

# Statistical-annotation keys that are pure geometry/typography. Everything else in the
# annotation block (content, mode, show_*, hide_nonsignificant, digits...) is the user's choice of
# scientific representation and stays out of this library.
ANNOTATION_GEOMETRY_KEYS = frozenset({
    "font_size", "line_width", "bracket_height_frac", "gap_frac", "top_margin_frac",
    "above_bar_pad_frac", "bracket_height_pt", "gap_pt", "label_offset_pt", "top_margin_pt",
})

# Blocks a style preset must not carry at all.
_FORBIDDEN_BLOCKS = ("mapping_roles", "config_options", "labels", "statistics", "annotations")

# Option keys that change what is computed rather than how it is drawn (see the capability
# audit): a style preset in this library must not carry them even though the core scope tables
# currently classify them as style.
SEMANTIC_OPTION_KEYS = frozenset({
    "error", "normalize", "log_y", "log_x", "y_scale", "x_scale", "scale", "z_score",
    "cluster_rows", "cluster_columns", "distance_metric", "linkage", "label_top_n",
    "lfc_cutoff", "p_cutoff", "threshold", "bin_width", "bins", "kde_bandwidth",
})


@dataclass
class ExperimentalPresetEntry:
    preset_id: str
    path: str
    name: str
    description: str
    plot_type: str
    universal: bool
    target_width_mm: Optional[float]
    width_class: str                 # 'single' | 'onehalf' | 'double' | 'custom'
    evidence_family: str             # neutral family key used in the research files
    evidence_summary: str
    status: str = "experimental"
    recommended_for: List[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        w = f", {self.target_width_mm:g} mm" if self.target_width_mm else ""
        return f"{self.name}  [experimental{w}]"


class ExperimentalPresetError(presets.PresetError):
    """An experimental preset file breaks a library rule."""


def experimental_dir() -> str:
    return resource_path(*EXPERIMENTAL_DIR_PARTS)


def experimental_presets_enabled() -> bool:
    """Opt-in switch. Frontends may also expose a checkbox; either turns the list on."""
    return os.environ.get(ENV_FLAG, "").strip().lower() in ("1", "true", "yes", "on")


def is_experimental(preset: Dict[str, Any]) -> bool:
    return isinstance(preset, dict) and isinstance(preset.get(EXPERIMENTAL_BLOCK), dict)


def validate_experimental_preset(preset: Dict[str, Any]) -> None:
    """The library rules, enforced on load and in the tests."""
    presets.validate_preset(preset)
    if preset.get("mode") != "style":
        raise ExperimentalPresetError("experimental presets must be style presets")
    for block in _FORBIDDEN_BLOCKS:
        if preset.get(block):
            raise ExperimentalPresetError(f"a style preset must not carry '{block}'")
    leaks = presets.preset_contains_data(preset)
    if leaks:
        raise ExperimentalPresetError(f"preset carries data-bound fields: {leaks}")
    bad = sorted(k for k in (preset.get("options") or {}) if k in SEMANTIC_OPTION_KEYS)
    if bad:
        raise ExperimentalPresetError(
            f"options that change what is computed are not allowed in this library: {bad}")
    ann = ((preset.get("statistics_display") or {}).get("annotation") or {})
    bad_ann = sorted(k for k in ann if k not in ANNOTATION_GEOMETRY_KEYS)
    if bad_ann:
        raise ExperimentalPresetError(
            "a preset may set the geometry of statistical annotations but not what they say "
            f"(stars vs P values, which comparisons are shown); not allowed: {bad_ann}")
    exp = preset.get(EXPERIMENTAL_BLOCK)
    if not isinstance(exp, dict):
        raise ExperimentalPresetError("missing 'experimental' provenance block")
    for key in ("preset_id", "evidence_family", "evidence_summary", "derived_from", "not_official"):
        if key not in exp:
            raise ExperimentalPresetError(f"experimental block lacks '{key}'")
    if exp.get("not_official") is not True:
        raise ExperimentalPresetError("experimental block must state not_official: true")
    text = f"{preset.get('name', '')} {preset.get('description', '')}".lower()
    hits = [w for w in _FORBIDDEN_NAME_WORDS if w in text.split() or f"{w}-" in text or f"{w} " in text]
    # 'cell' alone is too common a word in biology to forbid inside descriptions; only the name
    # is checked for it
    name_l = str(preset.get("name", "")).lower()
    hits = [w for w in hits if w != "cell"] + (["cell"] if "cell" in name_l.split() or "cell-" in name_l else [])
    if hits:
        raise ExperimentalPresetError(
            f"preset name/description uses journal or compliance wording {hits}; "
            "use a neutral name and keep provenance in the experimental block")
    tw = exp.get("target_width_mm")
    if tw is not None:
        try:
            tw = float(tw)
        except (TypeError, ValueError):
            raise ExperimentalPresetError("target_width_mm must be a number")
        if not (30.0 <= tw <= 300.0):
            raise ExperimentalPresetError("target_width_mm must be between 30 and 300 mm")
        cw = (preset.get("layout") or {}).get("column_width")
        from make_my_figure_core.styles.engine import resolve_width_mm
        if cw is None or resolve_width_mm(cw) is None or abs(resolve_width_mm(cw) - tw) > 0.5:
            raise ExperimentalPresetError(
                "layout.column_width must equal experimental.target_width_mm so the preset "
                "actually renders at the width it claims")
        out_w = (preset.get("output") or {}).get("width_mm")
        if out_w is not None and abs(float(out_w) - tw) > 0.5:
            raise ExperimentalPresetError("output.width_mm must equal target_width_mm")


def _entry(path: str, preset: Dict[str, Any]) -> ExperimentalPresetEntry:
    exp = preset[EXPERIMENTAL_BLOCK]
    tw = exp.get("target_width_mm")
    return ExperimentalPresetEntry(
        preset_id=str(exp["preset_id"]),
        path=path,
        name=str(preset.get("name", "")),
        description=str(preset.get("description", "")),
        plot_type=str(preset.get("plot_type", "")),
        universal=bool(preset.get("universal")),
        target_width_mm=float(tw) if tw is not None else None,
        width_class=str(exp.get("width_class", "custom")),
        evidence_family=str(exp.get("evidence_family", "")),
        evidence_summary=str(exp.get("evidence_summary", "")),
        status=str(exp.get("status", "experimental")),
        recommended_for=list(exp.get("recommended_for") or []),
    )


def list_experimental_presets(directory: Optional[str] = None,
                              plot_type: Optional[str] = None) -> List[ExperimentalPresetEntry]:
    """Bundled experimental presets, validated; invalid files are skipped, never shown."""
    directory = directory or experimental_dir()
    if not os.path.isdir(directory):
        return []
    out: List[ExperimentalPresetEntry] = []
    for fn in sorted(os.listdir(directory)):
        if not fn.endswith(".json") or fn.startswith("_"):
            continue
        path = os.path.join(directory, fn)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                preset = json.load(fh)
            validate_experimental_preset(preset)
        except Exception:  # noqa: BLE001 - a broken bundled file must not break the UI
            continue
        e = _entry(path, preset)
        if plot_type and not e.universal and e.plot_type != plot_type:
            continue
        out.append(e)
    return out


def load_experimental_preset(preset_id_or_path: str,
                             directory: Optional[str] = None) -> Dict[str, Any]:
    if os.path.exists(preset_id_or_path):
        with open(preset_id_or_path, "r", encoding="utf-8") as fh:
            preset = json.load(fh)
        validate_experimental_preset(preset)
        return preset
    for e in list_experimental_presets(directory):
        if e.preset_id == preset_id_or_path or e.name == preset_id_or_path:
            return load_experimental_preset(e.path)
    raise ExperimentalPresetError(f"no experimental preset called {preset_id_or_path!r}")


def provenance_text(preset: Dict[str, Any]) -> str:
    """Human-readable provenance for the preview dialog and the docs."""
    exp = preset.get(EXPERIMENTAL_BLOCK) or {}
    lines = [NOTICE, ""]
    lines.append(f"Evidence family: {exp.get('evidence_family', 'unknown')}")
    lines.append(f"Summary: {exp.get('evidence_summary', '')}")
    d = exp.get("derived_from") or {}
    if d:
        lines.append(
            f"Derived from {d.get('papers', '?')} papers / {d.get('figures', '?')} figures / "
            f"{d.get('panels', '?')} panels measured; official requirements: "
            f"{d.get('official_sources', 'none cited')}.")
    if exp.get("target_width_mm"):
        lines.append(f"Target width: {exp['target_width_mm']:g} mm ({exp.get('width_class', 'custom')}), "
                     f"source: {exp.get('width_source', 'not stated')}")
    ev = exp.get("value_evidence") or {}
    if ev:
        lines.append("Per-value evidence class (observed / inferred / estimated / official):")
        for k, v in ev.items():
            lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def clone_for_lab(preset: Dict[str, Any], *, name: str, description: str = "") -> Dict[str, Any]:
    """A user-library copy of an experimental preset ("Save as my lab preset").

    The copy is an ordinary style preset the user owns and may edit; the experimental block is
    replaced by a ``provenance`` note so the origin stays visible without the copy being listed
    as experimental. Nothing analytical is added - the copy passes the same style-only rules.
    """
    import copy
    import datetime as _dt

    validate_experimental_preset(preset)
    exp = preset[EXPERIMENTAL_BLOCK]
    out = copy.deepcopy(preset)
    out.pop(EXPERIMENTAL_BLOCK, None)
    out["name"] = name.strip() or f"{preset.get('name', 'preset')} (lab copy)"
    out["description"] = description.strip() or preset.get("description", "")
    out["created"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    out.setdefault("notes", []).append(
        f"lab copy of experimental preset '{exp.get('preset_id')}' (evidence family "
        f"'{exp.get('evidence_family')}'); {NOTICE}")
    out["provenance"] = {"experimental_preset_id": exp.get("preset_id"),
                         "evidence_family": exp.get("evidence_family"),
                         "target_width_mm": exp.get("target_width_mm"),
                         "copied_from_app_version": preset.get("app_version")}
    presets.validate_preset(out)
    return out


# ---------------------------------------------------------------------------------------------
# Companion Figure Builder layout presets (panel letters, figure width) - same rules, same folder
# ---------------------------------------------------------------------------------------------

@dataclass
class ExperimentalLayoutEntry:
    preset_id: str
    path: str
    name: str
    description: str
    fig_width_mm: Optional[float]
    label_style: str
    label_size: Optional[float]
    label_weight: str
    evidence_family: str
    evidence_summary: str

    @property
    def label(self) -> str:
        w = f", {self.fig_width_mm:g} mm" if self.fig_width_mm else ""
        return f"{self.name}  [experimental layout{w}]"


def validate_experimental_layout_preset(preset: Dict[str, Any]) -> None:
    presets.validate_layout_preset(preset)
    exp = preset.get(EXPERIMENTAL_BLOCK)
    if not isinstance(exp, dict):
        raise ExperimentalPresetError("missing 'experimental' provenance block")
    for key in ("preset_id", "evidence_family", "evidence_summary", "derived_from", "not_official"):
        if key not in exp:
            raise ExperimentalPresetError(f"experimental block lacks '{key}'")
    if exp.get("not_official") is not True:
        raise ExperimentalPresetError("experimental block must state not_official: true")
    name_l = str(preset.get("name", "")).lower()
    hits = [w for w in _FORBIDDEN_NAME_WORDS if w in name_l.split() or f"{w}-" in name_l]
    if hits:
        raise ExperimentalPresetError(f"layout preset name uses journal or compliance wording {hits}")
    lay = preset.get("layout") or {}
    if lay.get("label_style") not in (None, "A", "a", "1"):
        raise ExperimentalPresetError("label_style must be one of A, a, 1")
    if preset.get("panel_sizes"):
        raise ExperimentalPresetError("a bundled layout preset carries no panel sizes (they belong to a figure)")


def list_experimental_layout_presets(directory: Optional[str] = None) -> List[ExperimentalLayoutEntry]:
    directory = directory or experimental_dir()
    if not os.path.isdir(directory):
        return []
    out: List[ExperimentalLayoutEntry] = []
    for fn in sorted(os.listdir(directory)):
        if not fn.endswith(presets.LAYOUT_PRESET_EXTENSION):
            continue
        path = os.path.join(directory, fn)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                preset = json.load(fh)
            validate_experimental_layout_preset(preset)
        except Exception:  # noqa: BLE001
            continue
        exp = preset[EXPERIMENTAL_BLOCK]
        lay = preset.get("layout") or {}
        out.append(ExperimentalLayoutEntry(
            preset_id=str(exp["preset_id"]), path=path, name=str(preset.get("name", "")),
            description=str(preset.get("description", "")),
            fig_width_mm=(float(lay["fig_width_mm"]) if lay.get("fig_width_mm") else None),
            label_style=str(lay.get("label_style", "A")),
            label_size=(float(lay["label_size"]) if lay.get("label_size") else None),
            label_weight=str(lay.get("label_weight", "bold")),
            evidence_family=str(exp.get("evidence_family", "")),
            evidence_summary=str(exp.get("evidence_summary", "")),
        ))
    return out


def load_experimental_layout_preset(preset_id_or_path: str, directory: Optional[str] = None) -> Dict[str, Any]:
    if os.path.exists(preset_id_or_path):
        with open(preset_id_or_path, "r", encoding="utf-8") as fh:
            preset = json.load(fh)
        validate_experimental_layout_preset(preset)
        return preset
    for e in list_experimental_layout_presets(directory):
        if e.preset_id == preset_id_or_path or e.name == preset_id_or_path:
            return load_experimental_layout_preset(e.path)
    raise ExperimentalPresetError(f"no experimental layout preset called {preset_id_or_path!r}")
