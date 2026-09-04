"""Delimited-text floats must parse correctly rounded, so CSV and Excel encodings of the same
table load to identical doubles (found by the Figure 5 input-equivalence benchmark)."""
import io

import pandas as pd

from make_my_figure_core.io.loaders import load_table

_ROWS = ["gene,pvalue,padj",
         "Zfp92,2.88286854002532e-18,1.93094534810896e-14",
         "Mt1,1.16713092275797e-15,5.21162861375526e-12",
         "Capn11,1.38186317870597e-09,0.5"]


def test_csv_floats_are_correctly_rounded():
    text = "\n".join(_ROWS) + "\n"
    df = load_table(text.encode("utf-8"), source_name="t.csv").dataframe
    assert df["padj"].iloc[0] == float("1.93094534810896e-14")
    assert df["padj"].iloc[1] == float("5.21162861375526e-12")
    assert df["pvalue"].iloc[2] == float("1.38186317870597e-09")


def test_csv_and_xlsx_load_to_identical_doubles(tmp_path):
    text = "\n".join(_ROWS) + "\n"
    csv_info = load_table(text.encode("utf-8"), source_name="t.csv")
    xlsx = tmp_path / "t.xlsx"
    with pd.ExcelWriter(xlsx, engine="openpyxl") as xw:
        pd.read_csv(io.StringIO(text), float_precision="round_trip").to_excel(xw, index=False)
    xlsx_info = load_table(str(xlsx))
    for col in ("pvalue", "padj"):
        assert (csv_info.dataframe[col].to_numpy() == xlsx_info.dataframe[col].to_numpy()).all()


def test_semicolon_and_pipe_delimiters_still_sniffed():
    for sep in (";", "|"):
        text = "\n".join(r.replace(",", sep) for r in _ROWS) + "\n"
        info = load_table(text.encode("utf-8"), source_name="t.txt")
        assert info.delimiter == sep and list(info.dataframe.columns) == ["gene", "pvalue", "padj"]
