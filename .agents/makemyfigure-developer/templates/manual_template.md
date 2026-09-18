### __DISPLAY_NAME__

*Registry key:* `__PLOT_TYPE__`

**What it shows.** __WHAT_THE_PLOT_ANSWERS__

**Required data.** One row per __UNIT_OF_OBSERVATION__ (long format). Required columns: __REQUIRED_ROLES__.
Optional: __OPTIONAL_ROLES__. Missing or non-numeric values in the value column are not drawn and are
reported in the export warnings.

**Column mapping.**

| role | meaning | example column |
|---|---|---|
| `x` | category / grouping variable | `group` |
| `y` | measured value | `value` |

**Important options.** __OPTIONS_TABLE__ (each option states whether it changes appearance only
[style] or what is computed/shown [config]).

**Statistics.** __STATISTICS_SENTENCE__ (test choice `auto` selects by design and n; results are
written to the statistics sidecar and drawn as brackets/labels; the renderer never computes tests
itself).

**Customisation.** Palette, marker size, line width, fonts, figure width and legend placement follow
the Publication style and any Figure preset; plot-specific options are listed above.

**Example.** `examples/by_plot_type/__SLUG__/` (synthetic, CC0): `data.csv`, `plotspec.json`, `README.md`.
Catalogue figure: rendered from that example by `scripts/build_plot_catalog_part.py`.

**Export and reproducibility.** SVG/PDF/PNG/TIFF/EPS with editable text; the PlotSpec sidecar and
statistics sidecar record mapping, options, style, n per group and test results; the figure reopens
from the sidecar or a Figure Package with identical numbers.
