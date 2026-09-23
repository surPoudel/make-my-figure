"""Pilot: reproducibility - PlotSpec versus Figure Package; save, move, reopen."""
TITLE = "Reproducibility: PlotSpec and Figure Package"
DATASETS = ["group_comparison.csv"]
PLOT = "boxplot_or_violin_with_points"


def run(drv, ctx):
    import os, shutil, zipfile, json
    drv.open_file(ctx.dataset("group_comparison.csv"))
    drv.select_plot(PLOT)
    drv.set_mapping("x", "group"); drv.set_mapping("y", "response")
    drv.enable_statistics(test="welch_t", comparison="all_pairs", group_column="group", correction="holm", annotation="p")
    drv.run_statistics()
    drv.update_preview()
    drv.capture("01_plot_with_stats", "window", "figure to preserve")
    ctx.fact("export_buttons", [b.text() for b in drv._target_widget("export").findChildren(drv.M.QPushButton)])
    drv.scroll_to("export")
    drv.capture("02_export_group", "export", "5. Export group")
    spec_path = drv.export("json", ctx.out("box.plot_spec.json"))
    with open(spec_path, encoding="utf-8") as fh:
        sidecar = json.load(fh)
    ctx.fact("plotspec_top_level_keys", sorted(sidecar))
    ctx.fact("plotspec_has_source_digest", "source" in json.dumps(sidecar.get("plot_spec", {})).lower())
    pkg = drv.save_package(ctx.out("box.mmfpackage"), capture_question="03_package_confirmation")
    with zipfile.ZipFile(pkg) as z:
        names = z.namelist()
    ctx.fact("package_members", names)
    ctx.fact("package_size_kb", round(os.path.getsize(pkg) / 1024, 1))
    # 'move' the package to another folder and reopen from a clean state
    moved = os.path.join(ctx.output_dir, "moved_elsewhere", "box_copy.mmfpackage")
    os.makedirs(os.path.dirname(moved), exist_ok=True)
    shutil.copy2(pkg, moved)
    drv.home(capture_question="04_home_question")
    drv.capture("04_home_again", "window", "back at the start screen")
    drv.open_package(moved)
    ctx.fact("reopened_mapping", drv.current_mapping())
    ctx.fact("reopened_status", drv.win.statusBar().currentMessage())
    ctx.fact("reopened_stats_enabled", drv.win.stats_panel.is_enabled())
    drv.capture("05_reopened_from_package", "window", "figure restored from the package alone")
    # PlotSpec without its data: what the app says
    drv.home()
    drv.open_plotspec(spec_path, ctx.dataset("group_comparison.csv"))
    ctx.fact("plotspec_file_dialogs", [s for s in drv.log.steps if s.get("dialog") == "file"][-2:])
    ctx.fact("plotspec_reopened_status", drv.win.statusBar().currentMessage())
    ctx.fact("plotspec_reopened_message", drv.message_text()[:300])
    drv.capture("06_open_plotspec", "window", "PlotSpec reopened together with its data file")
    drv.write_log()
