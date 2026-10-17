"""Mathematical transformations of numeric columns in an ordinary table.

The matrix workflow transforms every value column of a feature matrix. An
experimental table is different: one or two response columns sit beside
identifiers, factors and covariates, and only the columns the user names may
change. So a table transformation never touches an existing column. It adds a
derived column next to the original (``log10(total quantity)``) and the raw
column stays exactly as it was imported, so the user can plot or test either.

Nothing is decided for the user:

* the offset is explicit and defaults to **0** — no silent ``+ 1``;
* a value the transformation is undefined for (``x + offset <= 0`` for a log,
  ``< 0`` for a square root) is counted and shown before anything is applied,
  and the transformation is **refused** unless the user explicitly chooses to
  record those observations as missing;
* a column that is already on a log scale is not logged again.

Every confirmed transformation is recorded as a
:class:`~make_my_figure_core.matrix_workflow.PreprocessingStep` inside a
:class:`TablePreprocessingSpec`, which a Figure Package stores beside the raw
and derived tables and can replay to verify them.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from make_my_figure_core.matrix_workflow.preprocessing_spec import PreprocessingStep
from make_my_figure_core.version import __version__

# method -> (label template, base, needs_offset, domain)
#   domain: "positive" (x + offset > 0), "nonnegative" (x + offset >= 0), "any"
METHODS: Dict[str, Dict[str, Any]] = {
    "log2": {"label": "log2", "base": 2.0, "offset": True, "domain": "positive"},
    "log10": {"label": "log10", "base": 10.0, "offset": True, "domain": "positive"},
    "ln": {"label": "ln", "base": math.e, "offset": True, "domain": "positive"},
    "sqrt": {"label": "sqrt", "base": None, "offset": True, "domain": "nonnegative"},
    "zscore": {"label": "z-score", "base": None, "offset": False, "domain": "any"},
}
LOG_METHODS = {"log2", "log10", "ln"}
INVALID_POLICIES = ("refuse", "missing")

# Column-name words of a quantity that is already logarithmic. Matched as whole
# words: a substring test flagged "catalog_id" and "blog_views" as log values.
_ALREADY_LOG_WORDS = {"log", "log2", "log10", "ln", "lfc", "logfc", "log2fc", "log10fc", "neglog",
                      "neglog10", "mlog10", "logcpm", "log2cpm", "logp"}


class TransformError(ValueError):
    """A transformation that cannot be applied as requested."""


@dataclass(frozen=True)
class TableTransform:
    """One requested transformation of one numeric column."""

    column: str
    method: str
    offset: float = 0.0
    invalid: str = "refuse"                 # "refuse" | "missing"
    output_column: Optional[str] = None     # default: derived_column_name(...)
    ddof: int = 1                           # z-score: sample standard deviation

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TableTransform":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (d or {}).items() if k in known})

    @property
    def target(self) -> str:
        return self.output_column or derived_column_name(self.column, self.method, self.offset)


def available_methods() -> List[str]:
    return list(METHODS)


def _fmt_num(x: float) -> str:
    return f"{x:g}"


def derived_column_name(column: str, method: str, offset: float = 0.0) -> str:
    """``log10(total quantity)``, ``log2(count + 1)``, ``z-score(mass)``."""
    if method not in METHODS:
        raise TransformError(f"Unknown transformation {method!r}; choose one of {', '.join(METHODS)}.")
    inner = column if not offset else f"{column} + {_fmt_num(offset)}"
    return f"{METHODS[method]['label']}({inner})"


def looks_already_log(column: str) -> bool:
    import re

    words = re.split(r"[^a-z0-9]+", str(column).strip().lower())
    return any(w in _ALREADY_LOG_WORDS for w in words if w)


def _numeric(series: pd.Series) -> Tuple[np.ndarray, np.ndarray]:
    """(values as float, mask of entries that were non-numeric text)."""
    coerced = pd.to_numeric(series, errors="coerce")
    non_numeric = coerced.isna() & series.notna()
    return coerced.to_numpy(dtype="float64"), non_numeric.to_numpy()


@dataclass
class TransformPreview:
    """Everything the user should see before confirming a transformation."""

    column: str
    method: str
    offset: float
    output_column: str
    n_rows: int
    n_missing: int                  # missing in the original column
    n_non_numeric: int              # text that is not a number
    n_invalid: int                  # outside the method's domain
    invalid_rows: List[int]         # first few row positions (0-based) that are invalid
    n_valid: int                    # values that will be transformed
    original_min: Optional[float]
    original_max: Optional[float]
    transformed_min: Optional[float]
    transformed_max: Optional[float]
    can_apply: bool
    problems: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    original: List[Optional[float]] = field(default_factory=list)
    transformed: List[Optional[float]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _domain_mask(values: np.ndarray, method: str, offset: float) -> np.ndarray:
    """True where the value is present and inside the method's domain."""
    present = np.isfinite(values)
    domain = METHODS[method]["domain"]
    shifted = values + offset
    if domain == "positive":
        return present & (shifted > 0)
    if domain == "nonnegative":
        return present & (shifted >= 0)
    return present


def _compute(values: np.ndarray, valid: np.ndarray, method: str, offset: float, ddof: int) -> np.ndarray:
    out = np.full(values.shape, np.nan, dtype="float64")
    v = values[valid] + offset
    if method == "log2":
        out[valid] = np.log2(v)
    elif method == "log10":
        out[valid] = np.log10(v)
    elif method == "ln":
        out[valid] = np.log(v)
    elif method == "sqrt":
        out[valid] = np.sqrt(v)
    elif method == "zscore":
        x = values[valid]
        sd = float(np.std(x, ddof=ddof)) if x.size > ddof else float("nan")
        out[valid] = (x - float(np.mean(x))) / sd
    return out


def preview_transform(df: pd.DataFrame, t: TableTransform, *, already_transformed: Sequence[str] = (),
                      max_rows: int = 200) -> TransformPreview:
    """Describe exactly what applying ``t`` to ``df`` would do, without doing it."""
    if t.method not in METHODS:
        raise TransformError(f"Unknown transformation {t.method!r}; choose one of {', '.join(METHODS)}.")
    if t.column not in df.columns:
        raise TransformError(f"Column {t.column!r} is not in the table.")
    if t.invalid not in INVALID_POLICIES:
        raise TransformError(f"invalid must be one of {INVALID_POLICIES}, got {t.invalid!r}.")
    try:
        offset = float(t.offset or 0.0)
    except (TypeError, ValueError):
        raise TransformError(f"The offset must be a number, got {t.offset!r}.")
    if not math.isfinite(offset):
        raise TransformError("The offset must be a finite number.")
    if offset and not METHODS[t.method]["offset"]:
        raise TransformError(f"{t.method} does not take an offset.")

    values, non_numeric = _numeric(df[t.column])
    n = int(values.size)
    missing = (~np.isfinite(values)) & ~non_numeric
    valid = _domain_mask(values, t.method, offset)
    invalid = np.isfinite(values) & ~valid
    problems: List[str] = []
    notes: List[str] = []
    target = t.output_column or derived_column_name(t.column, t.method, offset)

    if int(non_numeric.sum()):
        problems.append(f"{int(non_numeric.sum())} value(s) in {t.column!r} are text, not numbers. "
                        "Fix them in the source table; they are not converted silently.")
    if t.method in LOG_METHODS and (t.column in already_transformed or looks_already_log(t.column)):
        problems.append(f"{t.column!r} already looks log-scaled. Taking the log of a log is almost never "
                        "intended; transform the original column instead.")
    if int(invalid.sum()):
        domain = METHODS[t.method]["domain"]
        need = "greater than 0" if domain == "positive" else "0 or greater"
        what = "x" if not offset else f"x + {_fmt_num(offset)}"
        msg = (f"{int(invalid.sum())} of {n} value(s) give {what} that is not {need}, so "
               f"{METHODS[t.method]['label']} is undefined for them (smallest value: "
               f"{_fmt_num(float(np.nanmin(values[invalid])))}).")
        if t.invalid == "missing":
            notes.append(msg + " They will be recorded as missing in the derived column; "
                         "the original values are kept.")
        else:
            problems.append(msg + " Choose an offset you can justify, a different transformation, "
                            "or explicitly record these observations as missing.")
    if t.method == "zscore":
        x = values[valid]
        with np.errstate(all="ignore"):
            sd = float(np.std(x, ddof=t.ddof)) if x.size > t.ddof else float("nan")
        if x.size <= t.ddof or sd == 0:
            problems.append(f"{t.column!r} has no spread (constant or too few values); a z-score is undefined.")
        elif not np.isfinite(sd):
            # R's scale() returns 0 for every value here (SD overflows to Inf):
            # a plausible-looking column of zeros. Refuse instead.
            problems.append(f"{t.column!r} spans too wide a range (up to {np.nanmax(np.abs(x)):g}) for its "
                            "standard deviation to be computed in double precision; a z-score would be "
                            "meaningless. Transform to a log scale first.")
    if target in df.columns:
        problems.append(f"The table already has a column named {target!r}.")
    if offset and t.method in LOG_METHODS:
        notes.append(f"Offset {_fmt_num(offset)} is added to every value before the logarithm "
                     "and is recorded with the result.")

    can_apply = not problems
    # Show the result for the values that are valid even when the transformation
    # is refused, so the user sees what they would get after fixing the problem.
    with np.errstate(all="ignore"):
        out = _compute(values, valid, t.method, offset, t.ddof)

    def _rng(a: np.ndarray, m: np.ndarray):
        sel = a[m & np.isfinite(a)]
        return (float(sel.min()), float(sel.max())) if sel.size else (None, None)

    omin, omax = _rng(values, np.isfinite(values))
    tmin, tmax = _rng(out, valid)

    def _cells(a):
        return [None if not np.isfinite(v) else float(v) for v in a[:max_rows]]

    return TransformPreview(
        column=t.column, method=t.method, offset=offset, output_column=target, n_rows=n,
        n_missing=int(missing.sum()), n_non_numeric=int(non_numeric.sum()),
        n_invalid=int(invalid.sum()),
        invalid_rows=[int(i) for i in np.flatnonzero(invalid) if i < max_rows],   # every shown row
        n_valid=int(valid.sum()), original_min=omin, original_max=omax,
        transformed_min=tmin, transformed_max=tmax, can_apply=can_apply,
        problems=problems, notes=notes, original=_cells(values), transformed=_cells(out))


def table_sha256(df: pd.DataFrame) -> str:
    """Content checksum of a table (column names, dtypes and values)."""
    from make_my_figure_core.package.tabledata import table_digest

    return table_digest(df)


def _sentence(t: TableTransform, offset: float) -> str:
    if t.method == "zscore":
        return f"{t.column!r} was z-scored (mean 0, SD 1; SD with ddof={t.ddof})"
    inner = "x" if not offset else f"x + {_fmt_num(offset)}"
    label = METHODS[t.method]["label"]
    return f"{t.column!r} was transformed as {label}({inner})"


@dataclass
class TablePreprocessingSpec:
    """How a derived table was made from a raw table. Replayable."""

    workflow: str = "table"
    source_name: Optional[str] = None
    source_sha256: Optional[str] = None             # checksum of the original file, when known
    source_sheet: Optional[str] = None
    source_table_digest: Optional[str] = None       # checksum of the raw table as loaded
    input_shape: Optional[List[int]] = None
    transforms: List[Dict[str, Any]] = field(default_factory=list)    # TableTransform dicts
    reshape: Optional[Dict[str, Any]] = None        # WideToLong dict: applied first, wide -> long
    preprocessing_steps: List[PreprocessingStep] = field(default_factory=list)
    derived_columns: List[str] = field(default_factory=list)
    column_roles: Optional[Dict[str, Any]] = None   # ColumnRoles.to_dict(), when assigned
    output_table_digest: Optional[str] = None
    output_shape: Optional[List[int]] = None
    warnings: List[str] = field(default_factory=list)
    method_summary: str = ""
    user_confirmed: bool = True
    created_at: Optional[str] = None
    app_version: str = __version__

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["preprocessing_steps"] = [s.to_dict() if isinstance(s, PreprocessingStep) else s
                                    for s in self.preprocessing_steps]
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TablePreprocessingSpec":
        d = dict(d or {})
        known = {f.name for f in fields(cls)}
        kw = {k: v for k, v in d.items() if k in known}
        kw["preprocessing_steps"] = [PreprocessingStep.from_dict(s) for s in d.get("preprocessing_steps", [])]
        return cls(**kw)

    @property
    def transform_objects(self) -> List[TableTransform]:
        return [TableTransform.from_dict(t) for t in self.transforms]

    @property
    def reshape_object(self):
        from make_my_figure_core.tabular.reshape import WideToLong

        return WideToLong.from_dict(self.reshape) if self.reshape else None


def apply_table_transforms(df: pd.DataFrame, transforms: Sequence[TableTransform], *,
                           source_name: Optional[str] = None, source_sha256: Optional[str] = None,
                           source_sheet: Optional[str] = None,
                           stamp_time: bool = True,
                           with_checksums: bool = True,
                           reshape=None) -> Tuple[pd.DataFrame, TablePreprocessingSpec]:
    """Return ``(derived_table, record)``. ``df`` is never modified.

    The derived table is the raw table with one new column per transformation,
    appended in order. Raises :class:`TransformError` — naming every problem —
    if any transformation cannot be applied as requested. ``with_checksums=False``
    skips the two table digests (1.4 s each for a million rows) for a working copy
    that is not being recorded - the dialog's analysis tab, a live preview.
    """
    sentences: List[str] = []
    reshape_step = None
    if reshape is not None:
        # A wide table is first gathered to long form (one row per observation);
        # column transformations then act on the long table.
        from make_my_figure_core.tabular.reshape import ReshapeError, wide_to_long

        try:
            derived, rpv = wide_to_long(df, reshape)
        except ReshapeError as exc:
            raise TransformError(str(exc)) from exc
        reshape_step = PreprocessingStep(
            step_id="wide_to_long", step_type="reshape", method_name="wide_to_long",
            parameters={**reshape.to_dict(), "id_columns_kept": rpv.id_columns, "levels": rpv.levels,
                        "n_rows_in": rpv.n_rows_in, "n_rows_out": rpv.n_rows_out,
                        "n_missing_dropped": rpv.n_missing_dropped},
            user_parameters=reshape.to_dict(), warnings=list(rpv.notes), user_confirmed=True)
        sentences.append(rpv.sentence)
    else:
        derived = df.copy()
    spec = TablePreprocessingSpec(
        source_name=source_name, source_sha256=source_sha256, source_sheet=source_sheet,
        source_table_digest=table_sha256(df) if with_checksums else None, input_shape=[int(df.shape[0]), int(df.shape[1])],
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds") if stamp_time else None)
    if reshape_step is not None:
        spec.reshape = reshape.to_dict()
        spec.preprocessing_steps.append(reshape_step)
        spec.warnings.extend(reshape_step.warnings)
    logged: List[str] = []
    for t in transforms:
        if t.column in spec.derived_columns:
            raise TransformError(f"{t.column!r} is a derived column; transform the original column instead.")
        pv = preview_transform(derived, t, already_transformed=logged)
        if not pv.can_apply:
            raise TransformError(" ".join(pv.problems))
        values, _ = _numeric(derived[t.column])
        valid = _domain_mask(values, t.method, pv.offset)
        derived[pv.output_column] = _compute(values, valid, t.method, pv.offset, t.ddof)
        params = {"column": t.column, "output_column": pv.output_column, "offset": pv.offset,
                  "base": METHODS[t.method]["base"], "invalid": t.invalid,
                  "n_valid": pv.n_valid, "n_invalid": pv.n_invalid, "n_missing": pv.n_missing}
        if t.method == "zscore":
            params["ddof"] = t.ddof
        step = PreprocessingStep(step_id=f"{t.method}:{t.column}", step_type="transform",
                                 method_name=t.method, parameters=params,
                                 user_parameters=TableTransform(t.column, t.method, pv.offset, t.invalid,
                                                                t.output_column, t.ddof).to_dict(),
                                 warnings=list(pv.notes), user_confirmed=True)
        spec.preprocessing_steps.append(step)
        spec.transforms.append(step.user_parameters)
        spec.derived_columns.append(pv.output_column)
        spec.warnings.extend(w for w in pv.notes if w not in spec.warnings)
        sentences.append(_sentence(t, pv.offset))
        if t.method in LOG_METHODS:
            logged.append(pv.output_column)
    spec.output_shape = [int(derived.shape[0]), int(derived.shape[1])]
    spec.output_table_digest = table_sha256(derived) if with_checksums else None
    spec.method_summary = ("; ".join(sentences) + ".") if sentences else "No transformation applied."
    return derived, spec


def replay(raw: pd.DataFrame, record: Dict[str, Any]) -> pd.DataFrame:
    """Re-run a stored :class:`TablePreprocessingSpec` on the raw table."""
    spec = TablePreprocessingSpec.from_dict(record)
    derived, _ = apply_table_transforms(raw, spec.transform_objects, stamp_time=False,
                                        reshape=spec.reshape_object)
    return derived


def file_sha256(path: str) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None
