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
