# Internal‑standard & control‑feature normalization

For targeted assays (e.g. spiked internal standards / housekeeping controls), normalize
each sample by its internal‑standard signal. The app **never guesses** which features
are standards — you identify them.

## Two layouts (both supported, explicitly)

**A. Internal‑standard features (rows).** You provide the feature IDs of the internal
standards. Per sample, the IS factor = mean/median of those feature rows in that
sample; each sample column is then **divided** by its factor (or **subtracted**, when
the data are log‑scale) — a ratio‑to‑internal‑standard.
```python
normalization.internal_standard_features(df, spec, feature_ids=["IS_0","IS_1"],
                                         how="median", operation="divide")
```
It reports **IS stability** (coefficient of variation of the per‑sample factor) and
warns if the standards are unstable (CV > 50%).

**B. Internal‑standard columns.** If the layout stores IS measurements as separate
columns, you map them explicitly; a per‑feature IS reference (row‑wise mean/median
across the IS columns) divides/subtracts each value cell.
```python
normalization.internal_standard_columns(df, spec, is_columns=["IScol1"], how="median")
```

## Control / housekeeping features
`control_features(...)` uses the same mechanism with a control/housekeeping feature list
and reports control stability.

## Reference sample/group
`reference_sample(df, spec, reference="S1")` (or a group name with metadata) expresses
each sample relative to a reference — useful for fold‑relative views.

All of these produce a **named derived matrix** and are recorded as a
`PreprocessingStep` in the `PreprocessingSpec`, so the choice is reproducible and the
downstream method sentence reflects it. No R, no rpy2.
