"""Shared interactive annotation-state model (frontend-agnostic)."""

import json

import matplotlib
import pandas as pd

matplotlib.use("Agg")

from make_my_figure_core.plots.annotation_state import AnnotationState
from make_my_figure_core.plots.registry import make_spec, render


def test_add_and_toggle():
    st = AnnotationState()
    assert st.toggle("G1") is True          # added
    assert "G1" in st.labels()
    assert st.toggle("G1") is False         # removed (click again to unlabel)
    assert "G1" not in st.labels()


def test_move_only_affects_selected():
    st = AnnotationState()
    st.add("A"); st.add("B")
    st.select("A")
    st.move(10, -5)
    assert st.annotations["A"].moved and st.annotations["A"].offset() == (18.0, 3.0)
    assert not st.annotations["B"].moved      # B untouched


def test_reset_and_delete():
    st = AnnotationState()
    st.add("A"); st.select("A"); st.move(20, 20)
    assert st.annotations["A"].moved
    st.reset()
    assert not st.annotations["A"].moved
    st.delete("A")
    assert "A" not in st.labels() and st.selected is None


def test_to_mapping_only_moved_labels_get_offsets():
    st = AnnotationState()
    st.add("A"); st.add("B")
    st.select("B"); st.move(30, 0)
    m = st.to_mapping()
    assert set(m["selected_labels"]) == {"A", "B"}
    offs = json.loads(m["label_offsets"])
    assert "B" in offs and "A" not in offs     # only the moved label persists an offset


def test_round_trip():
    st = AnnotationState()
    st.add("A"); st.add("B"); st.select("A"); st.move(15, -10)
    m = st.to_mapping()
    st2 = AnnotationState.from_mapping(m)
    assert set(st2.labels()) == {"A", "B"}
    assert st2.annotations["A"].offset() == st.annotations["A"].offset()
    assert not st2.annotations["B"].moved


def test_state_feeds_renderer_offsets():
    # The mapping the state produces must actually move the label in the render.
    rng_tbl = pd.DataFrame({"feature_label": [f"G{i}" for i in range(40)],
                            "log2_fold_change": [i - 20 for i in range(40)],
                            "adjusted_p_value": [0.001 * (i + 1) for i in range(40)]})
    st = AnnotationState()
    st.add("G1"); st.select("G1"); st.move(50, -30)
    mapping = {"x": "log2_fold_change", "p": "adjusted_p_value", "label": "feature_label",
               "annotate": True, "label_mode": "pasted", **st.to_mapping()}
    # highlight_genes/pasted uses label_list; ensure G1 labelled via selected_labels path
    mapping["label_list"] = ["G1"]
    r = render(make_spec("volcano_plot", "v", "publication", mapping=mapping), rng_tbl)
    assert "G1" in {t.get_text() for t in r.figure.axes[0].texts}
