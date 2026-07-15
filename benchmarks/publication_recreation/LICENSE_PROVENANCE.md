# License & provenance

Only permissively-licensed public data is used. No published figure images are stored.

| dataset | citation | DOI/source | data license | license URL | verified |
|---|---|---|---|---|---|
| penguins | Gorman KB, Williams TD, Fraser WR (2014) | 10.1371/journal.pone.0090081 | **CC0-1.0** | https://github.com/allisonhorst/palmerpenguins#license | palmerpenguins package states data released CC0 (with Palmer LTER attribution). |
| karate | Zachary WW (1977) | 10.1086/jar.33.4.3629752 | **Public-Domain** | https://networkx.org/documentation/stable/reference/generated/networkx.generators.social.karate_club_graph.html | Classic public-domain network; bundled in NetworkX (BSD-3). |
| iris | Fisher RA (1936) | 10.1111/j.1469-1809.1936.tb02137.x | **Public-Domain (CC BY 4.0 at UCI)** | https://archive.ics.uci.edu/dataset/53/iris | UCI ML Repository (CC BY 4.0); bundled in scikit-learn (BSD-3). |
| wine | Forina M, et al. (1991) | 10.24432/C5PC7J | **CC BY 4.0 (UCI)** | https://archive.ics.uci.edu/dataset/109/wine | UCI ML Repository (CC BY 4.0); bundled in scikit-learn (BSD-3). |
| diabetes | Efron B, Hastie T, Johnstone I, Tibshirani R (2004) | 10.1214/009053604000000067 | **Public / BSD-3 (scikit-learn)** | https://scikit-learn.org/stable/datasets/toy_dataset.html | Standard public regression dataset bundled in scikit-learn (BSD-3). |
| gapminder | Gapminder Foundation (2007) | https://www.gapminder.org/data/ | **CC-BY-4.0** | https://www.gapminder.org/free-material/ | Gapminder data released under CC BY 4.0 (gapminder.org free material). |

Raw downloads are cached under `datasets/<id>/raw/` (git-ignored). For network sources (Palmer Penguins, Gapminder) the direct data URL is recorded above and re-downloaded by `download_benchmark_assets.py`; scikit-learn / NetworkX datasets are bundled with those BSD-licensed libraries.
