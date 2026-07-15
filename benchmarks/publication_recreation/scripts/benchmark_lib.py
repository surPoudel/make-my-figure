"""Core library for the license-safe publication-recreation benchmark.

Each benchmark takes a REAL, permissively-licensed public dataset (CC0 / CC BY /
public-domain / BSD), curates it reproducibly, and recreates a representative
publication-style panel through Make My Figure's normal render path
(`registry.render` + the built-in ``publication`` style). Every value drawn is
traceable to a source column or a documented computation.

We deliberately DO NOT download or store any published figure image (to avoid all
figure-copyright risk); the "target" is a textual panel description and QC is
checklist-based. Recreations are described as "publication-grade / scientifically
traceable", never "exact reproductions".

Raw downloads live under ``datasets/<id>/raw/`` (git-ignored); curated CSVs under
``datasets/<id>/processed/`` (committed, small). Outputs under
``recreated_panels/<id>/``.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
BENCH_DIR = os.path.join(ROOT, "benchmarks", "publication_recreation")
DATASETS_DIR = os.path.join(BENCH_DIR, "datasets")
PANELS_DIR = os.path.join(BENCH_DIR, "recreated_panels")
REPORTS_DIR = os.path.join(BENCH_DIR, "reports")

# --- dataset acquisition (real, license-verified public sources) ------------


@dataclass
class Dataset:
    id: str
    title: str
    authors: str
    year: int
    doi: str
    source_url: str          # article / dataset landing page
    data_url: str            # direct data URL, or "builtin:<loader>"
    data_license: str        # SPDX-ish id
    license_url: str
    license_verified: str    # how we verified the license
    notes: str = ""

    def raw_dir(self) -> str:
        return os.path.join(DATASETS_DIR, self.id, "raw")

    def acquire(self, offline_ok: bool = True) -> Optional[pd.DataFrame]:
        """Return the raw dataframe, downloading/caching as needed.

        Network downloads are wrapped so an offline run skips gracefully
        (returns None) rather than failing.
        """
        os.makedirs(self.raw_dir(), exist_ok=True)
        if self.data_url.startswith("builtin:"):
            return self._load_builtin(self.data_url.split(":", 1)[1])
        cache = os.path.join(self.raw_dir(), "raw.csv")
        if not os.path.exists(cache):
            try:
                import requests
                r = requests.get(self.data_url, timeout=30)
                r.raise_for_status()
                with open(cache, "wb") as fh:
                    fh.write(r.content)
            except Exception as exc:  # offline / transient — skip gracefully
                if offline_ok:
                    print(f"  [skip] {self.id}: download unavailable ({exc})")
                    return None
                raise
        return pd.read_csv(cache)

    @staticmethod
    def _load_builtin(name: str) -> pd.DataFrame:
        if name == "karate":
            import networkx as nx
            g = nx.karate_club_graph()
            return pd.DataFrame([(u, v) for u, v in g.edges()], columns=["source", "target"])
        from sklearn import datasets as skd
        loader = {"iris": skd.load_iris, "wine": skd.load_wine,
                  "diabetes": skd.load_diabetes,
                  "breast_cancer": skd.load_breast_cancer}[name]
        b = loader()
        df = pd.DataFrame(b.data, columns=[c.strip().replace(" ", "_") for c in b.feature_names])
        if hasattr(b, "target"):
            df["target"] = b.target
            if getattr(b, "target_names", None) is not None and name != "diabetes":
                df["target_name"] = [b.target_names[i] for i in b.target]
        return df


DATASETS: Dict[str, Dataset] = {
    "penguins": Dataset(
        id="penguins",
        title="Ecological sexual dimorphism ... Pygoscelis penguins (Palmer Archipelago)",
        authors="Gorman KB, Williams TD, Fraser WR",
        year=2014, doi="10.1371/journal.pone.0090081",
        source_url="https://doi.org/10.1371/journal.pone.0090081",
        data_url="https://raw.githubusercontent.com/allisonhorst/palmerpenguins/main/inst/extdata/penguins.csv",
        data_license="CC0-1.0",
        license_url="https://github.com/allisonhorst/palmerpenguins#license",
        license_verified="palmerpenguins package states data released CC0 (with Palmer LTER attribution).",
        notes="Data CC0; underlying study CC BY 4.0."),
    "karate": Dataset(
        id="karate", title="An Information Flow Model for Conflict and Fission in Small Groups",
        authors="Zachary WW", year=1977, doi="10.1086/jar.33.4.3629752",
        source_url="https://www.jstor.org/stable/3629752",
        data_url="builtin:karate", data_license="Public-Domain",
        license_url="https://networkx.org/documentation/stable/reference/generated/networkx.generators.social.karate_club_graph.html",
        license_verified="Classic public-domain network; bundled in NetworkX (BSD-3).",
        notes="34 nodes, 78 edges."),
    "iris": Dataset(
        id="iris", title="The use of multiple measurements in taxonomic problems",
        authors="Fisher RA", year=1936, doi="10.1111/j.1469-1809.1936.tb02137.x",
        source_url="https://archive.ics.uci.edu/dataset/53/iris",
        data_url="builtin:iris", data_license="Public-Domain (CC BY 4.0 at UCI)",
        license_url="https://archive.ics.uci.edu/dataset/53/iris",
        license_verified="UCI ML Repository (CC BY 4.0); bundled in scikit-learn (BSD-3).",
        notes="150 samples, 3 species."),
    "wine": Dataset(
        id="wine", title="Wine recognition data (UCI)",
        authors="Forina M, et al.", year=1991, doi="10.24432/C5PC7J",
        source_url="https://archive.ics.uci.edu/dataset/109/wine",
        data_url="builtin:wine", data_license="CC BY 4.0 (UCI)",
        license_url="https://archive.ics.uci.edu/dataset/109/wine",
        license_verified="UCI ML Repository (CC BY 4.0); bundled in scikit-learn (BSD-3).",
        notes="178 samples, 13 features, 3 cultivars."),
    "diabetes": Dataset(
        id="diabetes", title="Least Angle Regression (diabetes data)",
        authors="Efron B, Hastie T, Johnstone I, Tibshirani R", year=2004,
        doi="10.1214/009053604000000067",
        source_url="https://www4.stat.ncsu.edu/~boos/var.select/diabetes.html",
        data_url="builtin:diabetes", data_license="Public / BSD-3 (scikit-learn)",
        license_url="https://scikit-learn.org/stable/datasets/toy_dataset.html",
        license_verified="Standard public regression dataset bundled in scikit-learn (BSD-3).",
        notes="442 samples; standardized features."),
    "gapminder": Dataset(
        id="gapminder", title="Gapminder (life expectancy, GDP per capita, population)",
        authors="Gapminder Foundation", year=2007, doi="",
        source_url="https://www.gapminder.org/data/",
        data_url="https://raw.githubusercontent.com/plotly/datasets/master/gapminderDataFiveYear.csv",
        data_license="CC-BY-4.0",
        license_url="https://www.gapminder.org/free-material/",
        license_verified="Gapminder data released under CC BY 4.0 (gapminder.org free material).",
        notes="Country-year panel; we use year 2007."),
}


# --- benchmark panel definitions --------------------------------------------


@dataclass
class Benchmark:
    id: str
    dataset: str
    plot_type: str
    figure_panel: str          # textual target-panel description
    target_description: str
    curate: Callable[[pd.DataFrame], Dict[str, pd.DataFrame]]  # raw -> {"data":df, "metadata":df?}
    mapping: Dict[str, Any]
    layout: Dict[str, Any] = field(default_factory=dict)
    statistics: Optional[Dict[str, Any]] = None
    transforms: str = ""       # human description of curation transforms
    aux_key: Optional[str] = None   # key in curate() output to pass as aux "metadata"

    def dir(self) -> str:
        return os.path.join(PANELS_DIR, self.id)

    def proc_dir(self) -> str:
        return os.path.join(DATASETS_DIR, self.dataset, "processed")


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


# ---- curation functions (deterministic; raw unchanged) ----

def _cur_penguins_scatter(df):
    d = df.dropna(subset=["bill_length_mm", "bill_depth_mm", "species"]).copy()
    return {"data": d[["species", "island", "bill_length_mm", "bill_depth_mm",
                       "flipper_length_mm", "body_mass_g"]]}


def _cur_penguins_box(df):
    d = df.dropna(subset=["body_mass_g", "species"]).copy()
    d["species"] = pd.Categorical(d["species"], ["Adelie", "Chinstrap", "Gentoo"])
    return {"data": d[["species", "body_mass_g"]].sort_values("species").reset_index(drop=True)}


def _cur_penguins_pca(df):
    d = df.dropna(subset=["bill_length_mm", "bill_depth_mm", "flipper_length_mm",
                          "body_mass_g", "species"]).reset_index(drop=True)
    d["sample_id"] = [f"P{i:03d}" for i in range(len(d))]
    feats = ["bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g"]
    matrix = d[["sample_id"] + feats].set_index("sample_id").T.reset_index()
    matrix = matrix.rename(columns={"index": "feature"})
    meta = d[["sample_id", "species", "island"]].rename(columns={"species": "group", "island": "batch"})
    return {"data": matrix, "metadata": meta}


def _cur_penguins_heatmap(df):
    feats = ["bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g"]
    d = df.dropna(subset=feats + ["species"])
    means = d.groupby("species")[feats].mean()
    z = (means - means.mean()) / means.std(ddof=0)
    m = z.T.reset_index().rename(columns={"index": "feature"})
    return {"data": m}


def _cur_karate(df):
    return {"data": df.copy()}


def _cur_penguins_forest(df):
    feat = "body_mass_g"
    d = df.dropna(subset=[feat, "species"])
    rows = []
    for sp, g in d.groupby("species"):
        m = g[feat].mean(); se = g[feat].std(ddof=1) / np.sqrt(len(g))
        rows.append({"subgroup": sp, "mean_body_mass_g": round(m, 1),
                     "ci_low": round(m - 1.96 * se, 1), "ci_high": round(m + 1.96 * se, 1),
                     "n": len(g)})
    return {"data": pd.DataFrame(rows)}


def _iris_predictions():
    from sklearn.datasets import load_iris
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_predict
    b = load_iris()
    X, y = b.data, b.target
    clf = LogisticRegression(max_iter=2000)
    proba = cross_val_predict(clf, X, y, cv=5, method="predict_proba")
    pred = proba.argmax(1)
    names = b.target_names
    return X, y, proba, pred, names


def _cur_iris_binary(df):
    # versicolor(1) vs virginica(2): a non-trivial, realistic ROC/PR/calibration.
    X, y, proba, pred, names = _iris_predictions()
    mask = np.isin(y, [1, 2])
    true = (y[mask] == 2).astype(int)                 # positive = virginica
    score = proba[mask][:, 2] / (proba[mask][:, 1] + proba[mask][:, 2] + 1e-12)
    out = pd.DataFrame({"true_label": true, "score_model_a": score,
                        "predicted_prob": score})
    return {"data": out}


def _cur_iris_confusion(df):
    X, y, proba, pred, names = _iris_predictions()
    out = pd.DataFrame({"true_label": [names[i] for i in y],
                        "predicted_label": [names[i] for i in pred]})
    return {"data": out}


def _cur_wine_pca(df):
    from sklearn.datasets import load_wine
    b = load_wine()
    feats = [c.strip().replace(" ", "_") for c in b.feature_names]
    X = pd.DataFrame(b.data, columns=feats)
    X["sample_id"] = [f"W{i:03d}" for i in range(len(X))]
    matrix = X.set_index("sample_id")[feats].T.reset_index().rename(columns={"index": "feature"})
    meta = pd.DataFrame({"sample_id": X["sample_id"],
                         "group": [f"cultivar_{b.target[i]+1}" for i in range(len(X))]})
    return {"data": matrix, "metadata": meta}


def _cur_diabetes_scatter(df):
    from sklearn.datasets import load_diabetes
    b = load_diabetes()
    d = pd.DataFrame(b.data, columns=b.feature_names)
    d["disease_progression"] = b.target
    return {"data": d[["bmi", "bp", "disease_progression"]]}


def _cur_gapminder_scatter(df):
    d = df[df["year"] == 2007].copy()
    d["log10_gdpPercap"] = np.log10(d["gdpPercap"])
    return {"data": d[["country", "continent", "gdpPercap", "log10_gdpPercap",
                       "lifeExp", "pop"]].reset_index(drop=True)}


BENCHMARKS: List[Benchmark] = [
    Benchmark("penguins_scatter", "penguins", "scatterplot_with_regression",
              "Fig: bill length vs bill depth by species (Simpson's paradox).",
              "Scatter of bill_length_mm (x) vs bill_depth_mm (y), colored by species, "
              "with per-relationship regression line and correlation annotation.",
              _cur_penguins_scatter,
              {"x": "bill_length_mm", "y": "bill_depth_mm", "color": "species", "fit_line": True},
              layout={"x_label": "Bill length (mm)", "y_label": "Bill depth (mm)"},
              transforms="Drop rows with missing bill/species; keep morphometric columns."),
    Benchmark("penguins_box", "penguins", "boxplot_or_violin_with_points",
              "Fig: body mass distribution by species with group comparison.",
              "Box + points of body_mass_g by species with Kruskal-Wallis + Dunn pairwise "
              "annotations (BH-corrected).",
              _cur_penguins_box,
              {"x": "species", "y": "body_mass_g", "kind": "box", "points": True},
              layout={"x_label": "Species", "y_label": "Body mass (g)"},
              statistics={"enabled": True, "test": "kruskal_wallis",
                          "comparison_mode": "all_pairs", "correction": "bh"},
              transforms="Drop missing body_mass; order species Adelie<Chinstrap<Gentoo."),
    Benchmark("penguins_pca", "penguins", "pca_scatter_from_matrix",
              "Fig: PCA of morphometrics separating species.",
              "PCA scatter from a 4-feature x N-sample matrix, colored by species, shaped by island.",
              _cur_penguins_pca,
              {"matrix_row_id": "feature", "metadata_key": "sample_id",
               "color": "group", "shape": "batch"},
              aux_key="metadata",
              transforms="Features x samples matrix from 4 morphometrics; metadata=species/island."),
    Benchmark("penguins_heatmap", "penguins", "heatmap_clustered_matrix",
              "Fig: z-scored morphometric means by species (clustered heatmap).",
              "Clustered heatmap of per-species mean morphometrics, z-scored per feature.",
              _cur_penguins_heatmap,
              {"row_id": "feature", "cluster_rows": True, "cluster_columns": True,
               "color_scale": "diverging"},
              transforms="Per-species feature means, z-scored across species per feature."),
    Benchmark("penguins_forest", "penguins", "forest_plot",
              "Fig: mean body mass by species with 95% CI (forest).",
              "Forest plot of per-species mean body_mass_g with 95% confidence intervals "
              "(reference at the overall mean).",
              _cur_penguins_forest,
              {"label": "subgroup", "estimate": "mean_body_mass_g",
               "lower": "ci_low", "upper": "ci_high", "reference": 4200.0},
              layout={"x_label": "Mean body mass (g)"},
              transforms="Per-species mean +/- 1.96*SE (normal 95% CI); reference=overall mean."),
    Benchmark("karate_network", "karate", "network_graph",
              "Fig: Zachary karate club social network.",
              "Undirected social network from the 78-edge karate club edge list, spring layout.",
              _cur_karate,
              {"source": "source", "target": "target", "layout": "spring", "seed": 42},
              transforms="Edge list from networkx.karate_club_graph()."),
    Benchmark("iris_roc", "iris", "roc_curve",
              "Fig: ROC for versicolor-vs-virginica classification.",
              "ROC curve (+AUC) from 5-fold cross-validated logistic-regression probabilities.",
              _cur_iris_binary,
              {"label": "true_label", "score": "score_model_a"},
              transforms="LogisticRegression (OvR, 5-fold cross_val_predict); positive=virginica."),
    Benchmark("iris_pr", "iris", "precision_recall_curve",
              "Fig: precision-recall for versicolor-vs-virginica.",
              "Precision-recall curve (+AUPRC) from the same cross-validated probabilities.",
              _cur_iris_binary,
              {"label": "true_label", "score": "score_model_a"},
              transforms="Same prediction table as iris_roc."),
    Benchmark("iris_confusion", "iris", "confusion_matrix",
              "Fig: 3-class confusion matrix.",
              "Confusion matrix of true vs predicted species (5-fold CV predictions).",
              _cur_iris_confusion,
              {"true": "true_label", "predicted": "predicted_label", "normalize": "true"},
              transforms="Row-normalized; labels are species names."),
    Benchmark("iris_calibration", "iris", "calibration_plot",
              "Fig: reliability curve for the virginica probability.",
              "Calibration/reliability curve of predicted probability vs observed frequency (10 bins).",
              _cur_iris_binary,
              {"label": "true_label", "prob": "predicted_prob", "n_bins": 8},
              transforms="Predicted virginica probability vs observed fraction."),
    Benchmark("wine_pca", "wine", "pca_scatter_from_matrix",
              "Fig: PCA of wine chemistry separating cultivars.",
              "PCA scatter from a 13-feature x 178-sample matrix, colored by cultivar.",
              _cur_wine_pca,
              {"matrix_row_id": "feature", "metadata_key": "sample_id", "color": "group"},
              aux_key="metadata",
              transforms="13 chemical features x samples matrix; metadata=cultivar."),
    Benchmark("diabetes_scatter", "diabetes", "scatterplot_with_regression",
              "Fig: disease progression vs BMI.",
              "Scatter of standardized BMI (x) vs one-year disease progression (y) with "
              "regression line and correlation.",
              _cur_diabetes_scatter,
              {"x": "bmi", "y": "disease_progression", "fit_line": True},
              layout={"x_label": "BMI (standardized)", "y_label": "Disease progression"},
              transforms="scikit-learn diabetes; BMI vs target."),
    Benchmark("gapminder_scatter", "gapminder", "scatterplot_with_regression",
              "Fig: life expectancy vs income (2007), by continent.",
              "Scatter of log10 GDP per capita (x) vs life expectancy (y) colored by continent, "
              "with regression + correlation (Preston-curve style).",
              _cur_gapminder_scatter,
              {"x": "log10_gdpPercap", "y": "lifeExp", "color": "continent", "fit_line": True},
              layout={"x_label": "log10 GDP per capita (2007 US$)", "y_label": "Life expectancy (years)"},
              transforms="Filter year==2007; log10 of gdpPercap."),
]
