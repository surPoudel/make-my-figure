# Volcano plot annotations (v0.5)

The volcano plot (`volcano_plot`) has a full, reproducible label-control system.
All settings live in the PlotSpec `mapping`, so an exported figure regenerates
identically.

## Master switch
- `annotate` (default `true`) — turn all labels/arrows on or off. With
  `annotate: false` only points, threshold lines, and the legend are drawn
  (`n_labeled = 0`).

## Label modes (`label_mode`)
| Mode | Behavior |
|---|---|
| `top_fdr` (default) | Label the top `top_n` features by smallest p / FDR |
| `top_lfc` | Label the top `top_n` by absolute log2 fold change |
| `top_up_down` | Label `top_n_up` up **and** `top_n_down` down separately |
| `selected` | Label only `selected_labels` |
| `pasted` | Label the genes in `label_list` (paste a gene list) |
| `significant_all` | Label all significant genes **only if** the count ≤ `max_labels_warn`; otherwise warn and fall back to top-N |

Explicitly `selected_labels` are always labeled regardless of mode.

## Which name & how many
- `label_by`: `symbol` (default), `id`, or `both` (uses `id_col` for the ID).
- `top_n` (default 10), `top_n_up` / `top_n_down` (default 8).
- `max_labels_warn` (default 40): if more labels are requested, the renderer
  warns (recommend fewer labels or a larger figure) and caps the count.

## Placement, arrows & styling
- `show_arrows` (default `true`): displaced labels are connected to their points
  with subtle publication-style arrows (via `adjustText` when available; a
  distance-based fallback otherwise). Set `false` for no connectors.
- `label_box` (default `false`): draw a background box behind each label.
- `label_color` (default: class color / text color), `label_font_size`
  (default: profile annotation size), `repel_strength` (adjustText expansion).
- The top margin auto-expands so labels are not clipped.

## Publication defaults
Subtle grey non-significant points; colorblind-safe up (red) / down (blue);
visible-but-not-overpowering threshold lines; legend outside the data area. When
`layout.subtitle` is unset and `auto_subtitle` is on (default), the subtitle is
built automatically: `Up: N | Down: N | FDR < c, |log2FC| >= c`.

## Demo variants (used in the QA gallery)
Applied as `mapping` overrides on the volcano example:
1. **Labels off** — `{"annotate": false}`
2. **Top up/down + arrows** — `{"label_mode": "top_up_down", "top_n_up": 6, "top_n_down": 6, "show_arrows": true}`
3. **Pasted gene list** — `{"label_mode": "pasted", "label_list": ["GENE001", "GENE050", "GENE123"]}`

## Limitations
`adjustText` repel is best-effort — with very many crowded labels some residual
overlap is possible; the renderer warns, caps at `max_labels_warn`, and
recommends fewer labels or a larger figure.

## Click to identify / label a point (desktop, v0.5)

On the desktop app's live figure, tick **"Click a point to identify / label it"**
(under *Labels & size*). Then, on a **volcano** or **scatter** plot:

- **Click near a point** → its name (gene symbol for volcano, sample id/label for
  scatter) and coordinates appear in the status bar — so you can see *which* point
  that blue dot at, say, `log2FC ≈ −4, −log10p ≈ 2` actually is.
- The click also **toggles a label** on that point. Labels you add are stored in
  the PlotSpec (`mapping.selected_labels`), so they **persist on export/reload**
  and are drawn on top of whatever label mode is active. Click the point again to
  remove its label.

How it works: each render emits a `pickable_points` table (data coords + name per
point) and a `pick_label_column`; the app maps your click to the nearest point.
Picks are kept per plot type and reset when you load new data.

**Limitations:** identify/label is an interactive desktop feature (the exported
SVG/PDF/PNG is static — only the labels you added persist). It currently covers
volcano and scatter; other plot types label **by name** (e.g. heatmap "highlight
gene list"). Drag-to-reposition a label/arrow is not implemented.

## Interactive labelling (shared model)

Volcano, MA, scatter and lollipop share one annotation model
(`make_my_figure_core/plots/annotation_state.py`): add / toggle (click again to
unlabel) / select / move / reset / delete. It serializes to the PlotSpec mapping the
renderers already consume — `selected_labels` (labelled points) and `label_offsets`
(JSON `{label: [dx, dy]}` in points, **only for manually moved labels**, so unmoved
labels keep auto-placement with leader lines). Moving one label never disturbs the
others, and offsets round-trip through the spec so manual placement persists on export.

- **Desktop:** click a point to label it, click again to unlabel; per-label offsets
  persist in the PlotSpec.
- **Streamlit** (static canvas): the sidebar "Label points (annotate)" expander is the
  click-to-label fallback — choose points, then move a selected label with x/y offset
  controls (Reset restores auto-placement).
