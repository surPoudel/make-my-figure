"""Shared, frontend-agnostic user-facing strings.

A single source of truth so the Streamlit and desktop apps show identical wording for
the placeholder plot selection, the one visible style, and the top-level workflow
actions — avoiding cross-frontend drift (e.g. one app auto-selecting the first plot
while the other shows a placeholder).
"""

# No-plot placeholder — selecting it renders nothing until the user picks a real plot.
PLOT_TYPE_PLACEHOLDER = "— Choose a plot type… —"

# The single visible style identity.
STYLE_DISPLAY_NAME = "Publication"

# Top-level workflow action labels (ellipsis = opens a dialog / guided workflow).
ACTION_HOME = "Home / Upload New Data"
ACTION_DEFINE_GROUPS = "Define groups…"
ACTION_MATRIX_WORKFLOW = "Matrix workflow…"

# Empty-state guidance shown after data loads but before a plot is chosen.
EMPTY_STATE_MESSAGE = (
    "Data loaded. Choose a plot type to render a figure, or open Matrix workflow for a "
    "guided feature-matrix workflow."
)
