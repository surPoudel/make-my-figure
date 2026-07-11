"""Multi-panel figure builder for Make My Figure.

Compose individual plots into a publication composite (Figure 1A, 1B, 1C, ...)
with automatic bold panel labels, clean aligned layout, and a reproducible
multi-panel sidecar that references each panel's PlotSpec + StatsSpec.
"""

from make_my_figure_core.panels.models import Panel, FigureLayout, MultiPanelFigure
from make_my_figure_core.panels.builder import (
    build_figure,
    export_multipanel,
    multipanel_sidecar,
    draft_legend,
    import_external_panel,
    panel_from_dict,
    panel_warnings,
)

__all__ = [
    "Panel",
    "FigureLayout",
    "MultiPanelFigure",
    "build_figure",
    "export_multipanel",
    "multipanel_sidecar",
    "draft_legend",
    "import_external_panel",
    "panel_from_dict",
    "panel_warnings",
]
