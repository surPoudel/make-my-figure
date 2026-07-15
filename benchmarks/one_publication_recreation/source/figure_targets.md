# Target panels (textual descriptions from the article; no images stored)

Paper: Gorman et al. 2014, *PLoS ONE* 9(3):e90081 (CC BY 4.0). We describe the
target panels in our own words / brief attributed paraphrase of the figure
legends; we do not reproduce the figure images.

## Panel A — culmen (bill) dimensions by species
Target: a scatter of culmen (bill) length vs culmen depth with points coloured by
species, showing that within each *Pygoscelis* species bill length and depth are
positively associated, while species occupy distinct regions of bill-shape space.
App plot type: `scatterplot_with_regression` (per-species trend).

## Panel B — body mass by species
Target: the distribution of body mass (g) across the three species, underpinning
the paper's analysis of size differences/sexual dimorphism. Gentoo penguins are
substantially heavier than Adelie and Chinstrap. App plot type:
`boxplot_or_violin_with_points` + pairwise statistics.

## Panel C — morphometric separation
Target: multivariate separation of species by body-size measurements. App plot
type: `pca_scatter_from_matrix` (PCA of the four z-scored morphometrics).

Note: the article's own figures include a study-site map and analyses beyond
these panels; we recreate only the data-backed morphometric panels that map to
Make My Figure plot types.
