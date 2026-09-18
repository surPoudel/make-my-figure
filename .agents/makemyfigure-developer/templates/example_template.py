# Builder for scripts/generate_example_data.py  (paste ABOVE the EXAMPLES list; keep it deterministic)
#
# Every builder receives a numpy Generator seeded per plot by the generator script and returns
# ``(primary_df, aux_df_or_None)``. Data are SYNTHETIC: plausible, clearly demonstrating the plot,
# never copied from a publication. Cover: several groups, unequal n, a realistic dynamic range.

def b___SLUG__(rng):
    groups = ["Control", "Treatment A", "Treatment B"]
    n_per = [8, 10, 7]                                   # unequal n on purpose
    rows = []
    for g, n, shift in zip(groups, n_per, (0.0, 0.8, 1.4)):
        vals = rng.normal(loc=1.0 + shift, scale=0.35, size=n).round(3)
        for i, v in enumerate(vals):
            rows.append({"group": g, "value": float(v), "batch": f"B{i % 2 + 1}"})
    return pd.DataFrame(rows), None


# Entry for the EXAMPLES list (adapt roles/columns; ``sheet`` must be unique and <= 31 chars):
#
# Example("__PLOT_TYPE__", "__SLUG__", "__SHEET__",
#         "__ONE_LINE_PURPOSE__",
#         b___SLUG__, ["group", "value"], ["batch"],
#         replace_help="Replace `group` with your condition column and `value` with the measurement.",
#         common_mistakes=["Wide (one column per group) instead of long format",
#                          "Summary rows (means) mixed with raw observations"]),
