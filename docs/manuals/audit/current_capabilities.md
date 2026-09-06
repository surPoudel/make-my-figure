# Make My Figure — current capability audit

**Application:** Make My Figure (Python package `make_my_figure_core`; desktop app `apps/desktop_app`; browser app `apps/streamlit_app`)
**Version audited:** 1.1.0 (`make_my_figure_core/version.py`) — release branch `release/v1.1.0-integration` (first audited at commit `ac49ff8` on 2026-09-03; re-verified for v1.1.0 on 2026-09-06: 22/22 manual instructions and 8/8 documented workflows re-executed, screenshots recaptured)
**Audit dates:** 2026-09-03 (initial), 2026-09-06 (v1.1.0 re-verification)
**Method:** every fact below was read from the code on this commit, exercised in the running application (desktop offscreen on Qt, browser app in headless Chromium, both on Linux), or both. Nothing was taken from the README, changelog or earlier documents without re-verification.

Classification key: **impl** = implemented on this commit · **tested** = covered by the pytest suite · **desktop** = a control exists in the PySide6 app · **browser** = a control exists in the Streamlit app · **documented** = covered in the two manuals produced with this audit · **limitation** = a boundary a user needs to know.

## 1. Identity, packaging, platforms

| Feature | impl | tested | desktop | browser | documented | limitation |
|---|---|---|---|---|---|---|
| Version string (`1.1.0`), build banner with commit | yes | yes (`test_style_leaks_and_version`) | status bar on launch; Help → About | sidebar banner + 🔧 Diagnostics | yes | the About dialog now falls back to the build-info commit, so both show the same commit (fixed for v1.1.0) |
| Desktop entry point `python -m apps.desktop_app.main` | yes | GUI tests skip without Qt | — | — | yes | needs PySide6 (`pip install -e ".[desktop]"`) and Qt system libraries on Linux |
| Browser entry point `streamlit run apps/streamlit_app/streamlit_app.py` | yes | AppTest suites | — | — | yes | Streamlit ≥ 1.30 |
| Packaged installers (PyInstaller): `MakeMyFigure-1.1.0-Setup.exe`, `-windows.zip`, `.dmg`, `.AppImage`, `-linux-x86_64.tar.gz` | yes (built from the v1.1.0 tag on the GitHub Actions native runners; `--selftest` passes on all three) | build scripts + CI workflow | — | — | yes | the v1.1.0 installers contain everything documented here, including Figure presets and the histogram |
| Supported OS | Windows, macOS, Linux (native), WSL (source only) | Linux CI | — | — | yes | macOS/Windows not exercised in this audit |
| Python for source installs | `requires-python >= 3.9` | CI 3.11 | — | — | yes | 3.9 is allowed by metadata but pip's byte-compile step failed on a PySide6 template under Apple's 3.9 during collaborator testing; recommend 3.10–3.12 and `--no-compile` |

## 2. Data input

| Feature | impl | tested | desktop | browser | documented | limitation |
|---|---|---|---|---|---|---|
| CSV / TSV / TXT / `.tab` delimited | yes | `test_loaders` | Open data file…, drag-and-drop | Upload file | yes | unknown extensions are parsed as delimited text with a warning |
| Excel `.xlsx`, `.xlsm`, `.xls` | yes (openpyxl; `.xls` read-only via pandas) | yes | yes | yes | yes | `.xls` merged-header recovery unavailable (legacy format has no merge map) |
| Multi-sheet workbook browser, every sheet selectable | yes | `test_workbook`, `test_multisheet_ui`, `test_controller_workbook` | 📑 Worksheet box | 📑 Worksheet + Workbook browser | yes | classification is advisory |
| Worksheet classification (`differential_results`, `matrix`, `metadata`, `enrichment`, `documentation`, `generic`, `empty`, `unknown`) | yes | yes | tooltip/info label | caption | yes | heuristic |
| Header row choice (first row / chosen row / two stacked rows / no header) + merged-cell recovery + forward fill | yes | `test_header_row_and_merged_headers` | **no control** (loads header row 1) | yes (sidebar) | yes | desktop cannot choose a header row |
| Editable data preview (edits re-render) | yes | AppTest | Data preview tab | data editor | yes | — |
| Missing-value detection warnings, numeric coercion | yes | yes | Messages tab | warnings | yes | — |
| In-app grouping: wide matrix → long, group by column values, guess groups from names | yes | `test_grouping` | 🗂 Define groups… dialog | 🗂 Define groups expander | yes | — |
| Volcano DE-column auto-detection (edgeR/limma/DESeq2 headers), user-confirmed | yes | `test_de_detect` | prefilled mapping | prefilled mapping | yes | never computes DE |

## 3. Plot registry (38 renderers, enumerated from `plots/registry.py`)

All 38 render from bundled examples in `tests/test_renderers*.py` and the preset QC. Display names as shown in both apps:

Bar plot with error bars · Grouped bar plot with error bars · Clustered heatmap · Volcano plot · Scatter plot · Box / violin plot with points · Line / time-course with error band · Ridge / density plot · Histogram (binned distribution) · Enrichment dot plot · Kaplan-Meier survival curve · Stacked composition bar plot · Waterfall plot · PCA scatter (matrix + metadata) · Oncoprint mutation heatmap · Lollipop mutation plot · ROC curve · Forest plot · Dot / strip plot · Beeswarm plot · Paired dot plot / slopegraph · Raincloud plot · Hierarchical clustering dendrogram · MA plot (differential expression) · Manhattan plot (GWAS) · Q-Q plot (p-value / quantile) · Bland-Altman (method agreement) · Precision-recall curve · Confusion matrix · Calibration plot · Dose-response curve · UpSet plot (set intersections) · Swimmer plot · Spider plot (longitudinal change) · Sankey / alluvial flow (two-stage) · UMAP / t-SNE embedding scatter · Hierarchical clustering (heatmap + clusters) · Network graph

| Aspect | impl | tested | desktop | browser | documented | limitation |
|---|---|---|---|---|---|---|
| Column roles and options from one registry (`ui_hints.py`), 164 options, each with a style/config scope | yes | `test_figure_presets` | generic widgets | generic widgets + hand-written ones | yes | — |
| Multi-column roles (`survival_columns`, `value_columns`) as multi-select lists | yes | yes | QListWidget | multiselect | yes | — |
| Optional numeric options shown as "(auto)" | yes | yes | spin-box special value | empty text box | yes | — |

## 4. Statistics (18 methods, `statistics/TESTS`)

| Family | Methods | tested | annotation on figure | limitation |
|---|---|---|---|---|
| Two-group | Student's t, Welch's t, Mann-Whitney U, paired t, Wilcoxon signed-rank | `test_statistics_core`, `test_statistics_oracle_validation` (scipy/statsmodels oracles) | bar, grouped bar, box/violin (brackets or above-bar) | — |
| Omnibus | one-way ANOVA, two-way ANOVA, repeated-measures ANOVA, Kruskal-Wallis | yes | omnibus text; post-hoc pairwise optional | Dunnett's test is **not** implemented |
| Post-hoc | Dunn's test | yes | brackets | — |
| Categorical | Chi-square, Fisher's exact | yes | stacked composition corner panel | — |
| Survival | log-rank, Cox proportional hazards (HR) | yes | Kaplan-Meier corner panel | log-rank cannot be computed from a precomputed curve — refused with a message |
| Correlation / regression | Pearson, Spearman, linear regression, GLM (multi-predictor) | yes | scatter fit-stats box | — |
| Multiple testing | Benjamini-Hochberg, Bonferroni, Holm, none | yes | adjusted p in table/labels | — |
| Effect sizes | Cohen's d, Hedges' g, rank-biserial, Cliff's delta, eta-squared (partial approx.), Cramér's V, odds ratio, R², Spearman rho, hazard ratio | yes | optional on figure | — |
| Comparison modes | auto, all pairs, vs control, within each x, selected pairs, omnibus only | yes | — | — |
| Annotation content | stars, p, adjusted p, p+stars, statistic, effect, p+statistic, full, flags, custom template | `test_annotation_formatting`, `test_stats_annotations` | — | — |
| Annotation placement | bracket, above each bar (needs control group) | `test_above_bar_annotation` | — | line plot has no statistical annotation |
| Method sentence, stats table export (CSV/TSV), method report (markdown) | yes | yes | buttons | shown/downloads | yes | — |
| Invariant: every drawn p-value comes from a stored `StatResult` | yes | yes | — | — | yes | — |

## 5. Matrix Workflow, preprocessing, QC

| Feature | impl | tested | desktop | browser | documented | limitation |
|---|---|---|---|---|---|---|
| Steps: ① Map columns ② Define groups ③ Preprocess (raw-like) ④ Validation ⑤ Recommend & generate | yes | `test_matrix_workflow_core`, `test_matrix_workflow_rendering`, `test_desktop_matrix_controller`, `test_streamlit_matrix_wizard` | 🧮 Matrix workflow… dialog (tabs) | Workflow → Matrix workflow (guided) | yes | later tabs stay disabled until mapping / groups are confirmed |
| Value scale must be confirmed (`normalized`, `log_normalized`, `raw_numeric`, `unknown_user_confirmed`) | yes | yes | combo | select | yes | no silent guessing |
| Annotation columns never treated as measurements without confirmation | yes | `test_memory_guards` | unselected by default | unselected by default | yes | — |
| Metadata: upload file, from workbook sheet, in-app assignment, sample matching report | yes | yes | ⬆ Upload metadata file…; table | uploader; table | yes | — |
| Preprocessing methods (`available_methods`): arcsinh, center, column_zscore, control_features, cpm, filter, global_zscore, impute, internal_standard_columns, internal_standard_features, ln, log, log10, log2, median_scale, quantile, reference_sample, robust_scale, row_zscore, sqrt, standard_scale, tmm, total_sum, upper_quartile, voom, winsorize, zscore | yes | `test_preprocessing_transforms`, `test_normalization_methods`, `test_internal_standard_normalization`, `test_transforms` | yes | yes | yes | applied only to raw-like data; each step recorded in a `PreprocessingSpec`; original matrix preserved; `voom` is the limma-style transform of the matrix only (no DE) |
| Normalization recommendations (total_sum, median_scale, upper_quartile, quantile, row_zscore, internal_standard_features) with assumptions/risks | yes | `test_preprocessing_recommendations` | yes | yes | yes | advisory |
| QC diagnostics + QC plots: library size, sample median, per-sample box, value density, zero fraction, missing fraction, sample correlation, PCA, mean–variance | yes | `test_preprocessing_diagnostics`, `test_preprocessing_qc_plots`, `test_matrix_qc_polish` | Run diagnostics; Save before/after QC report… | 🔧 Diagnostics | yes | — |
| Differential summary (two-group: welch_t, students_t, mann_whitney, paired_t, wilcoxon; multi-group: anova, kruskal; BH/Bonferroni/Holm), feature-level summary | yes | `test_differential`, `test_feature_differential_summary`, `test_processed_matrix_differential_summary` | Compute differential summary | Run differential screen / Compute differential summary | yes | **not** DESeq2/edgeR/limma; optional `count-de` extra (PyDESeq2) is opt-in and untested here |
| Handoff to the plot editor with provenance; revert to raw matrix | yes | `test_matrix_handoff` | Open in plot editor; ↩ Revert | Open in plot editor; ↺ Revert | yes | — |
| Derived matrices saved as new CSV with steps recorded | yes | yes | yes | yes | yes | — |

## 6. Recommendations

| Feature | impl | tested | desktop | browser | documented | limitation |
|---|---|---|---|---|---|---|
| Rule-based schema detection: precomputed_differential, survival, gwas, classification, dose_response, network_edge_list, mutation_matrix, enrichment, correlation_matrix, expression_like_matrix, numeric_matrix, matrix_plus_metadata, paired, generic_long, unknown | yes | `test_recommendations`, `test_plot_recommendations` | Recommended plots group (Generate / Add to Figure Builder / Dismiss) | 🔮 Recommended figures expander | yes | advisory; confidence is a heuristic score, not a probability |
| Statistics suggestions per plot/mapping | yes | yes | "Suggested:" line in Statistics | shown | yes | advisory |
| Transform recommendations after analysis | yes | yes | — | — | yes | — |

## 7. Publication controls, colour, annotations

| Feature | impl | tested | desktop | browser | documented | limitation |
|---|---|---|---|---|---|---|
| Single **Publication** style; palettes publication / colorblind_safe / high_contrast / grayscale | yes | `test_publication_style*`, `test_styles`, `test_style_migration` | 5. Publication style | 5. Publication style | yes | not a journal template; legacy journal-named profiles migrate on load |
| Typography (title/axis/tick/annotation/legend pt, font family on desktop), marker size, line width, spine width, grid | yes | yes | ② Typography | ② Typography | yes | browser has no font-family control |
| Axes & labels: tick angles, label/title padding; margins; auto-fix layout | yes | `test_layout_and_annotations`, `test_layout_qc` | ③ / ① | ③ / ① | yes | — |
| Legend location (inside/outside positions), legend pt, outside | yes | yes | ④ | ④ | yes | — |
| Colorbar location/pad/size (heatmap, clustering, confusion, enrichment) | yes | yes | ⑤ | ⑤ | yes | — |
| Capability-aware controls: inapplicable controls are reported, never silently ignored (`styles/capabilities.py`, generated from renderer source) | yes | `test_style_capabilities_audit` | caption | warnings | yes | the browser app sends every style token, so plots without markers/lines/legends show several "ignored" notices by default |
| Plot-specific colours: heatmap colormap, network node/edge colours, volcano up/down/ns, MA ns, Manhattan cutoff line | yes | yes | 3. Options | options | yes | no free-form colour picker; colours are chosen from curated lists (network accepts a JSON node-colour map in the browser) |
| Click-to-identify / click-to-label (volcano, scatter, MA); labels persist in the PlotSpec | yes | `test_pick_identify`, `test_annotation_state` | Point picking checkbox | Label points expander (pick + offset controls) | yes | desktop has no drag-to-move; offsets are set in the browser app or PlotSpec |
| Duplicate feature labels: all / unique / count, representative rule (p, adj p, effect, statistic, first) | yes | `test_duplicate_labels` | options | options | yes | — |
| Manual annotation layer in PlotSpec (`annotations`: text, arrow, callout, box, region, bracket, hline, vline) | yes | `test_layout_and_annotations` | via PlotSpec / imported panels | via PlotSpec | yes | no general in-app drawing editor for generated plots |
| Publication readiness check + layout QC + scored Publication QC with fixes | yes | `test_publication_qc*`, `test_xlabel_overlap_qc` | Publication QC button; Messages | ✅ Publication QC expander | yes | advisory |

## 8. Figure presets

| Feature | impl | tested | desktop | browser | documented | limitation |
|---|---|---|---|---|---|---|
| Style preset and full-configuration preset for every plot type; no data, table name or provenance | yes | `test_figure_presets` (157), `test_figure_preset_qc` (38/38), `test_streamlit_presets`, `test_figure_preset_ui_wiring` | Figure preset group + File → Figure preset | Figure preset expander | yes | — |
| Apply, Save preset…, Import…, Export…, Delete, Reset to Publication defaults | yes | yes | yes | yes | yes | browser import is a file uploader; export is a download |
| Missing columns reported for remapping, never substituted | yes | yes | dialog | warning | yes | — |
| Per-user library: `%APPDATA%\MakeMyFigure\presets`, `~/Library/Application Support/MakeMyFigure/presets`, `$XDG_DATA_HOME/make_my_figure/presets`; `MAKE_MY_FIGURE_PRESETS` override | yes | yes | — | — | yes | macOS/Windows paths derived from platform convention, not exercised here |
| Format `make_my_figure.figure_preset` v1, extension `.mmfpreset.json`; raw PlotSpec / sidecar loads as full preset | yes | yes | — | — | yes | — |

## 9. Reproducibility records

| Record | impl | written by | documented |
|---|---|---|---|
| PlotSpec (`*.plot_spec.json`, sidecar with `render_metadata`) | yes | every export | yes |
| StatsSpec (`*.stats_spec.json`) | yes | export when statistics ran | yes |
| MatrixSpec, SampleMetadataSpec, PreprocessingSpec | yes | Matrix Workflow (embedded in provenance / QC report) | yes |
| FigureSpec (`*.figure_spec.json`) + `figure_builder_assets/` | yes | Figure Builder save | yes |
| Layout preset (`*.mmflayout.json`) | yes | Figure Builder | yes |
| Before/after QC report (PNG/PDF contact sheet) | yes | Matrix Workflow | yes |
| Statistics method report (markdown), stats table (CSV/TSV) | yes | Statistics panel | yes |

## 10. Figure Builder

| Feature | impl | tested | desktop | browser | documented | limitation |
|---|---|---|---|---|---|---|
| Generated panels (PlotSpec + table, re-rendered), imported panels (PNG/JPG/JPEG/TIF/TIFF/WEBP/BMP raster; PDF/SVG/EPS via optional `import-panels` extra, rasterised at 300 dpi) | yes | `test_multipanel`, `test_imported_panels` | Save current plot as panel; Open Figure Builder…; Import panel from file… | ⑤ Figure Builder inside the guided Matrix workflow only (columns + compose) | yes | browser builder has no per-panel sizing or import |
| Grid: columns, rows, figure width (mm), horizontal/vertical gutters, panel letter style (A/a/1), export DPI | yes | yes | yes | columns only | yes | no free x/y placement, no z-order, no snap grid — it is a grid layout |
| Per-panel width/height in inches (aspect preserved), order, duplicate, remove | yes | yes | yes | — | yes | — |
| Global fonts applied to every panel | yes | yes | yes | — | yes | — |
| Imported-panel transforms: fit mode, crop, rotate, flip, auto-trim, border, background, annotations | yes | yes | yes | — | yes | — |
| Export PNG/SVG/PDF + FigureSpec | yes | yes | Save figure… | downloads | yes | **panel content is embedded as raster** at the panel DPI; only panel letters/titles are vector text |
| Layout presets (save/apply/import/export/delete) | yes | yes | Layout preset group | — | yes | — |

## 11. Export

| Format | vector/raster | DPI applies | text editable | where |
|---|---|---|---|---|
| SVG | vector | no | yes (`svg.fonttype: none`) | both apps |
| PDF | vector | no | yes (Type 42 fonts) | both apps |
| EPS | vector | no | yes (Type 42) | core/desktop ZIP; not a browser button |
| PNG | raster | yes (150–600 in UI) | — | both apps |
| TIFF | raster (LZW) | yes | — | core/desktop ZIP; not a browser button |
| PlotSpec JSON / StatsSpec JSON | — | — | — | both apps |
| ZIP bundle of formats + sidecars | — | — | — | desktop (Export all as ZIP) |

## 12. Help, navigation, panels

| Feature | impl | desktop | browser | limitation |
|---|---|---|---|---|
| Help dialog: Plot types (from manifest), Format your data, Privacy, Publication style disclaimer | yes | Help → Help… | sidebar captions | — |
| About (version, commit), Copy debug info, Diagnose toolbar | yes | Help menu | 🔧 Diagnostics expander | About shows `commit unknown` |
| Home / Upload New Data (clears state) | yes | button + File menu | 🏠 Reset / Upload new data | — |
| Pop-out / dock panels (Plot Controls, Data & Messages, Figure), Reset Layout, Maximize Figure Panel | yes | View menu; ⮊ Dock back | — | — |
| Background rendering workers (responsive UI) | yes | yes | — | — |

## 13. Known limitations (from code and tests)

- Publication is a general manuscript style, **not** a journal template, and does not guarantee acceptance.
- Statistics are computed, not chosen: the researcher selects the method; recommendations are advisory.
- No DE inference (DESeq2/edgeR/limma) is performed; DE p-values are read verbatim. Dunnett's test is not implemented.
- Heatmap/clustering cap features at 2 000 rows by default (`max_features`, adjustable 50–50 000) and select by variance.
- Figure Builder composites embed panel content as raster; free positioning/z-order is not available.
- Desktop app has no header-row selector (browser app does); desktop has no drag-to-move for labels.
- Browser Figure Builder exists only inside the guided Matrix workflow and supports columns only.
- Two cosmetic desktop defects observed offscreen: group titles containing "&" ("Plot type & style", "Labels & size", "Axes & labels", "Recommend & generate") render with a Qt mnemonic (the "&" is consumed), (the About-dialog commit lookup was fixed in v1.1.0).
- Browser app reports several "style control … ignored" notices for plot types without markers, lines or legends because every style token is always sent.
- The v1.1.0 installers are built from the same tagged source as these manuals.
- Cross-platform font/spacing differences are expected; no byte-identical output promise.
