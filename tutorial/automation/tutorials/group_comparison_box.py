"""Pilot: box / violin plot with points and a statistical test (group_comparison.csv)."""
TITLE = "Box / violin plot with points and statistics"
DATASETS = ["group_comparison.csv"]
PLOT = "boxplot_or_violin_with_points"


def run(drv, ctx):
    drv.open_file(ctx.dataset("group_comparison.csv"))
    ctx.fact("columns", drv.columns())
    ctx.fact("recommendation_header", drv.recommendation_header())
    ctx.fact("recommendation_cards", [c["title"] for c in drv.recommendation_cards()])
    drv.capture("01_open_data", "window")
    drv.select_plot(PLOT)
    ctx.fact("proposed_mapping", {k: w.currentText() for k, w in drv.mapping_widgets().items()})
    drv.set_mapping("x", "group")
    drv.set_mapping("y", "response")
    drv.update_preview()
    drv.scroll_to("mapping")
    drv.capture("02_mapping", "mapping")
    drv.capture("03_initial_plot", "window", "box plot with points")
    kinds = [drv.option_widgets()["kind"].itemText(i) for i in range(drv.option_widgets()["kind"].count())]
    ctx.fact("kind_choices", kinds)
    drv.set_option("kind", "violin")
    drv.set_option("point_size", 12)
    drv.set_labels(ylabel="Response (a.u.)", xlabel="")
    drv.update_preview()
    drv.scroll_to("options")
    drv.capture("04_customization", "options")
    drv.capture("04b_violin", "figure", "violin variant")
    drv.set_option("kind", "box")
    # statistics: all pairwise comparisons, Holm correction, exact P on the figure
    sp = drv.win.stats_panel
    ctx.fact("test_choices", [sp.test_combo.itemText(i) for i in range(sp.test_combo.count())])
    ctx.fact("comparison_choices", [sp.mode_combo.itemText(i) for i in range(sp.mode_combo.count())])
    ctx.fact("correction_choices", [sp.correction_combo.itemText(i) for i in range(sp.correction_combo.count())])
    ctx.fact("annotation_choices", [sp.annotation_combo.itemText(i) for i in range(sp.annotation_combo.count())])
    ctx.fact("suggested_test_note", getattr(sp, "suggestion_label", None).text() if getattr(sp, "suggestion_label", None) else "")
    drv.enable_statistics(test="welch_t", comparison="all_pairs", group_column="group",
                          correction="holm", annotation="p")
    drv.run_statistics()
    md = drv.result_metadata()
    ctx.fact("stats_metadata_keys", sorted(k for k in md if "stat" in k.lower()))
    ctx.fact("stats_method_sentence", drv.stats_panel_text()[:600])
    drv.scroll_to("stats")
    drv.capture("05_statistics", "stats", "statistics panel")
    drv.capture("05b_plot_with_brackets", "figure", "significance brackets")
    drv.export("png", ctx.out("box_stats.png"))
    drv.export("svg", ctx.out("box_stats.svg"))
    drv.capture("06_final_plot", "window", "final")
    ctx.fact("stats_table_rows", drv.stats_table_rows())
    drv.export_stats_table(ctx.out("box_stats_table.csv"))
    drv.export_method_report(ctx.out("box_methods.md"))
    drv.write_log()
