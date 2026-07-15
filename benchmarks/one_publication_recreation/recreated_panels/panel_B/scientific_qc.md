# Scientific QC — Panel B (boxplot_or_violin_with_points)

Source (processed): `processed_data/panel_B_body_mass.csv` — 342 rows.
Columns used: {'x': 'species', 'y': 'body_mass_g', 'kind': 'box', 'points': True}

- mapping[x]='species' present ✓
- mapping[y]='body_mass_g' present ✓
- group counts (body_mass complete): {'Adelie': 151, 'Chinstrap': 68, 'Gentoo': 123} (sum=342) ✓
  full-dataset counts {'Adelie': 152, 'Chinstrap': 68, 'Gentoo': 124} (n=344) minus rows lacking body_mass_g by species {'Adelie': 1, 'Chinstrap': 0, 'Gentoo': 1} -> 342 analysed

No statistical brackets are drawn (the paper uses linear models with covariates — a different method; not reproduced here). The box summaries trace directly to the data:
  - Adelie: median body mass = 3700 g
  - Chinstrap: median body mass = 3700 g
  - Gentoo: median body mass = 5000 g
  (Gentoo >> Adelie ~ Chinstrap — matches the paper's reported size ordering.)

**Result: PASS**