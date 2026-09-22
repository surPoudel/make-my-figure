# Manual acceptance test - experimental publication presets

Branch: `feature/evidence-derived-journal-presets` (worktree `make_my_plot_journal_presets`).
Nothing here is merged or released. Work through every step in both frontends and record the
result in the table at the end. A step that cannot be completed is a blocker for any future merge.

## Before you start

1. Run the automated suites and compare with `reports/journal_presets/baseline_test_run.md`:
   `python -m pytest tests -q` (on Windows, PySide6 installed, so the Qt tests run too).
2. Run the preset QC and open its README: `python scripts/experimental_preset_qc.py`
   -> `reports/journal_presets/qc/README.md`. Every non-PASS cell must be either fixed or listed as
   a known limitation in `docs/EXPERIMENTAL_PUBLICATION_PRESETS.md`.
3. Open `reports/journal_presets/comparison_sheets/` and look at each sheet: the same synthetic
   figure under Publication defaults and under each experimental preset, at the target width.

## Desktop application (apps/desktop_app)

| # | Step | Expected |
|---|---|---|
| D1 | Start the app, load the bundled example for "Box / violin plot with points". | Figure renders with Publication defaults. |
| D2 | In "Figure preset", the "Show experimental presets" box is **unticked** by default. | The combo lists only your own presets. |
| D3 | Tick "Show experimental presets". | Entries with the suffix `[experimental, NN mm]` appear; the status line says how many and "preview required". No entry name contains a journal name or the words compliant/approved/ready. |
| D4 | Select an experimental preset and click **Apply** (not Preview). | The preview dialog opens anyway - experimental presets are never applied blind. |
| D5 | In the dialog: two images (Current settings / With this preset) on synthetic data, a list of settings with old -> new values, the provenance text (evidence family, numbers of papers/figures/panels, official sources, target width and its source), the green "Checked: no data ... changes" line. | All present; the images visibly differ in typography/line weights; the text is readable. |
| D6 | Click **Cancel**. | Status says "Preview closed; nothing applied."; controls unchanged; figure unchanged. |
| D7 | Repeat D4 and click **Apply**. | Controls update (font sizes, spine width, width preset = numeric mm, palette...); figure re-renders; status says "Applied preset ... after preview: N setting(s)". |
| D8 | Check the data-bound controls after D7: column roles, statistics test, thresholds, axis labels, limits. | **Unchanged.** |
| D9 | Export SVG/PDF/PNG. Measure the exported PDF width (e.g. in a PDF viewer's document properties or with `pdfinfo`). | Within about 10 % of the preset's target width for the plot types listed as recommended; the QC README lists the exceptions. |
| D10 | Switch plot type to "Clustered heatmap", then to "Kaplan-Meier survival curve" and apply the same preset via preview each time. | Universal settings apply; options not applicable are listed as skipped, never silently ignored. |
| D11 | Hand-edit a copy of an experimental preset file to add `"options": {"lfc_cutoff": 3}` and import it. | The library refuses it ("options that change what is computed are not allowed"), or the preview shows the red "Refused" line and Apply is disabled. |
| D12 | Save the current configuration as your own style preset after applying an experimental one; restart the app; apply your saved preset. | The saved preset reproduces the look; it is listed under your presets, not as experimental. |
| D13 | Open the File > Figure preset menu. | "Preview & apply selected preset..." is present and works like the button. |
| D14 | Build a two-panel figure in the Figure Builder with panels styled by different presets, save a Figure Package, re-open it. | Panel styles survive the round trip; the package manifest records the preset name/provenance in each PlotSpec's style block (no preset file is required to re-open). |

## Browser application (apps/streamlit_app)

| # | Step | Expected |
|---|---|---|
| S1 | Open the app with an example dataset; expand "Figure preset". | "Show experimental presets" unticked by default; only your presets listed. |
| S2 | Tick it; choose an experimental entry; the **Apply** button is disabled for experimental entries. | Only **Preview** is available. |
| S3 | Click **Preview**. | Two images (before/after on synthetic data), a table of settings (now / preset), the provenance info box, the green safety line, and "Apply this preset" / "Cancel". |
| S4 | Click **Cancel**. | Preview disappears; controls unchanged. |
| S5 | Preview again and click **Apply this preset**. | Sidebar controls update; figure re-renders; success message names the preset. |
| S6 | Verify column mappings, statistics and thresholds unchanged. | Unchanged. |
| S7 | Download the exported SVG/PDF and check the width. | As in D9. |

## Wording and honesty checks

| # | Check | Expected |
|---|---|---|
| W1 | Search both UIs and `docs/EXPERIMENTAL_PUBLICATION_PRESETS.md` for journal names in preset *names* or any "compliant / approved / ready / guaranteed" wording. | None in shipping UI text; journal families are named only in the provenance/evidence documentation. |
| W2 | Read the provenance text of each preset. | It states the evidence family, counts, official sources with access dates, the target width and its source, and the evidence class of each value (observed / inferred / estimated / official). |
| W3 | Confirm `reports/journal_presets/manuscript_future_claims.md` exists and that the manuscript itself was **not** changed. | True. |

## Record

| Step | Result (pass / fail / n.a.) | Notes | Tester | Date |
|---|---|---|---|---|
| D1 (macOS, matplotlib < 3.10) | fail -> fixed | `boxplot() got an unexpected keyword argument 'orientation'`; fixed in `plots/box_violin.py`, see `reports/journal_presets/matplotlib_compat_check.md`; re-test required | author | 2026-09-17 |
| all (re-test on the merged base) | pending | 2026-09-22: `origin/main` v1.1.1 (39 plot types) merged into this branch (c5bb8b0); stable-sort fix for pandas-dependent sample order (stacked bars, oncoprint / lollipop tie order), see `reports/journal_presets/matplotlib_compat_check.md`. Pull the branch again before repeating D1-D14 / S1-S7; the stacked composition example should list samples S01, S02, S03, ... within each group on every machine. | author | |
| D1-D14 | | | | |
| S1-S7 | | | | |
| W1-W3 | | | | |

Only after every row passes may a merge into `main` be considered. No tag, no release and no
change to the shipping preset library follows from this document by itself.
