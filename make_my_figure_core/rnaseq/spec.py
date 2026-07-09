"""RnaSeqSpec: a serializable, reproducible record of an RNA-seq analysis.

It integrates with PlotSpec/StatsSpec by living alongside them in exports. It
records inputs (+ checksums), the detected mode, the design formula and
contrasts, thresholds, the DE method label, R/package versions, and output
paths - everything needed to reproduce or audit a volcano/heatmap.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


def file_checksum(path: str, *, algo: str = "sha256", max_bytes: int = 64 * 1024 * 1024
                  ) -> Optional[str]:
    """Return a short checksum of a file (first ``max_bytes``), or None on error."""
    try:
        h = hashlib.new(algo)
        read = 0
        with open(path, "rb") as fh:
            while read < max_bytes:
                chunk = fh.read(min(1024 * 1024, max_bytes - read))
                if not chunk:
                    break
                h.update(chunk)
                read += len(chunk)
        return f"{algo}:{h.hexdigest()[:32]}"
    except Exception:
        return None


@dataclass
class RnaSeqSpec:
    """Reproducibility record for one RNA-seq analysis/plot."""

    input_mode: str = "unknown"               # de_result | expression_matrix | raw_counts
    input_files: Dict[str, str] = field(default_factory=dict)     # role -> filename
    input_checksums: Dict[str, str] = field(default_factory=dict)
    count_matrix_info: Dict[str, Any] = field(default_factory=dict)
    metadata_info: Dict[str, Any] = field(default_factory=dict)
    gene_annotation_info: Dict[str, Any] = field(default_factory=dict)
    condition_column: Optional[str] = None
    reference_group: Optional[str] = None
    comparison_group: Optional[str] = None
    covariates: List[str] = field(default_factory=list)
    batch_column: Optional[str] = None
    subject_column: Optional[str] = None
    design_formula: Optional[str] = None
    contrasts: List[str] = field(default_factory=list)
    filtering: Dict[str, Any] = field(default_factory=dict)
    normalization_method: Optional[str] = None
    de_method: Optional[str] = None           # human-readable method label
    de_method_id: Optional[str] = None        # machine id, e.g. 'edger_limma_voom'
    r_script_path: Optional[str] = None
    r_version: Optional[str] = None
    package_versions: Dict[str, str] = field(default_factory=dict)
    output_files: Dict[str, str] = field(default_factory=dict)
    de_columns_used: Dict[str, Optional[str]] = field(default_factory=dict)
    volcano_thresholds: Dict[str, Any] = field(default_factory=dict)
    heatmap_transform: Optional[str] = None
    gene_selection_method: Optional[str] = None
    software_versions: Dict[str, str] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def add_input(self, role: str, path: str, *, checksum: bool = True) -> None:
        self.input_files[role] = os.path.basename(path)
        if checksum and os.path.exists(path):
            cs = file_checksum(path)
            if cs:
                self.input_checksums[role] = cs

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RnaSeqSpec":
        known = {f: data[f] for f in cls.__dataclass_fields__ if f in data}
        return cls(**known)


# DE-method labels — used so the app never mislabels the analysis.
DE_METHODS = {
    "edger_limma_voom": "edgeR (TMM normalization + filtering) with limma-voom and "
                        "empirical Bayes moderated t-test",
    "edger_ql": "edgeR quasi-likelihood F-test (TMM normalization)",
    "edger_lrt": "edgeR likelihood-ratio test (TMM normalization)",
    "limma_ebayes": "limma empirical Bayes moderated t-test",
    "edger": "edgeR exact test (TMM normalization)",
    "deseq2": "DESeq2 (median-of-ratios normalization, negative-binomial GLM, Wald test)",
}


def method_report_markdown(spec: RnaSeqSpec) -> str:
    """A manuscript-ready methods paragraph for the RNA-seq analysis."""
    lines: List[str] = ["# RNA-seq differential-expression methods", ""]
    method = spec.de_method or DE_METHODS.get(spec.de_method_id or "", "the configured method")
    if spec.input_mode == "de_result":
        lines.append("Differential-expression results were supplied precomputed; Make My "
                     "Figure did not recompute the statistics. The volcano plot uses the "
                     "log fold change and (adjusted) p-values from the uploaded table.")
    else:
        design = spec.design_formula or "~ Group"
        contrasts = ", ".join(spec.contrasts) if spec.contrasts else "the requested contrast(s)"
        lines.append(f"Differential expression was assessed with {method}. Counts were "
                     f"filtered for low expression and normalized"
                     + (f" ({spec.normalization_method})" if spec.normalization_method else "")
                     + f". The design was `{design}`"
                     + (f" with covariate(s) {', '.join(spec.covariates)}" if spec.covariates else "")
                     + (f" and batch term `{spec.batch_column}`" if spec.batch_column else "")
                     + f"; contrasts: {contrasts}. Multiple testing was controlled with "
                     "Benjamini-Hochberg FDR.")
    if spec.volcano_thresholds:
        t = spec.volcano_thresholds
        lines.append("")
        lines.append(f"Volcano thresholds: |log2FC| >= {t.get('lfc_cutoff', 1.0)}, "
                     f"{'FDR' if t.get('use_adjusted', True) else 'p'} < {t.get('alpha', 0.05)}.")
    vers = []
    if spec.r_version:
        vers.append(f"R {spec.r_version}")
    for k, v in (spec.package_versions or {}).items():
        vers.append(f"{k} {v}")
    for k, v in (spec.software_versions or {}).items():
        vers.append(f"{k} {v}")
    if vers:
        lines += ["", "Software: " + ", ".join(vers) + "."]
    lines += ["", ("> RNA-seq differential expression depends on experimental design, "
                   "normalization, model specification, covariates, and multiple-testing "
                   "correction. Make My Figure reports the analysis method and design, but "
                   "users remain responsible for confirming that the model matches their "
                   "study design.")]
    return "\n".join(lines)
