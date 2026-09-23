# Reshaping and derived columns - what the application can restructure

Make My Figure is not a spreadsheet editor. It offers a small set of restructuring steps,
each visible in the interface, and it always keeps the original table so you can go back
(**Revert to original data** appears next to the plot type after a reshape).

Source of this list: the current desktop application (`apps/desktop_app/grouping_panel.py`,
`matrix_wizard.py`, the recommendation cards). Nothing else is offered.

## 1. Edit cells in the Data preview

The first 50 rows of the **Data preview** tab are editable; the figure follows each edit. Use it
to fix a typo in a group label, not to enter data.

## 2. Define groups...

The **Define groups...** button opens a dialog with two tabs.

**Assign sample groups (wide matrix)** - for a feature-by-sample matrix: choose the *Feature id
column*, then assign each sample column to a group in the table (edit the *Group* column, or
**Auto-guess groups from names**). Then choose what the grouped table is for:

* *Bar / box / violin comparisons (long table)* - the matrix is reshaped to one row per
  (feature, sample) with a group column; optional *DE test* and *Features to include* (all, or
  only selected features);
* *Heatmap / PCA (keep the matrix + add a group color strip)* - the matrix stays as it is and
  the groups become a colour strip.

**Group by column values** - for a long table: choose a *Source column*, a *New group column
name*, and map each value to a group label (edit the *Group* column). This is how you derive a
grouping from a coded column (`C0`, `C1`, `C2` becomes `Control`, `Low`, `High`) or collapse
several values into fewer groups.

## 3. Recommendation cards that reshape

Some cards in **Recommended figures** reshape before plotting, and say so in green and red
text on the card, for example *Ridge of per-column distributions (reshape -> long)*:
"Reshapes your data and saves a new CSV, then plots it" / "Reshapes the data (wide -> long) and
saves <name>__long.csv". Clicking **Generate** performs the reshape, writes the new CSV next to
the original, loads it and draws. **Revert to original data** brings the original back.

The reshapes available this way are the three transforms of the core: wide-to-long,
correlation matrix (from selected numeric columns) and value counts (frequency of a
categorical column).

## 4. Matrix workflow...

For expression-like matrices the **Matrix workflow...** button opens a five-tab wizard:
*① Map columns* (Feature ID column, Feature display column, Value scale (you confirm), value
columns; **Confirm mapping**), *② Define groups* (assign value columns to groups, **Upload
metadata file...**, **Confirm groups**), *③ Preprocess (raw-like)* (**Run diagnostics**, QC plot
preview, recommended preprocessing that you choose, **Apply preprocessing -> use processed
matrix**, **Save before/after QC report...**, **Revert to raw matrix**), *④ Validation*, and
*⑤ Recommend & generate* (optional feature-level differential summary with Test, Correction,
Group A, Group B; recommended plots with **Open in plot editor** and **Quick preview**).
Recommendations there are advisory and nothing is applied without a click. The workflow has its
own tutorial and video (`14_Complete_Workflows/matrix_workflow.md`, planned after the pilot).

## When reshaping is useful

| you have | you want | use |
|---|---|---|
| one column per sample (wide) | box plot per group | Define groups > Assign sample groups > long table |
| a coded column (`C0`, `C1`) | readable group names | Define groups > Group by column values |
| several numeric columns | their distributions side by side | the ridge "reshape -> long" card |
| a raw count matrix | PCA / heatmap after normalisation | Matrix workflow |

Everything else - joins, formulas, pivoting beyond these - is done in your spreadsheet or
analysis tool before opening the file.
