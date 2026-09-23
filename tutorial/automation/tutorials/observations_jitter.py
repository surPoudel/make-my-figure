"""Showing individual observations and controlling jitter (showcase_group_comparison.csv).

Every step changes one control of '3. Options' on the same 40 observations; the figure is
captured after each change so the reader sees the effect. Ends with statistics, a publication
preset previewed and applied, and export.
"""
TITLE = "Showing individual observations and controlling jitter"
DATASETS = ["showcase_group_comparison.csv"]
PLOT = "boxplot_or_violin_with_points"


def _opts(drv):
    out = {}
    for k, w in drv.option_widgets().items():
        if hasattr(w, "isChecked") and not hasattr(w, "currentText"):
            out[k] = w.isChecked()
        elif hasattr(w, "currentText"):
            out[k] = w.currentText()
        elif hasattr(w, "value"):
            out[k] = w.value()
    return out


def run(drv, ctx):
    drv.open_file(ctx.dataset("showcase_group_comparison.csv"))
    ctx.fact("columns", drv.columns())
    ctx.fact("recommendation_header", drv.recommendation_header())
    drv.select_plot(PLOT)
    ctx.fact("proposed_mapping", {k: w.currentText() for k, w in drv.mapping_widgets().items()})
    drv.set_mapping("x", "group"); drv.set_mapping("y", "cytokine_pg_ml")
    drv.set_labels(ylabel="Cytokine (pg/ml)", xlabel="")
    drv.update_preview()
    ctx.fact("option_defaults", _opts(drv))
    ctx.fact("option_labels", {o.key: o.label for o in drv.win.controller.options(PLOT)})
    drv.scroll_to("options")
    drv.capture("01_defaults_options", "options", "3. Options as first shown")
    drv.capture("01b_defaults_plot", "figure", "default rendering: box, adaptive points")
    ctx.fact("group_n", drv.result_metadata().get("group_n"))

    # 1. observations off / on
    drv.set_option("points", False); drv.update_preview()
    drv.capture("02_points_off", "figure", "Show individual observations off")
    drv.set_option("points", True); drv.update_preview()
    # 2. jitter width
    drv.set_option("point_jitter_width", 0.10); drv.update_preview()
    drv.capture("03_jitter_narrow", "figure", "Jitter width 0.10")
    drv.set_option("point_jitter_width", 0.35); drv.update_preview()
    drv.capture("03b_jitter_default", "figure", "Jitter width 0.35")
    # 3. marker size
    drv.set_option("point_size", 60); drv.update_preview()
    drv.capture("04_point_size_60", "figure", "Point size 60 pt2")
    # 4. marker style: open circles with a coloured edge, then filled with a dark edge
    drv.set_option("point_fill", "open"); drv.set_option("point_edge", "same"); drv.set_option("point_edge_width", 1.2)
    drv.update_preview()
    drv.capture("05_open_circles", "figure", "open circles, edge in the group colour")
    drv.set_option("point_fill", "filled"); drv.set_option("point_edge", "dark"); drv.set_option("point_edge_width", 1.0)
    drv.update_preview()
    drv.capture("05b_filled_dark_edge", "figure", "filled, dark edge")
    # 5. arrangement
    drv.set_option("point_arrangement", "beeswarm"); drv.update_preview()
    drv.capture("06_beeswarm", "figure", "beeswarm arrangement")
    drv.set_option("point_arrangement", "jitter")
    # 6. box appearance and sample sizes
    drv.set_option("box_fill", "outline"); drv.set_option("show_n", "below"); drv.update_preview()
    drv.capture("07_box_outline_n_labels", "figure", "outline boxes, n below each group")
    drv.scroll_to("options")
    drv.capture("07b_options_after", "options", "3. Options after the changes")
    ctx.fact("options_after_changes", _opts(drv))
    # 7. statistics
    drv.enable_statistics(test="welch_t", comparison="all_pairs", group_column="group", correction="holm", annotation="p")
    drv.run_statistics()
    ctx.fact("stats_table_rows", drv.stats_table_rows())
    drv.capture("08_statistics_brackets", "figure", "Welch all pairs, Holm, exact P")
    drv.scroll_to("stats")
    drv.capture("08b_statistics_panel", "stats")
    # 8. publication preset: preview, then apply
    entries = drv.show_experimental_presets(True)
    ctx.fact("preset_entries", entries)
    info = drv.preview_preset("Box + observations (outline)", apply=True, capture_name="09_preview_dialog")
    ctx.fact("preview_changes", info.get("changes", "")[:1200])
    ctx.fact("preview_safety", info.get("safety"))
    ctx.fact("preview_buttons", info.get("buttons"))
    ctx.fact("preview_status", info.get("status"))
    drv.update_preview()
    ctx.fact("options_after_preset", _opts(drv))
    ctx.fact("stats_table_rows_after_preset", drv.stats_table_rows())
    drv.capture("10_after_preset", "figure", "after the preset")
    # 9. keep adjusting after the preset: it is a starting point
    drv.set_option("point_size", 40); drv.set_option("point_jitter_width", 0.25); drv.update_preview()
    drv.capture("11_adjusted_after_preset", "figure", "point size and jitter changed after the preset")
    drv.export("pdf", ctx.out("observations.pdf")); drv.export("svg", ctx.out("observations.svg")); drv.export("png", ctx.out("observations.png"))
    drv.capture("12_final", "window", "final state")
    drv.write_log()
