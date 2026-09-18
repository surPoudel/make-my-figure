# New-plot workflow: from a request to a general, reusable plot type

This is the reasoning part of the lifecycle in `AGENT.md` section 2. The scripts do the mechanical
part; this file is about deciding WHAT to build so it stays useful for unrelated data for years.

## 1. Input modes

| mode | input | what to do first | limits |
|---|---|---|---|
| A - name | "Add a dumbbell plot." | Write the grammar worksheet from your own knowledge of the plot family; confirm the name is not already registered under another display name (`inspect_registry.py`, `find_related_renderers.py`). | Names are ambiguous ("dot plot" means three different plots); state your interpretation in the plan. |
| B - description | marks, groups, statistics in words | Map each sentence to a worksheet row. Ask only if two readings lead to materially different renderers. | none |
| C - reference image | local PNG/JPG/PDF page | Look at the image (vision-capable model) OR ask the user for the description below (no vision). Fill the worksheet from what is SEEN, then generalise. A statistical annotation in the reference (stars, P value, test name) is GRAMMAR: "this plot supports a comparison of that shape via StatsSpec"; the test name and value are content and are never typed in. | Without vision, do not pretend: request the "describe the reference plot" answers in section 2.1. |
| D - reference paper | local PDF + "Fig. 3D" | Extract text and images locally (`pdftotext`, PyMuPDF `fitz`, or `pdfimages`; all offline). Read the figure legend and methods for the plot's meaning, n, error definition and test. Then treat it as mode C. | Never fetch the paper online; never copy its data, labels, colours, dimensions. If the paper's data are supplied with a permissive licence they may become an ADDITIONAL published-data gallery example; the bundled example stays synthetic. |

### 2.1 Questions to answer when no vision is available (mode C/D fallback)
What is on each axis (categorical / numeric / time / ordered)? What marks are drawn (points, bars,
boxes, violins, lines, areas, tiles, arrows, text)? How many groups and how are they distinguished
(position, colour, shape, panel)? Are individual observations shown? Which summary (mean, median)
and which error (SD, SEM, CI, IQR) are shown? Are there brackets, stars, P values, reference lines,
labels on points? Is anything transformed (log, z-score, percent change, cumulative)? Legend where?

## 2. Plot-grammar worksheet (fill this in; it goes into the plan)

```
Question the plot answers:
Unit of observation / data shape (long / wide / matrix / edge list / survival / intervals):
Required roles (name : type : meaning):
Optional roles:
Grouping (colour / position / panels):            Panels? (only the histogram draws panels on main; answer no unless essential)
Marks (per layer, drawing order):
Encodings (position, colour, size, shape, alpha) and their semantics:
Summary statistics drawn (mean/median/...):       Error definition (SD/SEM/CI/IQR/none):
Inferential statistics that make sense (pairwise, vs control, omnibus+posthoc, paired, correlation, survival, categorical) -> StatsSpec shapes (StatsSpec = the plain dict spec["statistics"], see statistics/schemas.py):
Transformations inherent to the plot (e.g. log dose, cumulative incidence, z-score) vs user preprocessing:
Annotations (brackets, n labels, reference lines, point labels, corner panel):
Axes (scales, limits policy, tick policy, orientation switch?):
Legend (needed when? placement policy):
Colour semantics (categorical palette / continuous colormap / diverging / significance colours):
Layout behaviour (width presets, aspect, many groups, long labels, missing values, category order):
Missing-value behaviour (drop + warn / show as gap / error):
What the sidecar metadata must record (n per group, summary, error, test, order):
```

## 3. Generalisation test

Remove the reference. Is the result still a useful scientific plot type for unrelated data? A
renderer fails the test if any of these are true: it depends on column NAMES rather than roles;
it draws paper-specific labels, colours, thresholds or dimensions unless the user sets them; it
only works for the reference's group count or n; the "statistics" are typed-in values. Redesign
until every one is false. Data are supplied by the user; example data are synthetic and seeded.

## 4. Decision: NEW RENDERER or EXTENSION

Extend an existing renderer when the requested plot differs only in marks that are already
options or could be one presentational option (fill, orientation, point arrangement, a summary
overlay), and the data shape, roles and statistics are the same. Create a new renderer when the
unit of observation, the required roles, the axes semantics or the statistics differ, or when the
option would change what the existing plot MEANS (a box plot with a fitted curve is not a box
option). Do not create a new plot merely because the name differs (raincloud vs half-violin with
points); do not overload a renderer until its docstring needs "or" three times.

Worked examples:
- **NEW despite the same data shape.** A dumbbell plot takes the same long table as the paired
  slopegraph (subject, condition, value), but the categorical axis means ITEMS (slopegraph: conditions),
  colour means CONDITION (slopegraph: subject group), exactly two conditions are allowed, and a legend is
  mandatory. The decisive criterion is "axes semantics differ": a new renderer that reuses the slopegraph's
  paired-value aggregation helper.
- **EXTENSION.** "Half violins with a box and jittered points" is the registered raincloud plot; a
  request for "violin plus box plus points" is a `kind` option of the box/violin renderer. Same unit of
  observation, same roles, same statistics: add an option, not a plot.
- **NEW because the y axis is defined differently.** An ECDF (step at every observation, y fixed 0-1)
  is not a histogram option even though the histogram has a cumulative frequency polygon: bins would
  become meaningless and the docstring would need its fourth "or".

## 5. Implementation plan template (write before editing)

```
Plot type: <registry key>  Display name: <...>  Decision: NEW | EXTENSION of <plot_type>
Grammar worksheet: (attach)
Files to change (the union of what the references require; drop lines that do not apply, never silently):
  make_my_figure_core/plots/<module>.py (new|edit)
  make_my_figure_core/plots/registry.py (import + _RENDERERS + _DEFAULT_MAPPINGS + _DISPLAY_NAMES; append at the end = UI order)
  make_my_figure_core/ui_hints.py (COLUMN_FIELDS, OPTIONS with explicit scope=; add the key ONCE)
  make_my_figure_core/styles/capabilities.py (ALWAYS regenerate: scripts/audit_style_capabilities.py --write)
  make_my_figure_core/statistics/runner.py resolve_columns + test_registry.py recommend_tests (when roles differ in meaning from bar/box; a NEW TEST touches more, see statistics.md)
  make_my_figure_core/recommendations/plot_recommender.py (only with a data-shape rule + false-positive test)
  scripts/generate_example_data.py (builder + Example appended at the END of EXAMPLES), examples/ regenerated (generate_example.py)
  scripts/build_plot_catalog_part.py (PURPOSE, LIMITS, STATS_PLOTS) + docs/manuals/assets/figures/<pt>.png (render_plot_matrix.py --catalog-figure)
  scripts/build_manual_diagrams.py (plot count in a label) + docs/manuals rebuilt (build_plot_catalog_part.py, build_manuals.py) + docs/manuals/audit/current_capabilities.md
  reports/figure_preset_qc/all_plot_preset_matrix.csv regenerated (scripts/build_figure_preset_qc.py; a test requires a row per plot)
  README.md (badge + "N plot types" line), docs/PLOT_TYPE_REQUIREMENTS.md, CHANGELOG.md Unreleased
  tests/test_<plot_type>.py + bump the tests pinning the plot count (inspect_registry.py lists them)
Components reused: (from find_related_renderers)
New code required: (marks, geometry helpers, options)
Schema changes: none expected (plot_type is a free string; style block undeclared) | <...>
UI changes: none expected | matrix-shaped plot -> _MATRIX_PLOT_TYPES in both apps | aux table wiring in Streamlit
Statistics: none | shapes ... via run_and_annotate
Tests: registration, roles, render, missing values, edge cases, options, statistics, PlotSpec, preset, builder, export
Documentation: catalogue entry, manual section, Quick Start (if workflow changes), CHANGELOG
Risks / open questions:
```

## 6. Data model rules

Roles, never column names. Required roles raise `RenderError` with the role and plot type. Optional
roles change the drawing only when present. Categorical order = order of first appearance
(`dict.fromkeys` / `ordered_unique`); there is no global category-order key on main, so a renderer
that needs another order declares its own `category_order` option (choices such as data / alphabetical
/ by value) and documents it. Orientation is an option only when both directions are meaningful. Missing or non-numeric values are dropped and counted in a warning; never silently
imputed. Never pick a scientific variable for the user (no "the first numeric column").

## 7. Customisation standard and publication-first default

Expose every scientifically sensible presentation control through the existing style block
(`references/styling.md`) and `ui_hints.Option` with an explicit scope (`style` = appearance only,
`config` = changes what is computed or shown). Apply the definition literally for NEW options (a
`complementary` or `cumulative` switch changes what is shown, so it is `config`); some older options
on main are scoped more loosely (histogram's `cumulative` and `normalize` are `style`) and are legacy,
not precedent. Do not add controls that cannot matter for the plot.
No hard-coded aesthetic a user cannot change; palette, marker size, line width, fonts, legend
location, figure width come from the style profile. The first render with the bundled example must
be manuscript-usable: the render matrix's `default` panel is the acceptance reference.

## 8. Statistics and scientific freeze

Statistics flow through StatsSpec (the plain dict `spec["statistics"]`, normalised by
`statistics/schemas.py`) -> `stats_integration.run_and_annotate` -> shared annotation
geometry (`references/statistics.md`, `annotations.md`). A renderer only draws stored results. Before
and after rendering, the input table, group assignments, transformations and statistics are
identical; `validate_plot_integration.py` and `audit_roundtrip.py` check this and the tests keep it.
