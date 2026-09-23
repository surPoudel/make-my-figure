"""Pilot: save a Figure Preset from one dataset and apply it to an unrelated one."""
TITLE = "Figure presets: style travels, data stays"
DATASETS = ["group_comparison.csv", "one_table_many_plots.csv"]
PLOT = "boxplot_or_violin_with_points"


def run(drv, ctx):
    drv.open_file(ctx.dataset("group_comparison.csv"))
    drv.select_plot(PLOT)
    drv.set_mapping("x", "group"); drv.set_mapping("y", "response")
    drv.set_option("kind", "violin"); drv.set_option("point_size", 14)
    drv.set_labels(ylabel="Response (a.u.)", width="single")
    drv.update_preview()
    drv.capture("01_refined_plot", "window", "refined violin on dataset 1")
    ctx.fact("preset_buttons", [b.text() for b in drv._target_widget("preset").findChildren(drv.M.QPushButton)])
    drv.scroll_to("preset")
    drv.capture("02_preset_panel", "preset", "the Figure preset panel")
    path = drv.save_preset("Tutorial violin style", "style", capture_dialog="03_save_preset_dialog")
    ctx.fact("preset_file", path)
    import json, os
    with open(path, encoding="utf-8") as fh:
        preset = json.load(fh)
    ctx.fact("preset_top_level_keys", sorted(preset))
    ctx.fact("preset_contains_data", any(k in json.dumps(preset) for k in ("response", "Vehicle", "P001")))
    # unrelated dataset, same plot type
    drv.open_file(ctx.dataset("one_table_many_plots.csv"))
    drv.select_plot(PLOT)
    drv.set_mapping("x", "treatment"); drv.set_mapping("y", "response")
    drv.update_preview()
    drv.capture("04_second_dataset_default", "window", "dataset 2 with default appearance")
    status = drv.apply_preset("Tutorial violin style")
    ctx.fact("apply_status", status)
    spec = drv.current_spec()
    ctx.fact("mapping_after_apply", drv.current_mapping())
    drv.update_preview()
    drv.capture("05_second_dataset_preset", "window", "dataset 2 after applying the preset")
    md = drv.result_metadata()
    ctx.fact("n_after_apply", md.get("n") or md.get("group_n") or md.get("counts"))
    drv.export("png", ctx.out("preset_applied.png"))
    drv.capture("06_final_plot", "figure")
    drv.write_log()
