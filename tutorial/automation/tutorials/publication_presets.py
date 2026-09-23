"""Publication presets: the experimental library, Preview & apply, before / after, keep adjusting."""
TITLE = "Publication presets: preview, apply, keep adjusting"
DATASETS = ["showcase_group_comparison.csv"]
PLOT = "boxplot_or_violin_with_points"


def run(drv, ctx):
    drv.open_file(ctx.dataset("showcase_group_comparison.csv"))
    drv.select_plot(PLOT)
    drv.set_mapping("x", "group"); drv.set_mapping("y", "cytokine_pg_ml")
    drv.set_labels(ylabel="Cytokine (pg/ml)", xlabel="")
    drv.enable_statistics(test="welch_t", comparison="all_pairs", group_column="group", correction="holm", annotation="p")
    drv.run_statistics()
    before_rows = drv.stats_table_rows()
    ctx.fact("stats_before", before_rows)
    drv.capture("01_before_preset", "figure", "before any preset")
    drv.scroll_to("preset")
    drv.capture("02_preset_panel_default", "preset", "Figure preset panel, experimental presets hidden")
    entries = drv.show_experimental_presets(True)
    ctx.fact("preset_entries", entries)
    ctx.fact("preset_status_after_toggle", drv.win.preset_status.text())
    drv.capture("03_preset_panel_experimental", "preset", "after ticking Show experimental presets")
    # preview only (cancel) to show the dialog, then preview and apply
    info = drv.preview_preset("Violin + observations", apply=False, capture_name="04_preview_dialog_violin")
    ctx.fact("preview_violin_changes", info.get("changes", "")[:1500])
    ctx.fact("preview_violin_safety", info.get("safety"))
    ctx.fact("preview_violin_status", info.get("status"))
    info2 = drv.preview_preset("Violin + observations", apply=True)
    ctx.fact("apply_violin_status", info2.get("status"))
    drv.update_preview()
    drv.capture("05_after_violin_preset", "figure", "Violin + observations applied")
    ctx.fact("stats_after_violin", drv.stats_table_rows())
    ctx.fact("statistics_unchanged", drv.stats_table_rows() == before_rows)
    # a width preset on top (universal)
    info3 = drv.preview_preset("Single column 89 mm (N)", apply=True, capture_name="06_preview_dialog_89mm")
    ctx.fact("apply_89mm_status", info3.get("status"))
    ctx.fact("preview_89mm_changes", info3.get("changes", "")[:1500])
    drv.update_preview()
    drv.capture("07_after_89mm_preset", "figure", "Single column 89 mm (N) applied")
    # keep adjusting after the preset
    drv.set_option("point_size", 30); drv.set_option("point_fill", "open"); drv.set_option("point_edge", "same")
    drv.update_preview()
    drv.capture("08_adjusted_after_presets", "figure", "open circles after the presets")
    drv.set_labels(ylabel="Cytokine (pg/ml)")
    drv.export("pdf", ctx.out("preset_final.pdf")); drv.export("png", ctx.out("preset_final.png"))
    drv.capture("09_final_window", "window")
    drv.write_log()
