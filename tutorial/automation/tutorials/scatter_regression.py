"""Pilot: scatter plot with regression (relationship_data.csv)."""
TITLE = "Scatter plot with regression line"
DATASETS = ["relationship_data.csv"]
PLOT = "scatterplot_with_regression"


def run(drv, ctx):
    drv.open_file(ctx.dataset("relationship_data.csv"))
    ctx.fact("columns", drv.columns())
    ctx.fact("recommendation_header", drv.recommendation_header())
    drv.capture("01_open_data", "window", "table loaded")
    drv.select_plot(PLOT)
    ctx.fact("proposed_mapping", {k: w.currentText() for k, w in drv.mapping_widgets().items()})
    drv.set_mapping("x", "expression_a")
    drv.set_mapping("y", "expression_b")
    drv.set_mapping("color", "cell_line")
    drv.set_mapping("label", None)
    drv.update_preview()
    drv.scroll_to("mapping")
    drv.capture("02_mapping", "mapping", "x, y, color roles")
    drv.capture("03_initial_plot", "window", "scatter with per-group regression lines")
    # customise: keep the regression line but show r and n, move the stats box
    ctx.fact("options", {k: (w.isChecked() if hasattr(w, "isChecked") else w.currentText() if hasattr(w, "currentText") else None)
                         for k, w in drv.option_widgets().items()})
    drv.set_option("show_r", True)
    drv.set_option("show_n", True)
    drv.set_option("fit_stats_loc", "upper left")
    drv.set_labels(title="", xlabel="Expression A (log2)", ylabel="Expression B (log2)")
    drv.update_preview()
    drv.scroll_to("options")
    drv.capture("04_customization", "options", "regression options")
    drv.capture("04b_customized_plot", "figure", "after customisation")
    # statistics panel: correlation for the same mapping
    drv.enable_statistics(test="spearman", annotation="p")
    drv.run_statistics()
    md = drv.result_metadata()
    ctx.fact("stats_metadata_keys", sorted(k for k in md if "stat" in k.lower()))
    ctx.fact("stats_method_sentence", drv.stats_panel_text()[:400]); ctx.fact("stats_table_rows", drv.stats_table_rows())
    drv.scroll_to("stats")
    drv.capture("05_statistics", "stats", "6. Statistics panel after Run statistics")
    drv.capture("05b_plot_with_stats", "figure", "figure after statistics")
    drv.export("pdf", ctx.out("scatter.pdf"))
    drv.export("png", ctx.out("scatter.png"))
    drv.capture("06_final_plot", "figure", "final")
    drv.write_log()
