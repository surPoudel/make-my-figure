"""The publication QC gallery renders the matrix-workflow plots cleanly.

Runs the matrix-workflow subset of scripts/generate_publication_qc_gallery.py so
the test stays fast; asserts no errors/fails, all expected plots present, and
per-plot PNGs written. The full gallery (all 37 plot types) is run on demand via
the script.
"""

import os
import sys

import matplotlib
import pytest

matplotlib.use("Agg")

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SCRIPTS = os.path.join(_ROOT, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)


def test_matrix_workflow_gallery_all_pass(tmp_path):
    import generate_publication_qc_gallery as g

    per_plot = tmp_path / "per_plot"
    per_plot.mkdir()
    records = g._matrix_workflow_plots(str(per_plot))
    assert records, "no matrix-workflow plots produced"

    errored = [r for r in records if r.get("qc_level") in ("error", "fail")]
    assert not errored, f"gallery errors/fails: {[(r['name'], r.get('warnings')) for r in errored]}"

    names = {r["name"] for r in records}
    assert {"mw_heatmap", "mw_heatmap_zscore", "mw_pca", "mw_sample_correlation",
            "mw_volcano", "mw_selected_violin"}.issubset(names)

    for r in records:
        assert r.get("png"), r["name"]
        assert os.path.exists(per_plot / os.path.basename(r["png"]))
        assert not r.get("export_problems"), (r["name"], r.get("export_problems"))


def test_full_gallery_report_generation(tmp_path):
    """Smoke: the report writer produces a CSV + Markdown for given records."""
    import generate_publication_qc_gallery as g

    recs = [{"name": "a", "group": "example", "status": "rendered", "qc_level": "pass",
             "qc_score": 100, "warnings": []}]
    g.write_reports(recs, str(tmp_path))
    assert (tmp_path / "qc_summary.csv").exists()
    assert (tmp_path / "qc_report.md").exists()
