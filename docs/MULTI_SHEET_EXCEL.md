# Multi-sheet Excel workbooks

Make My Figure treats an uploaded `.xlsx`/`.xls`/`.xlsm` file as a **workbook** that
may hold many worksheets — differential-result tables, matrices, sample metadata,
enrichment tables, README/notes sheets, and empty sheets. You browse and select any
worksheet before mapping, plotting, or running statistics. Both the Desktop and
Streamlit apps use the same workbook loader (`make_my_figure_core/io/workbook.py`).

## Uploading and selecting a worksheet

1. Upload the workbook once (Desktop: **Open data file**; Streamlit: **Upload file**).
2. A **Worksheet** dropdown appears listing **every** sheet in workbook order.
3. Pick a sheet — its preview, detected type, and shape are shown.
4. Map columns and plot as usual. Only the **selected** worksheet drives mapping,
   recommendations, plotting, preprocessing, statistics, and exports.
5. Switch worksheets from the dropdown at any time — **no need to re-upload**.

Switching a worksheet clears stale column mappings, recommendations, statistics,
preprocessing selections, and the rendered plot, then loads the newly selected sheet
cleanly. Mappings are never silently reused across sheets (different sheets can use
different column names).

## Every worksheet stays selectable

Sheets are **never hidden** because they don't look like data. Documentation/notes,
legends, and empty sheets remain selectable and previewable:

- **Empty sheet** — selectable; shows "This worksheet is empty"; plotting is disabled;
  workbook navigation stays active.
- **Text/notes sheet** — selectable; previewed; classified as *documentation/notes*;
  the app explains no compatible plot is detected but does not block selection.
- **Odd/late header row** — selectable; previewed raw; you can confirm the header row
  or choose *No header* (positional `column_1…` names) rather than discarding the sheet.
- **Hidden sheet** (as marked in the workbook) — listed and marked *(hidden)*, never
  silently omitted.

## Advisory sheet classification

Each sheet gets a lightweight, **advisory** type based on its headers/content:

| Type | Evidence |
|------|----------|
| precomputed differential results | fold-change + p-value/FDR headers (edgeR/limma/DESeq2 aliases) |
| numeric feature matrix | mostly numeric (sample-like) columns |
| metadata | a sample-id column plus a group column |
| enrichment / pathway | term/pathway/NES/gene-ratio-style headers |
| documentation / notes | mostly blank, or only text columns |
| empty | no rows or columns |
| generic tabular / unknown | anything else |

Classification is **only** a hint (e.g. *"Detected sheet type: documentation/notes.
You may still select and inspect this worksheet, but no plot is currently
recommended."*). It never removes or blocks a sheet.

## Worksheet-aware output naming

Exports fold the workbook and worksheet names into filenames so outputs from
different sheets never overwrite each other:

```
Sol_24M_vs_6M_volcano.svg / .png / .pdf
Sol_24M_vs_6M_volcano.plot_spec.json
Sol_24M_vs_6M_volcano.stats_spec.json
```

Sheet names are sanitized to be cross-platform-safe (invalid characters replaced,
Windows reserved names avoided, Unicode preserved for readability). Two sheets whose
names sanitize identically get distinct, non-colliding stems.

## Provenance

When data comes from a workbook, a `source` block is recorded in the PlotSpec (and
mirrored into the StatsSpec, MatrixSpec, and Figure Builder panels):

```json
"source": {
  "source_workbook_name": "Aging_DE.xlsx",
  "source_workbook_hash": "…",
  "source_sheet_name": "Sol_24M_vs_6M",
  "source_sheet_index": 2,
  "source_sheet_type": "differential_results",
  "source_header_row": 0
}
```

This travels into exported sidecar JSON so a figure is traceable to its exact
worksheet. Specs **without** a `source` block (CSV/TSV/single-table sources, or specs
saved before this feature) still load — the field is optional and backward-compatible.

## Using multiple DE comparison sheets

A common workflow is one workbook with several comparison sheets (e.g.
`Comparison_A`, `Comparison_B`). Select each sheet in turn; the app **re-runs DE
column detection per sheet** (it does not assume every sheet uses the same headers),
you confirm the mapping, and it recommends volcano / MA (when an abundance column
exists) / ranked-effect / lollipop / top-result table. Each sheet's exports carry
that sheet's name and provenance.

> Make My Figure never computes differential-expression statistics and has no R
> dependency: it **plots** a precomputed results table (→ volcano/MA) or a normalized
> matrix (→ heatmap/PCA). P-values are read verbatim.

## Optional matrix / metadata worksheets

For a sheet classified as a matrix, use the **Matrix workflow**; the selected
worksheet drives the mapping wizard and its provenance is stored. You may supply
sample metadata from another worksheet of the same workbook or from an external file;
matrix and metadata sources are recorded separately.

## Performance

The workbook is read once; sheet listing, preview, and full load work from cached
bytes keyed by content hash + sheet + read options — so switching sheets never
re-reads the file, and large sheets are only fully loaded when selected.

## Limitations

- Legacy `.xls` requires the optional `xlrd` engine; otherwise re-save as `.xlsx`.
- Password-protected/encrypted and corrupt workbooks surface a clear error rather
  than crashing.
- Hidden-sheet state is read from `.xlsx`/`.xlsm` (openpyxl); for `.xls` all sheets
  are shown without a hidden marker.
- Regenerate the synthetic test workbook with
  `python scripts/generate_multi_sheet_fixture.py`.
