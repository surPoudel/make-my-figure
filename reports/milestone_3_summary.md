# Milestone 3 Summary — License-aware paper & figure library

Date: 2026-06-30

## What was built

An HTTPS-only, license-aware harvesting pipeline (`make_my_figure/harvest/`) that
curates open-access, post-2020 papers from Nature/Science/Cell-family journals and
downloads figures + data **only** when the license clearly permits reuse + text/data
mining (CC BY / CC BY-SA / CC0). It produced a library of **10 valid papers** with a
full provenance report.

### Modules
- `harvest/licensing.py` — conservative license classifier (CC BY/SA/CC0 = permissive;
  CC BY-NC*, CC BY-ND*, subscription, unknown = blocked). Separates "permits reuse"
  from "permits TDM".
- `harvest/sources.py` — HTTPS data sources: Europe PMC search, NCBI PMC OA service
  (independent license confirmation), NCBI BioC (full text + captions + image
  filenames), PMC article-page figure-URL resolver, Europe PMC supplementary files.
  Descriptive User-Agent + contact, timeouts, rate-limiting. **No ftp://.**
- `harvest/pipeline.py` — orchestration: verify → license-gate (double-confirmed) →
  download permitted files → extract captions/panel labels/figures → write folder
  structure + per-paper and per-figure provenance.
- `scripts/harvest_library.py` — CLI runner.

## Results (this run)

10/10 valid papers accepted, 8 rejected. All papers 2025 (post-2020), all CC BY,
**48/48 figures downloaded** as real bitmaps, license confirmed by **two independent
sources** (Europe PMC + NCBI OA service). The journal list is ordered as a family
round-robin and run with `--per-journal-cap 2`, so all three families — **nature,
cell, and science** — are represented, including the Cell-family **iScience** and
**Cell Reports**.

| Journal | Group | Year | DOI | Figures | Supp |
|---|---|---|---|---|---|
| Nature Communications | nature | 2025 | 10.1038/s41467-025-67953-5 | 6/6 | 22 |
| Nature Communications | nature | 2025 | 10.1038/s41467-025-67906-y | 6/6 | 24 |
| iScience | cell | 2025 | 10.1016/j.isci.2025.113948 | 4/4 | 11 |
| iScience | cell | 2025 | 10.1016/j.isci.2025.114249 | 4/4 | 11 |
| Science Advances | science | 2025 | 10.1126/sciadv.aeb1017 | 5/5 | 11 |
| Science Advances | science | 2025 | 10.1126/sciadv.aea6007 | 7/7 | 14 |
| Cell Reports | cell | 2025 | 10.1016/j.celrep.2025.116604 | 6/6 | 16 |
| Cell Reports | cell | 2025 | 10.1016/j.celrep.2025.116569 | 1/1 | 2 |
| Communications Biology | nature | 2025 | 10.1038/s42003-025-09396-8 | 2/2 | 11 |
| Communications Biology | nature | 2025 | 10.1038/s42003-025-09449-y | 7/7 | 18 |

Journal groups: **nature 4, cell 4, science 2** across 5 journals.

Rejections were almost entirely **license-blocked** (CC BY-ND / CC BY-NC-ND, which
the EPMC `LICENSE:cc by` query returns as substring matches but the gate rejects),
plus one correction notice. This is the gate working as intended.

## Folder layout produced

```
figure_library/
  provenance_report.json
  nature/2025_<author>_<short_title>/
    paper_metadata.json   license.txt   provenance.json
    full_text/bioc.json
    figures/figNN_FigN.json + figNN_FigN.jpg + provenance.json
    supplementary/<source-data files>
  science/2025_Yudin_.../ ...
```

## Constraints honored (acceptance check)

- ✅ Metadata verified: title, journal, year, DOI, license, URLs.
- ✅ Post-2020 enforced (`min_year=2021`).
- ✅ Legality confirmed before any download — CC BY/SA/CC0 only, double-sourced.
- ✅ Only permitted files downloaded; HTTPS-only (no FTP, per user instruction).
- ✅ Figure images + captions + panel labels + supplementary/source data extracted.
- ✅ Organized `figure_library/{journal}/{year}_{first_author}_{short_title}/` layout.
- ✅ Provenance JSON for every paper **and** every figure.
- ✅ No fabrication — missing items recorded as null/"unavailable".
- ✅ Figure↔source-data matching marked `"uncertain"` (not guessed).
- ✅ Stopped at 10 valid papers + produced `provenance_report.json`.

## Known limitations

- **Panel labels are heuristic** (parsed from caption text; each figure carries a
  `panel_label_confidence` flag). Structured JATS panel markup isn't available over
  HTTPS for most Nature-family papers, so this is intentionally conservative.
- **Figure↔source-data linkage is not attempted** — supplementary files are stored
  at the paper level and explicitly flagged `uncertain`.
- **Figure bitmaps** come from the PMC article page's CDN URLs; if a paper's page
  can't be parsed, the image is recorded as not-downloaded (never fabricated).
- **Flagship *Nature* / *Science* / *Cell*** articles are intentionally absent: they
  are almost never CC BY, so the license gate surfaces their OA sister journals
  instead. This is expected and honest, not a coverage gap to "fix" by relaxing the gate.

## Tests

`pytest -q` → **116 passed** (91 plotting + 25 harvest/licensing). Harvest tests are
offline (license classification, panel-label heuristic, query syntax, non-article
filter, slug); the live harvest itself is run via the CLI.
