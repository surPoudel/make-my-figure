# Preprocessing QC report

## Method

Values were log2(x + 1.0) transformed, then row (feature) z-scored.

## Diagnostics (before → after)
- features: 55665 → 55665
- samples: 12
- overall skew: 91.20 → 0.40
- zero fraction: 52.36% → 38.97%
- value range: [0.0, 1787213.0] → [-3.28, 3.32]
- suspected type (before): intensity_like_skewed

## QC plots (before / after)
- **value_density** — before: `per_plot\value_density_before.png`, after: `per_plot\value_density_after.png`
- **sample_boxplot** — before: `per_plot\sample_boxplot_before.png`, after: `per_plot\sample_boxplot_after.png`
- **library_size** — before: `per_plot\library_size_before.png`, after: `per_plot\library_size_after.png`
- **mean_variance** — before: `per_plot\mean_variance_before.png`, after: `per_plot\mean_variance_after.png`
- **pca** — before: `per_plot\pca_before.png`, after: `per_plot\pca_after.png`
- **sample_correlation** — before: `per_plot\sample_correlation_before.png`, after: `per_plot\sample_correlation_after.png`

## Sample labels (QC axes show the short label)
| short | full sample name |
| --- | --- |
| `DHP001` | `3345023_DHP001` |
| `DHP002` | `3345024_DHP002` |
| `DHP003` | `3345025_DHP003` |
| `DHP004` | `3345026_DHP004` |
| `DHP005` | `3345027_DHP005` |
| `DHP006` | `3345028_DHP006` |
| `DHP007` | `3345029_DHP007` |
| `DHP008` | `3345030_DHP008` |
| `DHP009` | `3345031_DHP009` |
| `DHP010` | `3345032_DHP010` |
| `DHP011` | `3345033_DHP011` |
| `DHP012` | `3345034_DHP012` |

See `before_after_contact_sheet.png` (300-DPI overview) and the vector per-plot files in `per_plot/` (PDF/SVG). Every step is reproducible from the PreprocessingSpec; the original matrix is unchanged.