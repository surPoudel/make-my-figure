"""Figure-package round trips for the spatial plot types.

A spatial figure carries more state than a bar chart: tissue coordinates, a
declared unit and orientation, a colour normalisation, a scale bar, ROI
geometry, neighbourhood assignments. A package that restores the marks but
loses the orientation, or redraws a 500 um bar at a different length, has not
reproduced the figure - so the comparison here checks those explicitly rather
than trusting a generic artist signature.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from make_my_figure_core.examples import load_example
from make_my_figure_core.package import (
    PACKAGE_EXTENSION,
    PackageIntegrityError,
    content_for_single_plot,
    open_figure_package,
    single_plot_inputs,
    write_figure_package,
)
from make_my_figure_core.plots.registry import render

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SPATIAL_TYPES = [
    "spatial_categorical_map",
    "spatial_feature_map",
    "spatial_transcript_map",
    "spatial_roi_map",
    "spatial_composition_map",
    "neighborhood_enrichment_matrix",
]


def spatial_signature(fig, result) -> dict:
    """Everything a spatial figure must reproduce, not just its artists."""
    sig = {"size_inches": [round(float(v), 6) for v in fig.get_size_inches()], "axes": []}
    for ax in fig.axes:
        if getattr(ax, "_colorbar", None):
            continue
        entry = {
            "xlim": [round(float(v), 9) for v in ax.get_xlim()],
            "ylim": [round(float(v), 9) for v in ax.get_ylim()],
            "y_inverted": bool(ax.yaxis_inverted()),
            "aspect": str(ax.get_aspect()),
            "xlabel": ax.get_xlabel(), "ylabel": ax.get_ylabel(),
            "title": ax.get_title(),
            "offsets": [], "norms": [], "lines": [], "patches": 0,
        }
        for coll in ax.collections:
            try:
                off = np.asarray(coll.get_offsets(), dtype=float)
                if off.size:
                    entry["offsets"].append({
                        "n": int(off.shape[0]),
                        "sum": [round(float(off[:, 0].sum()), 6),
                                round(float(off[:, 1].sum()), 6)],
                        "min": [round(float(off[:, 0].min()), 6),
                                round(float(off[:, 1].min()), 6)],
                        "max": [round(float(off[:, 0].max()), 6),
                                round(float(off[:, 1].max()), 6)],
                    })
            except Exception:  # noqa: BLE001
                pass
            norm = getattr(coll, "norm", None)
            if norm is not None and norm.vmin is not None:
                entry["norms"].append([round(float(norm.vmin), 9), round(float(norm.vmax), 9)])
            entry["patches"] += len(getattr(coll, "get_paths", lambda: [])())
        for ln in ax.lines:                      # the scale bar is a Line2D
            xd, yd = ln.get_xdata(), ln.get_ydata()
            if len(xd) == 2:
                entry["lines"].append(round(float(abs(xd[1] - xd[0])), 9))
        entry["texts"] = sorted(t.get_text() for t in ax.texts if t.get_text())
        leg = ax.get_legend()
        entry["legend"] = [t.get_text() for t in leg.get_texts()] if leg else None
        sig["axes"].append(entry)
    sig["legend_figure"] = [[t.get_text() for t in lg.get_texts()] for lg in fig.legends]
    # the recorded spatial provenance must survive too
    spatial = dict(result.metadata.get("spatial") or {})
    sig["spatial_record"] = json.loads(json.dumps({
        k: spatial.get(k) for k in
        ("coordinate_units", "orientation", "equal_aspect", "categories", "n_cells",
         "transform", "colorbar_label", "color_scale", "vmin", "vmax",
         "scale_bar", "rois", "neighborhoods", "cell_types", "n_transcripts_drawn",
         "percentile_clip", "shared_color_scale")
        if k in spatial}, default=str))
    return sig


def _package(spec, df, tmp_path, name, **kw):
    res = render(spec, df)
    content = content_for_single_plot(spec, df, res, table_name=spec["input_table"],
                                      name=name, **kw)
    rep = write_figure_package(content, str(tmp_path / name))
    assert rep.path.endswith(PACKAGE_EXTENSION)
    return res, rep


@pytest.mark.parametrize("plot_type", SPATIAL_TYPES)
def test_spatial_round_trip_reproduces_the_figure(plot_type, tmp_path):
    info, aux, spec = load_example(plot_type)
    df = info.dataframe
    res, rep = _package(spec, df, tmp_path, plot_type)

    pkg = open_figure_package(rep.path)
    spec2, df2, _ = single_plot_inputs(pkg)
    pd.testing.assert_frame_equal(df, df2, check_exact=True, check_dtype=True)
    assert spec2 == json.loads(json.dumps(spec))

    res2 = render(spec2, df2)
    assert spatial_signature(res2.figure, res2) == spatial_signature(res.figure, res)


@pytest.mark.parametrize("plot_type", SPATIAL_TYPES)
def test_coordinate_units_and_orientation_survive_the_round_trip(plot_type, tmp_path):
    """A map that comes back mirrored, or with the units forgotten, is not the same figure."""
    info, _, spec = load_example(plot_type)
    df = info.dataframe
    res, rep = _package(spec, df, tmp_path, plot_type)
    spec2, df2, _ = single_plot_inputs(open_figure_package(rep.path))
    res2 = render(spec2, df2)
    a = res.metadata.get("spatial", {})
    b = res2.metadata.get("spatial", {})
    for key in ("coordinate_units", "orientation", "equal_aspect"):
        if key in a:
            assert a[key] == b[key], f"{plot_type}: {key} changed across the round trip"


def test_scale_bar_length_is_reproduced_not_recomputed(tmp_path):
    """A bar redrawn at a different length would silently restate the scale."""
    info, _, spec = load_example("spatial_categorical_map")
    spec = json.loads(json.dumps(spec))
    spec["spatial"].update({"coordinate_units": "micrometre", "scale_bar": True,
                            "scale_bar_length": 250.0})
    df = info.dataframe
    res, rep = _package(spec, df, tmp_path, "bar")
    spec2, df2, _ = single_plot_inputs(open_figure_package(rep.path))
    res2 = render(spec2, df2)
    bar_a = res.metadata["spatial"]["scale_bar"]
    bar_b = res2.metadata["spatial"]["scale_bar"]
    assert bar_a["drawn"] and bar_b["drawn"]
    assert bar_a["length"] == bar_b["length"] == 250.0
    assert bar_a["label"] == bar_b["label"]


def test_roi_geometry_is_reproduced_vertex_for_vertex(tmp_path):
    info, _, spec = load_example("spatial_roi_map")
    df = info.dataframe
    res, rep = _package(spec, df, tmp_path, "roi")
    spec2, df2, _ = single_plot_inputs(open_figure_package(rep.path))
    res2 = render(spec2, df2)
    a = res.metadata["spatial"]["rois"]
    b = res2.metadata["spatial"]["rois"]
    assert [r["roi"] for r in a] == [r["roi"] for r in b]
    for ra, rb in zip(a, b):
        assert ra["n_vertices"] == rb["n_vertices"]
        assert ra["area"] == pytest.approx(rb["area"], rel=1e-12)
        assert ra["centroid"] == pytest.approx(rb["centroid"], rel=1e-12)


def test_colour_normalisation_is_reproduced(tmp_path):
    """vmin/vmax decide what the colours mean; drifting limits change the claim."""
    info, _, spec = load_example("spatial_feature_map")
    df = info.dataframe
    res, rep = _package(spec, df, tmp_path, "feat")
    spec2, df2, _ = single_plot_inputs(open_figure_package(rep.path))
    res2 = render(spec2, df2)
    a, b = res.metadata["spatial"], res2.metadata["spatial"]
    assert a["vmin"] == pytest.approx(b["vmin"], rel=1e-12)
    assert a["vmax"] == pytest.approx(b["vmax"], rel=1e-12)
    assert a["transform"] == b["transform"]
    assert a["colorbar_label"] == b["colorbar_label"]


def test_neighbourhood_assignments_survive_as_data(tmp_path):
    """The published CN labels are data, and must come back bit-for-bit."""
    info, _, spec = load_example("spatial_categorical_map")
    df = info.dataframe
    assert "neighborhood" in df.columns
    spec = json.loads(json.dumps(spec))
    spec["mapping"]["category"] = "neighborhood"
    res, rep = _package(spec, df, tmp_path, "cn")
    spec2, df2, _ = single_plot_inputs(open_figure_package(rep.path))
    pd.testing.assert_series_equal(df["neighborhood"], df2["neighborhood"], check_exact=True)
    res2 = render(spec2, df2)
    assert res.metadata["spatial"]["categories"] == res2.metadata["spatial"]["categories"]


# --- a package must survive leaving the machine that made it ------------------

_CHILD = r'''
import json, os, sys
import matplotlib; matplotlib.use("Agg")
sys.path.insert(0, sys.argv[3])
sys.path.insert(0, os.path.join(sys.argv[3], "tests"))
from make_my_figure_core.package import open_figure_package, single_plot_inputs
from make_my_figure_core.plots.registry import render
from test_figure_package_spatial import spatial_signature
pkg = open_figure_package(sys.argv[1])
spec, df, aux = single_plot_inputs(pkg)
res = render(spec, df, aux=aux or None)
json.dump({"sig": spatial_signature(res.figure, res), "spec": spec,
           "rows": int(len(df)), "cols": list(df.columns)},
          open(sys.argv[2], "w"))
'''


@pytest.mark.parametrize("plot_type", ["spatial_categorical_map", "spatial_feature_map",
                                       "spatial_roi_map"])
def test_package_reopens_in_a_clean_process_after_the_source_is_destroyed(plot_type, tmp_path):
    """Process A builds it; process B never sees the source, which no longer exists."""
    lab_a = tmp_path / "lab_A"
    lab_a.mkdir()
    info, _, spec = load_example(plot_type)
    src = lab_a / "source.csv"
    info.dataframe.to_csv(src, index=False)

    from make_my_figure_core.io.loaders import load_table
    df = load_table(str(src)).dataframe
    spec = {**json.loads(json.dumps(spec)), "input_table": "source.csv"}
    res = render(spec, df)
    content = content_for_single_plot(spec, df, res, table_name="source.csv",
                                      source_path=str(src))
    rep = write_figure_package(content, str(lab_a / "figure"))
    sig_a = spatial_signature(res.figure, res)

    # one file travels; the laboratory that produced it is destroyed
    lab_b = tmp_path / "lab_B"
    lab_b.mkdir()
    dest = lab_b / "received.mmfpackage"
    shutil.copy2(rep.path, dest)
    shutil.rmtree(lab_a)
    assert not src.exists()

    out = lab_b / "result.json"
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["MPLBACKEND"] = "Agg"
    proc = subprocess.run([sys.executable, "-c", _CHILD, str(dest), str(out), ROOT],
                          cwd=str(lab_b), env=env, capture_output=True, text=True,
                          timeout=900)
    assert proc.returncode == 0, proc.stderr[-2000:]
    got = json.loads(out.read_text())
    assert got["sig"] == json.loads(json.dumps(sig_a))
    assert got["spec"] == json.loads(json.dumps(spec))
    assert got["rows"] == len(df)


# --- tampering must be detected ----------------------------------------------

def _rewrite_member(src_path, dest_path, member_pred, new_bytes_fn):
    """Copy a package, replacing the first member matching ``member_pred``."""
    import zipfile
    with zipfile.ZipFile(src_path) as zin:
        names = zin.namelist()
        target = next((n for n in names if member_pred(n)), None)
        assert target, f"no member matched in {names[:20]}"
        with zipfile.ZipFile(dest_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for n in names:
                data = zin.read(n)
                if n == target:
                    data = new_bytes_fn(data)
                zout.writestr(n, data)
    return target


@pytest.mark.parametrize("what,pred,mutate", [
    ("frozen table",
     lambda n: n.endswith(".mmftable.json") or ("table" in n and n.endswith(".json")),
     lambda b: b.replace(b"1", b"2", 1) if b"1" in b else b + b" "),
    ("plot spec",
     lambda n: n.endswith("plot_spec.json") or n.endswith("spec.json"),
     lambda b: b.replace(b"publication", b"PUBLICATION", 1) if b"publication" in b else b + b" "),
])
def test_tampering_with_a_packaged_spatial_file_fails_the_integrity_check(
        what, pred, mutate, tmp_path):
    info, _, spec = load_example("spatial_categorical_map")
    df = info.dataframe
    _, rep = _package(spec, df, tmp_path, "orig")
    bad = tmp_path / "tampered.mmfpackage"
    _rewrite_member(rep.path, bad, pred, mutate)

    # Assert the specific failure, not merely "something raised": a JSON parse
    # error would also abort the open, and would prove nothing about integrity.
    with pytest.raises(PackageIntegrityError) as excinfo:
        pkg = open_figure_package(str(bad))
        single_plot_inputs(pkg)          # some checks run on access
    assert "differ from the values recorded" in str(excinfo.value), str(excinfo.value)


def test_an_untouched_package_opens_cleanly(tmp_path):
    """The tamper tests only mean something if the control passes."""
    info, _, spec = load_example("spatial_categorical_map")
    _, rep = _package(spec, info.dataframe, tmp_path, "control")
    pkg = open_figure_package(rep.path)
    spec2, df2, _ = single_plot_inputs(pkg)
    assert len(df2) == len(info.dataframe)


# --- background images must travel with the package --------------------------

def _he_image(tmp_path):
    import matplotlib.pyplot as plt
    path = tmp_path / "he_section.png"
    plt.imsave(str(path), (np.random.default_rng(0).random((60, 80, 3)) * 255).astype("uint8"))
    return str(path)


def _spec_with_background(tmp_path):
    info, _, spec = load_example("spatial_categorical_map")
    df = info.dataframe
    spec = json.loads(json.dumps(spec))
    spec["spatial"].update({
        "background_image": _he_image(tmp_path),
        "background_extent": [float(df["x"].min()), float(df["x"].max()),
                              float(df["y"].min()), float(df["y"].max())],
        "background_alpha": 0.5,
    })
    return spec, df


def test_background_image_is_packaged_with_its_checksum(tmp_path):
    import zipfile
    spec, df = _spec_with_background(tmp_path)
    _, rep = _package(spec, df, tmp_path, "bg")
    with zipfile.ZipFile(rep.path) as z:
        assets = [n for n in z.namelist() if n.startswith("assets/")]
    assert any("he_section.png" in n for n in assets), assets
    manifest = json.loads(open_figure_package(rep.path).manifest and
                          json.dumps(open_figure_package(rep.path).manifest))
    entry = next(a for a in manifest["assets"] if a["asset_id"] == "spatial_background")
    assert len(entry["sha256"]) == 64


def test_figure_still_reconstructs_after_the_original_image_is_deleted(tmp_path):
    """The point of a package: the machine that opens it has neither file."""
    spec, df = _spec_with_background(tmp_path)
    original = spec["spatial"]["background_image"]
    res, rep = _package(spec, df, tmp_path, "bg")
    os.remove(original)
    assert not os.path.exists(original)

    spec2, df2, _ = single_plot_inputs(open_figure_package(rep.path))
    assert spec2["spatial"]["background_image"] != original, \
        "the reopened spec still points at the machine that made it"
    assert os.path.exists(spec2["spatial"]["background_image"])

    res2 = render(spec2, df2)
    a = res.metadata["spatial"]["background_image"]
    b = res2.metadata["spatial"]["background_image"]
    assert a["sha256"] == b["sha256"], "a different image was drawn"
    assert a["extent"] == b["extent"] and a["alpha"] == b["alpha"]


def test_a_background_image_is_never_silently_substituted(tmp_path):
    """A path that exists on the opening machine must not be picked up by accident."""
    spec, df = _spec_with_background(tmp_path)
    original = spec["spatial"]["background_image"]
    _, rep = _package(spec, df, tmp_path, "bg")
    # replace the file at the original path with a DIFFERENT image
    import matplotlib.pyplot as plt
    plt.imsave(original, np.zeros((60, 80, 3), dtype="uint8"))

    spec2, _, _ = single_plot_inputs(open_figure_package(rep.path))
    assert spec2["spatial"]["background_image"] != original
    import hashlib
    got = hashlib.sha256(open(spec2["spatial"]["background_image"], "rb").read()).hexdigest()
    assert got == spec2["spatial"]["background_image_sha256"]
    assert got != hashlib.sha256(open(original, "rb").read()).hexdigest()
