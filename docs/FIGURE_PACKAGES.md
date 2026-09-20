# Reproducible figure packages (`.mmfpackage`)

A **figure package** is one portable file that reproduces a Make My Figure figure on any
computer that has Make My Figure — without the original data files. It exists because a
PlotSpec alone is only a *recipe*: it names the table it was drawn from, it does not contain
the values.

## Three artifacts, three purposes

| Artifact | File | Contains | Needs to reopen |
|---|---|---|---|
| **PlotSpec** | `name.plot_spec.json` | the recipe for **one** plot: plot type, column roles, options, style, layout, statistics *configuration*, annotations, worksheet provenance, a content digest of the table | the source data table |
| **Figure preset** | `name.mmfpreset.json` | reusable appearance / configuration to apply to **new** data; never any data or table name | nothing (applies to your own table) |
| **Figure package** | `name.mmfpackage` | PlotSpec (or FigureSpec) **plus** a frozen copy of the exact table(s) used, the original source file when available, StatsSpec results, MatrixSpec / SampleMetadataSpec / PreprocessingSpec where they apply, imported images, PNG/SVG/PDF previews, the software environment, and a manifest with a SHA-256 for every file | nothing |

## What is inside

```
name.mmfpackage  (ZIP container)
├── manifest.json                 format, version, creator, every file with SHA-256 and size,
│                                 tables (shape, columns, dtypes, digest), components, assets,
│                                 relationships (derived_from), warnings, privacy notice
├── plot_spec.json                single plot           | figure_spec.json  composite
├── stats_spec.json               when statistics ran   | panels/<id>/plot_spec.json, stats_spec.json, panel.json
├── matrix_spec.json, sample_metadata_spec.json, preprocessing_spec.json    when the plot came
│                                                                            from the Matrix Workflow
├── data/<table>.mmftable.json    lossless canonical table (what the renderer receives)
├── data/<table>.csv              human-readable copy (not used for reconstruction)
├── data/original/<table>/<file>  the original CSV/TSV/XLSX when it was available (provenance)
├── assets/<panel>/<image>        imported panel images (composites)
├── preview/figure.png .svg .pdf  what the figure looked like when the package was saved
├── environment/environment.json  Make My Figure version and commit, Python, library versions
└── README.txt
```

The canonical table format (`mmftable`, format version 1) records every column with its
dtype: doubles are written with the shortest round-trip representation (exact, including
NaN, ±Inf and negative zero), integers exactly, strings and missing values distinctly,
categoricals with their categories and order, datetimes as nanoseconds. Decoding reproduces
the DataFrame bit for bit. Its bytes are deterministic, so the SHA-256 of the table file is a
content digest of the data.

## Source and derived data

When a plot was drawn from a preprocessed matrix the package holds **both** the original
matrix (provenance) and the exact derived matrix the plot used, plus the PreprocessingSpec
that links them. On opening, the figure is drawn from the frozen *derived* table; the
application also replays the recorded chain on the frozen source and reports whether it
still reproduces the derived table. It never substitutes the recomputed values for the
frozen ones.

## Statistics

The package stores the StatsSpec with every result (test, comparison, statistic, P,
adjusted P, effect size, CI). On opening, the statistics are recomputed from the frozen
data by the same engine and compared with the stored results; any difference is reported
as a warning. With frozen data and the same version the results are identical.

## Integrity and safety

* Every file in the container is listed in `manifest.json` with its byte size and SHA-256.
  The reader verifies all of them *before* anything is rendered and refuses to open a
  package whose contents changed ("Package integrity check failed: data differ from the
  values recorded when the package was created"). Unlisted files are also rejected.
* The manifest is validated against `schemas/figure_package_manifest.schema.json`; packages
  in a newer format version are refused with a message to update the application.
* The container is treated as untrusted input: member names must be relative and free of
  `..`, drive letters or backslashes; symbolic links are rejected; entry counts, sizes and
  compression ratios are capped; nothing is unpickled or executed; image assets are copied
  byte-for-byte into a fresh managed folder under a sanitised name.
* No absolute paths are stored. The original file is recorded by **name** (and copied), not
  by location.

## Privacy

A package **contains data**. Both interfaces say so before saving ("Figure packages include
the data required to reproduce the figure") and the notice is repeated in the package's
README and manifest. Share packages only with people who may see those data.

## Using packages

**Desktop — save:** finalise the plot, then **5. Export → Save Figure Package (.mmfpackage)**
(or *File → Save Reproducible Figure Package…*, Ctrl+Shift+S). A dialog lists what will be
included and the estimated size. **Export all as ZIP** now contains the figure files, the
PlotSpec/StatsSpec JSON **and** the package.

**Desktop — open:** landing page **Open Figure Package**, *File → Open Figure Package…*
(Ctrl+Shift+P), drag-and-drop, or *Recent files* (packages are marked 📦). The figure opens
in the normal editor with the frozen data; the status bar reports "integrity verified".
Multi-panel packages open in the Figure Builder with their layout and every panel's data.

**Figure Builder:** **Save Figure Package…** packages the composite (FigureSpec, all panel
PlotSpecs/StatsSpecs, every table, imported images, previews).

**Browser:** *Data source → Open Figure Package* (upload) and the **Figure Package** download
button in **Export**.

## Sharing a reproducible figure

1. Finalise the plot (or composite).
2. **Save Figure Package**.
3. Send the one `.mmfpackage` file.
4. The collaborator opens Make My Figure.
5. **Open Figure Package**.
6. The package integrity is verified.
7. The figure opens with the frozen data and configuration.
8. The collaborator inspects, edits and re-exports as usual — including saving a new package.

## PlotSpec files and changed data

A PlotSpec exported by v1.1.1 carries `source.source_table_sha256`, the digest of the table
it was drawn from. **Open PlotSpec** compares it with the table it finds and warns when the
data differ. Older PlotSpecs (v1.1.0) have no digest and open as before when their data
are present; they were never portable on their own.

## Format versioning

`manifest.json` → `format_version` (currently **1**) is independent of the software
version. Future versions of Make My Figure will migrate older packages or refuse newer ones
explicitly; a reader never guesses.

## Python API

```python
from make_my_figure_core.package import (content_for_single_plot, write_figure_package,
                                         open_figure_package, single_plot_inputs)
from make_my_figure_core.plots.registry import render

res = render(spec, df)
content = content_for_single_plot(spec, df, res, table_name="data.csv", source_path="data.csv")
write_figure_package(content, "figure.mmfpackage")

pkg = open_figure_package("figure.mmfpackage")       # validates, verifies every checksum
spec2, df2, aux2 = single_plot_inputs(pkg)
render(spec2, df2, aux=aux2 or None)
```
