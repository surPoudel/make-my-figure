"""GUI-free application logic for the desktop app.

Everything here is testable without a running Qt event loop: loading files,
listing plot types/styles, building a PlotSpec, rendering, and exporting. The
Qt layer (``main.py``) calls into this controller and never touches plotting
internals directly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from make_my_figure_core import data as mock_data
from make_my_figure_core import ui_hints
from make_my_figure_core.io.loaders import LoaderError, TableInfo, load_table
from make_my_figure_core.plots.base import RenderError
from make_my_figure_core.plots.registry import (
    available_plot_types,
    default_mapping,
    display_name,
    export_bundle_bytes,
    export_figure,
    render,
    write_sidecar,
)
from make_my_figure_core.spec.validate import (
    SpecValidationError,
    default_output_block,
)
from make_my_figure_core.styles.engine import list_profiles, load_profile
from make_my_figure_core.version import __version__

# Friendly labels for the three starter style profiles.
STYLE_LABELS = {
    "nature_like": "Nature-like",
    "science_like": "Science-like",
    "cell_like": "Cell-like",
}


@dataclass
class LoadedData:
    info: TableInfo
    table_name: str
    aux: Dict[str, TableInfo] = field(default_factory=dict)
    source_path: Optional[str] = None


class DesktopController:
    """Bridges the desktop GUI and the figure core."""

    version = __version__

    # --- catalog ---------------------------------------------------------
    def plot_types(self) -> List[Tuple[str, str]]:
        return [(pt, display_name(pt)) for pt in available_plot_types()]

    def styles(self) -> List[Tuple[str, str]]:
        return [(s, STYLE_LABELS.get(s, s)) for s in list_profiles()]

    def column_fields(self, plot_type: str) -> List[str]:
        return ui_hints.column_fields(plot_type)

    def options(self, plot_type: str) -> List[ui_hints.Option]:
        return ui_hints.options(plot_type)

    def default_mapping(self, plot_type: str) -> Dict[str, Any]:
        return default_mapping(plot_type)

    def needs_metadata(self, plot_type: str) -> bool:
        return plot_type == mock_data.PCA_PLOT_TYPE

    def pca_metadata_fields(self) -> List[str]:
        return list(ui_hints.PCA_METADATA_FIELDS)

    # --- data loading ----------------------------------------------------
    def load_file(self, path: str) -> LoadedData:
        """Load a user file with friendly errors raised as ``LoaderError``."""
        info = load_table(path)
        return LoadedData(info=info, table_name=os.path.basename(path), source_path=path)

    def load_example(self, plot_type: str) -> LoadedData:
        info, aux = mock_data.load_sample(plot_type)
        name = mock_data.sample_filename(plot_type) or f"{plot_type}.csv"
        return LoadedData(info=info, table_name=name, aux=aux)

    def example_source_path(self, plot_type: str) -> Optional[str]:
        return mock_data.sample_path(plot_type)

    # --- spec + render ---------------------------------------------------
    def build_spec(
        self,
        plot_type: str,
        style_name: str,
        table_name: str,
        mapping: Dict[str, Any],
        *,
        layout: Optional[Dict[str, Any]] = None,
        width: str = "single",
        dpi: int = 300,
        formats: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        style = load_profile(style_name)
        w_mm = style.double_column_width_mm if width == "double" else style.single_column_width_mm
        spec: Dict[str, Any] = {
            "plot_type": plot_type,
            "input_table": table_name,
            "mapping": {k: v for k, v in mapping.items() if v not in (None, "")},
            "journal_style": style_name,
            "output": default_output_block(formats or ["svg", "png", "pdf"], width_mm=w_mm, dpi=dpi),
        }
        merged_layout = dict(layout or {})
        merged_layout["column_width"] = width
        spec["layout"] = merged_layout
        return spec

    def render(self, spec: Dict[str, Any], data: LoadedData):
        """Render a figure. Raises RenderError / SpecValidationError on failure."""
        aux = {k: v.dataframe for k, v in data.aux.items()} if data.aux else None
        return render(spec, data.info.dataframe, aux=aux)

    # --- export ----------------------------------------------------------
    def export_files(self, spec, result, base_path: str, formats: List[str], dpi: int = 300) -> Dict[str, Any]:
        files = export_figure(result.figure, base_path, formats, dpi=dpi)
        sidecar = None
        if "json" in [f.lower() for f in formats] or True:
            sidecar = write_sidecar(spec, result.metadata, base_path)
        return {"files": files, "sidecar": sidecar}

    def export_bundle(self, spec, result, formats: List[str], dpi: int = 300, basename: str = "figure") -> bytes:
        return export_bundle_bytes(spec, result, formats=formats, dpi=dpi, basename=basename)

    def save_template(self, plot_type: str, dest_path: str) -> str:
        """Copy the bundled example table for ``plot_type`` to ``dest_path``."""
        src = mock_data.sample_path(plot_type)
        if not src or not os.path.exists(src):
            raise FileNotFoundError(f"No bundled template for '{plot_type}'.")
        import shutil

        shutil.copyfile(src, dest_path)
        return dest_path
