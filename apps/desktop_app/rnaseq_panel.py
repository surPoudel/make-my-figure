"""Desktop RNA-seq workflow dialog (PySide6).

A thin Qt layer over :mod:`make_my_figure_core.rnaseq`: upload a table, detect
the mode (precomputed DE / normalized matrix / raw counts / metadata), map
columns, and generate a publication-grade volcano or heatmap. Raw-count DE is
run through R (edgeR + limma-voom); if R/packages are missing the dialog shows
exactly what to install and disables 'Run DE' - it never fabricates statistics.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPlainTextEdit, QPushButton, QSpinBox, QStackedWidget, QVBoxLayout, QWidget,
)

from make_my_figure_core.plots.registry import export_figure, render
from make_my_figure_core.rnaseq import (
    build_expression_matrix, check_r_environment, classify_de, detect_input_mode,
    heatmap_spec_from_expression, load_rnaseq_table, parse_de_table, run_de_pipeline,
    volcano_spec_from_de,
)
from make_my_figure_core.rnaseq.detect import split_expression_matrix
from make_my_figure_core.rnaseq.runner import RDependencyError
from make_my_figure_core.rnaseq.spec import RnaSeqSpec, method_report_markdown
from make_my_figure_core.rnaseq.validate import validate_counts, validate_metadata

_MODES = [("de_result", "Precomputed DE result"), ("expression_matrix", "Normalized matrix"),
          ("raw_counts", "Raw counts"), ("sample_metadata", "Sample metadata"),
          ("unknown", "Unknown / other")]
_NONE = "(none)"


class RnaSeqDialog(QDialog):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.setWindowTitle("RNA-seq workflow")
        self.controller = controller
        self.resize(1040, 720)
        self.info = None
        self.detection = None
        self.metadata = None
        self._result = None
        self._rnaseq_spec: Optional[RnaSeqSpec] = None

        root = QHBoxLayout(self)
        left = QVBoxLayout()
        root.addLayout(left, 0)

        # --- file + mode ---
        fbox = QGroupBox("1. Input")
        fl = QVBoxLayout(fbox)
        row = QHBoxLayout()
        self.file_label = QLabel("No file loaded.")
        self.file_label.setWordWrap(True)
        openb = QPushButton("Open table…")
        openb.clicked.connect(self._open_file)
        row.addWidget(openb)
        fl.addLayout(row)
        fl.addWidget(self.file_label)
        self.mode_combo = QComboBox()
        for v, lbl in _MODES:
            self.mode_combo.addItem(lbl, v)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        fl.addWidget(QLabel("Detected mode (override if needed):"))
        fl.addWidget(self.mode_combo)
        self.detect_label = QLabel("")
        self.detect_label.setWordWrap(True)
        self.detect_label.setStyleSheet("color:#555;font-size:11px;")
        fl.addWidget(self.detect_label)
        left.addWidget(fbox)

        # --- mode-specific controls ---
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_de_page())          # 0
        self.stack.addWidget(self._build_matrix_page())      # 1
        self.stack.addWidget(self._build_rawcount_page())    # 2
        left.addWidget(self.stack)

        # --- exports ---
        ebox = QGroupBox("Export")
        el = QVBoxLayout(ebox)
        for lbl, slot in [("Export figure (SVG/PNG/PDF)", self._export_figure),
                          ("Export RnaSeqSpec JSON", self._export_spec),
                          ("Export method report (.md)", self._export_report),
                          ("Export DE / significant table", self._export_table)]:
            b = QPushButton(lbl)
            b.clicked.connect(slot)
            el.addWidget(b)
        left.addWidget(ebox)
        left.addStretch(1)

        # --- preview + log ---
        rightw = QVBoxLayout()
        root.addLayout(rightw, 1)
        self.canvas = FigureCanvas(matplotlib.figure.Figure(figsize=(5, 4)))
        rightw.addWidget(self.canvas, 1)
        self.status = QPlainTextEdit()
        self.status.setReadOnly(True)
        self.status.setMaximumHeight(150)
        rightw.addWidget(self.status)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self.reject)
        rightw.addWidget(bb)

        self._log("Open a DE table (e.g. Ctrl_vs_Treatment_DE.txt), a normalized matrix "
                  "(e.g. voom_norm_annot.txt), or a raw count matrix.")

    # ------------------------------------------------------------------ pages
    def _build_de_page(self) -> QWidget:
        w = QWidget(); f = QFormLayout(w)
        self.de_lfc = QDoubleSpinBox(); self.de_lfc.setRange(0, 20); self.de_lfc.setValue(1.0)
        self.de_lfc.setSingleStep(0.5)
        self.de_alpha = QDoubleSpinBox(); self.de_alpha.setRange(1e-6, 1); self.de_alpha.setDecimals(4)
        self.de_alpha.setValue(0.05)
        self.de_use_adj = QCheckBox("Threshold on adjusted p (FDR)"); self.de_use_adj.setChecked(True)
        self.de_topn = QSpinBox(); self.de_topn.setRange(0, 200); self.de_topn.setValue(15)
        self.de_labelby = QComboBox(); self.de_labelby.addItems(["gene_symbol", "gene_id"])
        self.de_selected = QLineEdit(); self.de_selected.setPlaceholderText("comma-separated genes to label")
        f.addRow("|log2FC| >=", self.de_lfc)
        f.addRow("p / FDR <", self.de_alpha)
        f.addRow(self.de_use_adj)
        f.addRow("Top N labels", self.de_topn)
        f.addRow("Label by", self.de_labelby)
        f.addRow("Label genes", self.de_selected)
        gen = QPushButton("Generate volcano"); gen.clicked.connect(self._generate_volcano)
        f.addRow(gen)
        self.de_counts = QLabel("")
        f.addRow(self.de_counts)
        return w

    def _build_matrix_page(self) -> QWidget:
        w = QWidget(); f = QFormLayout(w)
        self.hm_transform = QComboBox()
        self.hm_transform.addItems(["zscore", "log2cpm", "cpm", "log2p1", "none"])
        self.hm_selection = QComboBox()
        self.hm_selection.addItems(["top_variable", "selected", "all"])
        self.hm_ngenes = QSpinBox(); self.hm_ngenes.setRange(2, 500); self.hm_ngenes.setValue(50)
        self.hm_genes = QLineEdit(); self.hm_genes.setPlaceholderText("comma-separated genes (for 'selected')")
        self.hm_cluster_rows = QCheckBox("Cluster rows"); self.hm_cluster_rows.setChecked(True)
        self.hm_cluster_cols = QCheckBox("Cluster columns"); self.hm_cluster_cols.setChecked(True)
        metab = QPushButton("Load sample metadata (optional)…"); metab.clicked.connect(self._load_metadata)
        self.hm_annot = QLineEdit(); self.hm_annot.setPlaceholderText("metadata cols for annotation, e.g. Group,Sex")
        f.addRow("Transform", self.hm_transform)
        f.addRow("Gene selection", self.hm_selection)
        f.addRow("N genes", self.hm_ngenes)
        f.addRow("Genes", self.hm_genes)
        f.addRow(self.hm_cluster_rows)
        f.addRow(self.hm_cluster_cols)
        f.addRow(metab)
        f.addRow("Annotate by", self.hm_annot)
        gen = QPushButton("Generate heatmap"); gen.clicked.connect(self._generate_heatmap)
        f.addRow(gen)
        return w

    def _build_rawcount_page(self) -> QWidget:
        w = QWidget(); f = QFormLayout(w)
        self.r_status = QLabel(""); self.r_status.setWordWrap(True)
        f.addRow(self.r_status)
        self.setup_r_btn = QPushButton("Set up R for RNA-seq…")
        self.setup_r_btn.setToolTip("Install a self-contained R + edgeR/limma/DESeq2 environment "
                                    "(prebuilt binaries; needs internet once, ~1 GB).")
        self.setup_r_btn.clicked.connect(self._setup_r)
        f.addRow(self.setup_r_btn)
        self.rc_method = QComboBox()
        self.rc_method.addItem("edgeR + limma-voom (moderated t)", "edger_limma_voom")
        self.rc_method.addItem("DESeq2 (negative-binomial Wald)", "deseq2")
        self.rc_method.currentIndexChanged.connect(lambda _=None: self._refresh_r_status())
        f.addRow("DE method", self.rc_method)
        metab = QPushButton("Load sample metadata…"); metab.clicked.connect(self._load_metadata)
        f.addRow(metab)
        self.rc_group = QComboBox(); self.rc_ref = QComboBox(); self.rc_comp = QComboBox()
        self.rc_batch = QComboBox(); self.rc_cov = QLineEdit()
        self.rc_cov.setPlaceholderText("covariate cols, comma-separated (e.g. Age)")
        f.addRow("Condition column", self.rc_group)
        f.addRow("Reference group", self.rc_ref)
        f.addRow("Comparison group", self.rc_comp)
        f.addRow("Batch column", self.rc_batch)
        f.addRow("Covariates", self.rc_cov)
        self.rc_mincpm = QDoubleSpinBox(); self.rc_mincpm.setRange(0, 100); self.rc_mincpm.setValue(1.0)
        f.addRow("Filter: CPM >", self.rc_mincpm)
        # Output folder for DE results (DE tables + normalized matrix + spec + report).
        out_row = QHBoxLayout()
        self.rc_outdir = QLineEdit()
        self.rc_outdir.setPlaceholderText("(default: a temp results folder)")
        out_row.addWidget(self.rc_outdir)
        browse = QPushButton("Browse…"); browse.clicked.connect(self._pick_outdir)
        out_row.addWidget(browse)
        f.addRow("Output folder", out_row)
        valb = QPushButton("Validate input"); valb.clicked.connect(self._validate_raw)
        f.addRow(valb)
        self.run_de_btn = QPushButton("Run RNA-seq DE"); self.run_de_btn.clicked.connect(self._run_de)
        f.addRow(self.run_de_btn)
        self.use_voom_btn = QPushButton("Send normalized matrix to figure workspace")
        self.use_voom_btn.setToolTip("Load the DE-produced normalized (voom) matrix into the main "
                                     "window to build heatmaps, PCA, and other figures.")
        self.use_voom_btn.setEnabled(False)
        self.use_voom_btn.clicked.connect(self._use_voom_in_figures)
        f.addRow(self.use_voom_btn)
        self.rc_group.currentIndexChanged.connect(self._refresh_group_levels)
        return w

    def _pick_outdir(self):
        d = QFileDialog.getExistingDirectory(self, "Choose output folder for DE results")
        if d:
            self.rc_outdir.setText(d)

    def _current_method(self) -> str:
        return self.rc_method.currentData() if hasattr(self, "rc_method") else "edger_limma_voom"

    def _refresh_r_status(self):
        env = check_r_environment(method=self._current_method())
        self.run_de_btn.setEnabled(env.ready)
        self.r_status.setText(("✓ R ready: " + (env.r_version or ""))
                              if env.ready else "⚠ " + env.message.splitlines()[0]
                              + "  (use 'Set up R' or install R; Run DE disabled)")

    def _setup_r(self):
        from PySide6.QtCore import QThread, Signal, QObject

        if QMessageBox.question(
                self, "Set up R",
                "Download and install a self-contained R environment with edgeR, limma, and "
                "DESeq2?\n\nThis uses prebuilt binaries (no compiler needed), needs internet, "
                "and downloads roughly 1 GB the first time.") != QMessageBox.Yes:
            return
        from make_my_figure_core.rnaseq import install_r_environment

        self.setup_r_btn.setEnabled(False)
        self._log("Setting up R environment… (this can take several minutes)")

        class _Worker(QObject):
            line = Signal(str)
            done = Signal(dict)

            def run(self):
                res = install_r_environment(progress=self.line.emit)
                self.done.emit(res)

        self._r_thread = QThread()
        self._r_worker = _Worker()
        self._r_worker.moveToThread(self._r_thread)
        self._r_thread.started.connect(self._r_worker.run)
        self._r_worker.line.connect(self._log)
        self._r_worker.done.connect(self._on_r_installed)
        self._r_thread.start()

    def _on_r_installed(self, res: dict):
        self._r_thread.quit(); self._r_thread.wait()
        self.setup_r_btn.setEnabled(True)
        if res.get("ok"):
            self._log("R environment ready: " + str(res.get("rscript")))
            QMessageBox.information(self, "R ready",
                                    "R + edgeR/limma/DESeq2 installed. You can now run DE.")
        else:
            self._log("R setup did not complete. See log above.")
            QMessageBox.warning(self, "R setup failed",
                                "Could not complete the R install. Check your internet "
                                "connection and the log, or install R manually.")
        self._refresh_r_status()

    # ------------------------------------------------------------------ file
    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open RNA-seq table", "",
                                              "Tables (*.txt *.tsv *.csv *.xlsx);;All files (*)")
        if not path:
            return
        try:
            self.info = load_rnaseq_table(path)
        except Exception as exc:
            QMessageBox.warning(self, "Could not load", str(exc)); return
        self._source_path = path
        self.detection = detect_input_mode(self.info)
        self.file_label.setText(f"{os.path.basename(path)} — {self.info.n_rows} rows × "
                                f"{len(self.info.columns)} cols")
        idx = self.mode_combo.findData(self.detection["mode"])
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)
        self.detect_label.setText("Detected: " + "; ".join(self.detection.get("reasons", [])))
        self._on_mode_changed()

    def _on_mode_changed(self):
        mode = self.mode_combo.currentData()
        self.stack.setCurrentIndex({"de_result": 0, "expression_matrix": 1,
                                    "raw_counts": 2}.get(mode, 0))
        if mode == "raw_counts":
            self._refresh_r_status()
            if self.info is not None:
                _, sample_cols = split_expression_matrix(self.info.dataframe)
                self._log(f"Raw counts: {len(sample_cols)} sample columns detected. "
                          "Load sample metadata to choose the condition column.")

    def _load_metadata(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open sample metadata", "",
                                              "Tables (*.csv *.tsv *.txt *.xlsx);;All files (*)")
        if not path:
            return
        from make_my_figure_core.io.loaders import load_table
        try:
            self.metadata = load_table(path).dataframe
        except Exception as exc:
            QMessageBox.warning(self, "Could not load metadata", str(exc)); return
        self._meta_path = path
        cols = [_NONE] + list(self.metadata.columns)
        for combo in (self.rc_group, self.rc_batch):
            combo.blockSignals(True); combo.clear(); combo.addItems(cols); combo.blockSignals(False)
        # guess group
        for i, c in enumerate(self.metadata.columns):
            if c.lower() in ("group", "condition", "treatment"):
                self.rc_group.setCurrentText(c); break
        self._refresh_group_levels()
        self._log(f"Loaded metadata: {os.path.basename(path)} ({self.metadata.shape[0]} samples).")

    def _refresh_group_levels(self):
        if self.metadata is None:
            return
        gcol = self.rc_group.currentText()
        if gcol in (_NONE, "") or gcol not in self.metadata.columns:
            return
        levels = [str(x) for x in self.metadata[gcol].dropna().unique()]
        for combo in (self.rc_ref, self.rc_comp):
            combo.blockSignals(True); combo.clear(); combo.addItems(levels); combo.blockSignals(False)
        if len(levels) >= 2:
            self.rc_ref.setCurrentIndex(0); self.rc_comp.setCurrentIndex(1)

    # --------------------------------------------------------------- generate
    def _show_figure(self, result):
        self._result = result
        idx = self.canvas.figure.number if hasattr(self.canvas.figure, "number") else None
        rightw = self.canvas.parentWidget().layout()
        # replace canvas figure
        import matplotlib.pyplot as plt
        old = self.canvas
        new_canvas = FigureCanvas(result.figure)
        rightw.replaceWidget(old, new_canvas)
        old.setParent(None)
        self.canvas = new_canvas
        self.canvas.draw()

    def _generate_volcano(self):
        if self.info is None:
            return
        try:
            de = parse_de_table(self.info.dataframe)
            de = classify_de(de, lfc_cutoff=self.de_lfc.value(), alpha=self.de_alpha.value(),
                             use_adjusted=self.de_use_adj.isChecked())
            selected = [s.strip() for s in self.de_selected.text().split(",") if s.strip()]
            spec = volcano_spec_from_de(de, label_by=self.de_labelby.currentText(),
                                        top_n_labels=self.de_topn.value(),
                                        selected_genes=selected or None,
                                        input_table=os.path.basename(getattr(self, "_source_path", "de")))
            result = render(spec, de.frame)
        except Exception as exc:
            QMessageBox.warning(self, "Volcano failed", str(exc)); return
        self._current_spec = spec
        self._de = de
        self._rnaseq_spec = self._make_spec("de_result", volcano=de.thresholds,
                                            de_columns=de.mapping)
        self.de_counts.setText(f"Up: {de.n_up} | Down: {de.n_down} | n.s.: {de.n_ns}")
        self._show_figure(result)
        self._log(f"Volcano generated. Up={de.n_up}, Down={de.n_down}, n.s.={de.n_ns}.")

    def _generate_heatmap(self):
        if self.info is None:
            return
        try:
            mc, sc = split_expression_matrix(self.info.dataframe)
            em = build_expression_matrix(self.info.dataframe, metadata_columns=mc, sample_columns=sc)
            genes = [g.strip() for g in self.hm_genes.text().split(",") if g.strip()]
            annot_cols = [c.strip() for c in self.hm_annot.text().split(",") if c.strip()]
            sid = None
            if self.metadata is not None:
                for c in self.metadata.columns:
                    if c.lower() in ("sampleid", "sample_id", "sample", "id"):
                        sid = c; break
            hm = heatmap_spec_from_expression(
                em, transform=self.hm_transform.currentText(),
                selection=self.hm_selection.currentText(), n_genes=self.hm_ngenes.value(),
                genes=genes or None, cluster_rows=self.hm_cluster_rows.isChecked(),
                cluster_columns=self.hm_cluster_cols.isChecked(),
                metadata=self.metadata, sample_id_col=sid,
                annotation_columns=annot_cols or None)
            result = render(hm["spec"], hm["dataframe"])
        except Exception as exc:
            QMessageBox.warning(self, "Heatmap failed", str(exc)); return
        self._current_spec = hm["spec"]
        self._rnaseq_spec = self._make_spec("expression_matrix", heatmap=hm["transform"],
                                            selection=hm["selection"])
        self._show_figure(result)
        self._log(f"Heatmap generated: {hm['n_genes']} genes, transform={hm['transform']}.")

    def _validate_raw(self):
        if self.info is None or self.metadata is None:
            QMessageBox.information(self, "Need inputs", "Load both a count matrix and metadata.")
            return
        _, sample_cols = split_expression_matrix(self.info.dataframe)
        counts = self.info.dataframe.set_index(self.info.dataframe.columns[0])[sample_cols] \
            if self.info.dataframe.columns[0] not in sample_cols else self.info.dataframe[sample_cols]
        crep = validate_counts(self.info.dataframe, sample_cols)
        mrep = validate_metadata(self.metadata, group_col=self._group_or_none(),
                                 count_samples=sample_cols)
        lines = ["COUNTS: " + ("OK" if crep.ok else "ERRORS")]
        lines += ["  ! " + e for e in crep.errors] + ["  · " + w for w in crep.warnings]
        lines += [f"  {crep.summary}"]
        lines += ["METADATA: " + ("OK" if mrep.ok else "ERRORS")]
        lines += ["  ! " + e for e in mrep.errors] + ["  · " + w for w in mrep.warnings]
        self._log("\n".join(lines))

    def _group_or_none(self):
        g = self.rc_group.currentText()
        return None if g in (_NONE, "") else g

    def _run_de(self):
        if self.info is None or self.metadata is None:
            QMessageBox.information(self, "Need inputs", "Load a count matrix and metadata.")
            return
        base = self.info.dataframe
        gid_col = base.columns[0]
        meta_cols, sample_cols = split_expression_matrix(base)
        counts = base.set_index(gid_col)[sample_cols]
        # annotation = the non-sample metadata columns (geneSymbol/bioType/...) keyed
        # by gene id, so the voom matrix output matches the annotated template.
        annot_cols = [c for c in meta_cols if c != gid_col and c in base.columns]
        annotation = base.set_index(gid_col)[annot_cols] if annot_cols else None
        sid = next((c for c in self.metadata.columns
                    if c.lower() in ("sampleid", "sample_id", "sample", "id")), None)
        group = self._group_or_none()
        covs = [c.strip() for c in self.rc_cov.text().split(",") if c.strip()]
        batch = None if self.rc_batch.currentText() in (_NONE, "") else self.rc_batch.currentText()
        outdir = self.rc_outdir.text().strip() or None
        self._log("Running DE… (this can take a minute)")
        try:
            res = run_de_pipeline(
                counts, self.metadata, sample_id_col=sid, group_col=group,
                reference_group=self.rc_ref.currentText(),
                comparisons=[{"group1": self.rc_comp.currentText(),
                              "group2": self.rc_ref.currentText()}],
                covariates=covs, batch=batch, annotation=annotation,
                min_cpm=self.rc_mincpm.value(), method=self._current_method(),
                output_dir=outdir)
        except RDependencyError as exc:
            QMessageBox.warning(self, "R not available", str(exc)); self._log(str(exc)); return
        except Exception as exc:
            QMessageBox.critical(self, "DE failed", str(exc)); self._log(str(exc)); return
        self._rnaseq_spec = res["rnaseq_spec"]
        self._last_results = res
        self._voom_path = res.get("voom_file")
        # Persist the RnaSeqSpec + method report next to the DE outputs.
        try:
            import json as _json

            odir = res.get("output_dir", "")
            with open(os.path.join(odir, "analysis.rnaseq_spec.json"), "w", encoding="utf-8") as fh:
                _json.dump(self._rnaseq_spec.to_dict(), fh, indent=2)
            with open(os.path.join(odir, "rnaseq_methods.md"), "w", encoding="utf-8") as fh:
                fh.write(method_report_markdown(self._rnaseq_spec))
        except Exception:
            pass
        self._log("DE complete. " + (res.get("method", {}).get("de_method", "")) +
                  "\nDesign: " + str(res.get("method", {}).get("design_formula")) +
                  "\nResults saved to: " + res.get("output_dir", "") +
                  "\nDE tables: " + ", ".join(os.path.basename(p) for p in res["de_tables"].values()) +
                  "\nNormalized matrix: " + os.path.basename(res.get("voom_file", "")))
        self.use_voom_btn.setEnabled(bool(self._voom_path and os.path.exists(self._voom_path)))
        # auto-generate a volcano from the first DE table
        first = next(iter(res["de_tables"].values()), None)
        if first:
            self.info = load_rnaseq_table(first)
            self._source_path = first
            idx = self.mode_combo.findData("de_result"); self.mode_combo.setCurrentIndex(idx)
            self._generate_volcano()
        QMessageBox.information(
            self, "DE complete",
            f"Differential expression finished.\n\nResults saved to:\n{res.get('output_dir','')}\n\n"
            "Use 'Send normalized matrix to figure workspace' to make heatmaps/PCA from the "
            "normalized matrix, or export the DE table / volcano below.")

    def _use_voom_in_figures(self):
        """Load the DE-produced normalized matrix into the main figure workspace."""
        path = getattr(self, "_voom_path", None)
        if not path or not os.path.exists(path):
            QMessageBox.information(self, "No normalized matrix",
                                    "Run DE first to produce a normalized matrix."); return
        parent = self.parent()
        if parent is not None and hasattr(parent, "load_path"):
            parent.load_path(path)
            self._log(f"Loaded normalized matrix into the figure workspace: {os.path.basename(path)}")
            self.accept()
        else:
            QMessageBox.information(self, "Unavailable",
                                    "Open this dialog from the main window to send data to the "
                                    "figure workspace.")

    # ----------------------------------------------------------------- export
    def _make_spec(self, mode, **kw) -> RnaSeqSpec:
        spec = RnaSeqSpec(input_mode=mode)
        if getattr(self, "_source_path", None):
            spec.add_input("table", self._source_path)
        if kw.get("volcano"):
            spec.volcano_thresholds = kw["volcano"]
        if kw.get("de_columns"):
            spec.de_columns_used = {k: v for k, v in kw["de_columns"].items()}
        if kw.get("heatmap"):
            spec.heatmap_transform = kw["heatmap"]
            spec.gene_selection_method = kw.get("selection")
        return spec

    def _export_figure(self):
        if self._result is None:
            QMessageBox.information(self, "Nothing to export", "Generate a figure first."); return
        path, _ = QFileDialog.getSaveFileName(self, "Export figure", "rnaseq_figure.svg",
                                              "SVG (*.svg);;PNG (*.png);;PDF (*.pdf)")
        if not path:
            return
        base, ext = os.path.splitext(path)
        export_figure(self._result.figure, base, [ext.lstrip(".").lower() or "svg", "png", "pdf"])
        self._log(f"Exported figure to {base}.(svg/png/pdf)")

    def _export_spec(self):
        if self._rnaseq_spec is None:
            QMessageBox.information(self, "Nothing to export", "Generate a result first."); return
        import json
        path, _ = QFileDialog.getSaveFileName(self, "Export RnaSeqSpec", "analysis.rnaseq_spec.json",
                                              "JSON (*.json)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self._rnaseq_spec.to_dict(), fh, indent=2)
        self._log(f"Exported RnaSeqSpec to {path}")

    def _export_report(self):
        if self._rnaseq_spec is None:
            QMessageBox.information(self, "Nothing to export", "Generate a result first."); return
        path, _ = QFileDialog.getSaveFileName(self, "Export method report", "rnaseq_methods.md",
                                              "Markdown (*.md)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(method_report_markdown(self._rnaseq_spec))
        self._log(f"Exported method report to {path}")

    def _export_table(self):
        de = getattr(self, "_de", None)
        if de is None:
            QMessageBox.information(self, "Nothing to export", "Generate a volcano first."); return
        path, _ = QFileDialog.getSaveFileName(self, "Export DE table", "de_results.csv",
                                              "CSV (*.csv);;TSV (*.tsv)")
        if not path:
            return
        sep = "\t" if path.lower().endswith(".tsv") else ","
        de.frame.to_csv(path, sep=sep)
        self._log(f"Exported DE table ({de.frame.shape[0]} genes) to {path}")

    def _log(self, msg: str):
        self.status.appendPlainText(msg)
