# Publication-recreation benchmarks

`benchmarks/publication_recreation/` is a **license-safe** QA suite that
recreates manuscript-style panels from underlying data through the app's
normal rendering path, then scores them with [Publication
QC](PUBLICATION_QC.md). It exists to catch rendering/style regressions and to
derive *aggregate* Publication-style improvements — it is **not** a library of
reproduced journal figures.

> Publication benchmark recreations are used for quality assurance and style
> improvement. They are not official reproductions unless explicitly stated
> and license-permitted. Make My Figure does not run RNA-seq differential
> expression analysis — the "volcano"/"MA" benchmark entries plot a
> **precomputed** differential-results table, exactly as a user-supplied one
> would be plotted. Users remain responsible for confirming that a figure and
> its statistics match their experimental design.

## Licensing and provenance policy

Every entry in `benchmarks/publication_recreation/manifest.json` records:
`dataset_id`, `title`, `authors`, `year`, `doi`, `source_url`, `dataset_url`,
`license`, `license_url`, `date_accessed`, `data_kind`, `data_type`,
`panel_type`, and `known_differences`.

- **`data_kind: "synthetic"`** — deterministic data generated locally
  (`CC0 / synthetic`), always available offline. It faithfully exercises a
  renderer and the scientific structure of that panel type; the layout/scale
  are illustrative only, not a reproduction of any specific published figure.
- **`data_kind: "real"`** — a genuinely public, permissively licensed dataset
  (CC0, CC BY, or similarly permissive). Only entries with a clear permissive
  license are stored; `scripts/curate_publication_benchmarks.py` downloads
  them over HTTPS **only when online**, and records a SHA-256 checksum. When
  offline, the entry is skipped gracefully and synthetic coverage stands in.
- **`status: "target_only"`** — a panel type with **no renderer** in this
  version (Manhattan/Q-Q, network graph, dose-response curve fitting). For
  these, only provenance and a target-panel description are recorded — nothing
  is recreated or fabricated.
- **Never redistribute copyrighted figures.** The suite never stores a
  screenshot or image of a published figure. When a real dataset cannot be
  stored under a clear permissive license, only its citation/DOI/URL/license
  and a text description of the target panel are kept.

## Honesty framing: synthetic vs. real, "recreation" vs. "copy"

Recreations are described as **publication-grade** or **style-aligned**
recreations — never as "exact copies." The suite does not claim a recreation
matches a published figure pixel-for-pixel, and makes no claim of journal
endorsement. Because most panels use deterministic synthetic data, absolute
scales and cluster structure in those panels are illustrative and are not
compared against any published panel; only the one real dataset (Palmer
Penguins, CC0-1.0) uses genuine measurements, mapped through the app the same
way a user's own upload would be.

## How to run it

```bash
python scripts/curate_publication_benchmarks.py     # prepare data (offline-safe)
python scripts/recreate_publication_panels.py       # render + export + QC each panel
python scripts/evaluate_publication_recreations.py  # checklist evaluation -> evaluation.md
```

Outputs land in `recreated_panels/<dataset_id>/` (PNG/SVG/PDF, a
`.plot_spec.json`, and a `.qc.json` per panel). A full run summary lives in
`benchmarks/publication_recreation/V0_6_BENCHMARK_RECREATION_REPORT.md`; the
design observations that fed the Publication style live under
`benchmarks/publication_recreation/style_notes/` (see
[docs/V0_6_PUBLICATION_STYLE_LESSONS.md](V0_6_PUBLICATION_STYLE_LESSONS.md)).

## Current coverage (as of the v0.6 report)

- **18 manifest entries.** 15 recreated through the app's rendering path (14
  synthetic + 1 real — Palmer Penguins, when online); 3 documented as
  **target-only** (no renderer exists for Manhattan/Q-Q, network graph, or
  dose-response in this version).
- **QC results across the 15 recreated panels: 12 pass, 3 warn, 0 fail.** Every
  recreated panel exported PNG + SVG + PDF and a reproducible `.plot_spec.json`.
  The three `warn`s are all the same low-confidence "axis label may be missing
  units" advisory (e.g. `time_months`, `pseudotime`, `bill_length_mm`), not a
  rendering defect.

## Limitations

- Synthetic-first / offline-safe by design, so the suite runs anywhere without
  network access or licensing risk.
- Evaluation is a **checklist**, not pixel similarity — no reference figures
  are stored or compared against.
- Three requested panel types have no renderer in this version and are
  documented as target-only rather than approximated with a misleading
  substitute.

## See also

- [docs/PUBLICATION_QC.md](PUBLICATION_QC.md) — the scoring engine used to evaluate every recreated panel.
- [docs/V0_6_PUBLICATION_STYLE_LESSONS.md](V0_6_PUBLICATION_STYLE_LESSONS.md) — the aggregate style lessons this suite produced.
- [docs/STYLE_REFERENCE_AUDIT.md](STYLE_REFERENCE_AUDIT.md) — the pre-v0.6 open-access style reference audit this suite builds on.
- `benchmarks/publication_recreation/README.md` — the in-directory reference for this suite.
