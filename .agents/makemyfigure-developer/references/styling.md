# Styling: the Publication style engine and how renderers consume it

Written 2026-09-17 against `main` (bb45c12) in this checkout. Every claim below
was read from the code cited; re-check with the commands at the end before
relying on it.

## 1. Where the code lives

| Path | Role |
|---|---|
| `make_my_figure_core/styles/engine.py` | `StyleProfile` dataclass (all tokens), palettes, `WIDTH_PRESETS_MM`, `load_profile`, `list_profiles`, legacy-name migration, learned-profile loading |
| `make_my_figure_core/styles/capabilities.py` | `PlotStyleCapabilities` per plot type; which style keys a plot honours; `warn_ignored_style_controls` |
| `make_my_figure_core/styles/publication_style_engine.py` | Palette variants (`PUBLICATION_PALETTES`), `recommended_overrides`, `STYLE_LESSONS`; advisory only |
| `make_my_figure_core/styles/__init__.py` | Re-exports `StyleProfile`, `load_profile`, `list_profiles`, `load_all_profiles`, `mm_to_inches` |
| `style_profiles/starter_journal_style_profiles.json` | Legacy starter tokens (`nature_like` / `science_like` / `cell_like`). Only palette, colormaps and column widths are read from it; the ~7 pt font sizes are deliberately ignored (`_parse_profile`) |
| `style_profiles/learned/*.json` | Aggregate "learned" profiles built by `scripts/build_learned_styles.py` from the CC-BY reference library; parsed by `_parse_learned`, which clamps fonts up to readable minimums |
| `make_my_figure_core/plots/base.py` | Renderer-side helpers that turn tokens into matplotlib calls: `figure_size`, `style_axes`, `place_legend`, `resolve_legend_location`, `apply_publication_layout`, `autorotate_xticklabels`, `apply_axis_overrides` |
| `make_my_figure_core/plots/registry.py::render` | The only place a spec's `style` block is merged into a profile and where capability warnings and the layout block are applied |
| `make_my_figure_core/qa/publication_check.py`, `qa/layout_qc.py` | Advisory readability / clipping checks run after every render |
| `scripts/audit_style_capabilities.py` | Scans renderer source and regenerates `_CAPS` in capabilities.py; drift fails `tests/test_style_capabilities_audit.py` |
| `docs/PUBLICATION_STYLE.md`, `docs/STYLE_PROFILES.md`, `docs/PLOT_STYLE_CONTROLS.md`, `docs/STYLE_REFERENCE_AUDIT.md`, `docs/V0_6_PUBLICATION_STYLE_LESSONS.md` | User-facing documentation |

## 2. One visible style: "publication"

Since v0.6 the app exposes a single style identity. `list_profiles()` returns
`["publication"]` plus any learned profile whose name starts with `publication`
(none are shipped on main: `style_profiles/learned/` holds only the three
journal-named files, which are hidden). Journal-named profiles are mapped by
`LEGACY_STYLE_ALIASES` / `normalize_style_name` to `publication`;
`registry.render` rewrites `spec["journal_style"]` before validation and records
a `style_migration` note in metadata. Tests enforcing this:
`tests/test_style_leaks_and_version.py`, `tests/test_style_migration.py`,
`tests/test_learned_styles.py`. Never add a journal name to a visible list;
`list_profiles` has a `_forbidden` token filter and the tests grep the apps.

The canonical profile is `_publication_profile()` = `StyleProfile(name="publication")`
with the dataclass defaults. `publication_style_engine.publication_variant("publication_accessible"|"publication_grayscale")`
returns the same tokens with a palette swap; that module is advisory and
changes nothing unless a caller applies its overrides.

## 3. StyleProfile tokens (engine.py)

Defaults are tuned to be readable on first render. Groups, with the field names a
renderer or preset can reference:

- Typography: `font_family` (list, default `["Arial","Helvetica","DejaVu Sans","sans-serif"]`),
  `base_font_pt` 11, `axis_font_pt` 12, `tick_label_pt` 10, `legend_pt` 10,
  `legend_title_pt` 11, `title_font_pt` 13, `title_font_weight` "bold",
  `annotation_pt` 9.5, `panel_label_pt` 13, `font_weight`, `text_color` "#1a1a1a".
- Axes: `spine_width_pt` 1.1, `tick_width`, `tick_length`, `tick_direction` "out",
  `show_top_spine`/`show_right_spine` False, `grid` False, `grid_width`, `grid_alpha`.
- Data marks: `line_width_pt` 1.8, `marker_size` 45 (scatter `s=`), `marker_edge_width`,
  `marker_alpha`, `regression_line_width`, `errorbar_line_width`, `errorbar_capsize`,
  `bar_edge_width`.
- Legend: `legend_frameon` False, `legend_loc` "best", `legend_outside` False, `legend_ncol` 1.
- Sizing / colour: `single_column_width_mm` 110, `double_column_width_mm` 180,
  `default_width_mm` 130, `export_dpi` 300, `preferred_exports`, `palette_role`,
  `palette` (list of hex), `sequential_cmap` "viridis", `diverging_cmap` "RdBu_r",
  `is_learned`, `extra`.

Methods: `figure_size_inches(width, aspect)`, `color_for(index)` (cycles the
palette), `rc_params()` (matplotlib rcParams; concrete font family list, editable
vector text via `svg.fonttype="none"`, `pdf.fonttype=42`), `apply()` (an
`rc_context`), `with_overrides(dict)` (deep-copies, applies `palette_name`
first, then any attribute-named key, then expands a single `font_family` string
into a fallback stack).

Fonts: `_installed_families` keeps only installed families and always appends
DejaVu Sans, so a missing Arial degrades silently instead of warning per artist.
No font files are committed. `tests/test_style_font_stack.py` and
`tests/test_font_survives_export.py` check the stack survives export.

## 4. Palettes and colormaps

- `NAMED_PALETTES` (engine.py): `publication`, `colorblind_safe` (Okabe-Ito),
  `high_contrast`, `grayscale`, plus hidden back-compat aliases
  `nature_like`/`science_like`/`cell_like`. `USER_PALETTES` is the list the UIs show.
- `_PALETTE_CMAPS` makes `colorblind_safe`, `high_contrast` and `grayscale` also
  switch `sequential_cmap`/`diverging_cmap`, so heatmap-type plots follow the
  palette. An explicit `sequential_cmap` override in the same style block still wins.
- Renderers obtain categorical colours only via `style.color_for(i)` or
  `style.palette`, and continuous maps via `style.sequential_cmap` /
  `style.diverging_cmap`. Literal colours in a renderer are allowed but are
  listed in `reports/figure_preset_qc/color_controls_audit.csv` so each is a
  known decision (volcano's up/down/ns colours are plot options, not palette).

## 5. Figure sizing

- `WIDTH_PRESETS_MM = {"single": 110, "onehalf": 140, "double": 180, "default": 130}`.
  These are the app's readable presets, not journal column widths (the starter
  JSON's 89/183 mm are not used for sizing on main).
- Renderers call `base.figure_size(spec, style, aspect=...)`, which reads
  `layout["column_width"]` (one of the four names; anything else becomes
  `default`) and an optional numeric `layout["aspect"]` that overrides the
  renderer's aspect. Heatmap-family renderers compute height from row count but
  honour an explicit `layout["aspect"]` the same way (`plots/heatmap.py`).
- `output.width_mm` / `output.height_mm` / `output.dpi` (from
  `spec.validate.default_output_block`, default 89 x 70 mm, 300 dpi) are
  recorded in metadata `export_dimensions` and used for export DPI; on main they
  are not used to set the figure size. Do not assume a physical-mm export path
  exists; the multi-panel `FigureLayout.fig_width_mm` (`panels/models.py`) is
  the only mm-driven sizing.
- No `figure_width_mm` style key is consumed by the engine even though
  `capabilities._UNIVERSAL` lists it.

## 6. The `style` block a PlotSpec accepts

`spec["style"]` is a flat dict of `StyleProfile` attribute names plus
`palette_name`. It is NOT declared in `schemas/plot_spec.schema.json` (the
schema permits additional properties), so validation does not catch typos;
`presets.STYLE_TOKEN_KEYS` is the authoritative allow-list and drops unknown
keys with a note. Keys the two frontends actually write (see
`apps/desktop_app/main.py::_collect_style_overrides`,
`apps/streamlit_app/streamlit_app.py` around `style_overrides`):
`title_font_pt`, `axis_font_pt`, `tick_label_pt`, `legend_pt`, `annotation_pt`,
`marker_size`, `line_width_pt`, `regression_line_width`, `spine_width_pt`,
`legend_outside`, `grid`, `palette_name`, `font_family`.

Layout controls live in `spec["layout"]`, not `style`: `column_width`, `aspect`,
`title`, `x_label`, `y_label`, `x_tick_rotation`, `y_tick_rotation`, tick/label/
title pads, `margin_*`, `subplot_wspace/hspace`, `legend_location`,
`x_scale`/`y_scale`, `auto_fix_layout`, colorbar geometry. `presets.LAYOUT_STYLE_KEYS`
is the canonical list. The registry applies these uniformly to
`figure.axes[0]` after the renderer returns (`apply_publication_layout`,
`place_legend` with `resolve_legend_location`), so a renderer does not need
per-key wiring for them, but it must draw its main content on the first axes.

## 7. How a renderer consumes style (the contract)

Signature: `render(spec, df, style) -> RenderResult` (optionally `aux=`). The
registry has already merged `spec["style"]` into `style`; the renderer must not
re-read `spec["style"]`. Pattern used by every renderer in `plots/`:

1. `with style.apply():` wrap all matplotlib calls so rcParams (fonts, sizes,
   spines, tick params) are in force while artists are created.
2. `fig, ax = plt.subplots(figsize=figure_size(spec, style, aspect=0.72))`.
3. Colours from `style.color_for(i)`; marks from `style.marker_size`,
   `style.marker_edge_width`, `style.marker_alpha`, `style.line_width_pt`,
   `style.regression_line_width`, `style.errorbar_line_width`,
   `style.errorbar_capsize`, `style.bar_edge_width`; text from
   `style.annotation_pt`, `style.text_color`; guide lines from
   `style.spine_width_pt`.
4. `style_axes(ax, style)` after labels; `autorotate_xticklabels(ax, style)` for
   categorical x; `place_legend(ax, style, ...)` for legends;
   `apply_axis_overrides(ax, spec, ...)` for x/y limits and y ticks.
5. Return `RenderResult(figure, metadata=base_metadata(...), warnings=[...])`.

`base_metadata` records `style_profile` and a disclaimer that the style is not a
journal template. Renderers never mutate the input DataFrame.

## 8. Capabilities: declared and audited

`capabilities._CAPS` maps plot type -> `PlotStyleCapabilities` flags
(`supports_palette`, `supports_marker_size`, `supports_line_width`,
`supports_legend`, `supports_continuous_colormap`, `supports_colorbar`,
`supports_axes`, node/edge colours, ...). `STYLE_CONTROL_CAPABILITY` maps style
keys to flags; `_UNIVERSAL` keys always apply. `registry.render` calls
`warn_ignored_style_controls` and appends a warning per inapplicable key, so a
control is never a silent no-op. Streamlit shows those warnings as captions.

The `_CAPS` block is GENERATED: `python scripts/audit_style_capabilities.py`
scans each renderer's source for `style.color_for(` / `style.palette`,
`sequential_cmap`/`diverging_cmap`, `.colorbar(`, `marker_size`,
`line_width_pt`/`regression_line_width`, `legend(`/`place_legend(`, writes
`reports/figure_preset_qc/color_controls_audit.csv`, and exits 1 on drift;
`--write` regenerates `_CAPS` (hand-written reasons live in the script's
`_REASONS`, axis-less plots in `_NO_AXES`). `tests/test_style_capabilities_audit.py`
runs the same drift check, so a new renderer that reads (or stops reading) a
token must be followed by `--write`, or the suite fails.

## 9. What makes a first render manuscript-usable

- Readable defaults baked into `StyleProfile` (12 pt axis labels, 10 pt ticks,
  1.1 pt spines, 45 pt^2 markers, colourblind-aware palette, no top/right spines,
  no grid, outward ticks).
- `qa/publication_check.check_publication_readiness` (MIN_LABEL_PT 9, MIN_TICK_PT 8)
  and `qa/layout_qc.check_layout` (clipping/overlap, `_MIN_FONT_PT` 6) run on
  every render and are stored in `metadata["publication_check"]` /
  `metadata["layout_qc"]`; `tests/test_publication_style.py::test_publication_check_passes_for_all_examples`
  is parametrised over `available_plot_types()`.
- Editable vector text on export (`registry._VECTOR_TEXT_RC`), tight bbox with
  axis labels added to `bbox_extra_artists`.
- `publication_style_engine.recommended_overrides(n_series=...)` suggests
  `legend_outside` at >= 4 series (`LEGEND_OUTSIDE_SERIES_THRESHOLD`); advisory.

## 10. Checklist: controls a new renderer must honour to be preset-compatible

- Use `style.apply()`, `figure_size(spec, style, aspect=...)`, `style_axes`.
- Take every colour from `style.color_for` / `style.palette` or
  `style.sequential_cmap` / `style.diverging_cmap`; if a colour must be fixed,
  expose it as a `ui_hints.Option(..., scope="style")` instead of a literal.
- Read `style.marker_size` and `style.line_width_pt` where the plot has markers
  or data lines; if it has neither, expect the audit to declare them unsupported
  and add a reason to `_REASONS`.
- Use `place_legend` (so `legend_location` re-placement and `legend_pt` work) and
  put primary content on `figure.axes[0]` (layout and legend controls target it).
- Respect `layout["title"]`, `x_label`, `y_label`; let the registry handle tick
  rotation, pads, margins, scales.
- Text sizes only from tokens (`annotation_pt`, `tick_label_pt`, ...); never
  hard-code a fontsize below the QA floors.
- Register the type in `plots/registry._RENDERERS`, `_DEFAULT_MAPPINGS`,
  `_DISPLAY_NAMES`; add `ui_hints.COLUMN_FIELDS` and `OPTIONS` with scopes; add a
  bundled example so `tests/test_figure_preset_qc.py` and the registry-wide
  tests (`grep -l "available_plot_types()" tests/*.py`) can exercise it.
- Run `python scripts/audit_style_capabilities.py --write` and
  `python scripts/build_figure_preset_qc.py` and commit the regenerated
  `capabilities.py` and `reports/figure_preset_qc/*`.

## Absent on main (do not assume)

- No evidence-derived journal presets, no `figure_width_mm` handling in the
  engine, no publication-variant chooser in the UIs (only palette names).
- Learned `publication*` profiles: machinery exists, no files shipped.

## Verify this is still current

```bash
cd "<repo>" && python -c "from make_my_figure_core.styles.engine import list_profiles, WIDTH_PRESETS_MM, USER_PALETTES; print(list_profiles(), WIDTH_PRESETS_MM, USER_PALETTES)"
grep -n "supports_\|_UNIVERSAL\|STYLE_CONTROL_CAPABILITY" make_my_figure_core/styles/capabilities.py | head -40
MPLBACKEND=Agg python scripts/audit_style_capabilities.py   # exit 0 = capabilities agree with renderer source
grep -n "def figure_size\|def style_axes\|def place_legend\|def apply_publication_layout" make_my_figure_core/plots/base.py
```
