# Curation report: gapminder

Raw acquired from `https://raw.githubusercontent.com/plotly/datasets/master/gapminderDataFiveYear.csv` (license CC-BY-4.0); raw kept unchanged under `raw/`.

Processed CSVs written to `processed/` by `curate_benchmark_data.py`.

## gapminder_scatter
Transforms: Filter year==2007; log10 of gdpPercap.
Mapping: `{'x': 'log10_gdpPercap', 'y': 'lifeExp', 'color': 'continent', 'fit_line': True}`
