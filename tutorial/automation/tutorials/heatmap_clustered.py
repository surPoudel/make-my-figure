"""Pilot: clustered heatmap from a feature x sample matrix (feature_sample_matrix.csv)."""
TITLE = "Clustered heatmap from a feature-by-sample matrix"
DATASETS = ["feature_sample_matrix.csv"]
PLOT = "heatmap_clustered_matrix"


def run(drv, ctx):
    drv.open_file(ctx.dataset("feature_sample_matrix.csv"))
    ctx.fact("columns", drv.columns())
    ctx.fact("recommendation_header", drv.recommendation_header())
    ctx.fact("cards", [c["title"] for c in drv.recommendation_cards()])
    drv.capture("01_open_data", "window", "matrix loaded")
    drv.select_plot(PLOT)
    ctx.fact("proposed_mapping", {k: w.currentText() for k, w in drv.mapping_widgets().items()})
    lw = drv.win._value_cols_widget
    ctx.fact("value_columns_offered", [lw.item(i).text() for i in range(lw.count())] if lw else None)
    ctx.fact("value_columns_preselected", [i.text() for i in lw.selectedItems()] if lw else None)
    drv.set_mapping("row_id", "gene_symbol")
    drv.update_preview()
    drv.scroll_to("mapping")
    drv.capture("02_mapping", "mapping", "row id and the Value columns list")
    drv.capture("03_initial_plot", "window", "clustered heatmap")
    opts = drv.option_widgets()
    ctx.fact("options", list(opts))
    for key, val in (("scale", "row_zscore"), ("colormap", None), ("cluster_columns", False)):
        if key in opts and val is not None:
            try:
                drv.set_option(key, val)
            except Exception as exc:  # noqa: BLE001 - record the real choices instead of guessing
                ctx.note(f"option {key}: {exc}")
    if "scale" in opts:
        w = opts["scale"]
        ctx.fact("scale_choices", [w.itemText(i) for i in range(w.count())] if hasattr(w, "count") else None)
    drv.update_preview()
    drv.scroll_to("options")
    drv.capture("04_customization", "options", "heatmap options")
    drv.capture("04b_customized", "figure")
    drv.export("png", ctx.out("heatmap.png"))
    drv.export("pdf", ctx.out("heatmap.pdf"))
    drv.capture("06_final_plot", "window", "final")
    drv.write_log()
