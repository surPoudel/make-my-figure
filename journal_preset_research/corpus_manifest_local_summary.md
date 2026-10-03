# Local corpus for the journal figure preset project - summary

Read-only inventory of every published paper/figure already on disk that could act as a style
reference. Source of truth: `corpus_manifest.csv` in this folder (146 rows, one per
paper/panel; 124 distinct DOIs).
Nothing was moved, copied or deleted; every absolute path in the manifest was checked to exist.

**Headline: 24 of 146 panel rows (20 distinct articles) have a published
figure IMAGE on disk and can be measured for visual style. The other 122 are
metadata-only records (candidate screens, DOI-only design references, source-data provenance).**

## Counts per journal family

| journal family | rows | of which image present |
|---|---|---|
| Nature-family | 99 | 15 |
| other | 28 | 8 |
| Cell-family | 9 | 1 |
| Science-family | 9 | 0 |
| mixed | 1 | 0 |

Journals behind the 24 measurable rows:

| journal | measurable panels |
|---|---|
| Nature Communications | 9 |
| eLife | 5 |
| Nature Cancer | 2 |
| eLife (Reviewed Preprint RP97654) | 2 |
| Nature Cell Biology | 1 |
| Nature | 1 |
| Developmental Cell | 1 |
| Nature Medicine | 1 |
| Nature Metabolism | 1 |
| PLoS ONE | 1 |

## Counts per plot family

| plot family | rows | of which image present |
|---|---|---|
| bar | 29 | 0 |
| other | 25 | 1 |
| scatter/regression | 15 | 4 |
| survival | 15 | 5 |
| volcano/MA | 15 | 4 |
| box/violin | 10 | 2 |
| line/time-course | 9 | 2 |
| heatmap | 8 | 2 |
| forest | 8 | 1 |
| PCA/UMAP | 6 | 1 |
| oncoprint/categorical | 3 | 1 |
| dot/bubble | 3 | 1 |

## Where the images actually are

1. **Figure 2 final six (highest quality).** For each of panels A-F: the untouched publisher figure
   PNG (0.26-1.4 MB), a previous reference crop, and a clean re-crop with a pixel-box provenance CSV.
   - `MakeMyFigure_manuscript_final/PRIVATE_REFERENCE_ONLY/Figure2_published_panels/` (14 PNGs)
   - `MakeMyFigure_submission_final/03_supplementary_figures/Supplementary_Figure_1_redesign/PRIVATE_REFERENCE_ONLY/untouched_originals/` (13 files, incl. the ONLY publisher full-resolution JPEG: `Panel_E_published_figure_full_highres_gr1_lrg.jpg`, 3336x2902)
   - `.../Supplementary_Figure_1_redesign/published_crops/` (6 crops + `published_crop_provenance.csv` with exact crop boxes and what is kept/excluded)
2. **Figure 2 superseded "Nat Commun six" (2026-09-04) and the archived Nature Metabolism panel.**
   `MakeMyFigure_manuscript_final/04_figure_evidence/Figure2/_superseded_2026-09-04/reference_panels/PRIVATE_REFERENCE_ONLY/Panel_{A..F}/`
   and `make_my_plot_task2/manuscriptv3/_archive/Figure2_{natcommun_six,panelD_natmetab_you}_2026-09-08/reference_panels/`.
3. **Figure 3: exactly two images**, both whole published figures rather than crops -
   `MakeMyFigure_manuscript_final/PRIVATE_REFERENCE_ONLY/Figure3_published_panels/` (Till 2024 Nat Commun Fig. 2, four KM panels; Schwaemmle 2025 Nat Commun Fig. 5, volcano + MA).
4. **Benchmarks: 8 eLife/PLoS crops** under
   `make_my_plot/benchmarks/ten_publication_recreation/publications/*/reference_figures/*/reference_panel.png`,
   each with a `crop_metadata.json` box and a `license.txt`. Mirrored byte-identically inside the
   `make_my_plot_figure4` and `make_my_plot_figure5` repos.
5. **Rendered comparisons (published vs recreation, published panel embedded):**
   `MakeMyFigure_manuscript_final/07_supplement/figures/SupplementaryFigure1_Figure2_published_vs_recreated.png`,
   `Manuscript_reorganization_091026/03_Supplementary_Figures/Supplementary_Figure_1.{svg,pdf,png}`
   (the six crops exist there only as base64 rasters inside the SVG), and the per-panel
   `supplementary_comparison/Panel_*_comparison.png` sets.

## Licence position

| licence as recorded locally | rows |
|---|---|
| CC BY 4.0 | 109 |
| unknown | 34 |
| CC BY-NC-ND 4.0 | 2 |
| CC BY-NC 4.0 | 1 |

Every article whose figure image is stored locally is CC BY 4.0, read from the article's own
full-text XML `<license>` element (Figure 2/Figure 3 sets) or from a `license.txt` written at
download time (benchmark set). Two non-CC-BY items are recorded and deliberately unused for imagery:
Boada-Romero 2025 Nat Cell Biol (CC BY-NC-ND, GEO matrix only) and Ahn 2023 Sci Adv (CC BY-NC,
rejected candidate). Roughly 14 further candidate articles were rejected on a CC BY-NC-ND licence
but their DOIs were never recorded, so they cannot be re-identified locally.

## Obvious gaps

- **No Science-family image at all.** Science Advances, Science and Science Translational Medicine
  appear only as candidate rows or as Figure 3 panel E (Lucero 2025), whose
  `source_figure_reference.md` records "Not stored (no image URL)" - Supplementary Figure 3 falls back
  to a citation placeholder for it. A Science/Sci Adv preset cannot be measured from local material.
- **Cell-family is one image deep.** Only Secchia 2022 Dev. Cell (UMAP). Cell, Cancer Cell, Molecular
  Cell, Cell Genomics and Cell Reports Medicine exist as candidate rows only.
- **No bar-chart image**, despite bar being the single largest plot family in the manifest (29 rows,
  0 with images) - the whole Figure 3 statistics candidate pool is bar/dot panels and none was
  downloaded. Same for **forest** (8 rows, 1 image: Penha 2023 eLife) and **dot/bubble**
  (3 rows, 1 image: Kume 2024 eLife).
- **Figure 4 and Figure 5 contribute no published imagery whatsoever.** Their 28 "high-impact figure
  design" references are DOI-only notes with no image, no XML and no licence recorded; their plotted
  data comes from the benchmark papers already listed.
- **Only two Figure 3 images, and both are whole figures, not panel crops** - no crop box is recorded
  for them, unlike the Figure 2 set which has `published_crop_provenance.csv`.
- **No local source-data workbook for the final Figure 2 six inside `MakeMyFigure_manuscript_final`**;
  they survive only in `make_my_plot_task2/manuscriptv3/Figure2/data/Panel_*/raw/`. The
  `Manuscript_reorganization_091026` tree stores neither workbooks nor image files, only URLs + SHA-256.
- **Journal metadata quality.** `article_type` is `research-article` for every article with a local
  JATS XML and unrecorded everywhere else (benchmarks, candidate CSVs, design notes store no
  `<article-type>`). Author fields in several `paper_metadata.json` files are empty lists or a raw
  affiliation dump, so authors in the manifest were taken from XML `<surname>` elements,
  `citation.txt`, and `07_References/reference_key_map.csv`.
- **Data-integrity issues seen while inventorying** (not fixed, read-only): the two Kume 2024 benchmark
  entries record different titles/authors for one DOI; `gorman2014_penguins/source/license_notes.md`
  claims no figure image is stored while a Fig. 3 PNG is present; `osipovich2023_zfp92_islet` is
  absent from the benchmark manifest; Till 2024's source sheet is recorded as "Figure 2" in one trace
  and "Figure 5" in Supplementary Table 2.

## Suggested next step for preset measurement

The immediately usable measurement set is the 24 image rows, dominated by
Nature-family (15) with a long tail of eLife/PLoS (8) and a single
Cell-family panel. For a genuinely cross-family preset study the corpus needs new acquisitions for
Science-family, Cell-family and bar/forest/dot panels - the candidate CSVs already name CC BY 4.0
articles for each of those (see rows with `usable_for_measurement = no` and a
`v2_candidate_panel_search.csv` or `published_statistics_candidate_search.csv` source).
