# Scientific QC — penguins_scatter

**Result: PASS**

Target panel: Fig: bill length vs bill depth by species (Simpson's paradox).

Transforms: Drop rows with missing bill/species; keep morphometric columns.

- mapping[x]='bill_length_mm' traced to source column ✓
- mapping[y]='bill_depth_mm' traced to source column ✓
- mapping[color]='species' traced to source column ✓
- rows=342, cols=6
