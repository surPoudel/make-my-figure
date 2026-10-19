"""Browser app: recorded column transformations and a factorial design check.

The same engine as the desktop "Prepare table" dialog
(``make_my_figure_core.tabular`` and ``statistics.factorial``): a transformation
adds a derived column next to the original, offsets are explicit and default to
0, invalid values are refused unless the user chooses to record them as missing,
and the factorial check explains a non-estimable design instead of computing it.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

from make_my_figure_core.io.loaders import table_info_from_dataframe
from make_my_figure_core.statistics.factorial import check_design, factorial_anova, model_coefficients
from make_my_figure_core.statistics.models import StatsError
from make_my_figure_core.tabular import (
    METHODS,
    TableTransform,
    TransformError,
    WideToLong,
    apply_table_transforms,
    preview_transform,
    preview_wide_to_long,
    suggest_wide_to_long,
    wide_to_long,
)

_LABELS = {"log10": "log10(x)", "log2": "log2(x)", "ln": "ln(x)", "sqrt": "√x", "zscore": "z-score"}
_KEY = "_tbl_transforms"
_KEY_RESHAPE = "_tbl_reshape"
_KEY_DIGEST = "_tbl_raw_digest"


def _fingerprint(raw: pd.DataFrame) -> str:
    """A fast change key for the session (the full table digest takes 1.4 s per million
    rows and would run on every rerun); the recorded checksum is still the full one."""
    rows = int(pd.util.hash_pandas_object(raw, index=False).sum() % (1 << 61))
    return f"{raw.shape}|{list(map(str, raw.columns))}|{rows}"


def _transforms_for(raw: pd.DataFrame) -> List[Dict[str, Any]]:
    digest = _fingerprint(raw)
    if st.session_state.get(_KEY_DIGEST) != digest:       # a different table: start clean
        st.session_state[_KEY_DIGEST] = digest
        st.session_state[_KEY] = []
        st.session_state[_KEY_RESHAPE] = None
    return st.session_state.setdefault(_KEY, [])


def _render_reshape(raw: pd.DataFrame) -> Optional[WideToLong]:
    """The Wide → long expander. Returns the recorded reshape (``None``: the wide table is used)."""
    current = st.session_state.get(_KEY_RESHAPE)
    current = WideToLong.from_dict(current) if current else None
    sug = suggest_wide_to_long(raw) if current is None else None
    title = "↕ Wide → long" + (" — suggested for this table" if sug else "") + (" — applied" if current else "")
    with st.expander(title, expanded=False):
        st.caption("For a wide table: one row per plant/animal and one column per repeated measurement "
                   "(Month_4, Month_6, …). The chosen columns become one column for their name (Month = 4, "
                   "6, …) and one for the value; every other column is repeated on each row. The wide "
                   "table is not changed, and the reshape is recorded in the Figure Package.")
        if sug:
            st.info("Suggested: " + sug.reason)
        start = current or (sug.spec if sug else None)
        cols = list(raw.columns)
        chosen = st.multiselect("Columns to gather", cols, default=list(start.value_columns) if start else [],
                                key="rs_cols")
        a, b = st.columns(2)
        names = a.text_input("Column names go to", ", ".join(start.names_to) if start else "name", key="rs_names",
                             help="Several names separated by commas split each column name at the separator.")
        values = b.text_input("Values go to", start.values_to if start else "value", key="rs_values")
        c, d = st.columns(2)
        prefix = c.text_input("Remove prefix", start.names_prefix if start else "", key="rs_prefix")
        sep = d.text_input("Split names at", (start.names_sep or "") if start else "", key="rs_sep")
        numeric = st.checkbox("Names that are all numbers become numbers", value=start.numeric_names if start
                              else True, key="rs_numeric")
        drop = st.checkbox("Leave out empty cells", value=start.drop_missing if start else True, key="rs_drop")
        spec = WideToLong(value_columns=tuple(chosen),
                          names_to=tuple(n.strip() for n in names.split(",") if n.strip()) or ("name",),
                          values_to=values.strip(), names_prefix=prefix, names_sep=sep or None,
                          numeric_names=numeric, drop_missing=drop)
        pv = preview_wide_to_long(raw, spec)
        for p in pv.problems:
            st.error(p)
        if pv.can_apply:
            st.markdown(f"**{pv.n_rows_in} rows → {pv.n_rows_out} rows.** " + " ".join(pv.notes))
            st.dataframe(wide_to_long(raw.head(12), spec)[0].head(12), use_container_width=True, height=220)
        e, f = st.columns(2)
        if e.button("Reshape and use", key="rs_apply", disabled=not pv.can_apply):
            st.session_state[_KEY_RESHAPE] = spec.to_dict()
            st.rerun()
        if current is not None and f.button("Use the wide table", key="rs_clear"):
            st.session_state[_KEY_RESHAPE] = None
            st.rerun()
    return current


def render_table_tools(table_info, table_name: str) -> Tuple[Any, str, Optional[Any], pd.DataFrame]:
    """Draw the expanders; return ``(table_info, table_name, record_or_None, raw_df)``.

    ``raw_df`` is always the table as loaded (a wide table stays wide); a recorded
    reshape and the column transformations both act on it through the record.
    """
    raw = table_info.dataframe
    transforms = _transforms_for(raw)
    reshape = _render_reshape(raw)
    base = raw
    if reshape is not None:
        try:
            base = wide_to_long(raw, reshape)[0]
        except Exception as exc:  # noqa: BLE001
            st.error(f"The recorded reshape no longer applies: {exc}")
            reshape = None
    if reshape is not None:
        # Transformations recorded before the reshape survive only on columns that still exist.
        st.session_state[_KEY] = [x for x in transforms if x.get("column") in base.columns]
        transforms = st.session_state[_KEY]
    record = None
    with st.expander("📋 Prepare table — transform columns, check a factorial design", expanded=False):
        st.caption("For an ordinary experimental table. A transformation adds a NEW column beside the "
                   "original; the original values are never changed, and every step is recorded in the "
                   "Figure Package. To only *display* raw values on a log scale, use ③ Axes ▸ axis "
                   "scale instead.")
        numeric = [str(c) for c in base.columns if pd.api.types.is_numeric_dtype(base[c])]
        if numeric:
            c1, c2, c3 = st.columns(3)
            col = c1.selectbox("Column", numeric, key="tbl_col")
            method = c2.selectbox("Transformation", list(METHODS), format_func=lambda m: _LABELS.get(m, m),
                                  key="tbl_method")
            offset = c3.number_input("Offset (added before the transformation)", value=0.0, format="%g",
                                     key="tbl_offset", disabled=not METHODS[method]["offset"])
            invalid = st.radio("Values the transformation is undefined for",
                               ["refuse", "missing"], horizontal=True, key="tbl_invalid",
                               format_func=lambda v: ("Refuse (fix the data or choose an offset)" if v == "refuse"
                                                      else "Record as missing in the new column"))
            t = TableTransform(col, method, float(offset) if METHODS[method]["offset"] else 0.0, invalid)
            try:
                pv = preview_transform(base, t, already_transformed=[TableTransform.from_dict(x).target
                                                                    for x in transforms])
                st.markdown(f"**{pv.output_column}** — valid {pv.n_valid} · invalid {pv.n_invalid} · "
                            f"missing {pv.n_missing}")
                for n in pv.notes:
                    st.caption(n)
                for p in pv.problems:
                    st.error(p)
                st.dataframe(pd.DataFrame({f"{col} (original)": pv.original,
                                           pv.output_column: pv.transformed}).head(50),
                             use_container_width=True, height=220)
                dup = any(TableTransform.from_dict(x).target == pv.output_column for x in transforms)
                if st.button("Add this transformation", key="tbl_add", disabled=not pv.can_apply or dup):
                    transforms.append(t.to_dict())
                    st.rerun()
            except TransformError as exc:
                st.error(str(exc))
        else:
            st.caption("This table has no numeric columns to transform.")
        if transforms:
            st.markdown("**Transformations applied (each adds a column):** " +
                        ", ".join(f"`{TableTransform.from_dict(x).target}`" for x in transforms))
            if st.button("Remove all transformations", key="tbl_clear"):
                st.session_state[_KEY] = []
                st.rerun()
        if transforms or reshape is not None:
            key = (st.session_state.get(_KEY_DIGEST), json.dumps(transforms, sort_keys=True), table_name,
                   json.dumps(reshape.to_dict() if reshape else None, sort_keys=True))
            cached = st.session_state.get("_tbl_derived_cache")
            if cached is not None and cached[0] == key:
                derived, record = cached[1], cached[2]
            else:
                try:
                    derived, record = apply_table_transforms(
                        raw, [TableTransform.from_dict(x) for x in transforms], source_name=table_name,
                        reshape=reshape)
                    st.session_state["_tbl_derived_cache"] = (key, derived, record)
                except TransformError as exc:
                    st.error(str(exc))
                    derived, record = None, None
            if derived is not None:
                table_info = table_info_from_dataframe(derived, f"{table_name} (derived)")
                table_name = f"{table_name} (derived)"
                stem = "long_table" if reshape is not None and not transforms else "derived_table"
                d1, d2 = st.columns(2)
                d1.download_button(f"Download {stem.replace('_', ' ')} (CSV)",
                                   derived.to_csv(index=False).encode("utf-8"),
                                   file_name=f"{stem}.csv", mime="text/csv", key="tbl_dl_csv")
                d2.download_button("Download transformation record (JSON)",
                                   json.dumps(record.to_dict(), indent=2, default=str).encode("utf-8"),
                                   file_name=f"{stem}.transformations.json", mime="application/json",
                                   key="tbl_dl_json")

        st.markdown("---\n**Factorial design check / ANOVA**")
        frame = table_info.dataframe
        cols = [str(c) for c in frame.columns]
        nums = [c for c in cols if pd.api.types.is_numeric_dtype(frame[c])]
        if nums:
            a1, a2 = st.columns(2)
            response = a1.selectbox("Response", nums, key="tbl_resp")
            factors = a2.multiselect("Factors (up to 3)", cols, max_selections=3, key="tbl_factors")
            b1, b2, b3, b4 = st.columns(4)
            covs = b1.multiselect("Covariates", nums, key="tbl_covs")
            subject = b2.selectbox("Subject / colony", ["(none)"] + cols, key="tbl_subject")
            inter = b3.radio("Model", ["full", "main"], key="tbl_inter",
                             format_func=lambda v: "Full factorial" if v == "full" else "Main effects")
            ss = b4.radio("Sums of squares", [2, 1, 3], key="tbl_ss",
                          format_func=lambda v: f"Type {({1: 'I', 2: 'II', 3: 'III'})[v]}",
                          help="Identical when every combination has the same n. Type I is sequential "
                               "(factor order matters); Type II is the default.")
            if st.button("Check design and run", key="tbl_run"):
                subj = None if subject == "(none)" else subject
                rep = check_design(frame, response, factors, covariates=covs, subject=subj, interactions=inter)
                st.text(f"Model: {rep.formula}\n\n{rep.explanation()}")
                if rep.estimable:
                    try:
                        res = factorial_anova(frame, response, factors, covariates=covs, subject=subj,
                                              interactions=inter, ss_type=int(ss))
                        st.markdown("**ANOVA table**")
                        st.dataframe(pd.DataFrame([{
                            "term": r.group_a, "df": r.df, "sum_sq": r.extra["sum_sq"], "F": r.statistic,
                            "P": r.p_value, "partial eta²": r.effect_size, "residual df": r.df2}
                            for r in res]), use_container_width=True)
                        coef = model_coefficients(frame, response, factors, covariates=covs, subject=subj,
                                                  interactions=inter)
                        st.markdown("**Coefficients** (sum-to-zero coding: each level's deviation from the "
                                    "mean of all levels; a factor's last level is minus the sum of the others; "
                                    "covariates are slopes; 95 % CI)")
                        st.dataframe(coef.drop(columns=["term"]), use_container_width=True)
                        st.download_button("Download coefficients (CSV)", coef.to_csv(index=False).encode("utf-8"),
                                           file_name="coefficients.csv", mime="text/csv")
                    except StatsError as exc:
                        st.error(str(exc))
    return table_info, table_name, record, raw
