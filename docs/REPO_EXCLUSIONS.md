# What is excluded from the Git repository (and why)

This repo intentionally omits some local-only content. Everything excluded is
either regenerable from code or is third-party material we prefer not to
redistribute. See `.gitignore` for the exact patterns.

## Harvested paper/figure library — `figure_library/` (LOCAL-ONLY)

The Milestone-3 harvester (`make_my_figure_core/harvest/`,
`scripts/harvest_library.py`) downloads **open-access, CC BY** papers and stores
figure images, captions, panel labels, and provenance under `figure_library/`.

- The figure **image bitmaps**, **supplementary files**, and **full text** were
  already local-only (git-ignored).
- We additionally **exclude the entire `figure_library/` directory** — including
  the derived caption/metadata JSON — from the repository. Although the source
  papers are CC BY (which permits redistribution with attribution), we keep all
  third-party paper content local-only to avoid any redistribution question and
  to keep the repo limited to our own work + synthetic data.
- **Nothing is lost:** the library is fully reproducible. Regenerate it with:
  ```bash
  python scripts/harvest_library.py --out figure_library --papers 10
  ```
  Provenance, licenses, and DOIs for the last run are summarized (as facts) in
  `reports/milestone_3_summary.md`, which **is** in the repo.

## Local tool / editor config

`.claude/`, `.idea/`, `.vscode/` — machine-specific configuration, not part of
the project.

## Build / environment artifacts

`.venv/`, `build/`, `dist/`, `*.egg-info/`, caches (`__pycache__`, `.pytest_cache`,
etc.), logs/temp files, and OS junk (`.DS_Store`, `Thumbs.db`).

## What IS in the repo (safe to share)

- The full application: `make_my_figure_core/`, `apps/streamlit_app/`,
  `apps/desktop_app/`, packaging (`packaging/`, `scripts/`, CI workflow), docs,
  and tests.
- **Synthetic** example/template data under `examples/` and `mock_data/`
  (generated from code, CC0 / project license — not derived from any publication).
- Reports and summaries (facts only: DOIs, licenses, counts).

No secrets, credentials, API keys, or tokens are stored anywhere in the repo.
