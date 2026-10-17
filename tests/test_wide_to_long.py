"""Wide → long reshaping: a wide table makes the same long table, figures and statistics.

Defect it prevents (measured 2026-10-17): the only reshape on offer, the "per-column
distributions" recommendation, turned the 60-row wide plant table (Species, Age,
Nitrogen, Replicate, Month_4 … Month_10) into 300 rows of [column, value]: it
gathered Replicate as a measurement and dropped Species, Age and Nitrogen, so no
faceted or grouped plot could be drawn from wide data.
"""
import hashlib
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from apps.desktop_app.controller import DesktopController
from make_my_figure_core.package.reader import verify_preprocessing
from make_my_figure_core.tabular import (
    TableTransform,
    TransformError,
    WideToLong,
    apply_table_transforms,
    preview_wide_to_long,
    replay,
    suggest_wide_to_long,
    wide_to_long,
)

FX = Path(__file__).parent / "fixtures"
WIDE = pd.read_csv(FX / "plant_growth_wide.csv")
LONG = pd.read_csv(FX / "plant_growth_facets.csv")
KEYS = ["Species", "Age", "Nitrogen_Concentration", "Replicate", "Month"]
C = DesktopController()


def _spec(**kw):
    return replace(suggest_wide_to_long(WIDE).spec, **{"values_to": "Growth_cm", **kw})


def _sorted(df):
    return df.sort_values(KEYS).reset_index(drop=True)


def test_suggestion_gathers_the_month_columns_and_keeps_every_other_column():
    sug = suggest_wide_to_long(WIDE)
    assert sug.spec.value_columns == ("Month_4", "Month_6", "Month_8", "Month_10")
    assert sug.spec.names_to == ("Month",) and sug.spec.names_prefix == "Month_"
    pv = preview_wide_to_long(WIDE, _spec())
    assert pv.can_apply and pv.id_columns == ["Species", "Age", "Nitrogen_Concentration", "Replicate"]
    assert (pv.n_rows_in, pv.n_rows_out) == (60, 240) and pv.levels == {"Month": [4, 6, 8, 10]}


def test_wide_table_reshapes_to_exactly_the_long_table_and_is_not_modified():
    before = WIDE.copy()
    long, _ = wide_to_long(WIDE, _spec())
    assert WIDE.equals(before)
    assert sorted(long.columns) == sorted(LONG.columns)
    assert list(long.columns) == ["Species", "Age", "Nitrogen_Concentration", "Replicate", "Month", "Growth_cm"]
    assert long["Month"].dtype.kind == "i"
    pd.testing.assert_frame_equal(_sorted(long), _sorted(LONG[long.columns]), check_exact=True)
    # each wide row is followed by its four months (tidyr::pivot_longer order)
    assert long["Month"].head(8).tolist() == [4, 6, 8, 10, 4, 6, 8, 10]


def test_long_table_gives_the_same_figure_numbers_and_statistics_as_the_original():
    long, _ = wide_to_long(WIDE, _spec())
    mapping = {"x": "Month", "y": "Growth_cm", "hue": "Nitrogen_Concentration", "facet_row": "Age",
               "facet_col": "Species"}
    stats = {"enabled": True, "test": "factorial_anova", "facet_scope": "figure"}
    res = []
    for df in (long, LONG):
        s = C.build_spec("boxplot_or_violin_with_points", "publication", "t.csv", mapping, width="default",
                         statistics=stats)
        res.append(C.render(s, C.loaded_from_dataframe(df, "t.csv")))
    a, b = (sorted((r.group_a, r.statistic, r.p_value) for r in x.stats_report.results) for x in res)
    assert len(a) == len(b) == 4 * 3          # 3 terms in each of 4 panels (4 grid factors: explained, not run)
    for (ga, fa, pa), (gb, fb, pb) in zip(a, b):
        assert ga == gb and fa == pytest.approx(fb, rel=1e-12) and pa == pytest.approx(pb, rel=1e-12)


@pytest.mark.parametrize("change,problem", [
    ({"values_to": "Species"}, "already a column"),
    ({"names_to": ("Month",), "values_to": "Month"}, "different names"),
    ({"value_columns": ("Month_4",)}, "at least two"),
    ({"value_columns": ("Month_4", "Age")}, "mix numbers and text"),
    ({"names_prefix": "", "names_sep": "_", "names_to": ("Month", "Extra", "More")}, "do not split"),
    ({"names_prefix": "Month_", "names_to": ("A", "B")}, "need a separator"),
])
def test_impossible_reshapes_are_refused_with_the_reason(change, problem):
    pv = preview_wide_to_long(WIDE, _spec(**{k: v for k, v in change.items()}))
    assert not pv.can_apply and any(problem in p for p in pv.problems), pv.problems
    with pytest.raises(Exception):
        wide_to_long(WIDE, _spec(**change))


def test_names_split_into_several_columns_and_text_levels_stay_text():
    wide = pd.DataFrame({"plant": [1, 2], "A_Young": [1.0, 2.0], "A_Old": [3.0, None],
                         "B_Young": [5.0, 6.0], "B_Old": [7.0, 8.0]})
    spec = WideToLong(value_columns=("A_Young", "A_Old", "B_Young", "B_Old"), names_to=("Species", "Age"),
                      values_to="height", names_sep="_")
    long, pv = wide_to_long(wide, spec)
    assert pv.n_rows_out == 7 and pv.n_missing_dropped == 1          # the empty A_Old cell is left out
    assert long.iloc[0].to_dict() == {"plant": 1, "Species": "A", "Age": "Young", "height": 1.0}
    assert set(long["Age"]) == {"Young", "Old"}
    kept, _ = wide_to_long(wide, replace(spec, drop_missing=False))
    assert len(kept) == 8 and kept["height"].isna().sum() == 1


def test_reshape_is_recorded_first_and_replays_with_column_transformations():
    spec = _spec()
    derived, record = apply_table_transforms(WIDE, [TableTransform("Growth_cm", "log10")], reshape=spec)
    assert record.reshape == spec.to_dict()
    assert [s.method_name for s in record.preprocessing_steps] == ["wide_to_long", "log10"]
    assert record.preprocessing_steps[0].parameters["n_rows_out"] == 240
    assert record.input_shape == [60, 8] and record.output_shape == [240, 7]
    np.testing.assert_allclose(derived["log10(Growth_cm)"], np.log10(derived["Growth_cm"]), rtol=1e-15)
    assert record.method_summary.startswith("The wide table (60 rows) was reshaped to long form")
    again = replay(WIDE, record.to_dict())
    pd.testing.assert_frame_equal(again, derived, check_exact=True)


def test_transformations_on_columns_that_were_gathered_are_refused():
    with pytest.raises(TransformError):
        apply_table_transforms(WIDE, [TableTransform("Month_4", "log10")], reshape=_spec())


def test_desktop_saves_a_long_copy_beside_the_wide_file_and_never_overwrites(tmp_path):
    src = tmp_path / "plants_wide.csv"
    src.write_bytes((FX / "plant_growth_wide.csv").read_bytes())
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    data = C.load_file(str(src))
    long = C.derive_table(data, [], reshape=_spec())
    assert C.raw_of(long) is data and C.reshape_of(long) == _spec()
    first = C.save_long_copy(long)
    second = C.save_long_copy(long)
    assert [Path(p).name for p in first] == ["plants_wide_long.csv", "plants_wide_long.transformations.json"]
    assert [Path(p).name for p in second] == ["plants_wide_long (2).csv",
                                              "plants_wide_long (2).transformations.json"]
    assert hashlib.sha256(src.read_bytes()).hexdigest() == digest            # wide file untouched
    back = pd.read_csv(first[0])
    pd.testing.assert_frame_equal(_sorted(back), _sorted(LONG[back.columns]), check_exact=True)
    # transformations added later are rebuilt from the wide table through the recorded reshape
    logged = C.derive_table(long, [TableTransform("Growth_cm", "log10")])
    assert C.reshape_of(logged) == _spec() and len(logged.info.dataframe) == 240
    assert C.derive_table(long, [], reshape=None) is data                    # back to the wide table


def test_figure_package_keeps_the_wide_table_and_verifies_the_reshape(tmp_path):
    src = tmp_path / "plants_wide.csv"
    src.write_bytes((FX / "plant_growth_wide.csv").read_bytes())
    data = C.load_file(str(src))
    long = C.derive_table(data, [], reshape=_spec())
    s = C.build_spec("boxplot_or_violin_with_points", "publication", long.table_name,
                     {"x": "Month", "y": "Growth_cm", "facet_col": "Species"}, width="default")
    res = C.render(s, long)
    from make_my_figure_core.package import MatrixContext

    raw = C.raw_of(long)
    ctx = MatrixContext(source_dataframe=raw.info.dataframe, source_name=raw.table_name,
                        source_path=raw.source_path, source_sheet=raw.sheet_name,
                        source_provenance=raw.source_provenance(),
                        preprocessing_spec=long.table_context["record"])
    content = C.package_content(long, s, res, matrix=ctx, name="plants")
    pkg = C.open_package(C.package_bytes(content))
    assert verify_preprocessing(pkg)["status"] == "identical"
    reopened, spec = C.loaded_from_package(pkg)
    assert reopened.info.dataframe.shape == (240, 6)
    assert C.raw_of(reopened).info.dataframe.shape == (60, 8)
    assert C.reshape_of(reopened) == _spec()
