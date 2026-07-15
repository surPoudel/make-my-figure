# Scientific QC — Panel B (boxplot_or_violin_with_points)

Source (processed): `processed_data/panel_B_body_mass.csv` — 342 rows.
Columns used: {'x': 'species', 'y': 'body_mass_g', 'kind': 'box', 'points': True}

- mapping[x]='species' present ✓
- mapping[y]='body_mass_g' present ✓
- group counts (body_mass complete): {'Adelie': 151, 'Chinstrap': 68, 'Gentoo': 123} (sum=342) ✓
  full-dataset counts {'Adelie': 152, 'Chinstrap': 68, 'Gentoo': 124} (n=344) minus rows lacking body_mass_g by species {'Adelie': 1, 'Chinstrap': 0, 'Gentoo': 1} -> 342 analysed

Statistics drawn on the figure (each from a stored StatResult via `run_statistics`, Mann–Whitney U, BH-corrected):
  - Adelie vs Chinstrap: Mann-Whitney U test, p=0.485, adj_p=0.485, n=219
  - Adelie vs Gentoo: Mann-Whitney U test, p=2.98e-42, adj_p=8.95e-42, n=274
  - Chinstrap vs Gentoo: Mann-Whitney U test, p=1.67e-28, adj_p=2.51e-28, n=191

**Result: PASS**