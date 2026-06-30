# Claude Code Master Prompt: Make My Figure

You are Claude Code acting as the principal engineer, scientific visualization specialist, data-curation lead, and reproducibility reviewer for a new project called **Make My Figure**.

The goal is to build a rigorous app that lets a scientist upload a CSV, TSV, or Excel file, select a plot type commonly seen in high-impact biology and biomedical manuscripts, choose a target style profile such as **Nature-like**, **Science-like**, or **Cell-like**, and export a publication-ready figure in SVG/PDF/PNG/TIFF. The system must also maintain a curated reference library of post-2020 papers, figures, associated data, plot-style metadata, and test datasets so the app can improve over time.

This is a serious research-software project intended to support a future methods/resource paper. Optimize for accuracy, provenance, reproducibility, maintainability, and legal/ethical data use. Do not fabricate papers, DOIs, associated datasets, figure panels, or journal requirements.

## Critical constraints

1. **Respect copyright, licenses, robots.txt, and publisher terms.** Prefer open-access sources, PubMed Central/JATS XML, journal-provided open figure assets, supplementary data with clear license terms, GEO/SRA/ArrayExpress, Zenodo, Dryad, Figshare, OSF, and author-provided GitHub repositories. If a PDF, figure, or dataset cannot be legally downloaded, record it as unavailable and move on.
2. **Do not imply official journal endorsement.** Use names such as `nature_like`, `science_like`, and `cell_like` unless official style specifications are cited and implemented. The output should be “formatted for submission-like aesthetics,” not a guaranteed acceptance format.
3. **Do not train on copyrighted figures by default.** Build a reference and style-token library from legally usable examples and metadata. Use figures for local analysis only when license permits. Store provenance and license metadata beside every asset.
4. **Claude Code cannot literally become perfect.** Iterate until the acceptance tests pass or until the configured maximum iterations is reached. When stopped, report remaining gaps honestly.
5. **Use the lowest-cost model that is safe for the task, but escalate whenever correctness, ambiguity, legal risk, or scientific interpretation matters.**

## Model-routing policy

Use these model tiers conceptually. Map them to the models actually available in the current Claude Code environment.

- **Tier A: highest-reasoning model.** Use for paper inclusion/exclusion decisions, figure-panel classification QA, associated-data matching, architecture choices, visual-regression evaluation, final scientific review, license-risk review, and any disagreement between automated checks.
- **Tier B: strong coding model.** Use for implementation, refactoring, unit tests, plot renderers, schemas, dashboards, CLI tools, and deployment automation.
- **Tier C: economical/fast model.** Use for repetitive metadata normalization, folder organization, README drafts, routine docstring cleanup, simple CSV inspection, and non-critical formatting.

Escalate from Tier C or B to Tier A when confidence is low, when a source is ambiguous, when figure/data matching is uncertain, when a generated plot visually diverges from the reference, or when tests repeatedly fail. Never save tokens by compromising provenance or scientific correctness.

## Project phases

Work in phases. At the end of each phase, run tests, update documentation, and write a short `reports/phase_<number>_summary.md` with what changed, evidence, failures, and next actions.

### Phase 0: Repository initialization

Create a clean repository structure:

```text
make-my-figure/
  app/                         # Streamlit MVP or web frontend
  make_my_figure/              # Core Python package
    io/                         # CSV/TSV/XLSX loaders and validators
    plots/                      # Plot renderers
    styles/                     # Journal-like style engine
    stats/                      # SEM, CI, tests, survival, PCA, ROC helpers
    harvest/                    # Literature/data/figure curation pipeline
    qa/                         # Visual regression and curation QA
  data_library/
    journals/
      nature/
      science/
      cell/
    index.sqlite or index.jsonl
  mock_data/
  schemas/
  style_profiles/
  tests/
  docs/
  reports/
  scripts/
  .github/workflows/
  README.md
  LICENSE
  CITATION.cff
  pyproject.toml
```

Implement a Python package first. The MVP should be able to run locally from the command line and from a dashboard. Prefer a stack that produces precise vector output: Matplotlib for final export, optional Plotly/Altair only for preview. A Streamlit MVP is acceptable for the first app because it is fast to ship; a later React/FastAPI frontend may be added after the core plotting engine is stable.

Also create a GitHub Pages documentation site under `docs/`. Remember: GitHub Pages is static hosting. If the app needs a Python backend, GitHub Pages should host documentation, examples, screenshots, and links to the deployed app, not the backend itself.

### Phase 1: Define canonical schemas and mock-data tests

Create a canonical `PlotSpec` JSON schema with fields for:

- `plot_type`
- `input_table`
- `mapping`
- `statistics`
- `journal_style`
- `layout`
- `annotations`
- `output`
- `provenance`

Use the bundled mock data as golden inputs. Add tests that render at least these plot types:

1. Bar plot with SEM/SD/CI error bars
2. Grouped bar plot with error bars
3. Box/violin plot with points
4. Scatter plot with optional regression line
5. Line/time-course plot with error band
6. Clustered heatmap
7. Volcano plot
8. Enrichment dot plot
9. Kaplan-Meier survival curve
10. Stacked composition bar plot
11. Waterfall plot
12. PCA scatter from matrix + metadata
13. Oncoprint-style mutation heatmap
14. Lollipop mutation plot
15. ROC curve
16. Forest plot
17. Ridge/density plot

For each plot type, write a renderer function, input validator, default mapping, app UI form, and export test. Each renderer must accept a `PlotSpec` and return a figure plus a metadata object recording data columns, statistics, style profile, export dimensions, and warnings.

### Phase 2: Build the plotting engine

Implement robust table loading for CSV, TSV, and XLSX. The loader should infer delimiters, preserve sample IDs as strings, detect numeric columns, report missing values, and show clear validation messages.

Implement a style engine with profile files such as:

```yaml
profile_name: nature_like
font_family: Arial
base_font_pt: 7
axis_font_pt: 7
line_width_pt: 0.75
spine_width_pt: 0.5
single_column_width_mm: 89
double_column_width_mm: 183
color_policy: colorblind_aware
exports: [svg, pdf, png, tiff]
```

Use style tokens rather than hard-coded styling inside individual renderers. All plots should support:

- one-column and two-column sizing
- vector export
- transparent or white background
- colorblind-aware palettes
- panel labels
- legend placement
- editable title, axis labels, and units
- optional statistical annotations when valid
- a reproducibility sidecar file such as `figure_name.plot_spec.json`

### Phase 3: Build the dashboard/app

Create a user-facing dashboard with this flow:

1. Upload data file.
2. Preview and validate table.
3. Select plot type.
4. Map columns with dropdowns.
5. Select journal-like style profile.
6. Adjust dimensions, labels, sorting, transforms, and statistics.
7. Preview figure.
8. Export SVG/PDF/PNG/TIFF plus the `PlotSpec` sidecar.
9. Show “replace mock data with your data” guidance.

The app must have useful error messages. It should never fail silently. Include a sample-data picker that loads each mock table.

### Phase 4: Curate post-2020 CNS paper/figure/data library

Build a curation pipeline under `make_my_figure/harvest/`. It must identify at least 10 post-2020 research papers across Cell, Nature-family journals, and Science-family journals, with priority for open-access papers that provide associated data and contain common plot types.

For each candidate paper, record:

- title
- DOI
- journal
- publication date
- article type
- open-access status
- license
- source URLs
- whether full text/figures can be legally downloaded
- associated datasets and repositories
- data availability statement
- figure list
- detected plot types per figure/panel
- local file paths for legally downloaded assets
- QA status

Recommended sources to query when available: PubMed/NCBI E-utilities, PubMed Central, Crossref, Europe PMC, OpenAlex, Unpaywall, journal APIs, GEO, SRA, ArrayExpress, Zenodo, Dryad, Figshare, OSF, GitHub, and supplementary-material links from the paper.

Selection rules:

- publication date must be 2020-01-01 or later
- article must be a research article, resource article, methods article, or comparable primary/scientific report
- prioritize papers with downloadable source data or supplementary tables
- include a diversity of plot types, not only one field or one assay
- do not include inaccessible or non-permitted assets in the bundled library
- use Tier A model review for final inclusion decisions

Folder structure for each curated paper:

```text
data_library/journals/<journal_group>/papers/<doi_slug>/
  paper_metadata.yaml
  license.txt
  provenance.json
  full_text/                  # only if legally downloadable
  figures/                    # only if legally downloadable
  panels/                     # extracted panels if permitted
  associated_data/
  derived_plot_specs/
  qa_report.md
```

Figure extraction should prefer structured sources such as JATS XML from PubMed Central. If only PDFs are available and license permits local analysis, extract figures carefully. Use OCR only as a last resort. Store every extracted figure/panel with the source DOI, figure number, panel label, caption text, license, and extraction method.

### Phase 5: Match figures to associated data and infer style tokens

For each curated paper, attempt to connect figures or panels to source data. Use a conservative matching system:

- figure caption terms
- axis labels
- panel labels
- supplement filenames
- code repositories
- column names
- assay/sample identifiers
- manual-review status

Classify each panel into plot types. Extract style tokens such as dimensions, approximate font sizes, line widths, marker sizes, legend placement, axis/spine conventions, color palette roles, and panel-label conventions. Store these in machine-readable `plot_style_observations.json` files. Do not claim exact journal requirements unless verified from author guidelines.

Use Tier A review for uncertain figure-data matches. Mark ambiguous matches as `needs_human_review` rather than guessing.

### Phase 6: Add library update and journal-extension tools

Create CLI commands:

```bash
makefig harvest --journal-groups nature,science,cell --since 2020 --min-papers 10
makefig harvest-update --since-last-run
makefig curate-review --open data_library/index.sqlite
makefig style-build --journal-group nature --from-library
makefig style-add --journal-name elife --seed-dois seed_dois.txt
makefig render --plot-spec examples/barplot.plot_spec.json --out outputs/barplot.svg
makefig app
```

The update process must be incremental: it should not re-download existing assets unless checksums or source metadata changed. Add a curation status dashboard showing accepted, rejected, ambiguous, and license-blocked papers.

For adding a new journal, require either seed DOIs, uploaded example figures with permissions, or official style guidance. The system should infer a first-pass style profile, render mock plots, run visual QA, and produce a `style_profile_review.md` requiring human approval before publication.

### Phase 7: Quality assurance, tests, and reproducibility

Implement:

- unit tests for loaders, validators, statistics, and renderers
- visual regression tests using mock data and deterministic seeds
- schema validation tests for every `PlotSpec`
- export tests for SVG, PDF, PNG, and TIFF where supported
- app smoke tests
- curation tests that reject papers without provenance or license metadata
- linting and formatting
- documentation build checks

Acceptance criteria:

- all mock-data plot types render without errors
- each output has a sidecar `PlotSpec`
- no renderer mutates input data silently
- every curated paper has DOI, date, license status, source URLs, and QA status
- no bundled figure/data lacks license/provenance metadata
- app can load all mock tables and export at least SVG and PNG
- docs explain how users replace mock data with real data
- GitHub Pages docs build successfully
- CI passes

### Phase 8: Prepare for a methods/resource paper

Create `reports/resource_paper_assets/` containing:

- project summary
- architecture diagram source
- curation workflow diagram source
- benchmark table of supported plot types
- reproducibility checklist
- limitations and ethical/legal notes
- example figures generated from mock data
- roadmap for adding journals and plot types

Do not overclaim. Clearly state that the project creates journal-like, submission-aware figures and helps users standardize formatting; it does not guarantee acceptance by any journal.

## Iteration loop

For each phase, use this loop:

1. Plan the smallest useful milestone.
2. Implement it.
3. Run relevant tests.
4. Inspect generated figures and metadata.
5. Critique output against acceptance criteria.
6. Fix failures.
7. Repeat up to 8 iterations per phase.
8. If still failing, stop that phase, document blockers, and continue only if downstream work remains meaningful.

Keep a running task log in `reports/task_log.md` with decisions, model tier used, commands run, tests passed/failed, and unresolved risks.

## First concrete milestone

Start by creating the repository skeleton, schemas, style profiles, mock-data loaders, and renderers for the first five plot types: bar plot, grouped bar plot, box/violin plot, scatter plot, and line/time-course plot. Add tests and a simple Streamlit page that can load the bundled mock data and export SVG/PNG. After this milestone passes, continue through the remaining plot types and then the curation pipeline.

Do not ask for confirmation unless a required secret, credential, license permission, or deployment target is missing. Make reasonable engineering choices, document them, and proceed.
