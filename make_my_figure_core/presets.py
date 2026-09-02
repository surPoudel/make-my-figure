"""Figure Presets: save a figure's configuration once, apply it to new data later.

A PlotSpec is a complete, reproducible record of *one* figure - it names the data table, the
columns, the thresholds, the styling, everything. That makes it the wrong thing to hand a
colleague who wants their own data to look the same: it carries a table name that does not exist
on their machine, column names that do not match, and thresholds that were chosen for a different
experiment. A **Figure Preset** is the part of a PlotSpec that is worth carrying between figures,
with the data-bound part separated out.

The difficulty is that the PlotSpec does not keep those parts apart. ``mapping`` holds column roles
(``x``, ``group``) alongside options (``bin_width``, ``draw_style``); ``layout`` holds the axis
labels (text about the data) alongside the tick angles and margins (geometry); ``statistics``
holds the test (analysis) alongside how its result is drawn (display). So this module classifies
every key of every block by *scope*, using the registry rather than a hand-written list:

* column roles come from ``ui_hints.column_fields``;
* each option's scope comes from ``ui_hints.Option.scope`` - declared at the option, so it cannot
  drift from the option itself;
* the layout, output and statistics blocks are split on fixed key sets kept here, because those
  blocks are shared by every plot type.

Two preset modes fall out of that:

``style``
    Portable visual configuration: typography, palette, line widths, layout geometry, legend and
    colorbar placement, export defaults, and the *visual* plot options. No table name, no column
    names, no thresholds, no axis limits, no data. This is what a lab saves as
    ``Lab_Default_Heatmap.mmfpreset.json`` and applies for years.

``full``
    Everything in ``style`` plus the data-bound configuration: column roles, thresholds and other
    analytical options, axis labels, axis limits, the statistics test, and manual annotations.
    Applying it to a different table applies what fits, reports every column role the new table
    cannot satisfy, and never guesses a substitute column.

Neither mode ever contains row-level values, the table name, or worksheet provenance.

Backward compatibility: ``load_preset`` also accepts a raw PlotSpec or an exported
``*.plot_spec.json`` sidecar and converts it to a full preset, so a figure saved before presets
existed is a preset already. Existing PlotSpec files keep loading through their own path untouched.
"""

from __future__ import annotations

import copy
import datetime as _dt
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from make_my_figure_core import ui_hints
from make_my_figure_core.version import __version__

PRESET_FORMAT = "make_my_figure.figure_preset"
PRESET_FORMAT_VERSION = 1
PRESET_EXTENSION = ".mmfpreset.json"

LAYOUT_PRESET_FORMAT = "make_my_figure.figure_layout_preset"
LAYOUT_PRESET_FORMAT_VERSION = 1
LAYOUT_PRESET_EXTENSION = ".mmflayout.json"

PRESET_MODES = ("style", "full")

# ---------------------------------------------------------------------------------------------
# Scope tables for the blocks every plot type shares.
# ---------------------------------------------------------------------------------------------

# layout keys that describe geometry and placement - portable between figures
LAYOUT_STYLE_KEYS = frozenset({
    "column_width", "aspect",
    "x_tick_rotation", "y_tick_rotation", "x_tick_horizontal_alignment",
    "x_tick_vertical_alignment", "x_tick_pad", "y_tick_pad",
    "x_label_pad", "y_label_pad", "title_pad", "y_label_rotation",
    "margin_left", "margin_right", "margin_top", "margin_bottom",
    "subplot_wspace", "subplot_hspace",
    "legend_location", "auto_fix_layout",
    "colorbar_location", "colorbar_pad", "colorbar_shrink", "colorbar_fraction",
})
# layout keys that are text about the data - full configuration only
LAYOUT_CONFIG_KEYS = frozenset({"title", "x_label", "y_label"})

# mapping keys that are neither roles nor registered options but are still data-bound
# (click-to-label picks and their offsets, UpSet's set list, colorbar geometry is style)
MAPPING_DATA_KEYS = frozenset({
    "selected_points", "selected_labels", "label_offsets", "point_offsets", "sets",
})
MAPPING_STYLE_EXTRA_KEYS = frozenset({
    "colorbar_location", "colorbar_pad", "colorbar_shrink", "colorbar_fraction",
})

# output keys: all of them are export defaults, i.e. style
OUTPUT_KEYS = ("formats", "width_mm", "height_mm", "dpi")

# statistics: the display block is style, the rest describes the analysis
STATS_DISPLAY_KEYS = ("annotation",)
STATS_NEVER_KEYS = frozenset({"source", "_annotation_info"})

# StyleProfile override keys a preset may carry. Anything else in spec["style"] is dropped with
# a note rather than written blindly, so a stray key cannot masquerade as a style token.
STYLE_TOKEN_KEYS = frozenset({
    "font_family", "base_font_pt", "axis_font_pt", "tick_label_pt", "legend_pt",
    "legend_title_pt", "title_font_pt", "annotation_pt", "panel_label_pt", "font_weight",
    "text_color", "spine_width_pt", "tick_width", "tick_length", "tick_direction",
    "show_top_spine", "show_right_spine", "grid", "grid_width", "grid_alpha",
    "line_width_pt", "marker_size", "marker_edge_width", "marker_alpha",
    "regression_line_width", "errorbar_line_width", "errorbar_capsize", "bar_edge_width",
    "legend_frameon", "legend_loc", "legend_outside", "legend_ncol",
    "palette_name", "palette", "sequential_cmap", "diverging_cmap",
})

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._ -]+")


class PresetError(ValueError):
    """A preset file or preset operation is invalid."""


# ---------------------------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------------------------

@dataclass
class MappingSplit:
    """A plot type's ``mapping`` block sorted by scope."""

    roles: Dict[str, Any] = field(default_factory=dict)          # column names - data-bound
    style_options: Dict[str, Any] = field(default_factory=dict)  # visual options
    config_options: Dict[str, Any] = field(default_factory=dict) # analytical options
    data_extras: Dict[str, Any] = field(default_factory=dict)    # picks/offsets/sets - data
    unknown: Dict[str, Any] = field(default_factory=dict)        # not registered anywhere


def option_scopes(plot_type: str) -> Dict[str, str]:
    """``{option_key: scope}`` for every registered option of ``plot_type``."""
    return {o.key: o.scope for o in ui_hints.options(plot_type)}


def role_keys(plot_type: str) -> List[str]:
    """Every mapping key that names a column (or list of columns) for ``plot_type``."""
    roles = list(ui_hints.column_fields(plot_type))
    if plot_type == "pca_scatter_from_matrix":
        roles += [k for k in ui_hints.PCA_METADATA_FIELDS if k not in roles]
    # every matrix-style plot may carry an explicit value-column list
    if "value_columns" not in roles:
        roles.append("value_columns")
    return roles


def split_mapping(plot_type: str, mapping: Optional[Dict[str, Any]]) -> MappingSplit:
    """Sort a ``mapping`` block by scope using the registry, never a per-plot list."""
    out = MappingSplit()
    scopes = option_scopes(plot_type)
    roles = set(role_keys(plot_type))
    for key, value in (mapping or {}).items():
        if key in roles:
            out.roles[key] = value
        elif key in MAPPING_DATA_KEYS:
            out.data_extras[key] = value
        elif key in scopes:
            (out.style_options if scopes[key] == "style" else out.config_options)[key] = value
        elif key in MAPPING_STYLE_EXTRA_KEYS:
            out.style_options[key] = value
        else:
            # Unregistered: treated as configuration, because the only safe assumption about an
            # unknown key is that it might depend on the data.
            out.unknown[key] = value
    return out


def _split_layout(layout: Optional[Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    style, config = {}, {}
    for key, value in (layout or {}).items():
        if value in (None, ""):
            continue
        if key in LAYOUT_STYLE_KEYS:
            style[key] = value
        elif key in LAYOUT_CONFIG_KEYS:
            config[key] = value
        else:
            style[key] = value      # an unknown layout key is geometry until shown otherwise
    return style, config


def _split_statistics(stats: Optional[Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """``(display, analysis)`` - display is how results are drawn, analysis is what was tested."""
    display, analysis = {}, {}
    for key, value in (stats or {}).items():
        if key in STATS_NEVER_KEYS:
            continue
        if key in STATS_DISPLAY_KEYS:
            display[key] = copy.deepcopy(value)
        else:
            analysis[key] = copy.deepcopy(value)
    # the analysis block is only meaningful when statistics were on
    if not analysis.get("enabled"):
        analysis = {}
    return display, analysis


def _clean_style_tokens(style: Optional[Dict[str, Any]], notes: List[str]) -> Dict[str, Any]:
    out = {}
    for key, value in (style or {}).items():
        if value is None:
            continue
        if key in STYLE_TOKEN_KEYS:
            out[key] = value
        else:
            notes.append(f"style key '{key}' is not a known style token and was not saved")
    return out


# ---------------------------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------------------------

def extract_preset(spec: Dict[str, Any], *, mode: str = "style", name: str = "",
                   description: str = "") -> Dict[str, Any]:
    """Build a Figure Preset from a PlotSpec.

    ``mode`` is ``"style"`` (portable visual configuration) or ``"full"`` (adds the data-bound
    configuration: roles, thresholds, labels, statistics, manual annotations). Neither mode
    copies the table name, worksheet provenance, or any row-level value.
    """
    if mode not in PRESET_MODES:
        raise PresetError(f"mode must be one of {PRESET_MODES}, got {mode!r}")
    if not isinstance(spec, dict) or not spec.get("plot_type"):
        raise PresetError("a preset needs a PlotSpec with a 'plot_type'")
    plot_type = str(spec["plot_type"])
    notes: List[str] = []

    split = split_mapping(plot_type, spec.get("mapping"))
    layout_style, layout_config = _split_layout(spec.get("layout"))
    stats_display, stats_analysis = _split_statistics(spec.get("statistics"))
    output = {k: v for k, v in (spec.get("output") or {}).items() if k in OUTPUT_KEYS}

    preset: Dict[str, Any] = {
        "format": PRESET_FORMAT,
        "format_version": PRESET_FORMAT_VERSION,
        "name": name or f"{plot_type} preset",
        "description": description,
        "mode": mode,
        "plot_type": plot_type,
        "journal_style": spec.get("journal_style", "publication"),
        "created": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "app_version": __version__,
        "style": _clean_style_tokens(spec.get("style"), notes),
        "layout": layout_style,
        "options": split.style_options,
        "output": output,
        "statistics_display": stats_display,
    }
    if mode == "full":
        preset["mapping_roles"] = copy.deepcopy(split.roles)
        preset["config_options"] = {**split.config_options, **split.unknown}
        preset["labels"] = layout_config
        preset["statistics"] = stats_analysis
        anns = spec.get("annotations")
        preset["annotations"] = copy.deepcopy(anns) if anns else []
    if notes:
        preset["notes"] = notes
    return preset


# ---------------------------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------------------------

@dataclass
class PresetApplyResult:
    """What ``apply_preset`` did, so a frontend can tell the user honestly."""

    spec: Dict[str, Any]
    applied: List[str] = field(default_factory=list)       # keys written, by block
    skipped: List[str] = field(default_factory=list)       # keys dropped, with reasons
    unresolved_roles: Dict[str, Any] = field(default_factory=dict)  # role -> wanted column(s)
    warnings: List[str] = field(default_factory=list)

    @property
    def needs_remapping(self) -> bool:
        return bool(self.unresolved_roles)


def _columns_present(wanted: Any, columns: Optional[Iterable[str]]) -> Tuple[bool, Any]:
    """Does the new table have the column(s) a role wants? Returns (ok, present_subset)."""
    if columns is None:
        return True, wanted           # no table to check against: caller takes responsibility
    cols = {str(c) for c in columns}
    if isinstance(wanted, (list, tuple)):
        present = [c for c in wanted if str(c) in cols]
        return (len(present) == len(wanted) and bool(present)), present
    return (str(wanted) in cols), wanted


def apply_preset(preset: Dict[str, Any], spec: Dict[str, Any], *,
                 columns: Optional[Iterable[str]] = None,
                 aux_columns: Optional[Iterable[str]] = None,
                 strict_plot_type: bool = False) -> PresetApplyResult:
    """Apply ``preset`` onto ``spec`` (which already names the *new* table and its columns).

    Returns a new spec - ``spec`` is not modified. Column roles from a full preset are applied
    only when the new table has that column; anything missing is returned in
    ``unresolved_roles`` for the frontend to ask about. Nothing is ever mapped to a
    different column than the preset named. Roles that name columns of an auxiliary table (the
    PCA sample-metadata colour/shape) are checked against ``aux_columns`` when given, and applied
    unchecked when the caller has no metadata to check against.

    A style preset made for another plot type still applies its universal parts (typography,
    palette, layout geometry, legend, export) - that is the "make every figure in the lab look
    like this" case - while its plot-specific options are dropped and listed. A *full* preset
    for another plot type is refused: its roles and thresholds mean nothing elsewhere.
    """
    validate_preset(preset)
    new = copy.deepcopy(spec)
    res = PresetApplyResult(spec=new)
    target = str(new.get("plot_type") or "")
    same_type = (preset["plot_type"] == target)
    if not same_type:
        if preset.get("mode") == "full" or strict_plot_type:
            raise PresetError(
                f"this is a full configuration for '{preset['plot_type']}' and cannot be "
                f"applied to a '{target}'. Save a Figure *style* preset to share settings "
                "across plot types.")
        res.warnings.append(
            f"Preset was saved for '{preset['plot_type']}'; only its universal settings "
            f"(typography, palette, layout, legend, export) were applied to this '{target}'.")

    # --- style tokens ---------------------------------------------------------------------
    style_tokens = {k: v for k, v in (preset.get("style") or {}).items() if k in STYLE_TOKEN_KEYS}
    if style_tokens:
        new["style"] = {**(new.get("style") or {}), **style_tokens}
        res.applied += [f"style.{k}" for k in style_tokens]
    if preset.get("journal_style"):
        new["journal_style"] = preset["journal_style"]

    # --- layout geometry ------------------------------------------------------------------
    layout = dict(new.get("layout") or {})
    for k, v in (preset.get("layout") or {}).items():
        layout[k] = v
        res.applied.append(f"layout.{k}")

    # --- output defaults ------------------------------------------------------------------
    if preset.get("output"):
        new["output"] = {**(new.get("output") or {}), **preset["output"]}
        res.applied += [f"output.{k}" for k in preset["output"]]

    # --- visual options -------------------------------------------------------------------
    mapping = dict(new.get("mapping") or {})
    scopes = option_scopes(target)
    for k, v in (preset.get("options") or {}).items():
        if k in scopes or k in MAPPING_STYLE_EXTRA_KEYS:
            mapping[k] = v
            res.applied.append(f"options.{k}")
        else:
            res.skipped.append(f"options.{k}: not an option of '{target}'")

    # --- statistics display ----------------------------------------------------------------
    if preset.get("statistics_display"):
        stats = dict(new.get("statistics") or {})
        for k, v in preset["statistics_display"].items():
            stats[k] = copy.deepcopy(v)
            res.applied.append(f"statistics.{k}")
        new["statistics"] = stats

    # --- full configuration ---------------------------------------------------------------
    if preset.get("mode") == "full" and same_type:
        roles_ok = set(role_keys(target))
        aux_roles = set(ui_hints.PCA_METADATA_FIELDS) if target == "pca_scatter_from_matrix" else set()
        for role, wanted in (preset.get("mapping_roles") or {}).items():
            if role not in roles_ok:
                res.skipped.append(f"mapping.{role}: not a column role of '{target}'")
                continue
            ok, present = _columns_present(wanted, aux_columns if role in aux_roles else columns)
            if ok:
                mapping[role] = copy.deepcopy(wanted)
                res.applied.append(f"mapping.{role}")
            else:
                res.unresolved_roles[role] = wanted
                res.warnings.append(
                    f"Column role '{role}' wanted {wanted!r}, which the new table does not "
                    "have. Choose a column for it - nothing was substituted.")
        for k, v in (preset.get("config_options") or {}).items():
            mapping[k] = v
            res.applied.append(f"options.{k}")
        for k, v in (preset.get("labels") or {}).items():
            layout[k] = v
            res.applied.append(f"layout.{k}")
        if preset.get("statistics"):
            stats = {**(new.get("statistics") or {}), **copy.deepcopy(preset["statistics"])}
            # a statistics block that names columns is data-bound too
            for col_key in ("group_column", "subgroup_column", "subject_column",
                            "reference_group"):
                val = stats.get(col_key)
                if val and col_key != "reference_group" and columns is not None \
                        and str(val) not in {str(c) for c in columns}:
                    res.unresolved_roles[f"statistics.{col_key}"] = val
                    res.warnings.append(
                        f"Statistics column '{col_key}' wanted {val!r}, which the new table "
                        "does not have. Choose a column for it - nothing was substituted.")
                    stats[col_key] = None
            new["statistics"] = stats
            res.applied.append("statistics")
        if preset.get("annotations"):
            new["annotations"] = copy.deepcopy(preset["annotations"])
            res.applied.append("annotations")
            res.warnings.append(
                "Manual annotations were restored at their saved positions; those positions "
                "were chosen for the original data and may need moving.")

    new["mapping"] = mapping
    if layout:
        new["layout"] = layout
    # A preset never carries these - make sure a spec derived from one never gains them either.
    for never in ("input_table_from_preset",):
        new.pop(never, None)
    return res


def universal_preset_from(preset: Dict[str, Any], *, name: str = "") -> Dict[str, Any]:
    """The plot-type-independent part of a style preset, for sharing across figure types."""
    validate_preset(preset)
    out = extract_preset({"plot_type": preset["plot_type"], "mapping": {},
                          "style": preset.get("style"), "layout": preset.get("layout"),
                          "output": preset.get("output"),
                          "journal_style": preset.get("journal_style")},
                         mode="style", name=name or f"{preset.get('name', 'preset')} (universal)")
    out["options"] = {}
    out["universal"] = True
    return out


# ---------------------------------------------------------------------------------------------
# Validation, files, legacy inputs
# ---------------------------------------------------------------------------------------------

def validate_preset(preset: Any) -> None:
    if not isinstance(preset, dict):
        raise PresetError("a preset must be a JSON object")
    if preset.get("format") != PRESET_FORMAT:
        raise PresetError(
            f"not a Figure Preset (format is {preset.get('format')!r}); expected {PRESET_FORMAT!r}")
    try:
        version = int(preset.get("format_version", 0))
    except (TypeError, ValueError):
        raise PresetError("format_version must be an integer")
    if version > PRESET_FORMAT_VERSION:
        raise PresetError(
            f"this preset was written by a newer version (format {version}); "
            f"this build reads up to format {PRESET_FORMAT_VERSION}")
    if preset.get("mode") not in PRESET_MODES:
        raise PresetError(f"mode must be one of {PRESET_MODES}")
    if not preset.get("plot_type"):
        raise PresetError("preset has no plot_type")
    for block in ("style", "layout", "options", "output", "statistics_display"):
        if block in preset and not isinstance(preset[block], dict):
            raise PresetError(f"preset block '{block}' must be an object")


def preset_contains_data(preset: Dict[str, Any]) -> List[str]:
    """Names of data-bearing fields present - must be empty for any preset this module writes.

    Used by the QC harness and by ``validate_preset`` callers that want the stronger check.
    """
    hits = []
    for key in ("input_table", "source", "column_annotations", "render_metadata", "data",
                "rows", "table", "dataframe"):
        if key in preset:
            hits.append(key)
    for key in MAPPING_DATA_KEYS:
        if key in (preset.get("options") or {}) or key in (preset.get("config_options") or {}):
            hits.append(f"options.{key}")
    if preset.get("mode") == "style":
        if preset.get("mapping_roles") or preset.get("labels") or preset.get("config_options"):
            hits.append("style preset carries full-configuration blocks")
    return hits


def coerce_to_preset(obj: Dict[str, Any], *, name: str = "") -> Dict[str, Any]:
    """Accept a preset, a raw PlotSpec, or an exported sidecar and return a preset.

    This is the backward-compatibility path: a figure saved before presets existed is a *full*
    preset already, it just has not been sorted by scope yet.
    """
    if not isinstance(obj, dict):
        raise PresetError("expected a JSON object")
    if obj.get("format") == PRESET_FORMAT:
        validate_preset(obj)
        return obj
    if "plot_spec" in obj and isinstance(obj["plot_spec"], dict):     # exported sidecar
        obj = obj["plot_spec"]
    if "plot_type" in obj and "mapping" in obj:                        # raw PlotSpec
        from make_my_figure_core.styles.engine import normalize_style_name
        spec = dict(obj)
        if spec.get("journal_style"):
            spec["journal_style"] = normalize_style_name(spec["journal_style"])
        preset = extract_preset(spec, mode="full",
                                name=name or f"{spec['plot_type']} (from PlotSpec)")
        preset.setdefault("notes", []).append(
            "converted from a PlotSpec; the table name and provenance were not carried over")
        return preset
    raise PresetError("this file is neither a Figure Preset nor a PlotSpec")


def preset_to_json(preset: Dict[str, Any]) -> str:
    return json.dumps(preset, indent=2, sort_keys=False)


def save_preset(preset: Dict[str, Any], path: str) -> str:
    validate_preset(preset)
    leaks = preset_contains_data(preset)
    if leaks:
        raise PresetError(f"refusing to write a preset that carries data: {leaks}")
    if not path.endswith(PRESET_EXTENSION) and not path.endswith(".json"):
        path = path + PRESET_EXTENSION
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(preset_to_json(preset))
    return path


def load_preset(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        obj = json.load(fh)
    return coerce_to_preset(obj, name=os.path.basename(path).split(".")[0])


def load_preset_bytes(data: bytes, *, name: str = "") -> Dict[str, Any]:
    return coerce_to_preset(json.loads(data.decode("utf-8")), name=name)


def safe_filename(name: str) -> str:
    cleaned = _SAFE_NAME.sub("_", (name or "preset").strip()).replace(" ", "_")
    cleaned = re.sub(r"_+", "_", cleaned).strip("._") or "preset"
    return cleaned


# ---------------------------------------------------------------------------------------------
# The user's preset library - one directory, shared by every frontend
# ---------------------------------------------------------------------------------------------

def default_preset_dir() -> str:
    """Where user presets live. ``MAKE_MY_FIGURE_PRESETS`` overrides (tests, portable installs)."""
    env = os.environ.get("MAKE_MY_FIGURE_PRESETS")
    if env:
        return env
    home = os.path.expanduser("~")
    # follow each platform's convention for per-user application data
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
        return os.path.join(base, "MakeMyFigure", "presets")
    if sys.platform == "darwin":
        return os.path.join(home, "Library", "Application Support", "MakeMyFigure", "presets")
    xdg = os.environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
    return os.path.join(xdg, "make_my_figure", "presets")


@dataclass
class PresetEntry:
    path: str
    name: str
    plot_type: str
    mode: str
    universal: bool = False
    created: str = ""

    @property
    def label(self) -> str:
        scope = "universal" if self.universal else ("style" if self.mode == "style" else "full")
        return f"{self.name}  [{scope}]"


class PresetStore:
    """The saved-preset library: list, save, delete, import, export."""

    def __init__(self, directory: Optional[str] = None):
        self.directory = directory or default_preset_dir()

    def _ensure(self) -> None:
        os.makedirs(self.directory, exist_ok=True)

    def list(self, plot_type: Optional[str] = None, *,
             include_universal: bool = True) -> List[PresetEntry]:
        """Presets for ``plot_type`` (all when None); universal style presets are always shown."""
        self._ensure()
        out: List[PresetEntry] = []
        for fn in sorted(os.listdir(self.directory)):
            if not fn.endswith(".json"):
                continue
            path = os.path.join(self.directory, fn)
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    p = json.load(fh)
                validate_preset(p)
            except Exception:  # noqa: BLE001 - a foreign file in the folder is not an error
                continue
            universal = bool(p.get("universal"))
            if plot_type and p.get("plot_type") != plot_type and not (universal and include_universal):
                continue
            out.append(PresetEntry(path=path, name=str(p.get("name") or fn), plot_type=p["plot_type"],
                                   mode=p["mode"], universal=universal,
                                   created=str(p.get("created", ""))))
        return out

    def path_for(self, preset: Dict[str, Any]) -> str:
        stem = safe_filename(f"{preset.get('name', 'preset')}")
        return os.path.join(self.directory, f"{stem}{PRESET_EXTENSION}")

    def save(self, preset: Dict[str, Any], *, overwrite: bool = True) -> str:
        self._ensure()
        path = self.path_for(preset)
        if os.path.exists(path) and not overwrite:
            raise PresetError(f"a preset named {preset.get('name')!r} already exists")
        return save_preset(preset, path)

    def load(self, path_or_name: str) -> Dict[str, Any]:
        if os.path.exists(path_or_name):
            return load_preset(path_or_name)
        for entry in self.list():
            if entry.name == path_or_name:
                return load_preset(entry.path)
        raise PresetError(f"no preset called {path_or_name!r}")

    def delete(self, path_or_name: str) -> bool:
        target = path_or_name if os.path.exists(path_or_name) else None
        if target is None:
            for entry in self.list():
                if entry.name == path_or_name:
                    target = entry.path
                    break
        if target is None or not os.path.abspath(target).startswith(os.path.abspath(self.directory)):
            return False
        os.remove(target)
        return True

    def import_file(self, src_path: str, *, rename: str = "") -> str:
        preset = load_preset(src_path)
        if rename:
            preset["name"] = rename
        return self.save(preset)

    def export_file(self, path_or_name: str, dest_path: str) -> str:
        return save_preset(self.load(path_or_name), dest_path)


# ---------------------------------------------------------------------------------------------
# Figure Builder layout presets - the composite's geometry without its panels
# ---------------------------------------------------------------------------------------------

def extract_layout_preset(mpf, *, name: str = "", description: str = "") -> Dict[str, Any]:
    """A reusable multi-panel layout: grid, sizes, spacing, label style, fonts. No content.

    Per-panel sizes are kept positionally so a "wide top panel + two bottom panels" layout can be
    reused; nothing about what the panels showed is saved. That is the FigureSpec's job.
    """
    layout = mpf.layout.to_dict()
    return {
        "format": LAYOUT_PRESET_FORMAT,
        "format_version": LAYOUT_PRESET_FORMAT_VERSION,
        "name": name or f"{len(mpf.panels)}-panel layout",
        "description": description,
        "created": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "app_version": __version__,
        "n_panels": len(mpf.panels),
        "layout": layout,
        "panel_sizes": [{"width_in": p.width_in, "height_in": p.height_in} for p in mpf.panels],
    }


def validate_layout_preset(preset: Any) -> None:
    if not isinstance(preset, dict) or preset.get("format") != LAYOUT_PRESET_FORMAT:
        raise PresetError("not a Figure Builder layout preset")
    if int(preset.get("format_version", 0)) > LAYOUT_PRESET_FORMAT_VERSION:
        raise PresetError("layout preset written by a newer version")
    if not isinstance(preset.get("layout"), dict):
        raise PresetError("layout preset has no layout block")
    for forbidden in ("panels", "figure", "plot_spec", "table"):
        if forbidden in preset:
            raise PresetError(f"a layout preset must not carry panel content ('{forbidden}')")


@dataclass
class LayoutApplyResult:
    warnings: List[str] = field(default_factory=list)


def apply_layout_preset(preset: Dict[str, Any], mpf) -> LayoutApplyResult:
    """Apply a layout preset to an existing composite in place. Panels keep their content."""
    from make_my_figure_core.panels.models import FigureLayout

    validate_layout_preset(preset)
    res = LayoutApplyResult()
    mpf.layout = FigureLayout.from_dict(preset["layout"])
    sizes = preset.get("panel_sizes") or []
    n_have, n_want = len(mpf.panels), len(sizes)
    for panel, size in zip(mpf.panels, sizes):
        panel.width_in = size.get("width_in")
        panel.height_in = size.get("height_in")
    if n_have != n_want and sizes:
        res.warnings.append(
            f"Layout was saved for {n_want} panel(s) and this figure has {n_have}; "
            f"{min(n_have, n_want)} panel size(s) were applied and the rest left as they were.")
    mpf.autolabel()
    return res


def save_layout_preset(preset: Dict[str, Any], path: str) -> str:
    validate_layout_preset(preset)
    if not path.endswith(".json"):
        path += LAYOUT_PRESET_EXTENSION
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(preset, fh, indent=2)
    return path


def load_layout_preset(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        obj = json.load(fh)
    if isinstance(obj, dict) and "figure" in obj and isinstance(obj["figure"], dict):
        # an exported FigureSpec: take its geometry, leave its panels behind
        fig = obj["figure"]
        preset = {
            "format": LAYOUT_PRESET_FORMAT, "format_version": LAYOUT_PRESET_FORMAT_VERSION,
            "name": f"{fig.get('name', 'figure')} layout", "description": "",
            "created": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "app_version": __version__,
            "n_panels": len(fig.get("panels") or []),
            "layout": fig.get("layout") or {},
            "panel_sizes": [{"width_in": p.get("width_in"), "height_in": p.get("height_in")}
                            for p in (fig.get("panels") or [])],
        }
        return preset
    validate_layout_preset(obj)
    return obj


class LayoutPresetStore(PresetStore):
    """Same library folder, different file kind."""

    def list(self, plot_type=None, *, include_universal=True):  # noqa: ARG002 - signature parity
        self._ensure()
        out = []
        for fn in sorted(os.listdir(self.directory)):
            if not fn.endswith(LAYOUT_PRESET_EXTENSION):
                continue
            path = os.path.join(self.directory, fn)
            try:
                p = load_layout_preset(path)
            except Exception:  # noqa: BLE001
                continue
            out.append(PresetEntry(path=path, name=str(p.get("name") or fn), plot_type="figure_builder",
                                   mode="layout", created=str(p.get("created", ""))))
        return out

    def path_for(self, preset):
        return os.path.join(self.directory, f"{safe_filename(preset.get('name', 'layout'))}"
                                            f"{LAYOUT_PRESET_EXTENSION}")

    def save(self, preset, *, overwrite=True):
        self._ensure()
        path = self.path_for(preset)
        if os.path.exists(path) and not overwrite:
            raise PresetError(f"a layout preset named {preset.get('name')!r} already exists")
        return save_layout_preset(preset, path)

    def load(self, path_or_name):
        if os.path.exists(path_or_name):
            return load_layout_preset(path_or_name)
        for entry in self.list():
            if entry.name == path_or_name:
                return load_layout_preset(entry.path)
        raise PresetError(f"no layout preset called {path_or_name!r}")


__all__ = [
    "PRESET_FORMAT", "PRESET_FORMAT_VERSION", "PRESET_EXTENSION", "PRESET_MODES",
    "LAYOUT_PRESET_FORMAT", "LAYOUT_PRESET_EXTENSION",
    "LAYOUT_STYLE_KEYS", "LAYOUT_CONFIG_KEYS", "STYLE_TOKEN_KEYS",
    "PresetError", "MappingSplit", "PresetApplyResult", "PresetEntry", "PresetStore",
    "LayoutPresetStore", "LayoutApplyResult",
    "split_mapping", "option_scopes", "role_keys",
    "extract_preset", "apply_preset", "universal_preset_from",
    "validate_preset", "preset_contains_data", "coerce_to_preset",
    "save_preset", "load_preset", "load_preset_bytes", "preset_to_json", "safe_filename",
    "default_preset_dir",
    "extract_layout_preset", "apply_layout_preset", "validate_layout_preset",
    "save_layout_preset", "load_layout_preset",
]
