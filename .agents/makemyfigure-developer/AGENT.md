# MakeMyFigure Developer

A repository-resident development agent for adding scientific plot types to MakeMyFigure and
carrying approved work through commit, push and release. It is written for ANY capable coding
model or human developer: nothing here depends on a particular vendor, on conversation memory, or
on internet access. All MakeMyFigure-specific knowledge lives in `references/`, the executable
knowledge in `scripts/`, and the starting points in `templates/`.

Read this file first. Read a reference file only when the step you are on names it.

## 0. Operating modes (permission model)

| mode | entered by | may do | must not do |
|---|---|---|---|
| **DEVELOP** (default) | any request | read, edit, run tests, render, update docs, build a local test app | commit (unless asked or `references/git-workflow.md` policy permits), merge, tag, release, push |
| **COMMIT** | "Commit these approved changes." | review the diff, commit approved files on the feature branch | push, merge |
| **PUSH** | "Push the approved branch." | run pre-push tests, push the feature branch | merge to main, tag |
| **RELEASE** | "Release the approved changes as vX.Y.Z." (explicit version) | the numbered runbook in `references/release-workflow.md` | anything the runbook does not list |

A request that does not name a mode is DEVELOP. Development ends at the acceptance gate (step 9).

## 1. Determine the task

- **New plot** from a name (mode A), a description (mode B), a reference image (mode C) or a
  reference paper/figure (mode D): follow section 2. Input modes and their limits are in
  `references/new-plot-workflow.md` (mode C needs a vision-capable model or a written description;
  mode D uses local PDF extraction only).
- **Extend an existing plot**: same lifecycle, skipping scaffolding.
- **Bug fix / refactor**: steps 2, 6, 7, 9.
- **Commit / push / release**: section 3.

## 2. New-plot lifecycle (DEVELOP)

`<S>` = `.agents/makemyfigure-developer/scripts`. The scripts find the repository from their own
location, so they work from any current directory; paths they print are relative to that repository.
Work on a feature branch, never on `main` (`references/git-workflow.md`); `inspect_registry.py` prints
the branch it inspected.

1. **Inspect the live repository.** `python <S>/inspect_registry.py` (add `--write` only when the
   inventory file will be part of the change; it writes `inventory/plot_inventory.{json,md}`). Never
   assume a plot count, a branch feature, or a file layout from memory; the inventory tells you what
   exists in THIS checkout (features present/absent, tests that pin the plot count).
2. **Understand the visualization** (question answered, data shape, roles, marks, encodings,
   statistics, inherent transformations, annotations) and write the plot-grammar worksheet from
   `references/new-plot-workflow.md`. For a reference figure extract the GRAMMAR, never the values,
   labels, colours or dimensions of that one figure. To fill the worksheet you will need the role
   conventions in `references/data-mapping.md`, the statistics shapes in `references/statistics.md`
   and the style-vs-config scope rule in `references/styling.md`.
3. **Search the architecture.** `python <S>/find_related_renderers.py "<description>" --roles x,y,...`
   then read the top 2-5 renderers and the shared components it lists.
4. **Decide**: NEW RENDERER or EXTENSION of an existing one (criteria in
   `references/new-plot-workflow.md`). Run the generalization test: useful for unrelated data with the
   reference removed? If not, redesign.
5. **Write the implementation plan** (files to change, components reused, new code, schema/UI
   changes, tests, docs) using the plan template in `references/new-plot-workflow.md`; it draws on
   `references/renderer-contract.md`, `examples-gallery.md` (seeded example, append at the END of
   EXAMPLES) and `testing.md` (test families, tests that pin the plot count). Show it before editing.
6. **Implement.** `python <S>/scaffold_plot.py <plot_type> --display "..." --roles ... [--wire]`
   creates the renderer and test files from `templates/` and writes a checklist to
   `inventory/scaffold_<plot_type>.md`. Then follow, in order: `references/renderer-contract.md`,
   `registry.md`, `data-mapping.md`, `styling.md`, `statistics.md` (only through StatsSpec, the plain dict
   `spec["statistics"]`, and the shared annotation code), `annotations.md`, `frontends.md` (usually no edit needed),
   `recommendations.md` (only with an explicit data-shape justification), `presets.md`,
   `plotspec.md`, `figure-builder.md`, `figure-package.md` (when present in the checkout).
   Add the deterministic example builder (`references/examples-gallery.md`) and run
   `python <S>/generate_example.py <plot_type>`.
7. **Validate.**
   - `python <S>/validate_plot_integration.py <plot_type>` (all required checks PASS),
   - `python <S>/audit_roundtrip.py <plot_type>` (PlotSpec, preset, builder, exports, package when present),
   - `python <S>/render_plot_matrix.py <plot_type>` and LOOK at every panel (`references/visual-qc.md`),
   - `python <S>/run_plot_tests.py <plot_type> --related <modules> --full` (`references/testing.md`);
     no unexplained regression is acceptable; bump tests that pin the plot count.
8. **Document.** Catalogue entry in `scripts/build_plot_catalog_part.py` (PURPOSE / STATS_PLOTS
   dictionaries) plus the catalogue figure `docs/manuals/assets/figures/<plot_type>.png`, written
   through the app by `python <S>/render_plot_matrix.py <plot_type> --catalog-figure`; then rebuild the
   manuals, add Quick Start text when a workflow changes, and a CHANGELOG `Unreleased` entry
   (`references/documentation.md`). Update any stale file in
   `references/` if the architecture changed (section 4).
9. **Build a local test app for the host OS** (`python <S>/build_local_test_app.py`, or `--source`)
   and STOP. Report: implementation summary, new plot, example data, gallery preview (matrix
   sheet), test results (report path), manual changes, local build path, known limitations, and the
   author checklist from `checklists/author-test-checklist.md` filled in for this plot. End with:
   **READY FOR AUTHOR TESTING.** Do not merge, tag or release.

## 3. Commit, push, release

Follow `references/git-workflow.md` for COMMIT and PUSH. RELEASE requires an explicit target
version; run `python <S>/release_preflight.py --version X.Y.Z` (read-only) and then the runbook in
`references/release-workflow.md` step by step, recording the result in `release_history/`
(`references/release-workflow.md`, ledger section). Semantic versioning follows project convention:
bug fix -> patch, backward-compatible plot/feature -> minor, breaking change -> major; ask when ambiguous.

## 3b. What writes into the repository tree

Read-only: `inspect_registry.py` (without `--write`), `find_related_renderers.py`,
`validate_plot_integration.py`, `audit_roundtrip.py`, `release_preflight.py`, `build_local_test_app.py --source/--dry-run`.
Writes: `inspect_registry.py --write` (inventory/), `scaffold_plot.py` (renderer, `tests/test_<plot_type>.py`,
inventory checklist; `--wire` edits registry.py and ui_hints.py), `generate_example.py` (examples/),
`render_plot_matrix.py` (reports/agent_runs/, git-ignored; `--catalog-figure` writes the manual figure),
`run_plot_tests.py` (reports/agent_runs/), `build_local_test_app.py` (build/, dist/). Project scripts that
write even in check mode are listed in `references/styling.md` and `documentation.md`.

## 4. Keep this agent current

After any approved architectural change (new spec version, preset or package format, frontend,
packaging), re-run `inspect_registry.py`, run the "Verify this is still current" commands at the end
of the affected reference files, and fix what is stale in the same change. Reference files point to
authoritative code; they never copy it.

## 5. Where things are

```
.agents/makemyfigure-developer/
  AGENT.md                 this file (control plane)
  references/              one topic per file; each ends with verification commands
  scripts/                 inspect_registry, find_related_renderers, scaffold_plot, generate_example,
                           validate_plot_integration, audit_roundtrip, render_plot_matrix,
                           run_plot_tests, build_local_test_app, release_preflight (+ _common)
  templates/               renderer_template.py, test_template.py, example_template.py, manual_template.md
  checklists/              author-test-checklist.md
  inventory/               generated: plot_inventory.{json,md}, scaffold checklists
release_history/           release ledger (never rewrite old entries)
```
