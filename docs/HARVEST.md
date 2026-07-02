# License-aware figure-library harvesting (Milestone 3)

Builds a curated library of **open-access, post-2020** papers from Nature-,
Science-, and Cell-family journals, downloading figures/data **only** when the
license clearly permits reuse + text/data mining (CC BY / CC BY-SA / CC0).

> This is a conservative automated license classification, **not legal advice**.
> Flagship *Nature*, *Science*, and *Cell* articles are almost never CC BY, so
> the gate naturally surfaces their open-access sister journals (Nature
> Communications, Communications Biology, Scientific Reports, Science Advances,
> iScience, Cell Reports, …). Nothing is fabricated.

## Run it

```bash
python scripts/harvest_library.py --out figure_library --papers 10 --per-journal-cap 3
```

Options: `--min-year` (default 2021, strictly post-2020), `--per-journal-cap`
(diversity), `--delay` (politeness, seconds), `--no-figures`, `--no-supplementary`.

## What it does, per paper

1. **Verify metadata** — title, journal, year, DOI, license, URLs (Europe PMC).
2. **Confirm post-2020** — reject anything earlier than `--min-year`.
3. **Confirm reuse is legal** — license must be CC BY / CC BY-SA / CC0, and this
   is confirmed by **two independent sources** (Europe PMC *and* the NCBI PMC OA
   service). Corrections/errata/retractions are excluded.
4. **Download only permitted files** over **HTTPS only** (no FTP):
   - full text via NCBI BioC (the legal TDM artifact),
   - figure bitmaps via the PMC article page's `cdn.ncbi.nlm.nih.gov` URLs,
   - supplementary/source data via Europe PMC.
5. **Extract** figure images, captions, titles, and **panel labels** (parsed
   from caption text; confidence is flagged, since we have caption text rather
   than structured panel markup).
6. **Store** under `figure_library/{journal_group}/{year}_{first_author}_{short_title}/`.
7. **Provenance** — a `provenance.json` for every paper and a per-figure record
   for every figure (plus `figures/provenance.json`).

## Honesty rules (enforced in code)

- **No fabrication.** Anything unavailable is recorded as `null` / `"unavailable"`.
- **Figure ↔ source-data matching is marked `"uncertain"`** — we do not guess
  which supplementary file backs which panel.
- Panel-label extraction carries a `panel_label_confidence` flag
  (`heuristic_low` / `heuristic_medium` / `none`).

## Folder contents

```
figure_library/
  provenance_report.json                # run-level summary (accepted/rejected)
  {nature|science|cell|other}/
    {year}_{first_author}_{short_title}/
      paper_metadata.json
      license.txt
      provenance.json
      full_text/bioc.json
      figures/
        figNN_FigN.json                  # caption, panel labels, image provenance
        figNN_FigN.jpg                   # CC BY/CC0 bitmap (if resolved over HTTPS)
        provenance.json                  # per-figure index
      supplementary/...                  # source data when HTTPS-available
```

## Sources

Europe PMC REST; NCBI PMC OA service (`oa.fcgi`); NCBI BioC (`pmcoa.cgi`);
NCBI PMC article pages / `cdn.ncbi.nlm.nih.gov`. All HTTPS, rate-limited, with a
descriptive User-Agent and contact address.
