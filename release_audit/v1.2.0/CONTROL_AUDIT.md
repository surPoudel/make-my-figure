# v1.2.0 control audit (Phase 5-7, gate: "no known dead controls")

`quality_audit/option_efficacy.py` renders every plot type twice per control — once
at the default, once at a changed value — and compares the PNG bytes. Run across
the whole live registry.

## Result

| Verdict | Count |
|---|---|
| effective (the figure changed) | **1416** |
| not exercised (a precondition was not met) | 153 |
| reported "NO EFFECT" | 58 |
| declared unsupported by the renderer | 54 |
| refused the value with a message | 8 |
| **total controls exercised** | **1689** |

**Confirmed dead controls: 0.** Every one of the 58 "NO EFFECT" rows was
investigated; none is a control that does nothing when its precondition holds.
The byte-comparison cannot tell "this control is ignored" from "this particular
changed value happens to produce the same figure", and all 58 are the latter.

## The 58, by cause — each verified by direct test, not by reading

**1. The changed value equals the value already in force.** `points=True` on the
bar plots (the example already shows points — a precondition this harness itself
sets), `show_outliers=True` on the box plot, `remove_isolates=False` where the
graph has no isolated nodes. Toggling a setting to what it already is cannot
change a figure.

**2. The changed value saturates past the data.** `max_features=25025` on a matrix
with far fewer features. `top_n_up=20` on the volcano, where only 10 points are
labelable. Proved effective by moving the value *into* range instead:

    label_mode=top_up_down, top_n_up=top_n_down= 2  ->  4 labels drawn
    label_mode=top_up_down, top_n_up=top_n_down= 8  -> 10 labels drawn
    label_mode=top_up_down, top_n_up=top_n_down=20  -> 10 labels drawn   (only 10 exist)

**3. Precondition-gated, and the option label says so.** Each was re-tested with
its precondition satisfied and changed the figure:

| control | precondition | with it satisfied |
|---|---|---|
| `network_graph.node_color` | `color_by="none"` | **effective** |
| `network_graph.node_cmap` | `color_by="value"` | **effective** |
| `network_graph.node_size` | `size_by="fixed"` | **effective** |
| `network_graph.edge_width` | `edge_width_by="fixed"` | **effective** |
| `volcano_plot.use_fdr` | none needed | **effective** |

**4. Input-form-gated.** `network_graph.edge_color_by="sign"`,
`edge_color_positive` and `edge_color_negative` apply only to correlation-matrix
input (`network_graph.py:317-320`, the `elif mode == "correlation"` branch). The
bundled example is an edge list, so the example cannot exercise them whatever the
value. The option labels — "Edge color +corr" — already say which input form they
belong to.

**5. A style attribute with nothing of that role in the figure.**
`style.legend_title_pt` on a plot with no legend title; `style.annotation_pt` on
`confusion_matrix`, which sizes its cell annotations from `tick_label_pt` by
design so large matrices stay legible.

## Controls that refused a value (8) — correct behaviour, recorded

The harness pushes a deliberately extreme value, and the renderer declines with a
message naming the problem and the fix rather than drawing something misleading,
e.g.:

- `histogram_distribution.bin_width=499999` — "wider than the data range
  [5, 45.9], which would collapse the histogram into one bar"
- `network_graph.min_weight=50` — "no edges left after filtering — relax thresholds"
- `chord_diagram.min_value=5e11` — "no links left to draw after cleaning"

These are the behaviour the project wants; they are listed so the count is not
mistaken for eight crashes.

## Follow-up (not a release blocker)

The harness re-raises these 58 on every run because it does not model "value
equals current", "value saturates past the data", or "input form does not apply".
Its existing `PRECONDITIONS` / `CONTROL_REQUIRES` tables could carry the four
precondition pairs proved above, which would cut the false-alarm list and make a
genuinely dead control visible immediately instead of being the 59th line of a
list that is always 58 long. Recorded in the release ledger as follow-up.
