# Scientific QC — penguins_box

**Result: PASS**

Target panel: Fig: body mass distribution by species with group comparison.

Transforms: Drop missing body_mass; order species Adelie<Chinstrap<Gentoo.

- mapping[x]='species' traced to source column ✓
- mapping[y]='body_mass_g' traced to source column ✓
- rows=342, cols=2
- statistics: 1 StatResult(s) drawn from run_statistics (test=kruskal_wallis, corr=bh) ✓
