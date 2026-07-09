"""Run the reproducible edgeR + limma-voom DE pipeline through R.

Safety/robustness requirements (from the milestone spec):

* Calls ``Rscript`` via a subprocess argument list — never a shell string — so
  spaces and OneDrive paths are handled correctly.
* Writes all inputs (counts, metadata, annotation, run spec, R script) to a
  temporary working directory.
* Captures stdout/stderr and an analysis log; captures R + package versions.
* Reports the exact design formula and contrasts.
* If R or edgeR/limma are missing it raises :class:`RDependencyError` with
  install instructions and does **not** fall back to a t-test.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

from make_my_figure_core.rnaseq.rscript import DE_SCRIPTS, RNASEQ_DE_R
from make_my_figure_core.rnaseq.spec import DE_METHODS, RnaSeqSpec

REQUIRED_R_PACKAGES = ["edgeR", "limma", "jsonlite"]
# Packages required per DE method (jsonlite is always needed for I/O).
METHOD_PACKAGES = {
    "edger_limma_voom": ["edgeR", "limma", "jsonlite"],
    "deseq2": ["DESeq2", "jsonlite"],
}

INSTALL_INSTRUCTIONS = (
    "RNA-seq differential expression needs R with Bioconductor packages "
    "(edgeR + limma for limma-voom, DESeq2 for the DESeq2 method).\n\n"
    "Easiest: in the app, click 'Set up R for RNA-seq' to install a self-contained "
    "R environment automatically (no separate R install needed).\n\n"
    "Manual alternative — install R from https://www.r-project.org/, then run:\n"
    '    if (!requireNamespace("BiocManager", quietly=TRUE)) install.packages("BiocManager")\n'
    '    BiocManager::install(c("edgeR", "limma", "DESeq2"))\n'
    '    install.packages("jsonlite")\n\n'
    "Precomputed DE tables can still be turned into volcano plots without R."
)


class RDependencyError(RuntimeError):
    """Raised when R or a required package is unavailable."""

    def __init__(self, message: str, *, missing: Optional[List[str]] = None):
        self.missing = missing or []
        super().__init__(message)


@dataclass
class REnvironment:
    has_r: bool
    rscript_path: Optional[str] = None
    r_version: Optional[str] = None
    installed_packages: Dict[str, Optional[str]] = field(default_factory=dict)
    missing_packages: List[str] = field(default_factory=list)
    ready: bool = False
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"has_r": self.has_r, "rscript_path": self.rscript_path,
                "r_version": self.r_version, "installed_packages": self.installed_packages,
                "missing_packages": self.missing_packages, "ready": self.ready,
                "message": self.message}


def find_rscript() -> Optional[str]:
    """Locate ``Rscript``. Preference: explicit override → R bundled in a frozen
    build → app-managed (on-demand) env → system PATH."""
    override = os.environ.get("MAKE_MY_FIGURE_RSCRIPT")
    if override and os.path.exists(override):
        return override
    try:
        from make_my_figure_core.rnaseq.r_setup import (
            bundled_rscript_path, managed_rscript_path,
        )

        return (bundled_rscript_path() or managed_rscript_path()
                or shutil.which("Rscript") or shutil.which("Rscript.exe"))
    except Exception:
        return shutil.which("Rscript") or shutil.which("Rscript.exe")


def check_r_environment(*, packages: Optional[List[str]] = None,
                        method: Optional[str] = None) -> REnvironment:
    """Probe for R + required packages. Never raises; returns a report.

    ``method`` (``edger_limma_voom`` | ``deseq2``) selects which packages are
    required; ``packages`` overrides it explicitly.
    """
    if packages is None:
        packages = METHOD_PACKAGES.get(method or "", REQUIRED_R_PACKAGES)
    rscript = find_rscript()
    if not rscript:
        return REnvironment(has_r=False, missing_packages=list(packages), ready=False,
                            message="Rscript was not found on PATH. " + INSTALL_INSTRUCTIONS)
    probe = (
        "ver <- R.version.string;"
        "pk <- c(%s);"
        "present <- pk[sapply(pk, function(p) requireNamespace(p, quietly=TRUE))];"
        "vv <- sapply(present, function(p) as.character(packageVersion(p)));"
        "cat(ver, '\\n');"
        "for (p in present) cat('PKG', p, vv[[p]], '\\n')"
    ) % ", ".join(f"'{p}'" for p in packages)
    try:
        res = subprocess.run([rscript, "-e", probe], capture_output=True, text=True, timeout=60,
                             env=_rscript_env(rscript))
    except Exception as exc:  # pragma: no cover - defensive
        return REnvironment(has_r=True, rscript_path=rscript, missing_packages=list(packages),
                            ready=False, message=f"Could not run Rscript: {exc}")
    r_version = None
    installed: Dict[str, Optional[str]] = {}
    for line in res.stdout.splitlines():
        line = line.strip()
        if line.startswith("R version") or "R version" in line:
            r_version = line
        elif line.startswith("PKG "):
            _, name, ver = line.split(None, 2)
            installed[name] = ver
    missing = [p for p in packages if p not in installed]
    ready = len(missing) == 0
    msg = "R environment ready." if ready else (
        f"Missing R package(s): {', '.join(missing)}.\n" + INSTALL_INSTRUCTIONS)
    return REnvironment(has_r=True, rscript_path=rscript, r_version=r_version,
                        installed_packages=installed, missing_packages=missing,
                        ready=ready, message=msg)


def _write_counts(counts: pd.DataFrame, path: str) -> None:
    df = counts.copy()
    df.index = pd.Index([str(i) for i in df.index], name="gene_id")
    # make gene ids unique
    if df.index.duplicated().any():
        df = df[~df.index.duplicated(keep="first")]
    df.to_csv(path, sep="\t")


def run_de_pipeline(
    counts: pd.DataFrame,
    metadata: pd.DataFrame,
    *,
    sample_id_col: str,
    group_col: str,
    reference_group: str,
    comparisons: List[Dict[str, str]],
    covariates: Optional[List[str]] = None,
    batch: Optional[str] = None,
    annotation: Optional[pd.DataFrame] = None,
    min_cpm: float = 1.0,
    method: str = "edger_limma_voom",
    output_dir: Optional[str] = None,
    timeout: int = 1800,
) -> Dict[str, Any]:
    """Run the DE pipeline. Returns a dict with de_tables, voom path, method,
    versions, log, and a populated :class:`RnaSeqSpec`.

    ``method`` is ``edger_limma_voom`` (default) or ``deseq2``. Raises
    :class:`RDependencyError` if R or the method's packages are unavailable.
    """
    if method not in DE_SCRIPTS:
        raise ValueError(f"Unknown DE method '{method}'. Options: {sorted(DE_SCRIPTS)}")
    env = check_r_environment(method=method)
    if not env.ready:
        raise RDependencyError(env.message, missing=env.missing_packages)

    covariates = covariates or []
    workdir = tempfile.mkdtemp(prefix="mmf_rnaseq_")
    out = output_dir or os.path.join(workdir, "results")
    os.makedirs(out, exist_ok=True)

    counts_file = os.path.join(workdir, "counts.tsv")
    meta_file = os.path.join(workdir, "meta.csv")
    script_file = os.path.join(workdir, "rnaseq_de.R")
    spec_file = os.path.join(workdir, "run_spec.json")
    _write_counts(counts, counts_file)
    metadata.to_csv(meta_file, index=False)
    annotation_file = ""
    if annotation is not None and not annotation.empty:
        annotation_file = os.path.join(workdir, "annotation.tsv")
        ann = annotation.copy()
        ann.index = pd.Index([str(i) for i in ann.index], name="gene_id")
        ann.to_csv(annotation_file, sep="\t")
    with open(script_file, "w", encoding="utf-8") as fh:
        fh.write(DE_SCRIPTS[method])

    run_spec = {
        "counts_file": counts_file, "meta_file": meta_file,
        "annotation_file": annotation_file, "output_dir": out,
        "sample_id_col": sample_id_col, "group_col": group_col,
        "reference_group": reference_group, "comparisons": comparisons,
        "covariates": covariates, "batch": batch or "", "min_cpm": float(min_cpm),
        "min_count": 10,
    }
    with open(spec_file, "w", encoding="utf-8") as fh:
        json.dump(run_spec, fh, indent=2)

    # Subprocess argument list (no shell) -> safe with spaces / OneDrive paths.
    # On Windows a conda R needs its library dirs on PATH to load its DLLs.
    proc = subprocess.run([env.rscript_path, script_file, spec_file],
                          capture_output=True, text=True, timeout=timeout, cwd=workdir,
                          env=_rscript_env(env.rscript_path))
    if "MMF_OK" not in proc.stdout:
        raise RuntimeError(
            "R DE pipeline failed.\nSTDOUT:\n" + proc.stdout[-4000:] +
            "\nSTDERR:\n" + proc.stderr[-4000:])

    minfo = _read_json(os.path.join(out, "method.json")) or {}
    versions = _read_json(os.path.join(out, "versions.json")) or {}
    de_tables: Dict[str, str] = {}
    # jsonlite auto-unboxes a length-1 vector to a scalar, so contrast_names may
    # be a single string rather than a list — normalize before iterating.
    cnames = minfo.get("contrast_names", [])
    if isinstance(cnames, str):
        cnames = [cnames]
    for cn in cnames:
        p = os.path.join(out, f"{cn}_DE.txt")
        if os.path.exists(p):
            de_tables[cn] = p
    voom_name = minfo.get("voom_file", "voom_norm_annot.txt")

    spec = RnaSeqSpec(
        input_mode="raw_counts",
        condition_column=group_col, reference_group=reference_group,
        comparison_group=(comparisons[0]["group2"] if comparisons else None),
        covariates=list(covariates), batch_column=batch,
        design_formula=minfo.get("design_formula"),
        contrasts=list((minfo.get("contrasts") or {}).values())
        if isinstance(minfo.get("contrasts"), dict) else list(minfo.get("contrasts") or []),
        filtering={"rule": minfo.get("filtering"), "min_cpm": float(min_cpm)},
        normalization_method=minfo.get("normalization"),
        de_method=minfo.get("de_method") or DE_METHODS.get(method),
        de_method_id=minfo.get("de_method_id", method),
        r_script_path="rnaseq_de.R", r_version=versions.get("r_version"),
        package_versions={k: v for k, v in versions.items() if k != "r_version"},
        output_files={"voom": os.path.join(out, voom_name),
                      "log": os.path.join(out, "analysis_log.txt"), **de_tables},
    )
    return {
        "de_tables": de_tables,
        "voom_file": os.path.join(out, voom_name),
        "method": minfo, "versions": versions,
        "log": _read_text(os.path.join(out, "analysis_log.txt")),
        "stdout": proc.stdout, "stderr": proc.stderr,
        "output_dir": out, "workdir": workdir, "rnaseq_spec": spec,
    }


def _read_json(path: str) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except Exception:
        return ""


def _rscript_env(rscript_path: Optional[str]) -> dict:
    """Environment for invoking Rscript (adds conda DLL dirs to PATH on Windows)."""
    try:
        from make_my_figure_core.rnaseq.r_setup import rscript_subprocess_env

        return rscript_subprocess_env(rscript_path)
    except Exception:
        return dict(os.environ)
