"""Make My Figure core: reusable manuscript-style figure engine.

Frontend-agnostic: data loading, PlotSpec validation, journal-like style
profiles, plot renderers, export logic, provenance helpers, and mock-data
helpers. Used by both the Streamlit app and the desktop (PySide6) app.
"""

from make_my_figure_core.version import __version__
from make_my_figure_core.io.loaders import load_table, TableInfo
from make_my_figure_core.spec.validate import validate_plot_spec, SpecValidationError
from make_my_figure_core.styles.engine import StyleProfile, load_profile, list_profiles
from make_my_figure_core.plots.registry import (
    render,
    render_to_files,
    available_plot_types,
    display_name,
    default_mapping,
    make_spec,
    export_bundle_bytes,
    figure_to_bytes,
    RenderResult,
)
from make_my_figure_core import data as mock_data
from make_my_figure_core import presets
from make_my_figure_core.resources import resource_path

__all__ = [
    "__version__",
    "load_table",
    "TableInfo",
    "validate_plot_spec",
    "SpecValidationError",
    "StyleProfile",
    "load_profile",
    "list_profiles",
    "render",
    "render_to_files",
    "available_plot_types",
    "display_name",
    "default_mapping",
    "make_spec",
    "export_bundle_bytes",
    "figure_to_bytes",
    "RenderResult",
    "mock_data",
    "presets",
    "resource_path",
]
