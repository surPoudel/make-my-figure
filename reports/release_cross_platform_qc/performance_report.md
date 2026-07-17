# Performance report — cross-platform (WSL/Windows focus)

## Observation
The user reports Mac is faster than WSL/Ubuntu-on-Windows for the same data.

## Root causes (ranked)
1. **Filesystem**: the repo/data live under `/mnt/c` (a Windows drive mounted in WSL)
   inside a **OneDrive**-synced folder. `/mnt/c` I/O under WSL is dramatically slower
   than the native Linux filesystem, and OneDrive adds sync overhead on every write.
   This dominates load/export timing and is environmental, not app logic.
2. **Interactive recompute**: heavy work (QC diagnostics, PCA, sample-correlation,
   statistics, large heatmaps/networks) is expensive; recomputing it on every widget
   change would compound the filesystem cost.

## App-side mitigations already in place
- Expensive steps run behind explicit **Run diagnostics / Compute / Generate / Apply**
  buttons, not on every widget change.
- QC distribution plots subsample features (`_QC_MAX_FEATURES = 4000`).
- Network centrality metrics (betweenness/closeness/eigenvector) are capped to graphs
  ≤ 500 nodes.
- Statistics are vectorized (scipy/statsmodels/numpy), no per-feature Python loops for
  the two-group family; feature-differential summary uses column-block math.
- Exports are written on demand, not continuously.

## Guidance (documented in docs/CROSS_PLATFORM_QC.md)
- For active development, keep the repo **and** data on the WSL Linux filesystem
  (e.g. `~/dev/make_my_plot`), not `/mnt/c` or OneDrive.
- Run Streamlit with `--server.fileWatcherType none` on synced folders to stop the
  file watcher from thrashing on OneDrive/`/mnt/c`.
- These are guidance, not an excuse for unnecessary recomputation — the app gates
  heavy work behind explicit actions and caches by spec.

## Not measured in this session
Wall-clock numbers per workflow were **not** captured on Mac vs Windows vs WSL in this
session (single-platform sandbox). Re-run the QC harness on each OS and compare the
timestamps / manifest; add per-step timers if a specific workflow is still slow.
