"""SampleMetadataSpec: a *confirmed* sample -> group mapping for a feature matrix.

Two ways to get here (both require explicit user confirmation):
  * upload a metadata table and confirm which columns are sample id / group /
    batch / paired id / display; or
  * build the assignment interactively (assign each value column to a group).

Frontend-agnostic, pure pandas. Groups/statistics are never run until this spec
is ``confirmed_by_user`` and its sample ids match the matrix value columns.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass
class SampleMetadataSpec:
    sample_id_column: Optional[str] = None
    sample_display_column: Optional[str] = None
    group_column: Optional[str] = None
    batch_column: Optional[str] = None
    paired_id_column: Optional[str] = None
    covariate_columns: List[str] = field(default_factory=list)
    sample_to_group: Dict[str, str] = field(default_factory=dict)
    confirmed_by_user: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SampleMetadataSpec":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (d or {}).items() if k in known})

    def groups(self) -> List[str]:
        seen: List[str] = []
        for g in self.sample_to_group.values():
            if str(g).strip() and g not in seen:
                seen.append(g)
        return seen

    def group_sizes(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for g in self.sample_to_group.values():
            if str(g).strip():
                out[g] = out.get(g, 0) + 1
        return out

    def samples_in_group(self, group: str) -> List[str]:
        return [s for s, g in self.sample_to_group.items() if g == group]

    def metadata_frame(self, *, sample_col: str = "sample", group_col: str = "group") -> pd.DataFrame:
        rows = [{sample_col: s, group_col: g}
                for s, g in self.sample_to_group.items() if str(g).strip()]
        return pd.DataFrame(rows, columns=[sample_col, group_col])


def metadata_from_assignment(sample_to_group: Dict[str, str]) -> SampleMetadataSpec:
    """Build a confirmed metadata spec from an in-app sample->group assignment."""
    clean = {str(s): str(g) for s, g in sample_to_group.items() if str(g).strip()}
    return SampleMetadataSpec(sample_id_column="sample", group_column="group",
                              sample_to_group=clean, confirmed_by_user=True)


def suggest_metadata_from_table(meta_df: pd.DataFrame, value_columns: List[str]
                                ) -> SampleMetadataSpec:
    """Suggest (do NOT confirm) sample-id / group columns from an uploaded table.

    Picks the metadata column whose values best overlap the matrix value-column
    names as the sample id, and a low-cardinality categorical column as the group.
    """
    cols = list(meta_df.columns)
    want = set(map(str, value_columns))
    sample_col = None
    best = -1
    for c in cols:
        overlap = sum(1 for v in meta_df[c].astype(str) if v in want)
        if overlap > best:
            best, sample_col = overlap, c
    group_col = None
    for c in cols:
        if c == sample_col:
            continue
        nun = meta_df[c].astype(str).nunique()
        if 2 <= nun <= max(2, len(cols) and len(meta_df) // 2 or 2):
            group_col = c
            break
    s2g: Dict[str, str] = {}
    if sample_col and group_col:
        for _, row in meta_df.iterrows():
            s = str(row[sample_col])
            if s in want:
                s2g[s] = str(row[group_col])
    return SampleMetadataSpec(sample_id_column=sample_col, group_column=group_col,
                              sample_to_group=s2g, confirmed_by_user=False)


def metadata_sample_match(meta: SampleMetadataSpec, value_columns: List[str]) -> Dict[str, Any]:
    """Report how well the metadata sample ids match the matrix value columns."""
    assigned = set(meta.sample_to_group)
    values = set(map(str, value_columns))
    return {
        "matched": sorted(assigned & values),
        "in_metadata_not_matrix": sorted(assigned - values),
        "in_matrix_not_metadata": sorted(values - assigned),
        "all_matched": bool(values) and values.issubset(assigned),
    }
