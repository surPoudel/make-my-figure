"""Matrix Workflow → canonical plot-editor handoff.

The Matrix Workflow prepares data + mappings, then hands off to the *same* plot
editor the normal workflow uses. These tests pin: the handoff builds a canonical
PlotSpec (same schema, full controls), provenance is preserved, thresholds/labels
stay editable, every plot type routes to its normal renderer, and there is no
second reduced plot-control schema.
"""

from __future__ import annotations

import pathlib

import matplotlib
matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest

import make_my_figure_core.matrix_workflow as mw
from apps.desktop_app.controller import DesktopController
from make_my_figure_core.plots.registry import render, available_plot_types
from make_my_figure_core.plots.handoff import PlotEditorHandoff, build_matrix_provenance
from make_my_figure_core.spec.validate import validate_plot_spec
from make_my_figure_core import ui_hints

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _matrix_setup():
    c = DesktopController()
    mdf = pd.DataFrame({"feature_id": [f"F{i}" for i in range(12)],
                        "gene": [f"G{i % 4}" for i in range(12)]})
    for s in range(6):
        g = "ctrl" if s < 3 else "treat"
        mdf[f"{g}_{s + 1}"] = np.random.default_rng(s).normal(10, 2, 12)
    data = c.loaded_from_dataframe(mdf, "matrix.csv")
    vcols = [x for x in mdf.columns if x.startswith(("ctrl", "treat"))]
    ms = mw.MatrixSpec(source_file="matrix.csv", feature_id_column="feature_id",
                       value_columns=vcols, annotation_columns=["gene"],
                       confirmed_by_user=True, source_workbook="Aging.xlsx",
                       source_sheet="Sol_24M_vs_6M", source_sheet_index=2)
    meta = mw.suggest_metadata_from_table(
        pd.DataFrame({"sample_id": vcols, "group": ["ctrl"] * 3 + ["treat"] * 3}), vcols)
    meta.confirmed_by_user = True
    # Realistic differential table (log2FC populated) for volcano/MA.
    diff = pd.DataFrame({
        "feature_id": [f"F{i}" for i in range(12)],
        "feature_label": [f"G{i % 4}" for i in range(12)],
        "log2_fold_change": np.linspace(-2, 2, 12),
        "p_value": np.linspace(1e-5, 0.5, 12),
        "adjusted_p_value": np.linspace(1e-4, 0.6, 12),
        "average_abundance": np.linspace(5, 15, 12),
    })
    return c, data, ms, meta, diff


def _rec(c, data, ms, meta, key):
    recs = c.matrix_recommendations(data, ms, meta, has_differential=True)
    return next(r for r in recs if r.key == key)


def _handoff(c, data, ms, meta, diff, key, **kw):
    return c.matrix_plot_handoff(data, _rec(c, data, ms, meta, key), ms, metadata=meta,
                                 differential_table=diff, **kw)


def _spec_from_handoff(c, h):
    """Simulate the editor building a canonical spec from the handoff."""
    loaded = c.loaded_from_handoff(h)
    hm = {**h.mappings, **h.defaults}
    fields = ui_hints.column_fields(h.plot_type) + ["color", "shape"]
    mapping = {k: hm[k] for k in fields if k in hm}
    if hm.get("value_columns"):
        mapping["value_columns"] = hm["value_columns"]
    for k in ("use_fdr", "scale", "color_scale", "cluster_rows", "cluster_columns"):
        if k in hm:
            mapping[k] = hm[k]
    spec = c.build_spec(h.plot_type, "publication", loaded.table_name, mapping,
                        source={**(loaded.source_provenance() or {}), **h.provenance})
    for k, v in (h.spec_extra or {}).items():
        spec[k] = v
    return spec, loaded


# 1. Volcano handoff creates a canonical, valid PlotSpec.
def test_volcano_handoff_builds_canonical_plotspec():
    c, data, ms, meta, diff = _matrix_setup()
    h = _handoff(c, data, ms, meta, diff, "volcano")
    assert h.plot_type == "volcano_plot"
    spec, _ = _spec_from_handoff(c, h)
    validate_plot_spec(spec, known_plot_types=list(available_plot_types()),
                       known_styles=["publication"])
    assert spec["source"]["source_workflow"] == "matrix"


# 2 / 15. Same control schema — the editor's canonical volcano options are the full
# set, and the Matrix wizard no longer defines its own style/threshold schema.
def test_no_second_volcano_control_schema():
    keys = {o.key for o in ui_hints.options("volcano_plot")}
    # canonical volcano controls all live in ui_hints (one schema)
    for expected in ("lfc_cutoff", "p_cutoff", "use_fdr", "annotate", "label_mode",
                     "duplicate_label_policy"):
        assert expected in keys
    # the desktop + streamlit matrix wizards no longer own a style/threshold panel
    dsk = (ROOT / "apps" / "desktop_app" / "matrix_wizard.py").read_text()
    stl = (ROOT / "apps" / "streamlit_app" / "matrix_wizard.py").read_text()
    assert "_build_style_group" not in dsk
    assert "def _style_controls" not in stl
    assert "mw_style_" not in stl


# 3-6. Thresholds + significance field are editable after handoff (canonical spec).
def test_thresholds_editable_after_handoff():
    c, data, ms, meta, diff = _matrix_setup()
    spec, loaded = _spec_from_handoff(c, _handoff(c, data, ms, meta, diff, "volcano"))
    spec["mapping"]["lfc_cutoff"] = 1.0
    spec["mapping"]["p_cutoff"] = 0.01
    r1 = render(spec, loaded.info.dataframe)
    spec["mapping"]["p_cutoff"] = 0.5   # looser threshold -> more significant
    r2 = render(spec, loaded.info.dataframe)
    assert r1.metadata["p_cutoff"] == 0.01 and r2.metadata["p_cutoff"] == 0.5
    assert (r2.metadata["n_up"] + r2.metadata["n_down"]) >= \
           (r1.metadata["n_up"] + r1.metadata["n_down"])   # 25: cache invalidates


def test_significance_field_switchable():
    c, data, ms, meta, diff = _matrix_setup()
    # FDR suggested by default; editor can remap the p column to raw p-value.
    h = _handoff(c, data, ms, meta, diff, "volcano")
    assert h.mappings["p"] == "adjusted_p_value"
    assert h.defaults.get("use_fdr") is True
    spec, loaded = _spec_from_handoff(c, h)
    spec["mapping"]["p"] = "p_value"          # switch to raw p
    r = render(spec, loaded.info.dataframe)
    assert r.metadata is not None


# 8-9. Full label + duplicate-label controls are available in the canonical editor.
def test_label_and_duplicate_controls_available():
    keys = {o.key for o in ui_hints.options("volcano_plot")}
    for k in ("annotate", "label_mode", "top_n", "label_by",
              "duplicate_label_policy", "duplicate_label_representative_rule",
              "duplicate_label_show_count"):
        assert k in keys


# 11-14. Provenance persists in the PlotSpec source block.
def test_provenance_persists_in_plotspec():
    c, data, ms, meta, diff = _matrix_setup()
    h = _handoff(c, data, ms, meta, diff, "volcano",
                 preprocessing=["log2", "quantile"], statistics={"method": "Welch t-test"})
    spec, _ = _spec_from_handoff(c, h)
    src = spec["source"]
    assert src["source_matrix_id"]                       # 11 matrix provenance
    assert src["source_statistics"]["method"] == "Welch t-test"   # 12 stats
    assert src["source_preprocessing"] == ["log2", "quantile"]    # 13 preprocessing
    assert src["source_sheet_name"] == "Sol_24M_vs_6M"            # 14 workbook/sheet
    assert src["source_workbook_name"] == "Aging.xlsx"


# 16-19. Each recommendation opens the correct normal renderer.
@pytest.mark.parametrize("key,expect", [
    ("volcano", "volcano_plot"),
    ("ma", "ma_plot"),
    ("heatmap_zscore", "heatmap_clustered_matrix"),
    ("pca_by_group", "pca_scatter_from_matrix"),
    ("box_by_group", "boxplot_or_violin_with_points"),
])
def test_handoff_routes_to_normal_renderer(key, expect):
    c, data, ms, meta, diff = _matrix_setup()
    kw = {"selected_features": ["F0", "F1"]} if key == "box_by_group" else {}
    h = _handoff(c, data, ms, meta, diff, key, **kw)
    assert h.plot_type == expect
    assert h.plot_type in set(available_plot_types())


# 20. Marker-size control exists for PCA after handoff (via Publication style).
def test_pca_marker_size_control_after_handoff():
    c, data, ms, meta, diff = _matrix_setup()
    h = _handoff(c, data, ms, meta, diff, "pca_by_group")
    spec, loaded = _spec_from_handoff(c, h)
    spec["style"] = {"marker_size": 80.0}     # canonical Publication style control
    r = render(spec, loaded.info.dataframe, aux={k: v for k, v in h.aux.items()})
    assert r.metadata is not None


# 21. Colorbar controls exist for the canonical heatmap editor.
def test_heatmap_colorbar_controls_exist():
    keys = {o.key for o in ui_hints.options("heatmap_clustered_matrix")}
    assert "colorbar_location" in keys or any("colorbar" in k for k in keys)


# 26. Exports use the canonical PlotSpec (has an output block).
def test_canonical_spec_has_output_block():
    c, data, ms, meta, diff = _matrix_setup()
    spec, _ = _spec_from_handoff(c, _handoff(c, data, ms, meta, diff, "volcano"))
    assert "output" in spec and "formats" in spec["output"]


# 27. Figure Builder can round-trip the fully configured plot (Panel from spec).
def test_figure_builder_receives_configured_plot():
    from make_my_figure_core.panels.models import Panel
    from make_my_figure_core.panels.builder import panel_from_dict
    c, data, ms, meta, diff = _matrix_setup()
    spec, _ = _spec_from_handoff(c, _handoff(c, data, ms, meta, diff, "volcano"))
    p = Panel(label="A", plot_spec=spec, source_name="matrix")
    back = panel_from_dict(p.to_dict())
    assert back.plot_spec["source"]["source_workflow"] == "matrix"


# 28. Existing saved specs without handoff provenance still load.
def test_legacy_spec_without_provenance_still_loads():
    spec = {"plot_type": "volcano_plot", "input_table": "old.csv",
            "mapping": {"x": "logFC", "p": "P.Value", "label": "gene"},
            "journal_style": "publication", "output": {"formats": ["png"], "dpi": 300}}
    validate_plot_spec(spec, known_plot_types=list(available_plot_types()),
                       known_styles=["publication"])


# 22-24. Handoff wiring present in both frontends; return preserves matrix state.
def test_both_frontends_wire_the_handoff():
    dsk_main = (ROOT / "apps" / "desktop_app" / "main.py").read_text()
    dsk_wiz = (ROOT / "apps" / "desktop_app" / "matrix_wizard.py").read_text()
    stl_app = (ROOT / "apps" / "streamlit_app" / "streamlit_app.py").read_text()
    stl_wiz = (ROOT / "apps" / "streamlit_app" / "matrix_wizard.py").read_text()
    # desktop: open button -> pending_handoff -> apply; dialog persisted for return
    assert "_open_in_editor" in dsk_wiz and "pending_handoff" in dsk_wiz
    assert "_apply_plot_handoff" in dsk_main and "self._matrix_dialog" in dsk_main
    assert "matrix_plot_handoff" in dsk_wiz
    # streamlit: open button sets handoff session state + switches workflow; return btn
    assert "Open in plot editor" in stl_wiz and "_handoff_source" in stl_wiz
    assert "_handoff_source" in stl_app and "Return to Matrix Workflow" in stl_app
    assert 'workflow_mode"] = "Quick plot"' in stl_wiz


# 29-30. Only Publication visible; no R/rpy2 added.
def test_only_publication_and_no_r():
    for f in ("apps/desktop_app/matrix_wizard.py", "apps/streamlit_app/matrix_wizard.py",
              "make_my_figure_core/plots/handoff.py"):
        src = (ROOT / f).read_text()
        assert "rpy2" not in src and "import rpy2" not in src
        for bad in ("nature_like", "science_like", "cell_like"):
            assert bad not in src
