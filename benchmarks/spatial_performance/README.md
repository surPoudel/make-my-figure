# Spatial workflow — performance

Measured on one machine (WSL2, Python 3.11, repo on a Windows-mounted filesystem).
**Timings are indicative, not a specification.** Stages are measured separately because
they scale differently, and an end-to-end average hides which one would hurt.

```bash
python run_benchmark.py                 # full sweep -> performance.csv
python scaling_check.py                 # complexity check -> scaling.csv
```

## Full workflow, by size

Seconds per stage. 167,780 cells is **real data** (Xenium Rep 1, Janesick et al. 2023);
the rest is synthetic tissue, which measures the software and not biology.

| Stage | 10k | 100k | **167,780 (real)** | 500k |
|---|---:|---:|---:|---:|
| Load CSV | 0.02 | 0.05 | **0.10** | 0.25 |
| Neighbour graph (kNN, k=10) | 0.03 | 0.38 | **0.84** | 2.46 |
| Local composition | 0.03 | 0.34 | **0.45** | 1.74 |
| CC neighbourhoods (k-means, 8 CNs) | 0.30 | 2.81 | **4.53** | 7.76 |
| CT-CN enrichment | 0.01 | 0.03 | **0.04** | 0.11 |
| Render categorical map | 0.11 | 0.70 | **1.24** | 2.93 |
| Export PNG | 0.20 | 0.68 | **0.81** | 1.86 |
| Export PDF | 0.19 | 0.92 | **1.28** | 3.20 |
| Export SVG | 0.22 | 0.97 | **1.39** | 3.20 |

**Analysis to figure at 500,000 cells: about 18 seconds.** Peak resident memory 766 MB.

### Transcripts

1,000,000 transcript points, **no subsampling**:

| Stage | Seconds |
|---|---:|
| Load CSV | 0.39 |
| Render transcript map | 5.33 |
| Export PNG | 3.14 |
| Export PDF | 6.11 |

## Complexity: measured, not asserted

The brief asks that default workflows avoid O(n²). "We use a k-d tree" is a claim, not
evidence, so `scaling_check.py` fits an exponent to observed timings:

| n | graph (s) | implied exponent |
|---:|---:|---:|
| 100,000 | 0.40 | 1.12 |
| 200,000 | 0.80 | 1.00 |
| 400,000 | 1.76 | 1.14 |

**Worst exponent 1.14** — near-linear. A brute-force all-pairs path would show ≈2.0, so
this check fails loudly if one ever creeps back in.

## Rasterisation: the honest reason

Dense marks are rasterised inside vector output while text, axes, legends and scale bars
stay vector. The usual justification is file size, and for SVG that holds — but **not for
PDF**:

| Points | Format | Vector | Rasterised |
|---:|---|---:|---:|
| 200,000 | SVG | 31.1 MB | **6.1 MB** |
| 200,000 | PDF | **3.1 MB** | 4.3 MB |

So rasterising makes SVG five times smaller and PDF slightly *larger*. The real reason to
rasterise is that a vector file containing 200,000 individual path objects is slow to
open, slow to scroll and awkward to edit, whichever way the byte count falls. Stating it
as a size win would be wrong, and is recorded here so nobody repeats the claim.

Rasterisation is controllable per figure (`spatial.rasterize`); transcript maps default to
on because they are dense by nature.

## What is expensive, and why

**k-means dominates** — 7.8 s of the 18 s at 500k cells, and it grows with the number of
neighbourhoods as well as the cell count. It is the one stage a user can make
arbitrarily slow by asking for many neighbourhoods, which is why the number is a user
decision the software never guesses.

Everything else is near-linear. Enrichment is trivial (0.11 s at 500k) because it is a
crosstab and a closed-form expression, not a loop.

## No silent subsampling

Nothing in these paths reduces the data on its own. `spatial.max_points` subsamples only
when asked, records the seed and the before/after counts in the figure metadata, and
warns. Above 2,000,000 transcripts the renderer warns that drawing will be slow rather
than quietly thinning the points.
