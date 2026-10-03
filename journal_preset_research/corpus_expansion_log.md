# Corpus expansion log

Generated 2026-09-16T12:05 by `scripts/build_figure_corpus.py` following `corpus_sampling_protocol.md`.

## Data sources

* Europe PMC REST search + fullTextXML (open-access subset, `OPEN_ACCESS:y`). `SRC:PMC` was dropped (returns 0 for these journals; PubMed-indexed articles are `SRC:MED`).
* Figure bitmaps: `https://europepmc.org/articles/{PMCID}/bin/...` returned HTTP 403 (Cloudflare JavaScript challenge) on 2026-09-16 and was not bypassed. Images were taken from PubMed Central's CDN (URL read from `https://pmc.ncbi.nlm.nih.gov/articles/{PMCID}/`, `<img class="graphic">`, matched by file name to the JATS `graphic/@xlink:href`). Fallback: Europe PMC `supplementaryFiles` zip.
* Prior harvest: 16 papers / 77 figures already present in `../make_my_plot/figure_library` (harvested earlier by `scripts/harvest_library.py` of make_my_plot). They are referenced in place (not copied) and were skipped in the new download; they count toward family targets.

## Run history

* Run 1 (2026-09-16, three families in parallel, 0.34 s pacing) was audited and discarded: 276 of 797 stored images were 100-px GIF thumbnails (stem matching picked the wrong rendition) and ~140 candidates were rejected as 'no-xml' because Europe PMC answered non-200 under concurrent load (all returned XML on re-query). Its logs are kept in `PRIVATE_REFERENCE_ONLY/corpus/_run1_logs/`.
* Run 2 (this log) re-screened every candidate in the deterministic order with the v1.1 amendments of the protocol (section 12); already downloaded full-size files were reused, thumbnails replaced, and papers that fell out of the first-N selection were left in place (no folder was moved, renamed or deleted; existing thumbnail files were kept and full-size renditions added alongside) and are marked `deselected on re-screen` with usable_for_measurement=no in the manifest.

## Queries

| Family | Journal | Version class | hitCount | retrieved | Query |
|---|---|---|---|---|---|
| cell | Cell | publisher | 64 | 64 | `JOURNAL:"Cell" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND NOT AUTH_MAN:y` |
| cell | Cell | author manuscript | 147 | 120 | `JOURNAL:"Cell" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND AUTH_MAN:y` |
| cell | Cancer Cell | publisher | 17 | 17 | `JOURNAL:"Cancer Cell" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND NOT AUTH_MAN:y` |
| cell | Cancer Cell | author manuscript | 28 | 28 | `JOURNAL:"Cancer Cell" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND AUTH_MAN:y` |
| cell | Cell Metab | publisher | 12 | 12 | `JOURNAL:"Cell Metab" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND NOT AUTH_MAN:y` |
| cell | Cell Metab | author manuscript | 21 | 21 | `JOURNAL:"Cell Metab" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND AUTH_MAN:y` |
| cell | Cell Syst | publisher | 8 | 8 | `JOURNAL:"Cell Syst" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND NOT AUTH_MAN:y` |
| cell | Cell Syst | author manuscript | 15 | 15 | `JOURNAL:"Cell Syst" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND AUTH_MAN:y` |
| cell | Mol Cell | publisher | 39 | 39 | `JOURNAL:"Mol Cell" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND NOT AUTH_MAN:y` |
| cell | Mol Cell | author manuscript | 75 | 75 | `JOURNAL:"Mol Cell" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND AUTH_MAN:y` |
| cell | Cell Rep | publisher | 186 | 120 | `JOURNAL:"Cell Rep" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND NOT AUTH_MAN:y` |
| cell | Cell Rep | author manuscript | 1752 | 120 | `JOURNAL:"Cell Rep" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND AUTH_MAN:y` |
| nature | Nature | publisher | 2483 | 120 | `JOURNAL:"Nature" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND NOT AUTH_MAN:y` |
| nature | Nature | author manuscript | 72 | 72 | `JOURNAL:"Nature" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND AUTH_MAN:y` |
| nature | Nat Methods | publisher | 369 | 120 | `JOURNAL:"Nat Methods" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND NOT AUTH_MAN:y` |
| nature | Nat Methods | author manuscript | 11 | 11 | `JOURNAL:"Nat Methods" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND AUTH_MAN:y` |
| nature | Nat Biotechnol | publisher | 178 | 120 | `JOURNAL:"Nat Biotechnol" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND NOT AUTH_MAN:y` |
| nature | Nat Biotechnol | author manuscript | 37 | 37 | `JOURNAL:"Nat Biotechnol" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND AUTH_MAN:y` |
| nature | Nat Cell Biol | publisher | 261 | 120 | `JOURNAL:"Nat Cell Biol" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND NOT AUTH_MAN:y` |
| nature | Nat Cell Biol | author manuscript | 13 | 13 | `JOURNAL:"Nat Cell Biol" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND AUTH_MAN:y` |
| nature | Nat Commun | publisher | 38475 | 120 | `JOURNAL:"Nat Commun" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND NOT AUTH_MAN:y` |
| nature | Nat Commun | author manuscript | 11 | 11 | `JOURNAL:"Nat Commun" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND AUTH_MAN:y` |
| science | Science | publisher | 3 | 3 | `JOURNAL:"Science" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND NOT AUTH_MAN:y` |
| science | Science | author manuscript | 216 | 120 | `JOURNAL:"Science" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND AUTH_MAN:y` |
| science | Sci Adv | publisher | 9738 | 120 | `JOURNAL:"Sci Adv" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND NOT AUTH_MAN:y` |
| science | Sci Adv | author manuscript | 3 | 3 | `JOURNAL:"Sci Adv" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND AUTH_MAN:y` |
| science | Sci Transl Med | publisher | 5 | 5 | `JOURNAL:"Sci Transl Med" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND NOT AUTH_MAN:y` |
| science | Sci Transl Med | author manuscript | 45 | 45 | `JOURNAL:"Sci Transl Med" AND OPEN_ACCESS:y AND PUB_TYPE:"research-article" AND FIRST_PDATE:[2023-01-01 TO 2026-09-15] AND AUTH_MAN:y` |

Candidates were re-sorted locally by (firstPublicationDate desc, PMCID desc) and screened in that order; screening budget 120 per journal per version class.

## Screening and selection per journal

| Family | Journal | candidates | screened | eligible+selected | of which author manuscripts | rejected (reason: n) |
|---|---|---|---|---|---|---|
| cell | Cell | 184 | 33 | 8 | 0 | no-xml: 23; quantitative figures: 2 |
| cell | Cancer Cell | 45 | 16 | 8 | 0 | no-xml: 8 |
| cell | Cell Metab | 33 | 11 | 8 | 0 | no-xml: 3 |
| cell | Cell Syst | 23 | 14 | 8 | 2 | no-xml: 5; quantitative figures: 1 |
| cell | Mol Cell | 114 | 19 | 7 | 0 | no-xml: 11; quantitative figures: 1 |
| cell | Cell Rep | 240 | 14 | 7 | 0 | no-xml: 7 |
| nature | Nature | 192 | 17 | 9 | 0 | no-xml: 5; quantitative figures: 3 |
| nature | Nat Methods | 131 | 18 | 8 | 0 | no-xml: 9; quantitative figures: 1 |
| nature | Nat Biotechnol | 157 | 19 | 8 | 0 | no-xml: 9; quantitative figures: 2 |
| nature | Nat Cell Biol | 133 | 16 | 8 | 0 | no-xml: 8 |
| nature | Nat Commun | 131 | 18 | 8 | 0 | no-xml: 6; quantitative figures: 4 |
| science | Science | 123 | 29 | 16 | 16 | no-xml: 12; quantitative figures: 1 |
| science | Sci Adv | 123 | 39 | 16 | 0 | no-xml: 20; quantitative figures: 3 |
| science | Sci Transl Med | 50 | 35 | 16 | 14 | no-xml: 16; quantitative figures: 2; pubType review: 1 |

## Papers and figures per family (prior harvest + new)

Rows marked `deselected on re-screen` (excluded from all counts below): 0

| Family | papers | figure rows | usable=yes | partial | no |
|---|---|---|---|---|---|
| Nature | 50 | 281 | 188 | 90 | 3 |
| Science | 50 | 289 | 81 | 207 | 1 |
| Cell | 50 | 304 | 259 | 45 | 0 |

| Family | Journal | papers | figure rows | share of family papers |
|---|---|---|---|---|
| Cell | Cancer Cell | 8 | 56 | 16% |
| Cell | Cell | 8 | 56 | 16% |
| Cell | Cell Metabolism | 8 | 47 | 16% |
| Cell | Cell Reports | 9 | 49 | 18% |
| Cell | Cell Systems | 8 | 43 | 16% |
| Cell | Molecular Cell | 7 | 45 | 14% |
| Cell | iScience | 2 | 8 | 4% |
| Nature | Communications Biology | 3 | 15 | 6% |
| Nature | Nature | 9 | 42 | 18% |
| Nature | Nature Biotechnology | 8 | 38 | 16% |
| Nature | Nature Cell Biology | 8 | 54 | 16% |
| Nature | Nature Communications | 11 | 72 | 22% |
| Nature | Nature Methods | 8 | 44 | 16% |
| Nature | Scientific Reports | 3 | 16 | 6% |
| Science | Science | 16 | 87 | 32% |
| Science | Science Advances | 18 | 109 | 36% |
| Science | Science Translational Medicine | 16 | 93 | 32% |

## Selected papers (one row per paper; PMCID for the follow-up NCBI OA-package / publisher-PDF fetch)

| PMCID | family | journal | version | first pub date | DOI | main figs | figs downloaded | license URL | source |
|---|---|---|---|---|---|---|---|---|---|
| PMC10028007 | Cell | Cell Metabolism | publisher | 2023-03-01 | 10.1016/j.cmet.2023.02.004 | 7 | 7 | http://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC10171335 | Cell | Cancer Cell | publisher | 2023-04-27 | 10.1016/j.ccell.2023.04.002 | 7 | 7 | http://creativecommons.org/licenses/by/4.0/ | new download |
| PMC10206407 | Cell | Cell Systems | publisher | 2023-04-27 | 10.1016/j.cels.2023.03.003 | 7 | 7 | http://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC10432853 | Cell | Cell Metabolism | publisher | 2023-07-31 | 10.1016/j.cmet.2023.07.002 | 6 | 6 | http://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC10487638 | Cell | Cell Metabolism | publisher | 2023-08-03 | 10.1016/j.cmet.2023.07.003 | 7 | 7 | http://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC10507381 | Cell | Cancer Cell | publisher | 2023-08-30 | 10.1016/j.ccell.2023.08.002 | 5 | 5 | http://creativecommons.org/licenses/by/4.0/ | new download |
| PMC10659931 | Cell | Molecular Cell | publisher | 2023-11-16 | 10.1016/j.molcel.2023.10.018 | 6 | 6 | http://creativecommons.org/licenses/by/4.0/ | new download |
| PMC10722468 | Cell | Cell Metabolism | publisher | 2023-11-20 | 10.1016/j.cmet.2023.10.017 | 7 | 7 | http://creativecommons.org/licenses/by/4.0/ | new download |
| PMC10752370 | Cell | Cell Systems | publisher | 2023-12-12 | 10.1016/j.cels.2023.11.007 | 5 | 5 | http://creativecommons.org/licenses/by/4.0/ | new download |
| PMC10754148 | Cell | Cell | publisher | 2023-12-01 | 10.1016/j.cell.2023.11.028 | 7 | 7 | http://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC10783624 | Cell | Cell | publisher | 2023-12-20 | 10.1016/j.cell.2023.11.021 | 7 | 7 | http://creativecommons.org/licenses/by-nc/4.0/ | new download |
| PMC10804999 | Cell | Molecular Cell | publisher | 2023-12-15 | 10.1016/j.molcel.2023.11.016 | 6 | 6 | http://creativecommons.org/licenses/by-nc/4.0/ | new download |
| PMC10805001 | Cell | Molecular Cell | publisher | 2024-01-09 | 10.1016/j.molcel.2023.12.013 | 6 | 6 | http://creativecommons.org/licenses/by-nc/4.0/ | new download |
| PMC10864002 | Cell | Cancer Cell | publisher | 2024-01-04 | 10.1016/j.ccell.2023.12.005 | 7 | 7 | http://creativecommons.org/licenses/by/4.0/ | new download |
| PMC10864003 | Cell | Cancer Cell | publisher | 2024-01-04 | 10.1016/j.ccell.2023.12.008 | 8 | 8 | http://creativecommons.org/licenses/by/4.0/ | new download |
| PMC10929690 | Cell | Cancer Cell | publisher | 2024-01-18 | 10.1016/j.ccell.2023.12.021 | 7 | 7 | http://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC11060037 | Cell | Cell | publisher | 2024-04-10 | 10.1016/j.cell.2024.03.025 | 7 | 7 | http://creativecommons.org/licenses/by-nc/4.0/ | new download |
| PMC11065421 | Cell | Molecular Cell | publisher | 2024-04-09 | 10.1016/j.molcel.2024.03.015 | 7 | 7 | http://creativecommons.org/licenses/by/4.0/ | new download |
| PMC11106717 | Cell | Cell | publisher | 2024-05-01 | 10.1016/j.cell.2024.03.016 | 7 | 7 | http://creativecommons.org/licenses/by/4.0/ | new download |
| PMC11250105 | Cell | Cell Metabolism | publisher | 2024-07-01 | 10.1016/j.cmet.2024.06.001 | 5 | 5 | http://creativecommons.org/licenses/by/4.0/ | new download |
| PMC11258540 | Cell | Molecular Cell | publisher | 2024-07-01 | 10.1016/j.molcel.2024.06.013 | 7 | 7 | http://creativecommons.org/licenses/by-nc/4.0/ | new download |
| PMC11290321 | Cell | Cell | publisher | 2024-06-18 | 10.1016/j.cell.2024.05.038 | 7 | 7 | http://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC11349380 | Cell | Cell | publisher | 2024-07-31 | 10.1016/j.cell.2024.07.005 | 7 | 7 | http://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC11429458 | Cell | Cell | publisher | 2024-08-12 | 10.1016/j.cell.2024.07.030 | 7 | 7 | http://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC11667439 | Cell | Cell Systems | publisher | 2024-12-06 | 10.1016/j.cels.2024.11.003 | 7 | 7 | http://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC11687419 | Cell | Molecular Cell | publisher | 2024-12-20 | 10.1016/j.molcel.2024.11.031 | 6 | 6 | http://creativecommons.org/licenses/by/4.0/ | new download |
| PMC11738662 | Cell | Cell Systems | author manuscript | 2024-12-16 | 10.1016/j.cels.2024.12.002 | 2 | 2 | https://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC11913779 | Cell | Cancer Cell | publisher | 2023-07-01 | 10.1016/j.ccell.2023.06.006 | 7 | 7 | http://creativecommons.org/licenses/by/4.0/ | new download |
| PMC11922821 | Cell | Cell Systems | publisher | 2025-02-18 | 10.1016/j.cels.2025.101198 | 5 | 5 | http://creativecommons.org/licenses/by/4.0/ | new download |
| PMC12137002 | Cell | Cell Metabolism | publisher | 2025-04-07 | 10.1016/j.cmet.2025.03.009 | 6 | 6 | http://creativecommons.org/licenses/by/4.0/ | new download |
| PMC12332847 | Cell | Cell Systems | author manuscript | 2025-07-07 | 10.1016/j.cels.2025.101324 | 7 | 7 | https://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC12416865 | Cell | Cancer Cell | publisher | 2025-07-10 | 10.1016/j.ccell.2025.06.015 | 7 | 7 | http://creativecommons.org/licenses/by/4.0/ | new download |
| PMC12456964 | Cell | Cell | publisher | 2025-05-16 | 10.1016/j.cell.2025.04.030 | 7 | 7 | http://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC12488066 | Cell | Molecular Cell | publisher | 2025-08-01 | 10.1016/j.molcel.2025.07.005 | 7 | 7 | http://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC12490786 | Science | Science Translational Medicine | author manuscript | 2025-08-13 | 10.1126/scitranslmed.adn2601 | 7 | 7 | https://creativecommons.org/licenses/by/4.0/ (URL inferred from license text) | new download |
| PMC12870020 | Science | Science Translational Medicine | author manuscript | 2026-01-07 | 10.1126/scitranslmed.ado9383 | 5 | 5 | https://creativecommons.org/licenses/by/4.0/ (URL inferred from license text) | new download |
| PMC12916471 | Cell | Cell Systems | publisher | 2026-02-11 | 10.1016/j.cels.2025.101489 | 6 | 6 | http://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC12951864 | Nature | Nature Biotechnology | publisher | 2025-11-10 | 10.1038/s41587-025-02866-8 | 6 | 6 | https://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC13004167 | Science | Science | author manuscript | 2026-03-19 | 10.1126/science.adx3162 | 7 | 7 | https://creativecommons.org/licenses/by/4.0/ (URL inferred from license text) | new download |
| PMC13035345 | Science | Science Translational Medicine | author manuscript | 2025-10-15 | 10.1126/scitranslmed.adu2085 | 6 | 6 | https://creativecommons.org/licenses/by/4.0/ (URL inferred from license text) | new download |
| PMC13041778 | Science | Science | author manuscript | 2026-02-12 | 10.1126/science.adw4937 | 6 | 6 | https://creativecommons.org/licenses/by/4.0/ (URL inferred from license text) | new download |
| PMC13050621 | Nature | Nature Biotechnology | publisher | 2025-09-30 | 10.1038/s41587-025-02833-3 | 6 | 6 | https://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC13061089 | Science | Science Translational Medicine | author manuscript | 2026-03-04 | 10.1126/scitranslmed.adq4529 | 6 | 6 | https://creativecommons.org/licenses/by/4.0/ (URL inferred from license text) | new download |
| PMC13083267 | Cell | Cell Systems | publisher | 2026-03-11 | 10.1016/j.cels.2026.101536 | 4 | 4 | http://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13092281 | Science | Science | author manuscript | 2026-04-02 | 10.1126/science.adv7924 | 6 | 6 | https://creativecommons.org/licenses/by/4.0/ (URL inferred from license text) | new download |
| PMC13107528 | Science | Science | author manuscript | 2026-02-05 | 10.1126/science.adv2600 | 6 | 6 | https://www.science.org/about/science-licenses-journal-article-reuse | new download |
| PMC13124201 | Science | Science | author manuscript | 2026-03-05 | 10.1126/science.adu9394 | 5 | 5 | https://www.science.org/about/science-licenses-journal-article-reuse | new download |
| PMC13124994 | Cell | Cell Reports | publisher | 2026-04-07 | 10.1016/j.celrep.2026.117090 | 5 | 5 | http://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13125397 | Cell | Cell Reports | publisher | 2026-03-20 | 10.1016/j.celrep.2026.117114 | 6 | 6 | http://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC13125401 | Cell | Cell Reports | publisher | 2026-03-22 | 10.1016/j.celrep.2026.117146 | 7 | 7 | http://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC13237580 | Cell | Cell Metabolism | publisher | 2026-01-28 | 10.1016/j.cmet.2025.12.016 | 5 | 5 | http://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC13246279 | Science | Science Translational Medicine | author manuscript | 2026-01-21 | 10.1126/scitranslmed.adv4942 | 4 | 4 | https://creativecommons.org/licenses/by/4.0/ (URL inferred from license text) | new download |
| PMC13271882 | Nature | Nature Biotechnology | publisher | 2025-08-13 | 10.1038/s41587-025-02761-2 | 4 | 4 | https://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC13286266 | Science | Science | author manuscript | 2026-02-12 | 10.1126/science.aea1272 | 4 | 4 | https://creativecommons.org/licenses/by/4.0/ (URL inferred from license text) | new download |
| PMC13291444 | Cell | Cell Reports | publisher | 2026-06-04 | 10.1016/j.celrep.2026.117501 | 6 | 6 | http://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13308464 | Science | Science | author manuscript | 2026-06-18 | 10.1126/science.aec6396 | 6 | 6 | https://creativecommons.org/licenses/by/4.0/ (URL inferred from license text) | new download |
| PMC13345946 | Nature | Nature Methods | publisher | 2026-06-22 | 10.1038/s41592-026-03111-z | 6 | 6 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13346115 | Nature | Nature Methods | publisher | 2026-06-18 | 10.1038/s41592-026-03129-3 | 6 | 6 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13364638 | Nature | Nature Cell Biology | publisher | 2026-06-11 | 10.1038/s41556-026-01986-w | 7 | 7 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13364683 | Nature | Nature Cell Biology | publisher | 2026-06-24 | 10.1038/s41556-026-01982-0 | 5 | 5 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13364714 | Nature | Nature Cell Biology | publisher | 2026-07-06 | 10.1038/s41556-026-01981-1 | 7 | 7 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13364725 | Nature | Nature Cell Biology | publisher | 2026-06-15 | 10.1038/s41556-026-01991-z | 7 | 7 | https://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC13368582 | Nature | Nature Biotechnology | publisher | 2025-08-28 | 10.1038/s41587-025-02797-4 | 5 | 5 | https://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC13368584 | Nature | Nature Biotechnology | publisher | 2025-10-21 | 10.1038/s41587-025-02791-w | 6 | 6 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13372101 | Science | Science | author manuscript | 2026-04-09 | 10.1126/science.aea2100 | 7 | 7 | https://creativecommons.org/licenses/by/4.0/ (URL inferred from license text) | new download |
| PMC13396705 | Cell | Cell Metabolism | publisher | 2026-04-15 | 10.1016/j.cmet.2026.03.012 | 4 | 4 | http://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC13403147 | Science | Science | author manuscript | 2026-05-07 | 10.1126/science.adx1893 | 6 | 6 | https://www.science.org/about/science-licenses-journal-article-reuse | new download |
| PMC13441886 | Nature | Nature Methods | publisher | 2026-07-24 | 10.1038/s41592-026-03155-1 | 4 | 4 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13441889 | Nature | Nature Methods | publisher | 2026-07-20 | 10.1038/s41592-026-03159-x | 6 | 6 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13442000 | Nature | Nature Methods | publisher | 2026-07-30 | 10.1038/s41592-026-03176-w | 6 | 6 | https://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC13457098 | Nature | Nature Cell Biology | publisher | 2026-07-22 | 10.1038/s41556-026-02027-2 | 8 | 8 | https://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC13457102 | Nature | Nature Cell Biology | publisher | 2026-07-02 | 10.1038/s41556-026-02009-4 | 8 | 5 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13461360 | Nature | Nature Biotechnology | publisher | 2025-10-02 | 10.1038/s41587-025-02816-4 | 2 | 2 | https://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC13461361 | Nature | Nature Biotechnology | publisher | 2025-10-22 | 10.1038/s41587-025-02830-6 | 4 | 4 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13461362 | Nature | Nature Biotechnology | publisher | 2025-11-05 | 10.1038/s41587-025-02809-3 | 5 | 5 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13471043 | Cell | Cancer Cell | publisher | 2026-07-29 | 10.1016/j.ccell.2026.06.022 | 8 | 8 | http://creativecommons.org/licenses/by-nc/4.0/ | new download |
| PMC13491402 | Science | Science | author manuscript | 2026-02-26 | 10.1126/science.adv7378 | 5 | 5 | https://www.sciencemag.org/about/science-licenses-journal-article-reuse | new download |
| PMC13506674 | Cell | Cell Reports | publisher | 2026-07-31 | 10.1016/j.celrep.2026.117782 | 4 | 4 | http://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13506676 | Cell | Cell Reports | publisher | 2026-08-17 | 10.1016/j.celrep.2026.117776 | 7 | 7 | http://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC13506677 | Cell | Cell Reports | publisher | 2026-08-06 | 10.1016/j.celrep.2026.117786 | 7 | 7 | http://creativecommons.org/licenses/by-nc/4.0/ | new download |
| PMC13518231 | Nature | Nature | publisher | 2026-08-26 | 10.1038/s41586-026-10893-x | 4 | 4 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13518241 | Nature | Nature | publisher | 2026-08-19 | 10.1038/s41586-026-10912-x | 5 | 5 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13518244 | Nature | Nature | publisher | 2026-08-26 | 10.1038/s41586-026-10902-z | 4 | 4 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13538068 | Nature | Nature | publisher | 2026-08-19 | 10.1038/s41586-026-10914-9 | 4 | 4 | https://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC13538145 | Nature | Nature | publisher | 2026-08-19 | 10.1038/s41586-026-10904-x | 6 | 6 | https://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC13541613 | Nature | Nature Methods | publisher | 2026-08-05 | 10.1038/s41592-026-03177-9 | 6 | 6 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13541614 | Nature | Nature Methods | publisher | 2026-08-14 | 10.1038/s41592-026-03137-3 | 5 | 5 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13545012 | Nature | Nature Methods | publisher | 2026-09-04 | 10.1038/s41592-026-03211-w | 5 | 5 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13554239 | Nature | Nature Communications | publisher | 2026-09-08 | 10.1038/s41467-026-77191-y | 6 | 6 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13558045 | Nature | Nature | publisher | 2026-08-26 | 10.1038/s41586-026-10941-6 | 5 | 5 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13558073 | Nature | Nature | publisher | 2026-09-02 | 10.1038/s41586-026-10940-7 | 5 | 5 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13558076 | Nature | Nature | publisher | 2026-08-12 | 10.1038/s41586-026-10891-z | 5 | 5 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13558077 | Nature | Nature | publisher | 2026-08-12 | 10.1038/s41586-026-10886-w | 4 | 4 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13558581 | Nature | Nature Communications | publisher | 2026-09-09 | 10.1038/s41467-026-72182-5 | 5 | 5 | https://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC13561862 | Nature | Nature Cell Biology | publisher | 2026-08-24 | 10.1038/s41556-026-02038-z | 7 | 7 | https://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC13561871 | Nature | Nature Cell Biology | publisher | 2026-08-06 | 10.1038/s41556-026-02041-4 | 5 | 5 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13562520 | Nature | Nature Communications | publisher | 2026-09-10 | 10.1038/s41467-026-77555-4 | 9 | 9 | https://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC13562587 | Nature | Nature Communications | publisher | 2026-09-10 | 10.1038/s41467-026-77465-5 | 6 | 6 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13562589 | Nature | Nature Communications | publisher | 2026-09-10 | 10.1038/s41467-026-77731-6 | 6 | 6 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13562594 | Nature | Nature Communications | publisher | 2026-09-11 | 10.1038/s41467-026-77485-1 | 10 | 10 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13564803 | Science | Science Advances | publisher | 2026-09-11 | 10.1126/sciadv.aef4204 | 5 | 5 | https://creativecommons.org/licenses/by-nc/4.0/ | new download |
| PMC13564807 | Science | Science Advances | publisher | 2026-09-11 | 10.1126/sciadv.adz3976 | 6 | 6 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13564810 | Science | Science Advances | publisher | 2026-09-11 | 10.1126/sciadv.aef1694 | 8 | 8 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13564813 | Science | Science Advances | publisher | 2026-09-11 | 10.1126/sciadv.aed9568 | 7 | 7 | https://creativecommons.org/licenses/by-nc/4.0/ | new download |
| PMC13564824 | Science | Science Advances | publisher | 2026-09-11 | 10.1126/sciadv.aef3957 | 7 | 7 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13564827 | Science | Science Advances | publisher | 2026-09-11 | 10.1126/sciadv.aed4474 | 6 | 6 | https://creativecommons.org/licenses/by-nc/4.0/ | new download |
| PMC13564832 | Science | Science Advances | publisher | 2026-09-11 | 10.1126/sciadv.aec0989 | 6 | 6 | https://creativecommons.org/licenses/by-nc/4.0/ | new download |
| PMC13564844 | Science | Science Advances | publisher | 2026-09-11 | 10.1126/sciadv.aee0891 | 7 | 7 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13564881 | Science | Science Advances | publisher | 2026-09-11 | 10.1126/sciadv.aef1504 | 7 | 7 | https://creativecommons.org/licenses/by-nc/4.0/ | new download |
| PMC13564900 | Science | Science Advances | publisher | 2026-09-11 | 10.1126/sciadv.aec4911 | 5 | 5 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13564907 | Science | Science Advances | publisher | 2026-09-11 | 10.1126/sciadv.aeb8889 | 9 | 9 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13564909 | Science | Science Advances | publisher | 2026-09-11 | 10.1126/sciadv.aee5374 | 4 | 4 | https://creativecommons.org/licenses/by-nc/4.0/ | new download |
| PMC13564915 | Science | Science Advances | publisher | 2026-09-11 | 10.1126/sciadv.aeg1157 | 4 | 4 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13564927 | Science | Science Advances | publisher | 2026-09-11 | 10.1126/sciadv.aee5415 | 5 | 5 | https://creativecommons.org/licenses/by-nc/4.0/ | new download |
| PMC13564951 | Science | Science Advances | publisher | 2026-09-11 | 10.1126/sciadv.aee4501 | 5 | 5 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC13564977 | Science | Science Advances | publisher | 2026-09-11 | 10.1126/sciadv.aee4935 | 6 | 6 | https://creativecommons.org/licenses/by-nc/4.0/ | new download |
| PMC13569489 | Nature | Nature Communications | publisher | 2026-09-11 | 10.1038/s41467-026-77291-9 | 5 | 5 | https://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC13569845 | Nature | Nature Communications | publisher | 2026-09-11 | 10.1038/s41467-026-77392-5 | 6 | 6 | https://creativecommons.org/licenses/by-nc-nd/4.0/ | new download |
| PMC7615567 | Science | Science Translational Medicine | author manuscript | 2024-01-10 | 10.1126/scitranslmed.adi2403 | 4 | 4 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC7615651 | Science | Science Translational Medicine | author manuscript | 2024-01-24 | 10.1126/scitranslmed.add6883 | 8 | 8 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC7615785 | Science | Science Translational Medicine | author manuscript | 2024-02-28 | 10.1126/scitranslmed.adh0673 | 6 | 6 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC7616771 | Science | Science Translational Medicine | author manuscript | 2024-10-09 | 10.1126/scitranslmed.adj7552 | 7 | 7 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC7617732 | Science | Science Translational Medicine | author manuscript | 2024-02-21 | 10.1126/scitranslmed.adk1867 | 5 | 5 |  | new download |
| PMC7617978 | Science | Science Translational Medicine | author manuscript | 2025-07-09 | 10.1126/scitranslmed.adu4564 | 5 | 5 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC7617989 | Science | Science Translational Medicine | author manuscript | 2025-07-02 | 10.1126/scitranslmed.adu2459 | 7 | 7 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC7618036 | Science | Science Translational Medicine | author manuscript | 2025-08-06 | 10.1126/scitranslmed.ads3085 | 6 | 6 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC7618491 | Science | Science | author manuscript | 2026-02-19 | 10.1126/science.adw5137 | 5 | 5 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC7618742 | Science | Science Translational Medicine | author manuscript | 2026-01-07 | 10.1126/scitranslmed.adt5626 | 4 | 4 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC7618833 | Science | Science | author manuscript | 2026-02-26 | 10.1126/science.ady2822 | 5 | 5 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC7618901 | Science | Science | author manuscript | 2026-02-19 | 10.1126/science.ady6651 | 4 | 4 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC7619046 | Science | Science | author manuscript | 2026-05-21 | 10.1126/science.aeb6999 | 4 | 3 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC7619062 | Science | Science | author manuscript | 2026-03-26 | 10.1126/science.adz5344 | 5 | 5 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC7619443 | Science | Science | author manuscript | 2026-08-20 | 10.1126/science.aed9286 | 6 | 6 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC9765455 | Science | Science Translational Medicine | publisher | 2023-01-18 | 10.1126/scitranslmed.abq4064 | 5 | 5 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC9765459 | Science | Science Translational Medicine | publisher | 2023-03-01 | 10.1126/scitranslmed.add6383 | 8 | 8 | https://creativecommons.org/licenses/by/4.0/ | new download |
| PMC12727680 | Cell | Cell Reports | publisher | 2025-11-21 | 10.1016/j.celrep.2025.116604 | 6 | 6 | CC BY | prior harvest (figure_library) |
| PMC12647348 | Cell | Cell Reports | publisher | 2025-11-06 | 10.1016/j.celrep.2025.116569 | 1 | 1 | CC BY | prior harvest (figure_library) |
| PMC12752747 | Cell | iScience | publisher | 2025-11-27 | 10.1016/j.isci.2025.114249 | 4 | 4 | CC BY | prior harvest (figure_library) |
| PMC12767183 | Cell | iScience | publisher | 2025-12-03 | 10.1016/j.isci.2025.113948 | 4 | 4 | CC BY | prior harvest (figure_library) |
| PMC12835182 | Nature | Scientific Reports | publisher | 2025-12-31 | 10.1038/s41598-025-33244-8 | 7 | 7 | CC BY | prior harvest (figure_library) |
| PMC12775072 | Nature | Nature Communications | publisher | 2025-12-31 | 10.1038/s41467-025-67906-y | 6 | 6 | CC BY | prior harvest (figure_library) |
| PMC12877018 | Nature | Communications Biology | publisher | 2025-12-31 | 10.1038/s42003-025-09449-y | 7 | 7 | CC BY | prior harvest (figure_library) |
| PMC12764989 | Nature | Scientific Reports | publisher | 2025-12-31 | 10.1038/s41598-025-16474-8 | 7 | 7 | CC BY | prior harvest (figure_library) |
| PMC12868620 | Nature | Communications Biology | publisher | 2025-12-30 | 10.1038/s42003-025-09432-7 | 6 | 6 | CC BY | prior harvest (figure_library) |
| PMC12872613 | Nature | Nature Communications | publisher | 2025-12-31 | 10.1038/s41467-025-68099-0 | 7 | 7 | CC BY | prior harvest (figure_library) |
| PMC12835169 | Nature | Scientific Reports | publisher | 2025-12-31 | 10.1038/s41598-025-33268-0 | 2 | 2 | CC BY | prior harvest (figure_library) |
| PMC12848012 | Nature | Communications Biology | publisher | 2025-12-31 | 10.1038/s42003-025-09396-8 | 2 | 2 | CC BY | prior harvest (figure_library) |
| PMC12858907 | Nature | Nature Communications | publisher | 2025-12-31 | 10.1038/s41467-025-67953-5 | 6 | 6 | CC BY | prior harvest (figure_library) |
| PMC12716426 | Science | Science Advances | publisher | 2025-12-19 | 10.1126/sciadv.aea6007 | 7 | 7 | CC BY | prior harvest (figure_library) |
| PMC12716425 | Science | Science Advances | publisher | 2025-12-19 | 10.1126/sciadv.aeb1017 | 5 | 5 | CC BY | prior harvest (figure_library) |

## Plot-family counts (caption-based; a figure can carry several)

| plot_family | Nature | Science | Cell | total |
|---|---|---|---|---|
| scatter/regression | 52 | 41 | 67 | 160 |
| line/time-course | 59 | 74 | 74 | 207 |
| bar/group comparison | 134 | 156 | 201 | 491 |
| box/violin | 61 | 34 | 61 | 156 |
| PCA/UMAP | 25 | 16 | 39 | 80 |
| volcano/MA | 13 | 15 | 32 | 60 |
| heatmap | 41 | 30 | 65 | 136 |
| survival | 6 | 7 | 15 | 28 |
| forest/effect-size | 31 | 17 | 24 | 72 |
| dot/bubble | 21 | 35 | 41 | 97 |
| categorical/composition | 62 | 75 | 113 | 250 |
| microscopy/other | 190 | 176 | 196 | 562 |

## Date range achieved

* Newly downloaded papers: 2023-01-18 to 2026-09-11 (first publication date). Prior harvest: 2025-11 to 2025-12.
* Figure rows by year: {'2023': 84, '2024': 132, '2025': 155, '2026': 503}

## License distribution (figure rows)

* CC BY 4.0: 463
* CC BY-NC-ND 4.0: 213
* CC BY-NC 4.0: 94
* CC BY (prior harvest normalized): 77
* non-CC: https://www.science.org/about/science-licenses-journal-article-reuse L: 17
* non-CC: https://www.sciencemag.org/about/science-licenses-journal-article-reus: 5
* non-CC: exclusive licensee American Association for the Advancement of Science: 5

## Thumbnail repair pass (images narrower than 300 px)

* Figures examined with only a thumbnail rendition: 85; fixed (full-size file saved alongside, original kept): 81; unfixable: 4.

| PMCID | journal | figure | thumbnail file(s) | result | new file | width |
|---|---|---|---|---|---|---|
| PMC10171335 | Cancer Cell | Fig2 | Fig2.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC10171335/figures/Fig2.jpg | 761 |
| PMC10171335 | Cancer Cell | Fig5 | Fig5.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC10171335/figures/Fig5.jpg | 788 |
| PMC10171335 | Cancer Cell | Fig6 | Fig6.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC10171335/figures/Fig6.jpg | 779 |
| PMC10171335 | Cancer Cell | Fig7 | Fig7.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC10171335/figures/Fig7.jpg | 748 |
| PMC10206407 | Cell Systems | Fig2 | Fig2.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC10206407/figures/Fig2.jpg | 740 |
| PMC10206407 | Cell Systems | Fig5 | Fig5.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC10206407/figures/Fig5.jpg | 743 |
| PMC10206407 | Cell Systems | Fig6 | Fig6.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC10206407/figures/Fig6.jpg | 744 |
| PMC10206407 | Cell Systems | Fig7 | Fig7.gif (102px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC10206407/figures/Fig7.jpg | 741 |
| PMC10804999 | Molecular Cell | Fig3 | Fig3.gif (200px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC10804999/figures/Fig3.jpg | 740 |
| PMC10864002 | Cancer Cell | Fig3 | Fig3.gif (171px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC10864002/figures/Fig3.jpg | 750 |
| PMC10864002 | Cancer Cell | Fig7 | Fig7.gif (200px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC10864002/figures/Fig7.jpg | 729 |
| PMC10864003 | Cancer Cell | Fig2 | Fig2.gif (166px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC10864003/figures/Fig2.jpg | 748 |
| PMC10864003 | Cancer Cell | Fig3 | Fig3.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC10864003/figures/Fig3.jpg | 748 |
| PMC10864003 | Cancer Cell | Fig4 | Fig4.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC10864003/figures/Fig4.jpg | 748 |
| PMC10864003 | Cancer Cell | Fig5 | Fig5.gif (114px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC10864003/figures/Fig5.jpg | 737 |
| PMC10864003 | Cancer Cell | Fig6 | Fig6.gif (134px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC10864003/figures/Fig6.jpg | 748 |
| PMC10929690 | Cancer Cell | Fig2 | Fig2.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC10929690/figures/Fig2.jpg | 718 |
| PMC10929690 | Cancer Cell | Fig3 | Fig3.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC10929690/figures/Fig3.jpg | 727 |
| PMC10929690 | Cancer Cell | Fig4 | Fig4.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC10929690/figures/Fig4.jpg | 719 |
| PMC10929690 | Cancer Cell | Fig5 | Fig5.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC10929690/figures/Fig5.jpg | 740 |
| PMC10929690 | Cancer Cell | Fig6 | Fig6.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC10929690/figures/Fig6.jpg | 726 |
| PMC11060037 | Cell | Fig5 | Fig5.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC11060037/figures/Fig5.jpg | 719 |
| PMC11060037 | Cell | Fig6 | Fig6.gif (121px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC11060037/figures/Fig6.jpg | 757 |
| PMC11060037 | Cell | Fig7 | Fig7.gif (162px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC11060037/figures/Fig7.jpg | 749 |
| PMC11349380 | Cell | Fig1 | Fig1.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC11349380/figures/Fig1.jpg | 747 |
| PMC11349380 | Cell | Fig2 | Fig2.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC11349380/figures/Fig2.jpg | 783 |
| PMC11349380 | Cell | Fig3 | Fig3.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC11349380/figures/Fig3.jpg | 778 |
| PMC11349380 | Cell | Fig4 | Fig4.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC11349380/figures/Fig4.jpg | 738 |
| PMC11349380 | Cell | Fig5 | Fig5.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC11349380/figures/Fig5.jpg | 741 |
| PMC11429458 | Cell | Fig1 | Fig1.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC11429458/figures/Fig1.jpg | 746 |
| PMC11429458 | Cell | Fig5 | Fig5.gif (114px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC11429458/figures/Fig5.jpg | 745 |
| PMC11429458 | Cell | Fig6 | Fig6.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC11429458/figures/Fig6.jpg | 747 |
| PMC11429458 | Cell | Fig7 | Fig7.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC11429458/figures/Fig7.jpg | 746 |
| PMC11913779 | Cancer Cell | Fig7 | Fig7.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC11913779/figures/Fig7.jpg | 774 |
| PMC12456964 | Cell | Fig1 | Fig1.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC12456964/figures/Fig1.jpg | 726 |
| PMC12456964 | Cell | Fig2 | Fig2.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC12456964/figures/Fig2.jpg | 726 |
| PMC12456964 | Cell | Fig4 | Fig4.gif (124px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC12456964/figures/Fig4.jpg | 738 |
| PMC12456964 | Cell | Fig5 | Fig5.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC12456964/figures/Fig5.jpg | 738 |
| PMC12456964 | Cell | Fig6 | Fig6.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC12456964/figures/Fig6.jpg | 738 |
| PMC12456964 | Cell | Fig7 | Fig7.gif (119px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC12456964/figures/Fig7.jpg | 738 |
| PMC13061089 | Science Translational Medicine | Fig2 | Fig2.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13061089/figures/Fig2.jpg | 2100 |
| PMC13061089 | Science Translational Medicine | Fig4 | Fig4.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13061089/figures/Fig4.jpg | 1939 |
| PMC13061089 | Science Translational Medicine | Fig6 | Fig6.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13061089/figures/Fig6.jpg | 2100 |
| PMC13083267 | Cell Systems | Fig2 | Fig2.gif (113px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13083267/figures/Fig2.jpg | 724 |
| PMC13083267 | Cell Systems | Fig3 | Fig3.gif (99px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13083267/figures/Fig3.jpg | 724 |
| PMC13083267 | Cell Systems | Fig4 | Fig4.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13083267/figures/Fig4.jpg | 748 |
| PMC13124994 | Cell Reports | Fig2 | Fig2.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13124994/figures/Fig2.jpg | 729 |
| PMC13124994 | Cell Reports | Fig3 | Fig3.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13124994/figures/Fig3.jpg | 729 |
| PMC13124994 | Cell Reports | Fig4 | Fig4.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13124994/figures/Fig4.jpg | 729 |
| PMC13124994 | Cell Reports | Fig5 | Fig5.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13124994/figures/Fig5.jpg | 726 |
| PMC13125397 | Cell Reports | Fig2 | Fig2.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13125397/figures/Fig2.jpg | 746 |
| PMC13125397 | Cell Reports | Fig3 | Fig3.gif (104px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13125397/figures/Fig3.jpg | 736 |
| PMC13125397 | Cell Reports | Fig4 | Fig4.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13125397/figures/Fig4.jpg | 748 |
| PMC13125397 | Cell Reports | Fig5 | Fig5.gif (105px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13125397/figures/Fig5.jpg | 736 |
| PMC13125397 | Cell Reports | Fig6 | Fig6.gif (107px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13125397/figures/Fig6.jpg | 735 |
| PMC13246279 | Science Translational Medicine | Fig2 | Fig2.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13246279/figures/Fig2.jpg | 1050 |
| PMC13246279 | Science Translational Medicine | Fig4 | Fig4.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13246279/figures/Fig4.jpg | 682 |
| PMC13457102 | Nature Cell Biology | Fig2 | Fig2.gif (100px) | UNFIXABLE |  |  |
| PMC13457102 | Nature Cell Biology | Fig5 | Fig5.gif (100px) | UNFIXABLE |  |  |
| PMC13457102 | Nature Cell Biology | Fig6 | Fig6.gif (100px) | UNFIXABLE |  |  |
| PMC13471043 | Cancer Cell | Fig1 | Fig1.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13471043/figures/Fig1.jpg | 729 |
| PMC13471043 | Cancer Cell | Fig3 | Fig3.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13471043/figures/Fig3.jpg | 729 |
| PMC13471043 | Cancer Cell | Fig5 | Fig5.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13471043/figures/Fig5.jpg | 729 |
| PMC13471043 | Cancer Cell | Fig6 | Fig6.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13471043/figures/Fig6.jpg | 729 |
| PMC13471043 | Cancer Cell | Fig8 | Fig8.gif (110px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13471043/figures/Fig8.jpg | 740 |
| PMC13538068 | Nature | Fig2 | Fig2.gif (200px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13538068/figures/Fig2.webp | 1600 |
| PMC13538068 | Nature | Fig4 | Fig4.gif (200px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13538068/figures/Fig4.webp | 1600 |
| PMC13538145 | Nature | Fig1 | Fig1.gif (200px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13538145/figures/Fig1.webp | 1600 |
| PMC13538145 | Nature | Fig4 | Fig4.gif (186px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13538145/figures/Fig4.webp | 1512 |
| PMC13538145 | Nature | Fig6 | Fig6.gif (200px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13538145/figures/Fig6.webp | 1600 |
| PMC13564907 | Science Advances | Fig1 | Fig1.gif (200px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13564907/figures/Fig1.webp | 1600 |
| PMC13564907 | Science Advances | Fig2 | Fig2.gif (200px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13564907/figures/Fig2.webp | 1600 |
| PMC13564907 | Science Advances | Fig5 | Fig5.gif (200px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13564907/figures/Fig5.webp | 1599 |
| PMC13564907 | Science Advances | Fig7 | Fig7.gif (200px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13564907/figures/Fig7.webp | 1599 |
| PMC13564907 | Science Advances | Fig9 | Fig9.gif (200px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13564907/figures/Fig9.webp | 1600 |
| PMC13564915 | Science Advances | Fig1 | Fig1.gif (190px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC13564915/figures/Fig1.webp | 1600 |
| PMC7618036 | Science Translational Medicine | Fig5 | Fig5.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC7618036/figures/Fig5.jpg | 800 |
| PMC7618036 | Science Translational Medicine | Fig6 | Fig6.gif (149px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC7618036/figures/Fig6.jpg | 800 |
| PMC7619046 | Science | Fig1 | Fig1.gif (100px) | UNFIXABLE |  |  |
| PMC7619062 | Science | Fig2 | Fig2.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC7619062/figures/Fig2.jpg | 800 |
| PMC7619062 | Science | Fig5 | Fig5.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC7619062/figures/Fig5.jpg | 800 |
| PMC9765455 | Science Translational Medicine | Fig2 | Fig2.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC9765455/figures/Fig2.jpg | 777 |
| PMC9765455 | Science Translational Medicine | Fig3 | Fig3.gif (126px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC9765455/figures/Fig3.jpg | 750 |
| PMC9765455 | Science Translational Medicine | Fig4 | Fig4.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC9765455/figures/Fig4.jpg | 800 |
| PMC9765455 | Science Translational Medicine | Fig5 | Fig5.gif (100px) | fixed | PRIVATE_REFERENCE_ONLY/corpus/PMC9765455/figures/Fig5.jpg | 800 |

## Failures

* none

## Redistribution / notes

* none

## Known biases

* OA-subset selection: Nature, Science, Cell, Cancer Cell, Cell Metabolism, Molecular Cell publish mostly non-OA content; the OA subset is enriched for funder-mandated papers and author manuscripts.
* Author manuscripts (flagged `partial`) dominate Science, Science Translational Medicine and several Cell Press titles; their figures are author-supplied, not publisher-typeset.
* Date-descending ordering concentrates the corpus in 2025-2026.
* Caption-based plot-family assignment over-detects `bar/group comparison` (generic SEM/SD language) and under-detects families that captions do not name; to be refined visually.
* The prior harvest adds journals outside the target list (Communications Biology, Scientific Reports, iScience) to the Nature and Cell families.
* Europe PMC `JOURNAL:` matches the MEDLINE abbreviation exactly; alternative title strings are missed.
