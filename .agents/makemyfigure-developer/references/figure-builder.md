# Figure Builder: multi-panel composition (`make_my_figure_core/panels/`)

Documented from `main` as of 2026-09-17 (bb45c12). Paths are relative to the repo root.

## 1. Package layout

| File | Contents |
|---|---|
| `make_my_figure_core/panels/__init__.py` | re-exports `Panel`, `FigureLayout`, `MultiPanelFigure`, `build_figure`, `export_multipanel`, `multipanel_sidecar`, `draft_legend`, `import_external_panel`, `panel_from_dict`, `panel_warnings` |
| `make_my_figure_core/panels/models.py` | dataclasses `Panel`, `FigureLayout`, `MultiPanelFigure`; `default_labels(n, style)` |
| `make_my_figure_core/panels/builder.py` | rendering/rasterising/composing/exporting; FigureSpec sidecar; draft legend |
| `make_my_figure_core/figure_import.py` | importing external image files as panels (`import_asset`, `process_image`, `resolution_warnings`, `ImportedAsset`) |
| `docs/MULTI_PANEL_FIGURES.md`, `docs/IMPORT_EXTERNAL_PANELS.md` | user documentation |

Naming caution: `apps/desktop_app/panels_dock.py::PanelManager`, `docs/POP_OUT_PANELS.md` and
`tests/test_pop_out_panels.py` are about **UI dock panels** (Figure / Data & Messages / Plot
Controls windows that can float or dock in the desktop workbench). They have nothing to do with
figure panels; do not confuse the two when grepping "panel".

## 2. Models (`panels/models.py`)

**`Panel`** - one cell of the composite. Either a pre-rendered matplotlib `figure`, or
`plot_spec` + `table` (+ `aux`, `stats_spec`) rendered on demand, or an imported external image
(`image_path` set; `is_external` property). Fields: `label`, `title`, `caption`, provenance
(`source_name`, `source_workbook`, `source_sheet`), size hints `width_in`/`height_in` (None =
auto), imported-image controls (`image_meta`, `fit_mode` contain|fill|crop|stretch,
`preserve_aspect`, `crop`, `rotate` 0/90/180/270, `flip_h/v`, `auto_trim`, `background`,
`border`, `border_width`) and per-panel `annotations` (AnnotationSpec dicts, axes coords).
`to_dict()` is the FigureSpec panel record; it stores only the asset **basename** for
`image_path` and derives `stats_spec`/`source_*` from `plot_spec` when blank.

**`FigureLayout`** - grid and typography: `ncols`/`nrows` (None = auto), `width_ratios`,
`height_ratios`, `fig_width_mm` (180 default), `fig_height_mm` (None = derived), `wspace`,
`hspace`, label style (`label_style` A|a|1, `label_prefix`, `label_size` 14, `label_weight`
bold, `label_dx`/`label_dy`), `panel_dpi` (300), `background`, `show_titles` (False by default),
and figure-level font overrides `base_font_pt`, `axis_font_pt`, `tick_label_pt`, `legend_pt`
(`font_overrides()` returns the non-None ones). `to_dict`/`from_dict` (unknown keys ignored).

**`MultiPanelFigure`** - `name`, `panels`, `layout`, `legend_text`; `add_panel`, `remove_panel`,
`move_panel`, `duplicate_panel` all call `autolabel()`, which reassigns
`label_prefix + default_labels(...)` to every panel (labels are positional, not sticky).
`to_dict()` is the FigureSpec body.

## 3. Composition pipeline (`panels/builder.py::build_figure`)

1. `mpf.autolabel()`; `font_overrides = layout.font_overrides()`; the Publication profile is
   loaded for panel-letter fonts and annotation defaults.
2. Per panel: external -> `_external_panel_image` (loads the asset via `figure_import.import_asset`
   at `image_meta["rasterization_dpi"]`, applies `process_image` crop/rotate/flip/trim/background,
   collects `resolution_warnings`); generated -> `_render_panel_figure` (returns `panel.figure`
   if set, else copies `plot_spec`, injects `stats_spec` as `statistics` when absent, merges
   `font_overrides` into `spec["style"]`, calls `registry.render(spec, table, aux=aux)`), then
   `_figure_to_image` rasterises with `savefig(format="png", dpi=layout.panel_dpi,
   bbox_inches="tight")`. Aspect = image h/w.
3. Grid: `_auto_grid` (ncols = ceil(sqrt(n)) unless set). Panel width defaults to an even share of
   `fig_width_mm`; height defaults to width x aspect (so an auto-sized panel fills its cell with
   no letterboxing and no distortion). Column width = widest panel in the column, row height =
   tallest; `width_ratios`/`height_ratios` override when their length matches. Figure size is
   the sum of columns/rows scaled by `(1 + wspace)`/`(1 + hspace)`, or `fig_height_mm` if set.
4. Composite: `plt.figure` + `add_gridspec`, one `imshow` per panel. Generated panels always keep
   aspect and are top-anchored (`set_anchor("N")`); imported panels may `fill`/`stretch`
   (`aspect="auto"`, with a warning for stretch). Ticks hidden, spines hidden unless
   `panel.border`. Optional title, per-panel annotations (`annotations.apply_annotations`; data
   coords are coerced to axes coords for external panels), and the bold label drawn at
   `(label_dx, label_dy)` in axes fraction with `clip_on=False`. Unused trailing cells are hidden.
5. Figures the builder rendered itself are closed (`plt.close`); pre-rendered panel figures are
   left alone. Warnings are attached as `comp._mmf_panel_warnings` and read with
   `panel_warnings(fig)`.

Design trade-off (module docstring): panel **content is raster** at `panel_dpi`; panel labels
and titles are vector text. Each panel remains independently exportable as true vector from its
own PlotSpec.

## 4. Export paths and the FigureSpec sidecar

* `export_multipanel(fig, base_path, formats, dpi=300) -> List[str]` writes
  `<base>.<fmt>` for svg/png/pdf/tiff/eps under `_VECTOR_TEXT_RC` (`svg.fonttype none`,
  Type 42 fonts), `bbox_inches="tight"`, and passes `dpi` to **every** format because the panels
  are embedded rasters (`tests/test_multipanel.py::test_export_passes_dpi_to_all_formats`).
  TIFF uses LZW.
* `multipanel_sidecar(mpf, base_path)` writes `<base>.figure_spec.json` =
  `{"figure": mpf.to_dict(), "draft_legend": mpf.legend_text or draft_legend(mpf), "disclaimer": ...}`.
* `draft_legend(mpf)` builds "(A) title-or-'y by x'. Statistics were computed as recorded in the
  panel StatsSpec." sentences and always appends a DRAFT marker; it never invents biology.
* Reload: `panel_from_dict(d, assets_dir)` and `FigureLayout.from_dict(d)`. Tables are not in
  the FigureSpec; the caller must supply them (the desktop app keeps them in memory; the
  v1.1.1 Figure Package freezes them - see `figure-package.md`).
* `import_external_panel(src_path, assets_dir, *, label, title, width_in, rasterize_dpi=300,
  pdf_page=0, **transform) -> (Panel | None, ImportedAsset)`: copies the file into `assets_dir`
  (`figure_import.ASSETS_DIRNAME = "figure_builder_assets"`), records `original_filename`,
  `stored_asset`, dims, DPI, `sha256`, `is_vector_source`, `rasterization_dpi`, `page`.
  Supported: `RASTER_EXTS` png/jpg/jpeg/tif/tiff/webp/bmp and `VECTOR_EXTS` svg/pdf (eps is
  refused with a message). Import never raises for a bad file (`ImportedAsset.error`).

## 5. How the frontends expose it

**Desktop** (`apps/desktop_app/`):

* `main.py::action_save_panel` appends `{"plot_spec", "table", "aux", "title", "plot_type"}` to
  `MainWindow._saved_panels` (deep copies of the current spec and DataFrame).
* `main.py::action_figure_builder` opens `stats_panel.py::FigureBuilderDialog(controller,
  saved_panels, parent)`. The dialog's `_build_mpf` turns each saved dict into a `Panel`
  (imported ones via `image_path`/`image_meta`/fit/border/rotate/crop/annotations; generated ones
  with `plot_spec`, `table`, `aux`, `stats_spec = plot_spec["statistics"]`, `width_in`, `height_in`);
  `_make_layout` builds the `FigureLayout` from the controls; `_update_preview` calls
  `build_figure`; `_import_panel` calls `import_external_panel(path, self._assets_dir, width_in=3.2)`;
  `_save` calls `build_figure`, `draft_legend`, `export_multipanel(fig, base, [chosen, "svg", "pdf"],
  dpi=...)`, `multipanel_sidecar`, then copies imported assets next to the figure.
  Layout presets (`*.mmflayout.json`, `presets.py` `LAYOUT_PRESET_*`) are handled by
  `_apply_layout_preset`, `_save_layout_preset`, `_import_layout_preset`, `_export_layout_preset`;
  an exported FigureSpec can be loaded as a layout preset
  (`tests/test_figure_presets.py::test_exported_figurespec_loads_as_a_layout_preset`).
* `main.py` passes `_saved_panels` to `MatrixWizardDialog` so wizard-generated plots can be added.
* The `DesktopController` has no builder methods; the dialog imports `make_my_figure_core.panels`
  directly.

**Streamlit**:

* `apps/streamlit_app/streamlit_app.py` (the main app) has **no** Figure Builder; it exports a
  single plot plus its PlotSpec/StatsSpec sidecars.
* `apps/streamlit_app/matrix_wizard.py::_step_figure_builder` composes the wizard's session
  `panels` with `MultiPanelFigure` + `FigureLayout(ncols=...)` + `build_figure` and offers
  PNG/SVG/PDF via `registry.figure_to_bytes`. It writes no FigureSpec sidecar and has no
  external-panel import.

See `frontends.md` for the surrounding UI.

## 6. What a renderer must satisfy to work as a panel

The builder treats a renderer as a black box: `render(spec, table, aux)` -> `result.figure` ->
`savefig(png, bbox_inches="tight")`. Everything else follows from that:

1. **Return the Figure, never show it.** No `plt.show()`; no interactive backend assumptions.
   Tests run under `MPLBACKEND=Agg` and the builder rasterises off-screen.
2. **Own your figure size.** Create the figure with `plots/base.py::figure_size(spec, style,
   aspect=...)` (honours `layout.column_width`/`layout.aspect`). The builder scales the raster to
   its cell, so the size only sets the text-to-plot ratio; do not read screen DPI or resize after
   the fact. Do not call `plt.figure()` without `figsize`.
3. **Tight bbox must capture everything.** Legends, colorbars, outside tick labels and long axis
   labels must be real artists attached to the figure/axes so `bbox_inches="tight"` includes
   them. The registry's `export_figure` adds axis labels via `_bbox_extra_artists`; the builder's
   `_figure_to_image` does not, so keep labels inside the default tight box (call
   `fig.tight_layout()` or `apply_publication_layout` at the end as the existing renderers do).
4. **Legends outside the data area.** Use `plots/base.py::place_legend(ax, style, ...)` (it
   reserves margin with `subplots_adjust` for outside positions) or leave the legend on
   `figure.axes[0]` so `render`'s `layout.legend_location` relocation and the composite font
   overrides apply. Legends drawn on a secondary axes are not relocated.
5. **Respect style tokens for fonts.** The builder injects `base_font_pt`, `axis_font_pt`,
   `tick_label_pt`, `legend_pt` through `spec["style"]`; a renderer must render inside
   `with style.apply():` and take sizes from the `StyleProfile`, never from hard-coded points,
   or the composite will be typographically inconsistent (`tests/test_multipanel.py::test_font_overrides_reach_panel_render`).
6. **Do not close or reuse figures.** Return a fresh Figure per call; the builder closes the
   figures it rendered (`own_figs`) and leaves pre-rendered ones to the caller. Never call
   `plt.close("all")` inside a renderer (it would kill sibling panels that are still alive).
7. **Be re-renderable from the spec alone** (deterministic given `spec` + `table` + `aux`), since
   the FigureSpec stores only the PlotSpec; seeds belong in `mapping`.
8. **Pass `qa/publication_check.py::check_publication_readiness`** (labelled axes, readable
   font sizes, minimum figure size) because `tests/test_publication_style.py::test_publication_check_passes_for_all_examples`
   runs it for every registered type, and because the composite inherits those problems.
9. **Aux tables go through `aux`**, declared as a keyword in the renderer signature (the registry
   inspects the signature); the desktop saved-panel record carries `aux` so PCA-style panels work.

## 7. Tests that exercise the builder and panels

Builder-specific (all in `tests/`):

* `test_multipanel.py` - `test_autolabel_sequences`, `test_build_and_export`,
  `test_export_passes_dpi_to_all_formats`, `test_sidecar_has_panel_specs`, `test_panel_management`,
  `test_draft_legend_marks_draft`, `test_titles_off_by_default`, `test_per_panel_size_scales_figure`,
  `test_auto_height_follows_aspect_no_distortion`, `test_font_overrides_reach_panel_render`,
  `test_layout_font_overrides_dict`, `test_prerendered_figure_panel`.
* `test_imported_panels.py` - raster/PDF/SVG import, friendly errors, metadata, low-resolution
  warnings, aspect/crop, `test_mixed_figure_builds_and_exports`,
  `test_figurespec_roundtrip_restores_imported_panel`, `test_low_res_warning_surfaced_on_build`.
* `test_workbook_provenance.py` - `test_panel_records_and_round_trips_worksheet`,
  `test_two_panels_same_workbook_different_sheets_distinguishable`,
  `test_panel_derives_source_from_plot_spec_when_fields_blank`.
* `test_figure_presets.py` - layout-preset tests (`test_layout_preset_keeps_geometry_and_drops_content`,
  `test_layout_preset_applies_to_another_composite_and_warns_on_count_mismatch`,
  `test_layout_preset_refuses_panel_content`, `test_exported_figurespec_loads_as_a_layout_preset`,
  `test_figure_layout_roundtrips_through_dict`).
* `test_style_font_stack.py::test_composite_letters_use_the_publication_font_stack` - panel
  letters take the Publication font stack, not matplotlib's default.
* `test_style_capabilities_network.py::test_figure_builder_preserves_network_colors` - a
  panel's `plot_spec["mapping"]` style choices survive `build_figure` untouched.
* `test_one_publication_recreation.py::test_figure_builder_figurespec_and_exports` - checks the
  committed benchmark composite (`figure_spec.json` + `assembled_figure.{png,svg,pdf}`).
* `test_desktop_gui.py` / `test_pop_out_panels.py` need Qt and are skipped where PySide6 cannot
  load; the latter tests dock panels, not figure panels.

**There is no test on `main` that builds a composite for every registered plot type.** The
builder tests use two hand-made specs (bar + scatter). Per-type coverage that a panel implicitly
relies on comes from the "render every example" loops: `test_publication_style.py::test_publication_check_passes_for_all_examples`
(parametrised over `available_plot_types()`), `test_desktop_controller.py::test_every_example_loads_and_renders`,
`test_layout_qc.py::test_layout_qc_never_crashes_on_any_plot_type`,
`test_layout_and_annotations.py` (x/y tick rotation across all types),
`test_learned_styles.py::test_every_plot_type_renders_after_migration`,
`test_figure_presets.py` (`ALL_TYPES`), `test_figure_preset_qc.py`, `test_app_smoke.py::test_app_runs_each_sample_plot_type`.
On the v1.1.1 branch, `tests/test_figure_package.py::test_composite_package_round_trip` and
`tests/test_figure_package_controller.py::test_every_plot_type_packages_and_reopens` add
composite and per-type package coverage. A cheap gap-closer would be a parametrised test that
wraps each `examples.load_example(pt)` in a one-panel `MultiPanelFigure`, calls `build_figure`,
and asserts the figure has one image axes and no `panel_warnings`.

## 8. Files a new plot type touches for builder support

None in `panels/`. Builder support is automatic once the type is registered
(`plots/registry.py`), has an example (`examples/example_data_manifest.json` via
`scripts/generate_example_data.py`) and satisfies section 6. If the renderer needs an auxiliary
table, make sure the frontends' saved-panel records carry it (`main.py::action_save_panel`
already copies `data.aux`; the Streamlit wizard passes `p.get("aux")`).

## Verify this is still current

```bash
grep -n "^def \|^class " make_my_figure_core/panels/builder.py make_my_figure_core/panels/models.py
grep -n "def action_save_panel\|def action_figure_builder\|class FigureBuilderDialog\|def _build_mpf\|def _save" apps/desktop_app/main.py apps/desktop_app/stats_panel.py
grep -rn "build_figure\|MultiPanelFigure" apps/streamlit_app/*.py | head
grep -rln "from make_my_figure_core.panels\|make_my_figure_core.panels import" tests | sort
```
