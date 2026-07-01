# Make My Figure

**Publication-style scientific figures from Excel, CSV, and TSV data — without hours of manual formatting.**

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-306%20passing-brightgreen)
![Plot types](https://img.shields.io/badge/plot%20types-17-orange)
![Desktop](https://img.shields.io/badge/desktop-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

Make My Figure is a research-software tool for scientists who need publication-ready
figures but don't want to spend hours manually adjusting fonts, legends, colors, axes,
figure sizes, and export settings. Load a table, choose a plot type, pick a journal-like
style, preview the figure, fine-tune the formatting, and export a manuscript-ready file.

> **Journal-like, not official.** The **Nature-like**, **Science-like**, and **Cell-like**
> style profiles are visual aesthetics only. They are **not** official journal templates and
> do **not** guarantee compliance with, or acceptance by, any journal.

---

## Why this exists

After the analysis is done, researchers still spend a lot of time reformatting plots to
look publication-ready — resizing text, fixing legends that overlap the data, choosing
readable colorblind-safe palettes, cleaning up axes, and exporting at the right size and
resolution. It's repetitive, easy to get wrong, and hard to reproduce.

Make My Figure aims to reduce that repetitive formatting work: it produces strong,
readable figures **by default**, keeps the settings reproducible, and makes high-quality
scientific figures accessible to people who would rather not write plotting code.

## What Make My Figure can do

- Load **CSV, TSV, and Excel** files
- Start from built-in **example/template datasets** for every plot type
- Generate common **biological, biomedical, and scientific** plot types
- Apply **publication-style defaults automatically**
- Choose **journal-like style profiles** (Nature-/Science-/Cell-like, + a neutral publication default)
- Adjust **font sizes, line widths, marker sizes, palettes, legends, figure size, and DPI**
- **Preview** figures interactively
- Export **SVG, PDF, PNG, and a PlotSpec JSON** sidecar
- **Save templates** so you can replace the example data with your own
- Run as a **Streamlit** web/developer app
- Run as a **desktop app** on Windows, macOS, and Linux
- Keep your **data local** in the desktop app (no telemetry, no cloud upload)

## Supported plot types

The current renderers (17):

- Bar plot with error bars
- Grouped bar plot with error bars
- Box / violin plot with points
- Scatter plot (with optional regression line)
- Line / time-course plot with error band
- Clustered heatmap
- Volcano plot
- Enrichment dot plot
- Kaplan–Meier survival curve
- Stacked composition bar plot
- Waterfall plot
- PCA scatter (expression matrix + sample metadata)
- Oncoprint mutation heatmap
- Lollipop mutation plot
- ROC curve
- Forest plot
- Ridge / density plot

See **[docs/PLOT_TYPE_REQUIREMENTS.md](docs/PLOT_TYPE_REQUIREMENTS.md)** for the required and
optional columns of each plot type.

## Publication-style defaults

Every plot is styled to be publication-ready out of the box, so the first figure you see is
already clean:

- readable fonts (≈12 pt axis labels, 10 pt ticks)
- clean axes (thin spines, no chartjunk, top/right spines hidden)
- **colorblind-aware, high-contrast** palettes (not the default Matplotlib cycle)
- non-overlapping legends where possible (placed outside the data when needed)
- sensible figure sizes and margins
- export-safe layout (tight bounding boxes so labels/legends aren't clipped)
- vector-friendly **SVG/PDF** output with **editable text**

You can still refine everything from the app's style controls. After each render, a
lightweight **publication-readiness check** flags likely issues (text too small, legend
overlap, possible clipping, missing labels). It's advisory and never blocks export.
More detail: **[docs/STYLE_PROFILES.md](docs/STYLE_PROFILES.md)**.

## Example data and templates

Every plot type ships with a **synthetic** example dataset. These double as **templates**:
open one, click **Save template**, then replace the rows with your own data while keeping the
column names. See **[docs/EXAMPLE_DATA.md](docs/EXAMPLE_DATA.md)** and
**[docs/DATA_TEMPLATES.md](docs/DATA_TEMPLATES.md)**.

> The bundled example datasets are **synthetic** and are **not** copied from published
> papers. Published figures may be consulted as *visual style references only* where
> licensing permits local analysis; the tool does not copy published figures and does not
> present the synthetic examples as real biological findings.

## Apps

### Streamlit app

```bash
streamlit run apps/streamlit_app/streamlit_app.py
```

A browser-based interface — convenient for development, testing, and quick use.

### Desktop app

```bash
python -m apps.desktop_app.main
```

A zero-command desktop application (PySide6) with a live figure preview, an interactive
toolbar (pan/zoom/home/save), and resizable panels. Standalone installers can be built for
Windows, macOS, and Linux so end users don't need the command line. See
**[docs/DESKTOP_APP.md](docs/DESKTOP_APP.md)** and
**[docs/BUILD_INSTALLERS.md](docs/BUILD_INSTALLERS.md)**.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

For the desktop app's extra dependencies:

```bash
pip install -e ".[desktop]"
```

A step-by-step guide is in **[docs/QUICKSTART.md](docs/QUICKSTART.md)**.

## Quick start

1. Open the app (desktop or Streamlit).
2. Choose **Use example data**, or upload a **CSV / TSV / XLSX** file.
3. Select a **plot type**.
4. Map columns to roles (if needed).
5. Choose a **style profile**.
6. **Preview** the figure.
7. Adjust formatting if you like (fonts, palette, legend, size, DPI).
8. **Export** SVG, PDF, PNG, and the PlotSpec JSON.

## Reproducibility

Each figure can be exported alongside a **PlotSpec JSON** file that records the plot type,
column mapping, style profile, formatting options, and export settings. This makes figures
easier to reproduce, revise, and share. See
**[docs/EXPORTING_PUBLICATION_FIGURES.md](docs/EXPORTING_PUBLICATION_FIGURES.md)**.

## Privacy

- The desktop app runs **entirely on your computer**.
- Your data does not need to leave the machine.
- There is **no telemetry and no cloud upload**. Any such feature would only ever be added
  if explicitly implemented and clearly documented.

## Roadmap

Planned directions (not yet implemented unless stated elsewhere):

### Statistics support (planned — v2 roadmap)

Future versions may add commonly used statistical tests and figure annotations. **These are
not implemented yet.** Planned coverage includes:

- **Two-group tests:** Student's t-test, Welch's t-test, Mann–Whitney U, paired t-test,
  Wilcoxon signed-rank
- **Multi-group tests:** one-way ANOVA, two-way ANOVA, repeated-measures ANOVA (where
  appropriate), Kruskal–Wallis
- **Categorical tests:** chi-square, Fisher's exact
- **Survival / model statistics:** log-rank test for Kaplan–Meier curves, hazard-ratio
  display if model support is added
- **Multiple-testing correction:** Benjamini–Hochberg (FDR), Bonferroni
- **Figure annotations:** p-value labels, significance brackets, effect sizes, confidence
  intervals, and automatic method reporting

Any statistics feature will be **transparent and reproducible**: it will report the exact
test used, its assumptions, the sample size, the effect size, and the correction method.

### Other planned items

- A Python (and possibly R) package API
- More journal-like style profiles
- A multi-panel figure builder
- Better automatic label-collision avoidance
- More biomedical plot templates
- Smoother GraphPad/Prism-like workflows
- Improved style auditing from open-access figures
- PowerPoint / Illustrator-friendly SVG/PDF export
- Batch rendering

## Contributing

The project is under active development and feedback is very welcome. Useful areas:

- testing with real scientific workflows
- suggesting missing plot types
- improving example templates
- UI/UX feedback
- documentation
- statistical-method review (for the planned statistics features)
- packaging and installers
- accessibility and colorblind-safe palettes

Please open an issue or pull request to get started.

## License

Released under the **MIT License** — see [LICENSE](LICENSE).

## Citation

Citation information will be added once the project reaches a stable release.

---

<sub>Developer notes: internal design docs live in [`docs/`](docs/), and the original
research-software prompt/mock-data bundle used to bootstrap the project is kept under
[`claude_code/`](claude_code/) and [`reports/`](reports/).</sub>
