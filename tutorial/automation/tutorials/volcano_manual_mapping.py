"""Pilot: volcano plot, first with standard DESeq2-like names, then with renamed columns that the
user must map by hand (rnaseq_results.csv, rnaseq_results_renamed.csv)."""
TITLE = "Volcano plot: automatic detection and manual role mapping"
DATASETS = ["rnaseq_results.csv", "rnaseq_results_renamed.csv"]
PLOT = "volcano_plot"


def run(drv, ctx):
    # Part 1: standard column names are detected
    drv.open_file(ctx.dataset("rnaseq_results.csv"))
    ctx.fact("columns_standard", drv.columns())
    ctx.fact("recommendation_header_standard", drv.recommendation_header())
    ctx.fact("cards_standard", [c["title"] for c in drv.recommendation_cards()])
    drv.capture("01_open_data", "window", "DE table with standard names")
    drv.select_plot(PLOT)
    ctx.fact("proposed_mapping_standard", {k: w.currentText() for k, w in drv.mapping_widgets().items()})
    ctx.fact("message_after_detection", drv.message_text())
    drv.update_preview()
    drv.scroll_to("mapping")
    drv.capture("02_mapping_detected", "mapping", "roles detected from DESeq2-style names")
    drv.capture("02b_messages", "messages", "the Messages text about detected columns")
    drv.capture("03_initial_plot", "window", "volcano from detected roles")

    # Part 2: the same data with non-standard names
    drv.open_file(ctx.dataset("rnaseq_results_renamed.csv"))
    ctx.fact("columns_renamed", drv.columns())
    drv.select_plot(PLOT)
    proposed = {k: w.currentText() for k, w in drv.mapping_widgets().items()}
    ctx.fact("proposed_mapping_renamed", proposed)
    ctx.fact("message_renamed", drv.message_text())
    ctx.fact("rendered_before_manual_mapping", drv.rendered())
    drv.scroll_to("mapping")
    drv.capture("04_mapping_renamed_before", "mapping", "what the app proposes for renamed columns")
    drv.capture("04b_window_before", "window")
    drv.set_mapping("x", "effect_measure")
    drv.set_mapping("p", "p_raw")
    drv.set_mapping("label", "name")
    drv.set_mapping("id_col", "feature")
    ok = drv.update_preview()
    ctx.fact("rendered_after_manual_mapping", ok)
    drv.capture("05_mapping_renamed_after", "mapping", "roles assigned by hand")
    drv.capture("05b_plot_after_mapping", "window", "the volcano renders")
    # switch to the adjusted p-value and tighten cutoffs
    drv.set_mapping("p", "p_adjusted")
    drv.set_option("lfc_cutoff", 1.0)
    drv.set_option("p_cutoff", 0.05)
    drv.set_option("label_top_n", 10) if "label_top_n" in drv.option_widgets() else None
    drv.set_labels(xlabel="log2 fold change", ylabel="-log10 adjusted P")
    drv.update_preview()
    md = drv.result_metadata()
    ctx.fact("volcano_metadata_counts", {k: v for k, v in md.items() if isinstance(v, (int, float)) and ("up" in k or "down" in k or "n_" in k)})
    drv.scroll_to("options")
    drv.capture("06_customization", "options", "thresholds")
    drv.capture("06b_final_plot", "figure", "final volcano")
    drv.export("png", ctx.out("volcano.png"))
    drv.export("pdf", ctx.out("volcano.pdf"))
    drv.export("json", ctx.out("volcano.plot_spec.json"))
    drv.write_log()
