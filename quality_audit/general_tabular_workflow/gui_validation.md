# GUI validation

Platform for every run below: WSL2 Linux, Python 3.11.9, PySide6 6.11.2, Qt offscreen
platform (`QT_QPA_PLATFORM=offscreen`). The real `MainWindow` and dialogs were driven
programmatically: widget values were set, keys typed with `QTest`, buttons clicked.
**Nothing in this file was run on macOS**; see "Not covered".

## Desktop

| Area | How | Result |
|---|---|---|
| Title / X / Y label typing keeps focus | `QTest.keyClicks` with 300 ms pauses (longer than the 180 ms render debounce), on all 45 plot types and the violin mode; main window must stay active through re-renders | 51 / 51 pass; 4 of these fail on the unfixed v1.3.0 code |
| Canvas still takes focus when the user puts it there | focus canvas, re-render | pass |
| Import bee workbook (Excel) | `load_path` on the fixture | 11 columns, sheet `Sheet1`; classified as a generic table |
| Roles | dialog suggestions; manual changes win | pass |
| Transform + preview | log10 of `bee body size_mm`: preview row 1 shows 3.1 / 0.491362; valid 4, invalid 0, missing 0 | pass |
| Zeros and negatives | a `count` column with 0 and −1: Add disabled, "2 of 5 value(s)" shown; "record as missing" enables it; 2 missing in the derived column, originals kept | pass |
| Apply → plot | derived column mapped to y, first factor to x; plotted points equal log10 of the raw values (atol 1e-12) | pass |
| Log axis on the derived column | refused, with "twice" in Messages; axis stays linear | pass |
| Revert to original data | raw table restored exactly | pass |
| Axis controls visible exactly where supported | all 45 plot types, both axes | 45 / 45 |
| Untouched axis controls write nothing | spec layout has no axis keys | pass |
| Log10 + plain from the panel | axis log, values identical; back to Linear restores the axis and removes the keys | pass |
| Range from the panel | applied when it contains the data; refused with "would hide plotted values" when it does not | pass |
| Spec reload restores controls | log2 and minor-ticks-off restored in a second window | pass |
| Hidden settings do not leak | log2 set on a scatter, switched to a volcano: no axis keys in the volcano's spec, group hidden | pass |
| New plot resets | `reset_plot_styling` clears every axis control | pass |
| Factorial: non-estimable | bee three-way: all four reasons shown; no table; export disabled | pass |
| Factorial: estimable | simulated replicated three-way on `log10(quantity per bee)`: 7 terms, 36 residual df (screenshot 08) | pass |
| Analysis tab performance | five list refreshes build the derived table at most once, without checksums | pass |
| Figure Package save → fresh-process reopen | see figure_package_validation.md | pass |
| Packaged self-test | `--selftest`: 45 plot types + statistics + table transform + three-way ANOVA + log axis + Qt binding refcounts | SELFTEST OK |

Screenshots of these states: `tutorial/general_tabular_data/screenshots/01`–`09`,
captured from the real window by `tutorial/general_tabular_data/make_screenshots.py`.

## Browser (Streamlit AppTest, in-process)

Transform expander adds `log10(value)`; derived CSV, record JSON and Figure Package
downloads offered; the derived column is mappable and renders; Y axis scale offered on
the box plot and absent on the volcano plot; log10 + plain renders without error; the
design check explains its result (`tests/test_streamlit_table_tools_and_axis_scale.py`,
4 / 4).

## Not covered — needs a person or a Mac

* **macOS.** None of the above ran on macOS. The focus defect was found and fixed on
  Linux. The mechanism (a detached widget becoming a top-level window and taking
  activation) is Qt behaviour on every platform, but the fix has not been tried on
  the reporter's Mac.
* **Real mouse and keyboard** (rather than `QTest` events), native file dialogs, and
  screen reading by a scientist unfamiliar with the app.
* **Emoji** on buttons render as boxes in the Linux screenshots; this is an absent
  font on this machine, not the app.
