"""Recompute one published Fig 3A value from the formula, using no project code.

    score(t, n) = log2((|C_n,t| + F(t)) / (|C_n| + 1)) - log2(F(t))       [Tao et al. 2024]
"""
import math, sys
import numpy as np, pandas as pd

raw = "raw/CRC_clusters_neighborhoods_markers.csv"
df = pd.read_csv(raw, usecols=["ClusterName", "neighborhood10"], low_memory=False)
keep = df[(df.neighborhood10 != 1) & (df.ClusterName != "dirt")]

N = len(keep)
F = keep.ClusterName.value_counts() / N                 # F(t), overall frequency
tab = pd.crosstab(keep.neighborhood10, keep.ClusterName)  # |C_n,t|
size = tab.sum(axis=1)                                   # |C_n|

mine = pd.DataFrame(
    {t: np.log2((tab[t] + F[t]) / (size + 1.0)) - np.log2(F[t]) for t in tab.columns})

s1 = pd.read_excel("raw/cntools_S1_Data.xlsx", sheet_name="Figure 3A", header=None)
l0, l1 = s1[0].ffill(), s1[1].ffill()
pub = s1.loc[(l0 == "CN Enrichment Score") & (l1 == "CC*"), s1.columns[2:]].astype(float).to_numpy()

print(f"cells={N}  neighbourhoods={tab.shape[0]}  cell types={tab.shape[1]}")
print(f"published block: {pub.shape}\n")

# The sheet is unlabelled, so find each of my values in the published block.
flat = np.sort(pub.ravel())
hits = 0
for t in list(tab.columns)[:6]:
    for n in list(tab.index)[:3]:
        v = mine.loc[n, t]
        j = np.searchsorted(flat, v)
        near = min(flat[max(0, j-1):j+2], key=lambda z: abs(z - v)) if len(flat) else np.nan
        d = abs(near - v)
        hits += d < 1e-9
        print(f"  CN {n:>1}  {t[:26]:<26} mine={v:>10.6f}  nearest published={near:>10.6f}  |d|={d:.2e}")
print(f"\n{hits}/18 spot-checked values found in the published sheet to <1e-9")
