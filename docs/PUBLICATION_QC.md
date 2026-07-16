# Publication QC

Publication QC (`make_my_figure_core/qc/`) scores a rendered figure for
publication readiness and suggests non-destructive fixes. It is **advisory
only** — it never blocks rendering or export.

> **Publication style, not an official template.** Make My Figure does not
> provide official journal templates or claim compliance with any journal's
> formatting requirements. The Publication style is a general manuscript-ready
> visual style. Publication QC checks general figure hygiene (readability,
> resolution, labeling) — it is not a journal-compliance checker.

## How to run it

```python
from make_my_figure_core.qc import score_publication, suggest_fixes, apply_fixes

score = score_publication(result=result, spec=spec, stats_report=result.stats_report)
fixes = suggest_fixes(score, spec)
new_spec = apply_fixes(spec, [f["id"] for f in fixes])   # re-render with new_spec
```

`score_publication(*, result=None, figure=None, spec=None, stats_report=None)`
accepts either a `RenderResult` (`result=`) or a bare Matplotlib `figure=`.
Passing `spec` (the PlotSpec) and `stats_report` enables extra checks (export
DPI, method-report presence). It never raises — a failure inside a check is
swallowed and simply omits that check.

- **Desktop app** — the **"Publication QC"** button (enabled once a figure has
  been rendered) opens a dialog listing the score, level, and every warn/fail
  check with its suggestion. An **"Auto-fix & re-render"** button applies the
  available fixes and re-renders.
- **Streamlit app** — the **"Publication QC"** expander below the rendered
  figure shows the same score/level/checks live.

## Scoring and levels

`PublicationScore` has:

- `level`: `"pass"`, `"warn"`, or `"fail"`.
- `score`: 0–100, starting at 100 and penalized 12 points per `warn` and 30
  points per `fail` (floored at 0).
- `checks`: a list of `Check(id, level, message, suggestion, element)`.
- `summary`: a one-line human-readable summary.

`level` is `"fail"` if any check failed, `"warn"` if only warnings were raised,
and `"pass"` (score 100) if nothing was flagged. Use `score.issues()` to get
only the warn/fail checks (the actionable ones); `score.passed` is a shortcut
for `level == "pass"`.

## What is checked

1. **Existing advisory figure check** — folds in
   `qa.publication_check.check_publication_readiness`: missing x/y axis labels,
   text too small or likely clipped, a legend that may overlap the data, and
   dense tick labels.
2. **Export DPI at the intended physical size** (`check id: export_dpi`) — reads
   `output.dpi` from the PlotSpec. Below 150 DPI is a `fail`; below 300 DPI is a
   `warn` (many journals expect ≥300 DPI at final print size).
3. **Rasterized multi-panel resolution** (`panel_resolution`) — warns if a
   multi-panel figure's embedded raster content (`panel_dpi`) is below 200 DPI.
4. **Contrast** (`low_contrast`) — warns if an axis label's color has low
   luminance contrast against its background.
5. **Label crowding**, checked per plot type:
   - `heatmap_row_density` — warns above 60 heatmap row tick labels.
   - `label_crowding` — warns above 40 text annotations on a volcano plot.
   - `tick_density` — warns above 30 tick labels on any other axis.
6. **Missing statistical method report** (`missing_method_report`) — warns when
   statistics were computed/enabled but no method report
   (`stats_report.method_paragraph` / `metadata["statistics_report"]`) was
   recorded alongside the figure.
7. **Missing units** (`missing_units`) — a low-confidence advisory: if an axis
   label contains a unit-like keyword (time, dose, concentration, mass, …) but
   no bracket/parenthesis/slash/percent marker, it suggests adding units, e.g.
   `Time (h)`. This never fails the score.

## Interpreting warnings

Every `Check` carries a `suggestion` string and an `element` (the affected
figure part: `axes`, `legend`, `export`, `ticks`, `text`, `panels`,
`statistics`, `figure`). Treat `warn` as "worth a second look before
submission" and `fail` as "will likely be rejected or look wrong in print"
(currently only under-resolution exports trigger `fail`). A `pass` with score
100 means no check fired at all — it is not a guarantee the figure matches a
specific journal's requirements, only that no known readability/export issue
was detected.

## Auto-fixes

`suggest_fixes(score, spec)` maps each warn/fail check to zero or more
available fixes (deduped); `apply_fixes(spec, fix_ids)` returns a **new**
PlotSpec dict with those fixes applied (the input spec is never mutated).

| Fix id | Effect | Addresses check(s) |
|---|---|---|
| `enlarge_figure` | Sets `layout.column_width = "double"` | `readability`, `tick_density` |
| `legend_outside` | Sets `style.legend_outside = True` | `legend_overlap` |
| `hide_excess_labels` | Caps `mapping.max_labels` / `mapping.top_n` at their existing value or 15/20 | `tick_density`, `heatmap_row_density`, `label_crowding` |
| `increase_margins` | Raises `layout.pad_inches` to at least 0.25 | (available, not auto-suggested by any current check) |
| `increase_font` | Bumps `style.base_font_pt` / `axis_font_pt` / `tick_label_pt` by 1pt (with minimums) | `readability` |
| `increase_dpi` | Raises `output.dpi` to at least 300 | `export_dpi`, `panel_resolution` |

Some checks — `missing_axis_labels`, `low_contrast`, `missing_units`,
`missing_method_report` — have **no** automatic fix, because the fix would
require fabricating a label, a method sentence, or a color choice the app
cannot infer on your behalf; these always require a manual edit.

## See also

- [docs/V0_6_NEW_FEATURES.md](V0_6_NEW_FEATURES.md) — where QC fits in the v0.6 release.
- [docs/STYLE_PROFILES.md](STYLE_PROFILES.md) — the Publication style and the older, simpler advisory check it already ran before v0.6.
- [docs/PUBLICATION_BENCHMARKS.md](PUBLICATION_BENCHMARKS.md) — QC is the scoring mechanism used across the benchmark suite.
- `scripts/generate_v0_6_qc_gallery.py` — regenerates a QC score for every plot type's bundled example.

## Matrix-workflow gallery

`scripts/generate_publication_qc_gallery.py` renders **every plot type** (from its
bundled example) **plus the matrix-workflow plots** (heatmap, clustered z-score
heatmap, PCA, sample-correlation heatmap, volcano from a feature-level differential
summary, and a selected-feature violin from wide->long) with the single Publication
style, QC-scores each, and checks PNG/SVG/PDF exports. Outputs go to
`reports/publication_qc_gallery/` (`qc_summary.csv` + `qc_report.md` are tracked; the
images are regenerated on demand). See [MATRIX_WORKFLOW.md](MATRIX_WORKFLOW.md).
