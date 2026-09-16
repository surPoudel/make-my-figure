# Corpus sampling protocol: open-access research figures from three journal families

Version 1.0, written 2026-09-16 (before any download). Executed by
`scripts/build_figure_corpus.py`; every rule below is implemented there so the
corpus can be regenerated deterministically.

## 1. Purpose

Build a reproducible reference set of published, quantitative research figures
from the Nature, Science and Cell journal families so that figure *style*
(panel size, fonts, axis conventions, colour use, plot-type frequency) can be
measured against real published output. The downloaded material is a private
research reference only. It lives under `PRIVATE_REFERENCE_ONLY/corpus/<paper_id>/`,
which is git-ignored, and is never redistributed.

## 2. Data source and legal basis

* Source: Europe PMC REST API, restricted to the Europe PMC open-access subset
  (`OPEN_ACCESS:y`). Only articles carrying an explicit machine-readable
  `<license>` element in the JATS XML are stored; the license text and URL are
  recorded per paper and per figure row.
* Metadata/search: `https://www.ebi.ac.uk/europepmc/webservices/rest/search`
  (`format=json`, `resultType=lite`, `pageSize=100`, `sort=P_PDATE_D desc`, cursor paging).
* Full text: `https://www.ebi.ac.uk/europepmc/webservices/rest/{PMCID}/fullTextXML`.
* Figure bitmaps: the Europe PMC pattern `https://europepmc.org/articles/{PMCID}/bin/{href}`
  was tested on 2026-09-16 and is behind a Cloudflare JavaScript challenge (HTTP 403,
  "Just a moment..."); it is NOT bypassed. Instead the same open-access files are
  taken from PubMed Central: the PMC article page `https://pmc.ncbi.nlm.nih.gov/articles/{PMCID}/`
  is fetched once and each `<img class="graphic">` whose file name equals the JATS
  `<graphic xlink:href>` basename gives the CDN URL
  (`https://cdn.ncbi.nlm.nih.gov/pmc/blobs/.../{href}`). Fallback if the page or a
  file is missing: the Europe PMC `.../rest/{PMCID}/supplementaryFiles` zip, from
  which only main-figure files are extracted.
* Politeness: one client with a descriptive User-Agent, 0.34 s sleep between
  Europe PMC calls, 0.5 s between PMC/CDN downloads, 3 retries with back-off.

## 3. Scope

* Publication date window: `FIRST_PDATE:[2023-01-01 TO 2026-09-15]`.
* Publication type: `PUB_TYPE:"research-article"` (JATS `article-type` must also be
  `research-article` after the XML is fetched).
* Journals (Europe PMC uses MEDLINE abbreviations; the exact `JOURNAL:` values are):

| Family  | Journals (query value -> display name) |
|---------|-----------------------------------------|
| Nature  | "Nature" -> Nature; "Nat Methods" -> Nature Methods; "Nat Biotechnol" -> Nature Biotechnology; "Nat Cell Biol" -> Nature Cell Biology; "Nat Commun" -> Nature Communications |
| Science | "Science" -> Science; "Sci Adv" -> Science Advances; "Sci Transl Med" -> Science Translational Medicine |
| Cell    | "Cell" -> Cell; "Cancer Cell" -> Cancer Cell; "Cell Metab" -> Cell Metabolism; "Cell Syst" -> Cell Systems; "Mol Cell" -> Molecular Cell; "Cell Rep" -> Cell Reports |

* `SRC:PMC` from the original brief is NOT used: Europe PMC assigns `SRC:MED` to
  PubMed-indexed journal articles even when a PMCID exists, and `SRC:PMC` only to
  PMC-only records, so `SRC:PMC` returns zero hits for these journals. Having a
  PMCID plus `OPEN_ACCESS:y` is the operative filter.

## 4. Version preference (publisher vs author manuscript)

Many Science/Cell OA-subset records are NIH author manuscripts (Europe PMC flag
`AUTH_MAN:y`; JATS `<article-id pub-id-type="manuscript">`; file names `nihms-*`).
Their figures are author-supplied and were not typeset by the publisher. Rule:

1. Query each journal twice: `... AND NOT AUTH_MAN:y` (publisher versions) and
   `... AND AUTH_MAN:y` (author manuscripts).
2. Fill the journal quota from publisher versions first, in the deterministic order
   of section 6. Only if the quota is not met are author manuscripts appended, in the
   same order.
3. Author manuscripts are kept in the corpus but flagged: `article_type` =
   `research-article (author manuscript)`, `usable_for_measurement` = `partial`,
   note = "author manuscript; figures not publisher-typeset". They are usable for
   plot-family frequency and for author-side conventions, not for publisher typesetting.

## 5. Eligibility (judged from the full-text XML, no image viewing)

A paper is eligible when ALL hold:

* JATS `article-type="research-article"` and a `<license>` element is present.
* It has at least 2 main figures. Main figures are `<fig>` elements under
  `/article/body` or `/article/floats-group` whose label matches
  `^(Fig\.?|Figure)\s*\d+` and that are not inside `<supplementary-material>`,
  `<app>`/`<app-group>`, or `<sec sec-type="supplementary-material">`, and whose
  label does not contain "Extended Data", "Supplementary", "S\d". Each main figure
  must have a `<graphic>`.
* At least 2 main figures are "quantitative data figures", defined by the caption
  test below.
* Exclusions: the article type or title identifies a review, perspective, comment,
  protocol, resource description without data, or correction; papers whose captions
  are all schematic/microscopy only (no figure passes the quantitative test).

Caption test for a quantitative data figure (case-insensitive regex on the full
caption text): the caption matches at least one STRONG marker, or at least two WEAK
markers.

* STRONG: `quantif`, `\bn\s*=\s*\d`, `\bP\s*[<=>]`, `p\s*-?\s*value`, `mean\s*[±+/-]|mean\s+±|±\s*s\.?[de]\.?m?`,
  `s\.?e\.?m\.?\b|s\.?d\.?\b`, `box\s*plot|boxplot|violin`, `heat\s*map`,
  `kaplan|survival`, `volcano`, `\bPCA\b|principal component`, `\bUMAP\b|t-?SNE`,
  `bar\s*(chart|graph|plot)|bars? (represent|show|indicate)`, `scatter`,
  `regression|correlation|Pearson|Spearman|R\^?2|r\s*=`, `dose[- ]response|IC50|EC50`,
  `fold[- ]change|log2`, `error bars?`, `two-?sided|one-?sided|t-test|Wilcoxon|Mann|ANOVA|Kruskal|chi-?square|log-?rank|Fisher`,
  `\*\s*P|\*\*`, `confidence interval|95%\s*CI|hazard ratio|odds ratio|forest plot`,
  `AUC|ROC`, `enrichment|GSEA|GO term`, `time[- ]course|over time|kinetics`.
* WEAK: `percentage|%\s*of`, `distribution`, `frequency`, `expression level`,
  `ratio`, `number of`, `counts?\b`, `density`, `abundance`, `score`.

A figure is `microscopy/other` only (fails the test) when none of the above match
and the caption is dominated by `micrograph|immunofluorescence|confocal|staining|
representative image|schematic|model|cartoon|workflow|overview|cryo-?EM|structure|
density map|western blot|gel`.

## 6. Deterministic ordering and selection

* Candidate lists come from the API sorted by `P_PDATE_D desc`; the script then
  re-sorts locally by (`firstPublicationDate` desc, numeric PMCID desc) so ties are
  fixed. Paging uses `cursorMark` with `pageSize=100`.
* Candidates are examined in that order; the XML is fetched and eligibility checked
  one by one; the first N eligible per journal are taken. Ineligible papers are
  logged with the failing rule.
* Screening budget: at most 120 candidates screened per journal per version class
  to bound API load; if the quota is not reached the shortfall is redistributed.
* Family target: 50 papers (minimum acceptable 30). Per-journal quota: base =
  floor(50 / n_journals), the remainder given one each to the journals in the table
  order (Nature family 10 x 5; Science family 17,17,16; Cell family 9,9,8,8,8,8).
* Cap: no journal may exceed 40 % of its family (20 papers). If a journal cannot
  fill its quota (too few eligible OA papers), the shortfall is redistributed to
  the other journals of the family in table order, respecting the cap; if the cap
  blocks redistribution the family stays below 50 and this is logged.

## 7. Per-paper download and storage

`PRIVATE_REFERENCE_ONLY/corpus/<paper_id>/` where `paper_id` = PMCID. Contents:

* `fulltext.xml` (Europe PMC JATS), `pmc_page.html` is NOT stored (only parsed).
* `figures/Fig<N>.<ext>` main figures only, in the publisher-supplied format
  (currently `.webp`; some older records `.jpg`). Supplementary/Extended Data
  figures are skipped.
* `metadata.json`: PMCID, PMID, DOI, title, authors, journal, family, dates,
  article type, version class, license text/URL, per-figure caption, graphic href,
  download status, keyword hits, assigned plot families.
* `LICENSE.txt`: verbatim `<license>` text plus URL.

## 8. Plot-family assignment (caption-based, to be refined visually later)

Each main figure gets one or more of these families from caption regexes, in
this fixed vocabulary: `scatter/regression`, `line/time-course`, `bar/group comparison`,
`box/violin`, `PCA/UMAP`, `volcano/MA`, `heatmap`, `survival`, `forest/effect-size`,
`dot/bubble`, `categorical/composition`, `microscopy/other`.

| Family | Caption regex (case-insensitive) |
|---|---|
| scatter/regression | `scatter|regression|correlat|Pearson|Spearman|\bR\^?2\b|\br\s*=\s*[-0-9.]|linear fit|versus|vs\.` (the last two only together with a numeric marker) |
| line/time-course | `time[- ]course|over time|kinetic|trajector|growth curve|dose[- ]response|IC50|EC50|line (graph|plot)|curve|longitudinal|days? (after|post)|hours? (after|post)|\bdpi\b|\bh\s*p\.?i\.?` |
| bar/group comparison | `bar (chart|graph|plot)|bars? (represent|show|indicate|denote)|relative (expression|abundance|level)|fold[- ]change|normali[sz]ed to|compared (with|to) control|mean\s*[±+]|s\.?e\.?m\.?|s\.?d\.?\b|quantification of` |
| box/violin | `box\s*plot|boxplot|box[- ]and[- ]whisker|violin|median|interquartile|whisker` |
| PCA/UMAP | `\bPCA\b|principal component|\bUMAP\b|t-?SNE|\bPC\s?1\b|embedding|dimensionality reduction|cluster(ing)? (analysis|of cells)` |
| volcano/MA | `volcano|\bMA plot|differentially expressed|log2\s*\(?fold|-?log10\s*\(?\s*(P|adj|FDR|q)` |
| heatmap | `heat\s*map|hierarchical clustering|z-?score|row[- ]scaled|colou?r scale (indicates|represents)|matrix` |
| survival | `kaplan|survival (curve|analysis|probability)|log-?rank|overall survival|progression-free|hazard ratio|\bHR\s*=` |
| forest/effect-size | `forest plot|effect size|odds ratio|\bOR\s*=|hazard ratio|95%\s*CI|confidence interval|meta-analysis|coefficient` |
| dot/bubble | `dot plot|bubble|circle size|size of (the )?(dot|circle|point)s? (indicates|represents|reflects)|individual (data )?points|each (dot|point) represents` |
| categorical/composition | `stacked|proportion|percentage of|composition|pie chart|fraction of|distribution of|alluvial|Sankey|donut|contingency` |
| microscopy/other | `micrograph|immunofluorescen|confocal|stain|representative image|schematic|cartoon|workflow|diagram|cryo-?EM|crystal structure|density map|western blot|immunoblot|gel|FACS plot|flow cytometry plot|model of` |

A figure with no family match but passing the quantitative test is labelled
`bar/group comparison` when a statistical-test marker is present, otherwise
`microscopy/other` with note `unclassified-quantitative`. The manifest stores families joined by `|` in the order above. Panel granularity is `all` at this stage.

## 9. Manifest and log

* `journal_preset_research/corpus_manifest_expanded.csv`, one row per main figure,
  exact columns: `paper_id,authors,year,journal,journal_family,DOI,article_type,figure_number,panel,plot_family,local_source,license,usable_for_measurement,notes`.
  `local_source` is the path relative to the repository root. `license` is the license
  URL followed by the verbatim license text (whitespace-collapsed). `usable_for_measurement`
  is `yes` (publisher version, image downloaded, quantitative), `partial` (author
  manuscript, or figure is microscopy/schematic only), or `no` (image missing).
* `journal_preset_research/corpus_expansion_log.md`: exact queries, counts retrieved /
  screened / eligible / selected per journal and version class, failures, achieved date
  range, license distribution, known biases.

## 10. Known biases (recorded again in the log with numbers)

* OA-subset selection: for Nature, Science, Cell, Cancer Cell, Cell Metabolism,
  Molecular Cell most content is not in the OA subset; the OA fraction is enriched for
  funder-mandated (NIH, Wellcome, UKRI) work and for author manuscripts.
* Author manuscripts (Science, Sci Transl Med, Cell titles) are not publisher-typeset.
* Date-descending ordering weights the corpus toward 2025-2026 output.
* Caption-based classification under-detects families that authors do not name
  (e.g. dot plots described only as "individual points") and over-detects
  `bar/group comparison` because SEM/SD language is generic.
* Europe PMC `JOURNAL:` matching is exact on the MEDLINE abbreviation; articles indexed
  under a different title string are missed.

## 11. Earlier harvest counted in the corpus (added 2026-09-16 before download)

A prior harvest exists at `../make_my_plot/figure_library/` (16 papers, 77 main-figure
JPGs, all first published 2025, CC BY, produced earlier by `scripts/harvest_library.py`
of the make_my_plot repository; each paper folder holds `paper_metadata.json`,
`license.txt`, `figures/*.jpg` and `figures/figNN_figN.json` captions). Rules:

* These papers are included in `corpus_manifest_expanded.csv` with `local_source`
  pointing at the existing files (relative path from this repository root, i.e.
  `../make_my_plot/figure_library/...`); they are NOT copied or re-downloaded.
* Their PMCIDs are placed on a skip list so the Europe PMC pass never downloads them again.
* They count toward the per-family targets: the number of new papers requested from
  each family = 50 minus the number of prior-harvest research articles in that family
  (the Nature family also contains Communications Biology and Scientific Reports, the
  Cell family iScience, from the earlier journal list; they keep their real journal
  name and are marked `prior_harvest` in `notes`). The one author correction
  (0 figures) in the prior harvest yields no manifest row and is not counted.
* Their captions are classified with the same section 8 regexes; the quantitative
  eligibility test of section 5 is applied and recorded in `notes` but does not remove
  them from the manifest.

## 12. Amendments after the first execution pass (v1.1, 2026-09-16)

The first pass (run 1) was audited and discarded; run 2 replaced it with these
rules added to the script. The selection rule itself (first N eligible, publisher
versions first, date-desc then PMCID-desc) is unchanged.

* Image format preference: when PMC serves several renditions of a figure, prefer
  `.webp` > `.png` > `.jpg` > `.tif` > `.gif`; `.gif` files on PMC are 100-px
  thumbnails. Run 1 had matched by file stem and kept 276 thumbnails; run 2 harvests
  every CDN blob URL from the PMC page and applies the preference, and the
  `supplementaryFiles` fallback does the same. Any figure for which only a thumbnail
  exists is marked `thumbnail_only` and `usable_for_measurement = no`.
* Full-text XML retrieval: non-200 answers from Europe PMC are retried (4 attempts,
  3/6/9/12 s back-off); only HTTP 404 is accepted as "no full text". Correction after
  run 2: the ~142 "no-xml" rejections of runs 1-2 were NOT server failures but a script
  bug (responses beginning with a newline before `<!DOCTYPE` failed the
  `startswith(b"<")` check). The check now strips leading whitespace. Because the
  affected records are mostly the newest (JATS 1.4) ones, runs 1-2 under-sample 2026
  papers relative to the protocol's intent; this is recorded in the log's Known biases
  and a corrected selection (run 3) is a pending decision. Request pacing was slowed to 0.7 s (Europe PMC)
  and 0.6 s (PMC/CDN). Because those candidates precede later ones in the deterministic
  order, the selection was recomputed from scratch. Nothing under `PRIVATE_REFERENCE_ONLY/corpus/`
  is moved, renamed or deleted (downstream reviewers reference the existing paths):
  papers that dropped out stay in place and appear in the manifest with
  `usable_for_measurement = no` and `notes = "deselected on re-screen: ..."`; earlier
  thumbnail files stay and the full-size rendition is added alongside, the manifest
  `local_source` pointing at the best rendition.
* License URL inference: when the `<license>` element carries no `xlink:href` or
  creativecommons URL but the text names a Creative Commons license, the URL is
  inferred from the text and marked "(URL inferred from license text)". Records whose
  license is not Creative Commons (e.g. the AAAS "Science Journals Default License"
  on some Science author manuscripts) stay in the corpus as private reference but carry
  the note "non-CC publisher license" and are never `usable_for_measurement = yes`.
* The expansion log gains a per-paper table (PMCID, DOI, version, license) so a
  follow-up step can fetch the NCBI OA package with the publisher PDF.
