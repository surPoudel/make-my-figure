# Make My Figure v1.1.1 — release notes

Prepared on `main` on 2026-09-20. The `v1.1.1` tag, installers and GitHub release follow after the author's final check.

### Added — plot types

- **Circos-style chord diagram** (`chord_diagram`, `make_my_figure_core/plots/chord_diagram.py`):
  flows between categories that share one set, from an edge list with one row per link
  (`source`, `target`, optional numeric `value`, optional `group`). Segments are sized by total
  flow, ribbons by link value; options with explicit scopes for segment order, gap, start angle,
  ribbon colouring (source / target / group), transparency, labels (radial / tangential), total
  tick marks and the group legend (style), and for the minimum link value, directed reading
  (ribbons narrow toward the target) and self-links (config). No statistics: a chord diagram
  summarises flows. Bundled synthetic example (six cell types, compartment group), catalogue
  entry and figure, focused tests (`tests/test_chord_diagram.py`), and a low-confidence
  recommendation (0.55) alongside the network graph for `source`/`target` edge lists. Genomic
  multi-track Circos (ideogram coordinates, heatmap or histogram rings) is out of scope for
  this version; the ring geometry leaves room for tracks.

### Added — reproducible figure packages
- **Reproducible figure packages (`.mmfpackage`)** — one portable file that reopens a figure on
  another computer without the original data files: the PlotSpec (or FigureSpec + every panel's
  PlotSpec/StatsSpec), a frozen lossless copy of the exact table(s) the plot used (`mmftable`
  JSON: doubles bit-exact incl. NaN/±Inf/−0.0, missing values, strings, categories, dates), the
  original CSV/TSV/XLSX when available, the StatsSpec with results, the MatrixSpec /
  SampleMetadataSpec / PreprocessingSpec with both the original and the derived matrix, imported
  panel images, PNG/SVG/PDF previews, the software environment, and `manifest.json` (format
  version 1, JSON Schema `schemas/figure_package_manifest.schema.json`) with a SHA-256 for every
  file. Core: `make_my_figure_core.package` (writer, reader, assembly helpers, security scan).
- **Desktop:** *Open Figure Package* on the landing page and File menu (Ctrl+Shift+P), *Save
  Reproducible Figure Package…* (Ctrl+Shift+S) and *Save Figure Package (.mmfpackage)* in the
  Export group with a privacy notice ("Figure packages include the data required to reproduce the
  figure"), content list and size estimate; packages open from drag-and-drop and *Recent files*
  (📦); composite packages reopen in the Figure Builder with their layout and frozen panel data;
  Figure Builder *Save Figure Package…*; Help tab *Files & reproducibility*.
- **Browser:** *Data source → Open Figure Package* and a *Figure Package* download.
- On opening a package the statistics are recomputed from the frozen data and compared with the
  stored StatsSpec, and a recorded preprocessing chain is replayed on the frozen source and
  compared with the frozen derived matrix; differences are reported, frozen values are never
  replaced.
- Exported PlotSpecs carry `source.source_table_sha256`, a content digest of the plotted table;
  *Open PlotSpec* warns when the data it finds differ from the recorded table.
- `PreprocessingStep.user_parameters` records the requested parameters so a chain can be replayed
  exactly (older records are replayed by signature filtering).

### Changed
- **Export all as ZIP** now contains the publication files, `name.plot_spec.json`,
  `name.stats_spec.json` (when statistics ran), **`name.mmfpackage`** and a README.
- Desktop wording makes the three artifacts unmistakable: *Export PlotSpec JSON (specification
  only)*, *Open PlotSpec… (specification only; needs the data file)*, Figure preset (no data),
  Figure package (frozen data + specifications).
- *Open PlotSpec* accepts the `{"plot_spec": …, "render_metadata": …}` sidecar written by *Export
  PlotSpec JSON* (previously only the bare spec from *Save PlotSpec* reopened).

### Security
- Packages are untrusted input: member names are checked (no `..`, absolute paths, drive letters,
  backslashes, control characters), symbolic links and device entries are rejected, entry count,
  entry size, total size and compression ratio are capped, unlisted or altered files fail the
  integrity check, nothing is unpickled or executed.

### Documentation
- `docs/FIGURE_PACKAGES.md`; Quick Start and User Manual (Parts I §6, XV §61–63a, XVI §68, XVII
  §70, XXIII, XXIV, glossary) describe PlotSpec vs Figure preset vs Figure package and the
  eight-step "Sharing a reproducible figure" workflow; `reports/portable_package_current_state.md`
  (live-code audit of v1.1.0), `reports/v1.1.1_manuscript_claim_audit.md`,
  `reports/v1.1.1_manual_acceptance_test.md`.

### Fixed — library compatibility
- Figure-package tables written with pandas 3 (default `str` dtype) reopen with their dtype
  intact; on pandas 2 they reopen as `object`, which is what that pandas infers itself
  (`make_my_figure_core/package/tabledata.py`, test in `tests/test_figure_package_integrity.py`).
- The figure-preset QC script no longer writes into read-only pandas 3 array views.

### Packaging
- Packaging: the MIT `LICENSE`, `README.md` and `CHANGELOG.md` are bundled at the top level of the
  desktop builds (Windows zip and installer, macOS app, Linux tar.gz/AppImage); the installer shows
  the licence; `pyproject.toml` declares the licence and classifiers.
- Dependencies: bounded ranges (next major excluded) in `pyproject.toml` and `requirements.txt`, and
  a new `requirements-lock.txt` with the exact versions the release was tested with.

## Known limitations
- Figure packages freeze the exact table used; they are not encrypted. The export dialog states that
  the package contains the data required to reproduce the figure. Review contents before sharing.
- The chord diagram is the general circular flow plot; genomic multi-track Circos (ideogram coordinates,
  heatmap or histogram rings) is not included.
- Installers are unsigned (see v1.1.0 notes); Linux binaries need glibc 2.38 or newer.
- Publication is a general style, not a journal template, and the statistics are not a substitute for
  statistical review.
