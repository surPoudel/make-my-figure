# Agent validation record - 2026-09-17 (construction day)

Checkout: `feature/makemyfigure-developer-agent` forked from `main` bb45c12 (MakeMyFigure 1.1.0, 38 plot types).

## Script checks on the live checkout
- `inspect_registry.py`: 38 plots inventoried; feature detection correct after purging the editable-install
  finder (`figure_package` absent on main, present on `feature/evidence-derived-journal-presets`).
- `validate_plot_integration.py --all`: every plot passes except `upset_plot` (no `ui_hints.COLUMN_FIELDS`
  entry on main - a real gap, not a script defect). The validator also reports the two tests that pin the
  plot count and the README / manual-diagram counts.
- `audit_roundtrip.py`, `render_plot_matrix.py`, `run_plot_tests.py`, `generate_example.py --no-regenerate`,
  `build_local_test_app.py --dry-run`, `release_preflight.py --version 1.1.0` all ran; the agent copy was
  also run inside the presets worktree, where the Figure Package save/move/reopen step passed
  (integrity verified, signature and statistics identical).
- Scaffold trial: `scaffold_plot.py waffle_plot --wire` created renderer + test + checklist, wired
  registry and ui_hints; the template rendered with statistics on synthetic data; validation flagged the
  missing example and the stale pinned counts; everything was reverted (`git checkout`, files removed).

## Simulations (fresh agents given only AGENT.md)
1. **Mode A, "Add a dumbbell plot."** Produced the grammar worksheet, found the paired slopegraph and
   decided NEW RENDERER on the "axes semantics differ" criterion, and wrote a complete plan (files,
   reused helpers, StatsSpec paired shape via a corner panel, tests incl. pinned counts, docs incl. the
   catalogue dictionaries). 20 critique items.
2. **Mode C, local reference image (ECDF per group with rug, KS annotation, paper-specific labels).**
   Separated content (labels, colours, n, P value, panel letter) from grammar (value + group roles, step
   per group, rug and quantile-line options, distribution test via StatsSpec), decided NEW RENDERER over
   overloading the histogram, and planned a synthetic example unrelated to the image. 17 critique items.

## Deficiencies corrected the same day
AGENT.md: `--write` optional; references named at steps 2 and 5; branch/cwd guidance; catalogue figure
step made explicit; list of scripts that write into the tree; StatsSpec defined as the plain dict.
References: role naming conventions (data-mapping); resolve_columns rule and canonical renderers
(renderer-contract); generic text-panel mode and "adding a NEW test" file list (statistics); category
order, mode-C statistics annotations, legacy option scopes, worked NEW/EXTENSION examples, complete file
union in the plan template (new-plot-workflow); duplicate-key caution and removed authoring leak (registry).
Templates: renderer rewritten against the real `base_metadata`/`RenderResult`/`run_and_annotate` API with
style tokens and the draw -> layout -> statistics order; test template's export test fixed.
Scripts: Figure Package path uses the branch's `content_for_single_plot`/`single_plot_inputs`; validator
gained preset-QC row, catalogue figure, per-dictionary catalogue, README/diagram counts and pinned-count
comparison; matrix script gained `--category-role/--value-role`, `--catalog-figure` and an honesty note when
text-layout QC is absent; finder gained stop words, synonyms and matched-role output; Qt detection fixed
(`PySide6.QtWidgets`), over-broad `-k` filter removed; `reports/agent_runs/` git-ignored.

## Not fixed (findings about main, for the author)
- `upset_plot` lacks `ui_hints.COLUMN_FIELDS`; `ui_hints.OPTIONS` has duplicate keys for three plot types.
- `DesktopController.load_plotspec` cannot open the `{plot_spec, render_metadata}` sidecar wrapper.
- `docs/RECOMMENDED_FIGURES.md` and `docs/PLOT_TYPE_REQUIREMENTS.md` are stale (see recommendations.md, documentation.md).
- `find_related_renderers.py` ranks by keywords and role names only; after the synonym fix the forest plot appears third for a dumbbell query, but geometric similarity is not modelled. Always read the top 2-5 renderers rather than trusting the ranking.
