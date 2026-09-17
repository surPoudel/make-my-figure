"""Figure package integrity, security and versioning: tampering must be detected, bad
containers must fail with a user-facing message, and unsafe ZIPs must be rejected."""
from __future__ import annotations

import io
import json
import os
import zipfile

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest

from make_my_figure_core.examples import load_example
from make_my_figure_core.package import (
    PackageError,
    PackageFormatError,
    PackageIntegrityError,
    PackageVersionError,
    content_for_single_plot,
    inspect_figure_package,
    open_figure_package,
    table_from_json_bytes,
    table_to_json_bytes,
    write_figure_package,
)
from make_my_figure_core.package import manifest as M
from make_my_figure_core.package.security import PackageSecurityError, check_member_name, scan_zip
from make_my_figure_core.plots.registry import render


@pytest.fixture(autouse=True)
def _close():
    yield
    import matplotlib.pyplot as plt

    plt.close("all")


@pytest.fixture
def package(tmp_path):
    info, _, spec = load_example("scatterplot_with_regression")
    res = render(spec, info.dataframe)
    rep = write_figure_package(content_for_single_plot(spec, info.dataframe, res, table_name="x.csv"),
                               str(tmp_path / "good"))
    return rep.path


def _rewrite(src, dest, mutate):
    """Unpack, apply ``mutate(name, data) -> data|None``, repack (None drops the member)."""
    zin = zipfile.ZipFile(src)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zout:
        for zi in zin.infolist():
            data = mutate(zi.filename, zin.read(zi.filename))
            if data is not None:
                zout.writestr(zi.filename, data)
    return dest


def test_good_package_opens_and_inspect_reads_manifest(package):
    pkg = open_figure_package(package)
    assert pkg.integrity == "verified" and pkg.kind == "single_plot"
    m = inspect_figure_package(package)
    assert m["package_format"] == M.PACKAGE_FORMAT and m["format_version"] == M.PACKAGE_FORMAT_VERSION


def test_tampered_data_value_is_detected(package, tmp_path):
    def mutate(name, data):
        if name.startswith("data/") and name.endswith(".mmftable.json"):
            doc = json.loads(data)
            col = doc["columns"][1]
            col["values"][0] = 12345.678 if not isinstance(col["values"][0], str) else "tampered"
            return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
        return data
    bad = _rewrite(package, str(tmp_path / "tampered.mmfpackage"), mutate)
    with pytest.raises(PackageIntegrityError) as ei:
        open_figure_package(bad)
    assert "differ from the values recorded" in str(ei.value)


def test_tampered_spec_is_detected(package, tmp_path):
    def mutate(name, data):
        if name == "plot_spec.json":
            d = json.loads(data)
            d["layout"] = {**d.get("layout", {}), "title": "changed"}
            return json.dumps(d).encode()
        return data
    with pytest.raises(PackageIntegrityError):
        open_figure_package(_rewrite(package, str(tmp_path / "t2.mmfpackage"), mutate))


def test_wrong_checksum_in_manifest(package, tmp_path):
    def mutate(name, data):
        if name == "manifest.json":
            m = json.loads(data)
            m["files"][0]["sha256"] = "0" * 64
            return json.dumps(m).encode()
        return data
    with pytest.raises(PackageIntegrityError):
        open_figure_package(_rewrite(package, str(tmp_path / "t3.mmfpackage"), mutate))


def test_unlisted_extra_file_is_detected(package, tmp_path):
    zin = zipfile.ZipFile(package)
    dest = str(tmp_path / "extra.mmfpackage")
    with zipfile.ZipFile(dest, "w") as zout:
        for zi in zin.infolist():
            zout.writestr(zi.filename, zin.read(zi.filename))
        zout.writestr("data/injected.csv", b"a,b\n1,2\n")
    with pytest.raises(PackageIntegrityError) as ei:
        open_figure_package(dest)
    assert "not recorded in the manifest" in str(ei.value)


def test_missing_data_file(package, tmp_path):
    bad = _rewrite(package, str(tmp_path / "missing.mmfpackage"),
                   lambda n, d: None if n.startswith("data/") and n.endswith(".mmftable.json") else d)
    with pytest.raises(PackageFormatError) as ei:
        open_figure_package(bad)
    assert "incomplete" in str(ei.value)


def test_missing_plotspec(package, tmp_path):
    bad = _rewrite(package, str(tmp_path / "nospec.mmfpackage"), lambda n, d: None if n == "plot_spec.json" else d)
    with pytest.raises(PackageFormatError):
        open_figure_package(bad)


def test_corrupt_manifest_json(package, tmp_path):
    bad = _rewrite(package, str(tmp_path / "corrupt.mmfpackage"), lambda n, d: b"{not json" if n == "manifest.json" else d)
    with pytest.raises(PackageFormatError) as ei:
        open_figure_package(bad)
    assert "not valid JSON" in str(ei.value)


def test_manifest_schema_violation(package, tmp_path):
    def mutate(name, data):
        if name == "manifest.json":
            m = json.loads(data)
            del m["tables"]
            return json.dumps(m).encode()
        return data
    with pytest.raises(PackageFormatError) as ei:
        open_figure_package(_rewrite(package, str(tmp_path / "schema.mmfpackage"), mutate))
    assert "manifest is invalid" in str(ei.value)


def test_missing_manifest_and_not_a_zip(tmp_path):
    z = tmp_path / "nomanifest.mmfpackage"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("plot_spec.json", "{}")
    with pytest.raises(PackageFormatError) as ei:
        open_figure_package(str(z))
    assert "manifest.json is missing" in str(ei.value)
    notzip = tmp_path / "text.mmfpackage"
    notzip.write_text("hello")
    with pytest.raises(PackageFormatError) as ei:
        open_figure_package(str(notzip))
    assert "not a valid ZIP" in str(ei.value)
    with pytest.raises(PackageFormatError):
        open_figure_package(str(tmp_path / "does_not_exist.mmfpackage"))


def test_unsupported_newer_version(package, tmp_path):
    def mutate(name, data):
        if name == "manifest.json":
            m = json.loads(data)
            m["format_version"] = 99
            return json.dumps(m).encode()
        return data
    with pytest.raises(PackageVersionError) as ei:
        open_figure_package(_rewrite(package, str(tmp_path / "v99.mmfpackage"), mutate))
    assert "newer" in str(ei.value)


def test_wrong_package_format_marker(package, tmp_path):
    def mutate(name, data):
        if name == "manifest.json":
            m = json.loads(data)
            m["package_format"] = "something.else"
            return json.dumps(m).encode()
        return data
    with pytest.raises(PackageFormatError):
        open_figure_package(_rewrite(package, str(tmp_path / "fmt.mmfpackage"), mutate))


@pytest.mark.parametrize("name", ["../evil.json", "/abs/path.json", "C:/windows/x.json", "data/../../x", "a\\b.json",
                                  "data/./x.json", "bad\x00name"])
def test_malicious_member_names_rejected(name):
    with pytest.raises(PackageSecurityError):
        check_member_name(name)


def test_malicious_zip_path_traversal_rejected(package, tmp_path):
    zin = zipfile.ZipFile(package)
    dest = str(tmp_path / "traversal.mmfpackage")
    with zipfile.ZipFile(dest, "w") as zout:
        for zi in zin.infolist():
            zout.writestr(zi.filename, zin.read(zi.filename))
        zout.writestr("../../escape.txt", b"x")
    with pytest.raises(PackageFormatError) as ei:
        open_figure_package(dest)
    assert "safety" in str(ei.value)


def test_symlink_entry_rejected(tmp_path):
    dest = str(tmp_path / "link.mmfpackage")
    with zipfile.ZipFile(dest, "w") as zout:
        zi = zipfile.ZipInfo("manifest.json")
        zi.external_attr = (0o120777 << 16)      # symlink mode bits
        zout.writestr(zi, b"{}")
    with pytest.raises(PackageFormatError) as ei:
        open_figure_package(dest)
    assert "safety" in str(ei.value)


def test_zip_bomb_ratio_rejected(tmp_path):
    dest = str(tmp_path / "bomb.mmfpackage")
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zout:
        zout.writestr("manifest.json", b"{}")
        zout.writestr("data/zeros.mmftable.json", b"0" * (64 * 1024 * 1024))   # 64 MiB of zeros compresses ~1000×
    with pytest.raises(PackageFormatError) as ei:
        open_figure_package(dest)
    assert "compression ratio" in str(ei.value)


def test_entry_count_limit(tmp_path, monkeypatch):
    from make_my_figure_core.package import security

    monkeypatch.setattr(security, "MAX_ENTRIES", 3)
    dest = str(tmp_path / "many.mmfpackage")
    with zipfile.ZipFile(dest, "w") as zout:
        for i in range(5):
            zout.writestr(f"f{i}.txt", b"x")
    with pytest.raises(PackageSecurityError):
        scan_zip(zipfile.ZipFile(dest))


def test_no_pickle_or_code_paths_in_reader():
    src_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "make_my_figure_core", "package")
    text = "".join(open(os.path.join(src_dir, f), encoding="utf-8").read() for f in os.listdir(src_dir) if f.endswith(".py"))
    for forbidden in ("import pickle", "pickle.load", "import marshal", "eval(", "exec(", "extractall(",
                      "importlib.import_module(", "subprocess"):
        assert forbidden not in text, forbidden


def test_table_encoding_precision_cases():
    df = pd.DataFrame({
        "f": [0.1, -0.0, np.nan, np.inf, -np.inf, 1.93094534810896e-14, 1e308, 5e-324, 0.30000000000000004, 17.000000000000004],
        "i": np.arange(10, dtype="int64") * 10**15,
        "u": np.arange(10, dtype="uint64"),
        "s": ["a", None, "NaN", "Infinity", "ünïcödé 🧬", "", "x,y", '"q"', "nan", " lead/trail "],
        "b": [True, False] * 5,
        "c": pd.Categorical(list("lhlmhlhmhl"), categories=["l", "m", "h"], ordered=True),
        "I": pd.array([1, None, 3, 4, 5, 6, 7, 8, 9, 10], dtype="Int64"),
        "d": pd.to_datetime(["2024-01-01", None, "2025-06-30 12:34:56.123456789", "1970-01-01", "2000-02-29",
                             "2024-12-31", "1999-01-01", "2001-09-11", "2030-01-01", "1969-12-31"], format="mixed"),
        "f32": np.array([0.1, 0.2, 0.3, 1e-8, 3.4e38, -0.0, 1.0, 2.0, 7.7, 9.9], dtype="float32"),
    })
    blob, warnings = table_to_json_bytes(df)
    back = table_from_json_bytes(blob)
    pd.testing.assert_frame_equal(df, back, check_exact=True, check_dtype=True, check_categorical=True)
    assert back["f"].to_numpy().tobytes() == df["f"].to_numpy().tobytes()      # bit-identical doubles incl. -0.0/NaN
    assert back["f32"].to_numpy().tobytes() == df["f32"].to_numpy().tobytes()
    assert warnings == []
    # deterministic bytes -> stable digest
    assert table_to_json_bytes(back)[0] == blob


def test_table_object_column_types_preserved():
    df = pd.DataFrame({"o": [1, "two", 3.5, None, True, 2.0, "8", float("nan"), pd.NA, pd.NaT]})
    back = table_from_json_bytes(table_to_json_bytes(df)[0])
    assert [type(x).__name__ for x in back["o"]] == [type(x).__name__ for x in df["o"]]
    assert back["o"].iloc[8] is pd.NA and back["o"].iloc[9] is pd.NaT


def test_string_columns_round_trip_under_every_pandas_string_dtype():
    """pandas >= 3 infers the NaN-backed ``str`` dtype for text; pandas 2 infers ``object`` and offers the
    nullable ``string`` dtype. Each must round-trip with its dtype intact on the pandas that wrote it
    (2026-09-17: text columns came back as ``object`` on pandas 3.0, failing the identity check)."""
    from make_my_figure_core.package import tabledata as T

    text = ["a", None, "NaN", "", "x,y", "ünïcödé 🧬"]
    frames = {"inferred": pd.DataFrame({"s": text}), "string": pd.DataFrame({"s": pd.array(text, dtype="string")})}
    if T._HAS_DEFAULT_STR_DTYPE:
        frames["str"] = pd.DataFrame({"s": pd.Series(text, dtype="str")})
    for label, df in frames.items():
        blob, warnings = table_to_json_bytes(df)
        back = table_from_json_bytes(blob)
        pd.testing.assert_frame_equal(df, back, check_exact=True, check_dtype=True), label
        assert warnings == [], label
        assert table_to_json_bytes(back)[0] == blob, label
    # a document written by pandas >= 3 (dtype "str") decodes on every pandas: text and missing values intact
    doc = {"kind": "string", "dtype": "str", "values": ["a", None, "b"]}
    s = T._decode_values(doc)
    assert s.tolist()[0] == "a" and s.tolist()[2] == "b" and pd.isna(s.iloc[1])
    assert str(s.dtype) == ("str" if T._HAS_DEFAULT_STR_DTYPE else "object")
