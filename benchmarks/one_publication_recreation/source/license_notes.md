# License & provenance notes

**Article:** Gorman KB, Williams TD, Fraser WR (2014) *PLoS ONE* 9(3):e90081,
DOI 10.1371/journal.pone.0090081. PLoS ONE articles are published under
**CC BY 4.0** — reuse/adaptation is permitted with attribution.

**Data:** the penguin body-size measurements originate from the Palmer Station
LTER (Gorman et al. 2014) and are distributed as a **CC0-1.0** (public-domain
dedication) tidied release via the `palmerpenguins` project. We download that
CC0 release (`raw_data/`, SHA-256 in `checksums.json`).

**What we store:** raw CC0 CSVs, our reproducible processed CSVs, PlotSpecs/
StatsSpecs, recreated panel images we generated, and QC/report text.

**What we do NOT store:** any figure image from the article. Although CC BY would
permit reuse with attribution, we deliberately keep only the citation, figure
number, and a textual target description (`figure_targets.md`) to avoid any
figure-copyright ambiguity. Consequently **no image-similarity** is computed;
visual QC is checklist-based against the legend.

**No claims of exact reproduction.** Recreations are labelled
"Publication-grade recreation" — scientifically traceable to the CC0 data and
visually publication-grade, not pixel-identical. Some analyses are standard
equivalents of (not identical to) the paper's models; differences are documented
per panel.
