"""Wide → long reshaping of an ordinary table (tidyr's ``pivot_longer``).

A wide table keeps one row per plant (or animal, plot, colony) and one column per
repeated measurement::

    Species    Age    Nitrogen  Replicate  Month_4  Month_6  Month_8  Month_10
    Species_A  Old    High N    1          17.36    21.94    29.76    34.58

The group-comparison plots, facet grids and statistics need one row per
observation::

    Species    Age    Nitrogen  Replicate  Month  Growth_cm
    Species_A  Old    High N    1          4      17.36
    Species_A  Old    High N    1          6      21.94

:func:`wide_to_long` builds that table from the wide one. The wide table is never
modified: the long table is a new frame, every parameter is recorded in a
:class:`WideToLong`, and the record replays to the same table.

Nothing is guessed silently. :func:`suggest_wide_to_long` proposes the gathered
columns from their names ("Month_4", "Month_6" → ``Month`` = 4, 6), and
:func:`preview_wide_to_long` reports every problem before anything is applied:
a name already used by a kept column, gathered columns mixing text and numbers,
column names that do not split into the requested parts.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field, fields
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

_SEPARATORS = "_-. "
_STEM = re.compile(r"^(?P<stem>.*?[A-Za-z][A-Za-z ]*?)(?P<sep>[_\-. ]?)(?P<level>\d+(?:\.\d+)?)$")


@dataclass(frozen=True)
class WideToLong:
    """One wide → long reshape: which columns are gathered and what the new columns are called.

    ``names_to`` are the new column(s) that hold the gathered column names; with
    ``names_sep`` each name is split at that separator into one part per entry
    (``"A_Young"`` → ``Species = A``, ``Age = Young``). ``names_prefix`` is removed
    from every name first ("Month_4" → "4"). ``numeric_names`` turns the names into
    numbers when every one of them is a number. ``values_to`` holds the values.
    Every other column is kept and repeated on each row (``id_columns``; ``None``
    keeps them all).
    """

    value_columns: Tuple[str, ...]
    names_to: Tuple[str, ...] = ("name",)
    values_to: str = "value"
    names_prefix: str = ""
    names_sep: Optional[str] = None
    numeric_names: bool = True
    drop_missing: bool = True
    id_columns: Optional[Tuple[str, ...]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["value_columns"] = list(self.value_columns)
        d["names_to"] = list(self.names_to)
        d["id_columns"] = None if self.id_columns is None else list(self.id_columns)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WideToLong":
        known = {f.name for f in fields(cls)}
        kw = {k: v for k, v in (d or {}).items() if k in known}
        for key in ("value_columns", "names_to"):
            if key in kw:
                kw[key] = tuple(kw[key])
        if kw.get("id_columns") is not None:
            kw["id_columns"] = tuple(kw["id_columns"])
        return cls(**kw)


@dataclass
class ReshapePreview:
    """What :func:`wide_to_long` would do, and whether it can."""

    can_apply: bool
    n_rows_in: int = 0
    n_rows_out: int = 0
    n_missing_dropped: int = 0
    id_columns: List[str] = field(default_factory=list)
    new_columns: List[str] = field(default_factory=list)
    levels: Dict[str, List[Any]] = field(default_factory=dict)
    problems: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    sentence: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ReshapeError(ValueError):
    """A reshape that cannot be applied as requested."""


# --- suggestion -------------------------------------------------------------------------------

@dataclass
class ReshapeSuggestion:
    spec: WideToLong
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {"spec": self.spec.to_dict(), "reason": self.reason}


def suggest_wide_to_long(df: pd.DataFrame, *, min_columns: int = 2) -> Optional[ReshapeSuggestion]:
    """Propose a reshape when numeric columns share a name stem with a number after it.

    ``Month_4, Month_6, Month_8, Month_10`` → gather them into ``Month`` (4, 6, 8, 10)
    and ``value``. Returns ``None`` when no such family of at least ``min_columns``
    numeric columns exists; the user can still choose columns by hand.
    """
    families: Dict[Tuple[str, str], List[str]] = {}
    for c in df.columns:
        if not pd.api.types.is_numeric_dtype(df[c]):
            continue
        m = _STEM.match(str(c).strip())
        if m:
            families.setdefault((m.group("stem"), m.group("sep")), []).append(c)
    families = {k: v for k, v in families.items() if len(v) >= min_columns}
    if not families:
        return None
    (stem, sep), cols = max(families.items(), key=lambda kv: (len(kv[1]), -list(df.columns).index(kv[1][0])))
    name = stem.strip(_SEPARATORS) or "name"
    if name in df.columns and name not in cols:
        name = f"{name} (from columns)"
    spec = WideToLong(value_columns=tuple(cols), names_to=(name,), values_to="value",
                      names_prefix=f"{stem}{sep}", numeric_names=True)
    shown = ", ".join(map(str, cols[:4])) + (", …" if len(cols) > 4 else "")
    return ReshapeSuggestion(spec, f"{len(cols)} numeric columns ({shown}) look like one measurement "
                                   f"repeated over {name!r}. Gathering them gives one row per observation.")


# --- core -------------------------------------------------------------------------------------

def _as_number(text: str) -> Optional[float]:
    try:
        v = float(str(text).strip())
    except (TypeError, ValueError):
        return None
    return v if np.isfinite(v) else None


def _name_parts(spec: WideToLong) -> Tuple[Dict[str, List[str]], List[str]]:
    """``{column: [part per names_to]}`` and problems."""
    parts: Dict[str, List[str]] = {}
    problems: List[str] = []
    bad: List[str] = []
    for c in spec.value_columns:
        name = str(c)
        if spec.names_prefix and name.startswith(spec.names_prefix):
            name = name[len(spec.names_prefix):]
        if spec.names_sep:
            split = name.split(spec.names_sep)
            if len(split) != len(spec.names_to):
                bad.append(str(c))
                continue
            parts[c] = split
        else:
            parts[c] = [name]
    if bad:
        problems.append(f"{len(bad)} column name(s) do not split at {spec.names_sep!r} into "
                        f"{len(spec.names_to)} part(s) ({', '.join(spec.names_to)}): "
                        f"{', '.join(map(repr, bad[:5]))}{' …' if len(bad) > 5 else ''}.")
    if not spec.names_sep and len(spec.names_to) > 1:
        problems.append("Several names_to columns need a separator to split the column names at.")
    return parts, problems


def _converted_levels(parts: Dict[str, List[str]], spec: WideToLong) -> Dict[str, Dict[str, Any]]:
    """Per names_to column: {gathered column: level}. Numbers when every level is one."""
    out: Dict[str, Dict[str, Any]] = {}
    for i, target in enumerate(spec.names_to):
        raw = {c: p[i] for c, p in parts.items()}
        nums = {c: _as_number(v) for c, v in raw.items()}
        if spec.numeric_names and raw and all(v is not None for v in nums.values()):
            out[target] = {c: (int(v) if float(v).is_integer() else v) for c, v in nums.items()}
        else:
            out[target] = raw
    return out


def preview_wide_to_long(df: pd.DataFrame, spec: WideToLong) -> ReshapePreview:
    """Check ``spec`` against ``df`` and describe the result, without building it."""
    pv = ReshapePreview(can_apply=False, n_rows_in=int(len(df)))
    cols = list(df.columns)
    gathered = list(spec.value_columns)
    missing = [c for c in gathered if c not in cols]
    if missing:
        pv.problems.append(f"Column(s) not in the table: {', '.join(map(repr, missing))}.")
    if len(gathered) < 2:
        pv.problems.append("Choose at least two columns to gather.")
    if len(set(gathered)) != len(gathered):
        pv.problems.append("A column was chosen twice.")
    ids = [c for c in (spec.id_columns if spec.id_columns is not None else cols) if c not in gathered]
    absent_ids = [c for c in ids if c not in cols]
    if absent_ids:
        pv.problems.append(f"Kept column(s) not in the table: {', '.join(map(repr, absent_ids))}.")
    pv.id_columns = [c for c in ids if c in cols]
    new = list(spec.names_to) + [spec.values_to]
    blank = [n for n in new if not str(n).strip()]
    if blank:
        pv.problems.append("Every new column needs a name.")
    if len(set(new)) != len(new):
        pv.problems.append(f"The new columns need different names (got {', '.join(map(repr, new))}).")
    clash = [n for n in new if n in pv.id_columns]
    if clash:
        pv.problems.append(f"{', '.join(map(repr, clash))} is already a column of the table; choose another "
                           "name for the new column.")
    present = [c for c in gathered if c in cols]
    if present:
        kinds = {c: pd.api.types.is_numeric_dtype(df[c]) for c in present}
        if len(set(kinds.values())) > 1:
            text = [c for c, k in kinds.items() if not k]
            pv.problems.append(f"The gathered columns mix numbers and text ({', '.join(map(repr, text[:5]))} "
                               "hold text), so their values cannot share one column.")
    parts, part_problems = _name_parts(spec)
    pv.problems.extend(part_problems)
    if pv.problems:
        return pv
    levels = _converted_levels(parts, spec)
    for target, m in levels.items():
        vals = list(dict.fromkeys(m.values()))
        pv.levels[target] = vals
        if len(vals) == 1:
            pv.notes.append(f"Every gathered column gives {target!r} the same value ({vals[0]!r}).")
    combos = {tuple(levels[t][c] for t in spec.names_to) for c in present}
    if len(combos) < len(present):
        pv.problems.append(f"Two gathered columns give the same {' / '.join(spec.names_to)}; after removing "
                           f"the prefix {spec.names_prefix!r} their names coincide.")
        return pv
    n_missing = int(df[present].isna().sum().sum())
    pv.n_missing_dropped = n_missing if spec.drop_missing else 0
    pv.n_rows_out = int(len(df) * len(present) - pv.n_missing_dropped)
    pv.new_columns = new
    if n_missing:
        pv.notes.append(f"{n_missing} empty cell(s) in the gathered columns "
                        + ("are left out (no observation)." if spec.drop_missing else "are kept as missing values."))
    pv.sentence = _sentence(spec, pv)
    pv.can_apply = True
    return pv


def _sentence(spec: WideToLong, pv: ReshapePreview) -> str:
    cols = list(spec.value_columns)
    shown = ", ".join(map(repr, cols[:3])) + (f" … {cols[-1]!r}" if len(cols) > 3 else "")
    lv = "; ".join(f"{t} = {', '.join(map(str, v[:6]))}{' …' if len(v) > 6 else ''}"
                   for t, v in pv.levels.items())
    return (f"The wide table ({pv.n_rows_in} rows) was reshaped to long form: the {len(cols)} columns {shown} "
            f"were gathered into {', '.join(map(repr, spec.names_to))} ({lv}) and {spec.values_to!r}, "
            f"with {', '.join(map(repr, pv.id_columns)) or 'no other columns'} repeated on each row "
            f"({pv.n_rows_out} rows" + (f"; {pv.n_missing_dropped} empty cells left out" if pv.n_missing_dropped
                                        else "") + ")")


def wide_to_long(df: pd.DataFrame, spec: WideToLong) -> Tuple[pd.DataFrame, ReshapePreview]:
    """Return ``(long_table, preview)``. ``df`` is never modified.

    Rows stay in the order of the wide table, each wide row followed by its
    gathered values in column order (as ``tidyr::pivot_longer``). Raises
    :class:`ReshapeError` naming every problem when the reshape cannot be done.
    """
    pv = preview_wide_to_long(df, spec)
    if not pv.can_apply:
        raise ReshapeError(" ".join(pv.problems))
    present = list(spec.value_columns)
    parts, _ = _name_parts(spec)
    levels = _converted_levels(parts, spec)
    n, k = len(df), len(present)
    ids = df[pv.id_columns]
    out = ids.loc[ids.index.repeat(k)].reset_index(drop=True)
    for target in spec.names_to:
        out[target] = pd.Series([levels[target][c] for c in present] * n)
        if all(isinstance(v, (int, np.integer)) for v in levels[target].values()):
            out[target] = out[target].astype("int64")
    values = df[present].to_numpy().reshape(-1)
    out[spec.values_to] = pd.Series(values)
    if all(pd.api.types.is_numeric_dtype(df[c]) for c in present):
        out[spec.values_to] = pd.to_numeric(out[spec.values_to])
    if spec.drop_missing:
        out = out[out[spec.values_to].notna()].reset_index(drop=True)
    return out, pv
