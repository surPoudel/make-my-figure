# Spatial v2 — implementation plan

Branch `feature/spatial-v2`, cut from `main` at `05c4fc1` (v1.1.1 line). Not for merge or tag.

## 1. Audit findings that determine the design

Verified against the code, not assumed:

| Question | Finding | Consequence |
|---|---|---|
| Is `plot_type` constrained? | free string, no `enum` | new plot types need no schema change |
| Does PlotSpec reject unknown top-level keys? | no — `additionalProperties` unset, extra block accepted | a `spatial` block is a backward-compatible extension point |
| Is `mapping` closed? | open (`string|number|boolean|null|array`) | spatial mappings fit without schema surgery |
| Renderer contract | `render(spec, df, style) -> RenderResult`, module-level `PLOT_TYPE` | new renderers plug in unchanged |
| Registry shape | three parallel dicts in `plots/registry.py` (`_RENDERERS`, `_DEFAULT_MAPPINGS`, `_DISPLAY_NAMES`), 39 entries | additive registration |
| Analysis-record precedent | `MatrixSpec` / `StatsReport` dataclasses with `to_dict`/`from_dict` | `SpatialSpec` follows the same shape, not a new paradigm |
| Schema detection | `SCHEMAS` tuple + `detect_schema()` returning a string | spatial schemas are new return values |

Empirical check already run: a PlotSpec carrying an unknown `spatial` block and an unregistered
`plot_type` both validate. So v1.1.1 specs stay readable and no schema version bump is required.

## 2. Published methods — transcribed from the papers, not paraphrased

**CNTools (Tao et al. 2024, PLOS Comp Biol, CC-BY).**

* CC neighbourhood identification: "represents each cell by the CT frequencies among its nearest
  *m* neighbours **including itself** and then clusters cells into CNs using k-means."
* CT enrichment of cell type `t` in neighbourhood `n`:
  `log2((|C_n,t| + F(t)) / (|C_n| + 1)) - log2(F(t))`, where `F(t)` is the overall frequency of `t`.
* Differential CT enrichment: `log2 F^d_n(t) = b0 + b1 * 1[d in D] + b2 * log2 F^d(t)`, fitted per
  (cell type, neighbourhood) with **donor `d` as the observational unit**.
* Purity: `H(CT|CN) = sum_{n,t} |C_n,t|/|C| * log2(|C_n|/|C_n,t|)`.
* CRC experiment setting: CC with `m = 10`; dirt cells discarded before identification; 9 CNs.

**Janesick et al. 2023 (Nat Commun).** Fig. 2c marker genes are "log2(normalized UMI counts)";
scale bar 1 mm. The exact Space Ranger / Loupe normalisation is **not** fully specified in the
paper, which constrains what may be called an exact reproduction (see §5).

## 3. Scope decisions

New registered plot types — added only where geometry, data mapping or controls genuinely differ
from an existing renderer:

1. `spatial_categorical_map` — cells/spots by x/y, coloured by a discrete annotation.
2. `spatial_feature_map` — continuous value, colourbar, explicit normalisation.
3. `spatial_transcript_map` — per-transcript points, gene colours, optional context.
4. `spatial_roi_map` — polygon outlines/fills over spatial or image background.
5. `spatial_composition_map` — pie/donut glyphs at spot positions (Janesick Fig. 5i concept).
6. `neighborhood_enrichment_matrix` — colour = enrichment, point size = frequency (CNTools Fig. 3A).

39 -> 45. Deliberately **reused** rather than duplicated:

* neighbourhood assignment maps reuse `spatial_categorical_map` (same geometry, different column);
* differential enrichment reuses `heatmap` where its semantics already fit;
* ROI composition summaries reuse `stacked` / `grouped_barplot`;
* inter-CN communication reuses `network_graph`.

Cell-boundary/segmentation map is **deferred** — §4 of the brief forbids shipping a fragile
implementation for count, and robust polygon segmentation needs a vertex-table contract that the
validation datasets do not exercise.

## 4. Deliberate exclusions (with reasons, per §7D and §7I)

* **CNE** — implementable from Eqs 4–8, but validating it requires matching CNTools' own outputs
  on a published dataset; without that comparison it would be an unvalidated method wearing a
  published name. Excluded from v2.0.
* **Spatial LDA, ClusterNet, GAP, HMRF smoothing** — same standard, more moving parts.
* **Tensor decomposition, inter-CN CCA, CN combination maps, assembly rules** — out of first pass.
* **LIANA ligand-receptor inference** — availability in a tutorial is not a reason to add it to core.

## 5. Reproduction honesty

Janesick Fig. 2c will be classified a **scientific recreation**, not an exact analytical
reproduction, unless the deposited processed matrix yields the published values under a
documented transformation. Any gap gets stated in the audit table rather than closed by inventing
a normalisation.

CNTools Fig. 3A is the **exact** numerical target: S1 Data carries the underlying values, so
agreement should be to floating-point tolerance.

## 6. Licensing posture

* CNTools paper + S1 Data: PLOS **CC-BY** — redistributable with attribution.
* CNTools source: independent implementation from the published equations; no code vendored.
* Janesick / 10x data: restrictive terms. **Download + preparation scripts with checksums only**;
  no raw or derived 10x data committed unless terms are confirmed to permit it.
* CRC dataset (Schürch et al., Mendeley): licence to be checked before any derived file is committed.

## 7. Order of work

1. Baseline recorded, branch cut. *(done)*
2. `SpatialSpec` + neighbour graph + local composition + enrichment, with independent validation.
3. Renderers, one at a time: implement -> unit test -> render -> inspect -> fix.
4. Schema detection + recommendations.
5. Figure Package / round-trip / tamper tests.
6. Published-data benchmarks (CNTools first — it is the exact target).
7. GUI wiring, both apps on the same core.
8. Performance, documentation, `SPATIAL_V2_VALIDATION.md`, gate report.
