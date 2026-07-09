# Statistical annotation formatting

After running statistics you have full control over what appears on the figure.
**Every displayed value comes from the stored StatsSpec result** — the figure can
hide values, but the exported StatsSpec always retains them.

## Content modes

Choose from the **Annotation shows** dropdown (desktop) / selectbox (Streamlit):

| Mode | Example |
|------|---------|
| Stars only | `*`, `**`, `***`, `****`, `n.s.` |
| P-value only | `p = 0.023` |
| Adjusted p-value only | `q = 0.041` |
| P-value + stars | `p = 0.023 (*)` |
| Statistic only | `t = 2.43`, `F = 8.12`, `U = 34`, `W = 12`, `χ² = 5.71`, `HR = 1.82` |
| Effect size only | `g = 0.71`, `d = 0.64`, `r = 0.42`, `η² = 0.18`, `OR = 2.10` |
| P-value + statistic | `t = 2.43, p = 0.023` |
| P-value + effect size | `g = 0.71, p = 0.023` |
| Full compact | `Welch t = 2.43, g = 0.71, p = 0.023` |
| Custom (checkboxes) | any combination of the show-flags below |
| Custom template | your own `{token}` string |

## Custom template tokens

All value tokens are **bare** (no `p =` prefix, no symbol), so you compose freely:

| Token | Value |
|-------|-------|
| `{p}` | raw p-value (`0.023`, `<0.001`, `1.2e-05`) |
| `{p_adj}` | adjusted p-value |
| `{stars}` | significance stars / `n.s.` |
| `{stat_symbol}` / `{stat}` | statistic symbol (`t`) / value (`2.43`) |
| `{effect_symbol}` / `{effect}` | effect symbol (`g`) / value (`0.71`) |
| `{ci}` | confidence interval `[lo, hi]` |
| `{test_short}` | short test name (`Welch`) |
| `{n}` | total sample size |
| `{comparison}` | e.g. `A vs B` |

Examples: `{stars}` · `p = {p}` · `{effect_symbol} = {effect}, p = {p}`.

## Formatting controls

- p-value decimals; scientific-notation threshold; `p < 0.001` style vs exact.
- statistic digits; effect-size digits.
- `n.s.` vs `ns` for nonsignificant.
- **Hide non-significant annotations** — drops them from the figure while
  keeping every comparison in the exported StatsSpec.

## Guarantee

The renderer only reads stored `StatResult` values; it never recomputes a
statistic. Hiding a value on the figure does not remove it from the
`*.stats_spec.json` sidecar, so the full results remain reproducible.
