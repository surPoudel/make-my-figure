"""Master replay: most Make My Figure capabilities in ONE window, for a single long recording.

    python tutorial/automation/run_tutorial.py master_capabilities --onscreen --pause 1.5

Sequence (about 6-8 minutes at --pause 1.5; speed the recording up afterwards):
  1 start screen, Help
  2 a table with unhelpful headers: detected types, recommendation cards, the app's proposal
  3 correct one role; a scatter from the same table
  4 the showcase dataset: box + observations; jitter, size, fill, edge, beeswarm, n labels
  5 statistics: Welch pairs, Holm, exact P on brackets; export the table and the methods report
  6 publication preset: show experimental presets, Preview & apply, keep adjusting
  7 export PDF / SVG / PNG, PlotSpec, Figure Package; Home; reopen the package
  8 volcano: detected roles on DESeq2 names, then manual roles on renamed columns
  9 clustered heatmap: row id + value columns, row z-score
 10 Kaplan-Meier with log-rank P
 11 save panels, open the Figure Builder, save the composite and its package
Every step is a real widget action; each capture is a checkpoint for the narration script
(tutorial/video_scripts/master_from_data_to_figure.md).
"""
TITLE = "Master replay: from an ordinary table to a reproducible multi-panel figure"
DATASETS = ["ambiguous_columns.csv", "showcase_group_comparison.csv", "rnaseq_results.csv",
            "rnaseq_results_renamed.csv", "feature_sample_matrix.csv", "survival.csv", "relationship_data.csv"]


def run(drv, ctx):
    import os
    from PySide6.QtWidgets import QDialog, QMenu

    win = drv.win

    # ---------------------------------------------------------------- 1 start screen
    drv.capture("01_start_screen", "window", "start screen")
    drv.wait(1.0)
    orig = QDialog.exec

    def _exec(dlg, *a, **k):
        dlg.show(); drv.pump(20); drv.wait(2.0)
        drv._grab_widget(dlg, "01b_help", "Help dialog")
        dlg.hide()
        return QDialog.Rejected

    QDialog.exec = _exec
    try:
        win.action_help()
    finally:
        QDialog.exec = orig

    # ---------------------------------------------------------------- 2 bad headers
    drv.open_file(ctx.dataset("ambiguous_columns.csv"))
    ctx.fact("detected_types", drv.detected_types_text())
    ctx.fact("recommendation_header", drv.recommendation_header())
    drv.capture("02_ambiguous_table", "window", "table with unhelpful headers, recommendations")
    drv.wait(1.5)
    drv.select_plot("boxplot_or_violin_with_points")
    ctx.fact("box_proposal", {k: w.currentText() for k, w in drv.mapping_widgets().items()})
    drv.scroll_to("mapping")
    drv.capture("03_proposed_roles", "window", "the app's proposal")
    # ---------------------------------------------------------------- 3 correct, second plot
    drv.set_mapping("y", "score_final"); drv.update_preview()
    drv.capture("04_role_corrected", "window", "y changed by the researcher")
    drv.select_plot("scatterplot_with_regression")
    drv.set_mapping("x", "measurement_2"); drv.set_mapping("y", "score_final")
    drv.set_mapping("color", "condition_code"); drv.set_mapping("label", "thing")
    drv.update_preview()
    drv.capture("05_scatter_same_table", "window", "a scatter from the same table")
    drv.wait(1.0)

    # ---------------------------------------------------------------- 4 observations
    drv.open_file(ctx.dataset("showcase_group_comparison.csv"))
    drv.select_plot("boxplot_or_violin_with_points")
    drv.set_mapping("x", "group"); drv.set_mapping("y", "cytokine_pg_ml")
    drv.set_labels(ylabel="Cytokine (pg/ml)", xlabel="")
    drv.update_preview()
    ctx.fact("group_n", drv.result_metadata().get("group_n"))
    drv.scroll_to("options")
    drv.capture("06_default_box", "window", "default box with adaptive points")
    drv.set_option("points", False); drv.update_preview(); drv.wait(0.5)
    drv.set_option("points", True); drv.update_preview()
    drv.set_option("point_jitter_width", 0.10); drv.update_preview()
    drv.set_option("point_jitter_width", 0.35); drv.update_preview()
    drv.set_option("point_size", 60); drv.update_preview()
    drv.set_option("point_fill", "open"); drv.set_option("point_edge", "same"); drv.set_option("point_edge_width", 1.2)
    drv.update_preview()
    drv.capture("07_open_circles", "window", "open circles")
    drv.set_option("point_fill", "filled"); drv.set_option("point_edge", "dark"); drv.set_option("point_edge_width", 1.0)
    drv.update_preview()
    drv.set_option("point_arrangement", "beeswarm"); drv.update_preview(); drv.wait(0.5)
    drv.set_option("point_arrangement", "jitter")
    drv.set_option("box_fill", "outline"); drv.set_option("show_n", "below"); drv.update_preview()
    drv.capture("08_observations_styled", "window", "styled observations, n labels")

    # ---------------------------------------------------------------- 5 statistics
    drv.enable_statistics(test="welch_t", comparison="all_pairs", group_column="group",
                          correction="holm", annotation="p")
    drv.scroll_to("stats")
    drv.run_statistics()
    ctx.fact("stats_rows", drv.stats_table_rows())
    drv.capture("09_statistics", "window", "brackets with exact P; table; methods sentence")
    drv.export_stats_table(ctx.out("master_stats_table.csv"))
    drv.export_method_report(ctx.out("master_methods.md"))

    # ---------------------------------------------------------------- 6 publication preset
    drv.scroll_to("preset")
    drv.show_experimental_presets(True)
    drv.capture("10_experimental_presets", "window", "experimental presets listed")
    info = drv.preview_preset("Box + observations (outline)", apply=True, capture_name="11_preview_dialog")
    ctx.fact("preview_safety", info.get("safety")); ctx.fact("preview_status", info.get("status"))
    drv.update_preview()
    ctx.fact("stats_rows_after_preset", drv.stats_table_rows())
    drv.capture("12_after_preset", "window", "after the preset")
    drv.set_option("point_size", 40); drv.set_option("point_jitter_width", 0.25); drv.update_preview()
    drv.capture("13_adjusted_after_preset", "window", "still adjustable after the preset")

    # ---------------------------------------------------------------- 7 exports, package round trip
    drv.scroll_to("export")
    drv.export("pdf", ctx.out("master_box.pdf")); drv.export("svg", ctx.out("master_box.svg")); drv.export("png", ctx.out("master_box.png"))
    drv.export("json", ctx.out("master_box.plot_spec.json"))
    pkg = drv.save_package(ctx.out("master_box.mmfpackage"), capture_question="14_package_confirmation")
    drv.home(capture_question="15_home_question")
    drv.capture("16_start_screen_again", "window", "cleared")
    drv.open_package(pkg)
    ctx.fact("reopened_mapping", drv.current_mapping()); ctx.fact("reopened_status", win.statusBar().currentMessage())
    drv.capture("17_reopened_from_package", "window", "restored from the package alone")
    drv.wait(1.0)

    # ---------------------------------------------------------------- 8 volcano: detected, then manual
    drv.open_file(ctx.dataset("rnaseq_results.csv"))
    drv.select_plot("volcano_plot")
    ctx.fact("volcano_detected", {k: w.currentText() for k, w in drv.mapping_widgets().items()})
    drv.scroll_to("mapping")
    drv.capture("18_volcano_detected", "window", "DESeq2 names detected")
    drv.open_file(ctx.dataset("rnaseq_results_renamed.csv"))
    drv.select_plot("volcano_plot")
    ctx.fact("volcano_renamed_proposal", {k: w.currentText() for k, w in drv.mapping_widgets().items()})
    drv.capture("19_volcano_none", "window", "renamed columns: every role (none), Messages names the missing roles")
    drv.set_mapping("x", "effect_measure"); drv.set_mapping("p", "p_adjusted")
    drv.set_mapping("label", "name"); drv.set_mapping("id_col", "feature")
    drv.set_option("use_fdr", True); drv.set_option("top_n", 8)
    drv.set_labels(xlabel="log2 fold change", ylabel="-log10 adjusted P")
    drv.update_preview()
    drv.capture("20_volcano_manual", "window", "roles assigned by hand")
    drv.export("pdf", ctx.out("master_volcano.pdf"))

    # ---------------------------------------------------------------- 9 heatmap
    drv.open_file(ctx.dataset("feature_sample_matrix.csv"))
    drv.select_plot("heatmap_clustered_matrix")
    drv.set_mapping("row_id", "gene_symbol")
    drv.update_preview()
    drv.scroll_to("mapping")
    drv.capture("21_heatmap_values", "window", "row id + Value columns list")
    drv.set_option("scale", "row_zscore"); drv.set_option("cluster_columns", False); drv.update_preview()
    drv.capture("22_heatmap_zscore", "window", "row z-score, columns in file order")

    # ---------------------------------------------------------------- 10 Kaplan-Meier
    drv.open_file(ctx.dataset("survival.csv"))
    drv.select_plot("kaplan_meier_survival_curve")
    drv.set_mapping("time", "time_months"); drv.set_mapping("event", "event"); drv.set_mapping("group", "arm")
    drv.set_option("y_scale", "percent"); drv.set_labels(xlabel="Time (months)", ylabel="Survival (%)")
    drv.update_preview()
    drv.enable_statistics(test="logrank", group_column="arm", annotation="p")
    drv.run_statistics()
    ctx.fact("km_stats", drv.stats_table_rows())
    drv.capture("23_kaplan_meier_logrank", "window", "log-rank P on the figure")
    drv.save_panel()

    # ---------------------------------------------------------------- 11 panels and the builder
    drv.open_file(ctx.dataset("showcase_group_comparison.csv"))
    drv.select_plot("boxplot_or_violin_with_points")
    drv.set_mapping("x", "group"); drv.set_mapping("y", "cytokine_pg_ml")
    drv.set_option("box_fill", "outline"); drv.set_option("point_size", 40)
    drv.set_labels(ylabel="Cytokine (pg/ml)", xlabel="")
    drv.enable_statistics(test="welch_t", comparison="all_pairs", group_column="group", correction="holm", annotation="p")
    drv.run_statistics()
    drv.save_panel()
    drv.open_file(ctx.dataset("relationship_data.csv"))
    drv.select_plot("scatterplot_with_regression")
    drv.set_mapping("x", "expression_a"); drv.set_mapping("y", "expression_b"); drv.set_mapping("color", "cell_line")
    drv.set_labels(xlabel="Expression A (log2)", ylabel="Expression B (log2)")
    drv.update_preview()
    n = drv.save_panel()
    ctx.fact("panels_saved", n)
    drv.scroll_to("multipanel")
    drv.capture("24_three_panels_saved", "window", "three panels saved")
    res = drv.figure_builder(capture_name="25_figure_builder", save_figure=ctx.out("master_composite.png"),
                             save_package=ctx.out("master_composite.mmfpackage"))
    ctx.fact("composite_files", [os.path.basename(p) for p in res.get("figure_files", [])])
    drv.capture("26_end", "window", "end state")
    drv.write_log()
