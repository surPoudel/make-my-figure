# Scientific QC — gapminder_scatter

**Result: PASS**

Target panel: Fig: life expectancy vs income (2007), by continent.

Transforms: Filter year==2007; log10 of gdpPercap.

- mapping[x]='log10_gdpPercap' traced to source column ✓
- mapping[y]='lifeExp' traced to source column ✓
- mapping[color]='continent' traced to source column ✓
- rows=142, cols=6
