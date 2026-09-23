"""Pilot: your table does not need perfect column names (ambiguous_columns.csv)."""
TITLE = "Column mapping with ambiguous column names"
DATASETS = ["ambiguous_columns.csv"]


def run(drv, ctx):
    drv.capture("00_start_screen", "window", "start screen before any data")
    drv.open_file(ctx.dataset("ambiguous_columns.csv"))
    ctx.fact("columns", drv.columns())
    ctx.fact("detected_types", drv.detected_types_text())
    ctx.fact("recommendation_header", drv.recommendation_header())
    ctx.fact("recommendation_cards", drv.recommendation_cards())
    drv.capture("01_open_data", "window", "table loaded, no plot type chosen yet")
    drv.capture("01b_data_preview", "data", "the Data preview tab")

    # A. the app's own proposal for a group-comparison plot
    drv.select_plot("boxplot_or_violin_with_points")
    proposed = {k: w.currentText() for k, w in drv.mapping_widgets().items()}
    ctx.fact("box_proposed_mapping", proposed)
    drv.scroll_to("mapping")
    drv.capture("02_mapping_proposed", "mapping", "the roles the app proposed")
    drv.capture("02b_first_plot", "window", "figure drawn from the proposal")

    # B. the user disagrees: plot score_final instead, then swap the grouping column
    drv.set_mapping("y", "score_final")
    drv.update_preview()
    ctx.fact("box_mapping_after_change", drv.current_mapping())
    drv.capture("03_mapping_corrected", "mapping", "y changed to score_final")
    drv.capture("03b_plot_after_correction", "figure", "figure follows the new mapping")

    # C. a second plot from the same table: scatter of the two numeric columns
    drv.select_plot("scatterplot_with_regression")
    proposed_sc = {k: w.currentText() for k, w in drv.mapping_widgets().items()}
    ctx.fact("scatter_proposed_mapping", proposed_sc)
    drv.set_mapping("x", "measurement_2")
    drv.set_mapping("y", "score_final")
    drv.set_mapping("color", "condition_code")
    drv.set_mapping("label", "thing")
    ok = drv.update_preview()
    ctx.fact("scatter_options", list(drv.option_widgets()))
    drv.capture("04_scatter_mapping", "mapping", "same table, different roles")
    drv.capture("04b_scatter_plot", "window", "scatter with regression from the same file")

    # D. and a third: bar plot with error bars
    drv.select_plot("barplot_with_error_bar")
    drv.set_mapping("x", "condition_code")
    drv.set_mapping("y", "measurement_2")
    drv.update_preview()
    drv.capture("05_bar_plot", "window", "bar plot with error bars from the same file")
    ctx.fact("bar_proposed_error_option", drv.option_widgets()["error"].currentText() if "error" in drv.option_widgets() else None)

    # E. export the scatter version as PNG to show the workflow end
    drv.select_plot("scatterplot_with_regression")
    drv.set_mapping("x", "measurement_2"); drv.set_mapping("y", "score_final")
    drv.set_mapping("color", "condition_code")
    drv.update_preview()
    drv.export("png", ctx.out("ambiguous_scatter.png"))
    drv.export("svg", ctx.out("ambiguous_scatter.svg"))
    drv.capture("06_final", "figure", "final scatter")
    drv.write_log()
