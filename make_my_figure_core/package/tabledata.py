"""Lossless, dependency-free serialisation of a pandas DataFrame ("mmftable").

The portable figure package must hand the renderer *exactly* the table it was
given when the figure was exported: every double bit-for-bit (including NaN,
±Inf and negative zero), every missing value, every string, category order,
column order and row order. CSV cannot promise that (it has no dtype record and
no distinct token for "missing string"), and the columnar binary formats would
add a heavy optional dependency. So the package stores each table as a small
JSON document with an explicit per-column type record:

* floats are written with Python's shortest round-trip ``repr`` (exact for
  float64; float32 is widened and narrowed back exactly); NaN and ±Inf are the
  strings ``"NaN"``, ``"Infinity"``, ``"-Infinity"`` (strings are unambiguous
  inside a float column);
* integers are JSON integers (arbitrary precision, so int64/uint64 are exact);
  nullable integer/boolean columns write ``null`` for missing cells;
* strings are JSON strings, missing cells are ``null``;
* categoricals keep their categories (encoded recursively) and ordered flag;
* datetimes/timedeltas are int64 nanoseconds (plus the time zone);
* mixed ``object`` columns tag every non-string cell (``{"$t": "float", ...}``)
  so a number that pandas kept as an object round-trips as the same Python type.

The document is deterministic (sorted keys, fixed separators), which makes its
SHA-256 a stable *content digest* of the table — that digest is what the
manifest records and what the loader checks.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

TABLE_FORMAT = "make_my_figure.table"
TABLE_FORMAT_VERSION = 1


class TableEncodingError(ValueError):
    """Raised when a table cannot be encoded/decoded losslessly."""


# ----------------------------------------------------------------------------
# scalar helpers
# ----------------------------------------------------------------------------
def _enc_float(v: float) -> Any:
    v = float(v)
    if math.isnan(v):
        return "NaN"
    if math.isinf(v):
        return "Infinity" if v > 0 else "-Infinity"
    return v


def _dec_float(v: Any) -> float:
    if isinstance(v, str):
        if v == "NaN":
            return float("nan")
        if v == "Infinity":
            return float("inf")
        if v == "-Infinity":
            return float("-inf")
        raise TableEncodingError(f"unexpected float token {v!r}")
    if v is None:
        return float("nan")
    return float(v)


def _is_missing(v: Any) -> bool:
    if v is None:
        return True
    try:
        return bool(pd.isna(v)) if not isinstance(v, (list, tuple, dict, str, bytes)) else False
    except (TypeError, ValueError):
        return False


def _enc_object_cell(v: Any, warnings: List[str], colname: Any) -> Any:
    """Encode one cell of an ``object`` column with a type tag for non-strings."""
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if v is pd.NA:
        return {"$t": "NA"}
    if v is pd.NaT:
        return {"$t": "NaT"}
    if isinstance(v, (bool, np.bool_)):
        return {"$t": "bool", "v": bool(v)}
    if isinstance(v, (int, np.integer)):
        return {"$t": "int", "v": str(int(v))}
    if isinstance(v, (float, np.floating)):
        return {"$t": "float", "v": _enc_float(v)}
    if isinstance(v, pd.Timestamp):
        return {"$t": "timestamp", "v": v.isoformat()}
    if isinstance(v, (bytes, bytearray)):
        return {"$t": "bytes", "v": bytes(v).hex()}
    msg = f"column {colname!r}: value of type {type(v).__name__} stored as text"
    if msg not in warnings:
        warnings.append(msg)
    return {"$t": "str", "v": str(v), "orig_type": type(v).__name__}


def _dec_object_cell(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if isinstance(v, dict) and "$t" in v:
        t = v["$t"]
        if t == "bool":
            return bool(v["v"])
        if t == "int":
            return int(v["v"])
        if t == "float":
            return _dec_float(v["v"])
        if t == "timestamp":
            return pd.Timestamp(v["v"])
        if t == "bytes":
            return bytes.fromhex(v["v"])
        if t == "str":
            return str(v["v"])
        if t == "NA":
            return pd.NA
        if t == "NaT":
            return pd.NaT
    raise TableEncodingError(f"unexpected object cell {v!r}")

_STRING_DTYPE_NAMES = ("string", "string[python]", "string[pyarrow]", "str")


def _pandas_has_default_str_dtype() -> bool:
    try:
        return str(pd.Series(["a"], dtype="str").dtype) == "str"
    except Exception:  # pragma: no cover - very old pandas
        return False


_HAS_DEFAULT_STR_DTYPE = _pandas_has_default_str_dtype()


# ----------------------------------------------------------------------------
# column encoding
# ----------------------------------------------------------------------------
def _encode_values(s: pd.Series, warnings: List[str], colname: Any) -> Dict[str, Any]:
    dt = s.dtype
    col: Dict[str, Any] = {"dtype": str(dt)}
    if isinstance(dt, pd.CategoricalDtype):
        cats = _encode_values(pd.Series(dt.categories), warnings, colname)
        col.update(kind="category", categories=cats, ordered=bool(dt.ordered),
                   codes=[int(c) for c in s.cat.codes.to_numpy()])
        return col
    if pd.api.types.is_datetime64_any_dtype(dt):
        tz = getattr(dt, "tz", None)
        vals = s.dt.tz_convert("UTC") if tz is not None else s
        arr = vals.to_numpy(dtype="datetime64[ns]") if tz is None else vals.dt.tz_localize(None).to_numpy(dtype="datetime64[ns]")
        out = []
        for x in arr:
            out.append(None if np.isnat(x) else int(x.astype("int64")))
        col.update(kind="datetime", values=out, tz=str(tz) if tz is not None else None)
        return col
    if pd.api.types.is_timedelta64_dtype(dt):
        arr = s.to_numpy(dtype="timedelta64[ns]")
        col.update(kind="timedelta", values=[None if np.isnat(x) else int(x.astype("int64")) for x in arr])
        return col
    if pd.api.types.is_bool_dtype(dt):
        if str(dt) == "boolean":
            col.update(kind="bool", nullable=True, values=[None if pd.isna(x) else bool(x) for x in s.to_numpy(dtype=object)])
        else:
            col.update(kind="bool", nullable=False, values=[bool(x) for x in s.to_numpy()])
        return col
    if pd.api.types.is_integer_dtype(dt):
        if isinstance(dt, pd.api.extensions.ExtensionDtype):
            col.update(kind="int", nullable=True, values=[None if pd.isna(x) else int(x) for x in s.to_numpy(dtype=object)])
        else:
            col.update(kind="int", nullable=False, values=[int(x) for x in s.to_numpy()])
        return col
    if pd.api.types.is_float_dtype(dt):
        if isinstance(dt, pd.api.extensions.ExtensionDtype):   # Float64 etc.
            col.update(kind="float", nullable=True, values=[None if pd.isna(x) else _enc_float(x) for x in s.to_numpy(dtype=object)])
        else:
            col.update(kind="float", nullable=False, values=[_enc_float(x) for x in s.to_numpy(dtype="float64")])
        return col
    if pd.api.types.is_string_dtype(dt) and str(dt) in _STRING_DTYPE_NAMES:
        # "string"/"string[...]" are the nullable extension dtype; "str" is the pandas >= 3 default
        # string dtype (NaN-backed). Both round-trip as kind "string" with their dtype name recorded.
        col.update(kind="string", values=[None if pd.isna(x) else str(x) for x in s.to_numpy(dtype=object)])
        return col
    if dt == object:
        col.update(kind="object", values=[_enc_object_cell(x, warnings, colname) for x in s.to_numpy(dtype=object)])
        return col
    # Anything else (period, interval, sparse ...): stored as text with a warning.
    warnings.append(f"column {colname!r}: dtype {dt} is stored as text")
    col.update(kind="object", dtype="object",
               values=[None if _is_missing(x) else {"$t": "str", "v": str(x), "orig_type": str(dt)} for x in s.to_numpy(dtype=object)])
    return col


def _decode_values(col: Dict[str, Any], n: Optional[int] = None) -> pd.Series:
    kind = col["kind"]
    dtype = col.get("dtype", "object")
    if kind == "category":
        cats = _decode_values(col["categories"])
        codes = np.asarray(col["codes"], dtype="int64")
        cat = pd.Categorical.from_codes(codes, categories=pd.Index(cats), ordered=bool(col.get("ordered", False)))
        return pd.Series(cat)
    if kind == "datetime":
        vals = np.array([np.datetime64("NaT", "ns") if v is None else np.datetime64(int(v), "ns") for v in col["values"]],
                        dtype="datetime64[ns]")
        s = pd.Series(vals)
        if col.get("tz"):
            s = s.dt.tz_localize("UTC").dt.tz_convert(col["tz"])
        return s
    if kind == "timedelta":
        vals = np.array([np.timedelta64("NaT", "ns") if v is None else np.timedelta64(int(v), "ns") for v in col["values"]],
                        dtype="timedelta64[ns]")
        return pd.Series(vals)
    if kind == "bool":
        if col.get("nullable"):
            return pd.Series([None if v is None else bool(v) for v in col["values"]], dtype="boolean")
        return pd.Series(np.asarray(col["values"], dtype=bool))
    if kind == "int":
        if col.get("nullable"):
            return pd.Series([None if v is None else int(v) for v in col["values"]], dtype=dtype)
        return pd.Series(np.asarray([int(v) for v in col["values"]], dtype=dtype))
    if kind == "float":
        if col.get("nullable"):
            return pd.Series([None if v is None else _dec_float(v) for v in col["values"]], dtype=dtype)
        arr = np.asarray([_dec_float(v) for v in col["values"]], dtype="float64")
        return pd.Series(arr.astype(dtype) if dtype != "float64" else arr)
    if kind == "string":
        values = [None if v is None else str(v) for v in col["values"]]
        if dtype == "str" and not _HAS_DEFAULT_STR_DTYPE:
            # written by pandas >= 3; this pandas has no "str" dtype - object is what it would infer
            return pd.Series(values, dtype=object)
        return pd.Series(values, dtype=dtype)
    if kind == "object":
        return pd.Series([_dec_object_cell(v) for v in col["values"]], dtype=object)
    raise TableEncodingError(f"unknown column kind {kind!r}")


def _encode_label(lbl: Any) -> Any:
    if isinstance(lbl, tuple):
        return {"$tuple": [_encode_label(x) for x in lbl]}
    if isinstance(lbl, (np.integer,)):
        return {"$int": int(lbl)}
    if isinstance(lbl, (int,)) and not isinstance(lbl, bool):
        return {"$int": lbl}
    if isinstance(lbl, (float, np.floating)):
        return {"$float": _enc_float(lbl)}
    if lbl is None:
        return None
    return str(lbl)


def _decode_label(v: Any) -> Any:
    if isinstance(v, dict):
        if "$tuple" in v:
            return tuple(_decode_label(x) for x in v["$tuple"])
        if "$int" in v:
            return int(v["$int"])
        if "$float" in v:
            return _dec_float(v["$float"])
    return v


# ----------------------------------------------------------------------------
# public API
# ----------------------------------------------------------------------------
def encode_table(df: pd.DataFrame) -> Tuple[Dict[str, Any], List[str]]:
    """Encode ``df`` as an mmftable document. Returns ``(document, warnings)``."""
    if not isinstance(df, pd.DataFrame):
        raise TableEncodingError("encode_table expects a pandas DataFrame")
    warnings: List[str] = []
    columns = []
    for i in range(df.shape[1]):
        s = df.iloc[:, i]
        col = {"name": _encode_label(df.columns[i])}
        col.update(_encode_values(s, warnings, df.columns[i]))
        columns.append(col)
    idx = df.index
    if isinstance(idx, pd.RangeIndex):
        index: Dict[str, Any] = {"kind": "range", "start": int(idx.start), "stop": int(idx.stop),
                                 "step": int(idx.step), "name": _encode_label(idx.name)}
    elif isinstance(idx, pd.MultiIndex):
        index = {"kind": "multi", "names": [_encode_label(n) for n in idx.names],
                 "levels": [_encode_values(pd.Series(idx.get_level_values(i)), warnings, f"index[{i}]")
                            for i in range(idx.nlevels)]}
    else:
        index = {"kind": "values", "name": _encode_label(idx.name)}
        index.update(_encode_values(pd.Series(idx), warnings, "index"))
    doc = {
        "format": TABLE_FORMAT,
        "format_version": TABLE_FORMAT_VERSION,
        "n_rows": int(df.shape[0]),
        "n_columns": int(df.shape[1]),
        "columns_nlevels": int(getattr(df.columns, "nlevels", 1)),
        "columns_names": [_encode_label(n) for n in (df.columns.names if hasattr(df.columns, "names") else [None])],
        "columns": columns,
        "index": index,
    }
    return doc, warnings


def decode_table(doc: Dict[str, Any]) -> pd.DataFrame:
    """Rebuild the DataFrame from an mmftable document (exact dtypes and values)."""
    if not isinstance(doc, dict) or doc.get("format") != TABLE_FORMAT:
        raise TableEncodingError("not an mmftable document")
    if int(doc.get("format_version", 0)) != TABLE_FORMAT_VERSION:
        raise TableEncodingError(f"unsupported table format version {doc.get('format_version')}")
    n = int(doc["n_rows"])
    data = {}
    names = []
    for i, col in enumerate(doc["columns"]):
        s = _decode_values(col, n)
        if len(s) != n:
            raise TableEncodingError(f"column {col.get('name')!r} has {len(s)} values, expected {n}")
        data[i] = s
        names.append(_decode_label(col["name"]))
    df = pd.DataFrame(data) if data else pd.DataFrame(index=range(n))
    if doc.get("columns_nlevels", 1) > 1:
        df.columns = pd.MultiIndex.from_tuples(names, names=[_decode_label(x) for x in doc.get("columns_names", [])])
    else:
        df.columns = pd.Index(names, name=_decode_label((doc.get("columns_names") or [None])[0]))
    idx = doc["index"]
    if idx["kind"] == "range":
        df.index = pd.RangeIndex(start=idx["start"], stop=idx["stop"], step=idx["step"], name=_decode_label(idx.get("name")))
    elif idx["kind"] == "multi":
        levels = [_decode_values(lv) for lv in idx["levels"]]
        df.index = pd.MultiIndex.from_arrays(levels, names=[_decode_label(x) for x in idx["names"]])
    else:
        s = _decode_values(idx)
        df.index = pd.Index(s, name=_decode_label(idx.get("name")))
    return df


def table_to_json_bytes(df: pd.DataFrame) -> Tuple[bytes, List[str]]:
    """Deterministic UTF-8 JSON bytes for ``df`` (sorted keys, compact separators)."""
    doc, warnings = encode_table(df)
    raw = json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return raw.encode("utf-8"), warnings


def table_from_json_bytes(blob: bytes) -> pd.DataFrame:
    return decode_table(json.loads(blob.decode("utf-8")))


def table_digest(df: pd.DataFrame) -> str:
    """SHA-256 of the canonical mmftable encoding — a content digest of the table."""
    blob, _ = table_to_json_bytes(df)
    return hashlib.sha256(blob).hexdigest()


def table_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """Shape / column / dtype summary recorded in the manifest."""
    return {
        "n_rows": int(df.shape[0]),
        "n_columns": int(df.shape[1]),
        "columns": [str(c) for c in df.columns],
        "dtypes": {str(c): str(t) for c, t in df.dtypes.items()},
        "n_missing": int(df.isna().sum().sum()),
    }
