import pytest

from make_my_figure_core.plots.registry import available_plot_types, make_spec
from make_my_figure_core.spec.validate import (
    SpecValidationError,
    default_output_block,
    load_schema,
    validate_plot_spec,
)
from make_my_figure_core.styles.engine import list_profiles


def test_schema_loads():
    schema = load_schema()
    assert schema["title"].startswith("MakeMyFigure")
    assert "plot_type" in schema["required"]


def test_valid_spec_passes():
    spec = make_spec("volcano_plot", "volcano_plot.csv", "nature_like")
    out = validate_plot_spec(
        spec,
        known_plot_types=available_plot_types(),
        known_styles=list_profiles(),
    )
    assert out is spec


def test_missing_required_field_fails():
    spec = {"plot_type": "volcano_plot"}  # missing input_table, mapping, etc.
    with pytest.raises(SpecValidationError) as exc:
        validate_plot_spec(spec)
    assert any("input_table" in m or "mapping" in m for m in exc.value.errors)


def test_unknown_plot_type_reported():
    spec = make_spec("volcano_plot", "x.csv", "nature_like")
    spec["plot_type"] = "not_a_plot"
    with pytest.raises(SpecValidationError) as exc:
        validate_plot_spec(spec, known_plot_types=available_plot_types())
    assert any("not_a_plot" in m for m in exc.value.errors)


def test_unknown_style_reported():
    spec = make_spec("volcano_plot", "x.csv", "imaginary_journal")
    with pytest.raises(SpecValidationError) as exc:
        validate_plot_spec(spec, known_styles=list_profiles())
    assert any("imaginary_journal" in m for m in exc.value.errors)


def test_bad_output_format_rejected():
    spec = make_spec("volcano_plot", "x.csv", "nature_like")
    spec["output"] = default_output_block()
    spec["output"]["formats"] = ["docx"]  # not in enum
    with pytest.raises(SpecValidationError):
        validate_plot_spec(spec)
