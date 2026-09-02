"""Every registered plot type passes the Figure Preset QC, enumerated from the registry.

This runs the same per-plot check as ``scripts/build_figure_preset_qc.py`` - render, change
settings, save style and full presets, load a different dataset, apply, verify, export, round-trip -
so a renderer or option added later has to pass it too, and a check may only be N/A with a stated
reason.
"""

from __future__ import annotations

import csv
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_figure_preset_qc as qc  # noqa: E402

from make_my_figure_core.plots.registry import available_plot_types  # noqa: E402


@pytest.fixture(autouse=True)
def _close():
    yield
    plt.close("all")


@pytest.mark.parametrize("pt", available_plot_types())
def test_plot_type_passes_preset_qc(pt, tmp_path):
    row = qc.check_plot(pt, workdir=str(tmp_path))
    assert row["status"] == "PASS", row["notes"]
    # every non-applicable check names its reason
    for col in qc.COLUMNS:
        if row[col] == "N/A":
            assert f"{col}: N/A - " in row["notes"], f"{pt}: {col} is N/A without a reason"
    # the checks that can never be N/A
    for col in ("preset_save", "preset_load", "style_roundtrip", "full_config_roundtrip",
                "typography_roundtrip", "layout_roundtrip", "annotation_roundtrip",
                "new_data_safe", "png_export", "pdf_export", "svg_export"):
        assert row[col] == "PASS", f"{pt}: {col} = {row[col]} ({row['notes']})"


def test_matrix_covers_the_live_registry_with_the_required_columns():
    """The committed CSV must match the registry and carry exactly the specified columns."""
    path = qc.CSV_PATH
    assert path.exists(), "run scripts/build_figure_preset_qc.py"
    with open(path, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert list(rows[0].keys()) == qc.COLUMNS
    assert {r["plot_type"] for r in rows} == set(available_plot_types())
    assert all(r["status"] == "PASS" for r in rows), [r["plot_type"] for r in rows if r["status"] != "PASS"]


def test_at_least_three_settings_are_changed_for_every_type():
    assert len(qc.STYLE_CHANGES) + len(qc.LAYOUT_CHANGES) + len(qc.OUTPUT_CHANGES) >= 3
