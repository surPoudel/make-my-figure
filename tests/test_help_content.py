"""The desktop Help page must describe every registered plot type (columns + example file).

Regression for v1.1.1, where the Help dialog read only the legacy 18-dataset manifest and
showed "Required columns: —" / "Example file: None" for the 21 newer plot types.
"""
import os

os.environ.setdefault("MPLBACKEND", "Agg")

from apps.desktop_app import help_content  # noqa: E402
from make_my_figure_core.plots.registry import available_plot_types  # noqa: E402


def test_every_plot_type_has_columns_description_and_example_in_help():
    entries = {e["plot_type"]: e for e in help_content.plot_help()}
    assert set(entries) == set(available_plot_types())
    incomplete = [pt for pt, e in entries.items()
                  if not e["required_columns"] or not e["description"] or not e["example_file"] or not e["replacement_note"]]
    assert not incomplete, f"Help entries without columns/description/example: {incomplete}"


def test_help_example_files_exist_in_the_bundled_examples():
    from make_my_figure_core import resources
    for e in help_content.plot_help():
        path = os.path.join(resources.project_base(), "examples", e["example_file"])
        assert os.path.exists(path), f"{e['plot_type']}: {path}"
