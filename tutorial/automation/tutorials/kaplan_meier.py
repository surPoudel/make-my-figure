"""Pilot: Kaplan-Meier survival curve with a log-rank test (survival.csv)."""
TITLE = "Kaplan-Meier survival curve"
DATASETS = ["survival.csv"]
PLOT = "kaplan_meier_survival_curve"


def run(drv, ctx):
    drv.open_file(ctx.dataset("survival.csv"))
    ctx.fact("columns", drv.columns())
    ctx.fact("recommendation_header", drv.recommendation_header())
    ctx.fact("cards", [c["title"] for c in drv.recommendation_cards()])
    drv.capture("01_open_data", "window")
    drv.select_plot(PLOT)
    ctx.fact("proposed_mapping", {k: w.currentText() for k, w in drv.mapping_widgets().items()})
    ctx.fact("multi_column_roles", list(getattr(drv.win, "_multi_col_widgets", {}) or {}))
    drv.set_mapping("time", "time_months")
    drv.set_mapping("event", "event")
    drv.set_mapping("group", "arm")
    drv.update_preview()
    drv.scroll_to("mapping")
    drv.capture("02_mapping", "mapping")
    drv.capture("03_initial_plot", "window", "two survival curves")
    opts = drv.option_widgets()
    ctx.fact("options", {k: ([w.itemText(i) for i in range(w.count())] if hasattr(w, "count") and hasattr(w, "itemText") else type(w).__name__) for k, w in opts.items()})
    drv.set_labels(xlabel="Time (months)", ylabel="Survival probability")
    if "reference_line" in opts:
        try:
            drv.set_option("reference_line", True)
        except Exception as exc:  # noqa: BLE001
            ctx.note(f"reference_line: {exc}")
    drv.update_preview()
    drv.scroll_to("options")
    drv.capture("04_customization", "options")
    drv.enable_statistics(test="logrank", group_column="arm", annotation="p")
    drv.run_statistics()
    ctx.fact("stats_method_sentence", drv.stats_panel_text()[:500]); ctx.fact("stats_table_rows", drv.stats_table_rows())
    md = drv.result_metadata()
    ctx.fact("stats_metadata_keys", sorted(k for k in md if "stat" in k.lower()))
    drv.scroll_to("stats")
    drv.capture("05_statistics", "stats")
    drv.capture("05b_plot_with_logrank", "figure", "log-rank P on the figure")
    drv.export("pdf", ctx.out("km.pdf"))
    drv.export("png", ctx.out("km.png"))
    drv.capture("06_final_plot", "window", "final")
    drv.write_log()
