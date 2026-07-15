"""v0.6 single-Publication style: migration + user-facing cleanup guards."""

import os
import re

import matplotlib
import matplotlib.pyplot as plt
import pytest

matplotlib.use("Agg")

from apps.desktop_app.controller import DesktopController
from make_my_figure_core.plots.registry import make_spec, render
from make_my_figure_core.styles.engine import list_profiles

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Hyphenated/spaced display forms that must not appear in user-facing UI/docs.
_FORBIDDEN = re.compile(r"nature-like|science-like|cell-like|journal-like", re.IGNORECASE)
# Lines allowed to mention the phrases (migration/deprecation notes, changelog).
_ALLOW = re.compile(r"deprecat|removed|legacy|back-compat|migrat|changelog|older named",
                    re.IGNORECASE)


@pytest.fixture(autouse=True)
def _close_figs():
    yield
    plt.close("all")


def test_list_profiles_is_publication_only():
    profiles = list_profiles()
    assert profiles[0] == "publication"
    assert not (_FORBIDDEN.search(" ".join(profiles)))
    # any extra entries are benchmark-derived publication profiles
    assert all(p == "publication" or p.startswith("publication") for p in profiles)


def test_new_specs_use_publication_style():
    spec = make_spec("volcano_plot", "x.csv", "publication")
    assert spec["journal_style"] == "publication"


@pytest.mark.parametrize("legacy", ["nature_like", "science_like", "cell_like",
                                    "nature_like_learned", "journal_like"])
def test_old_plotspec_with_journal_name_still_loads(legacy):
    """A saved PlotSpec referencing a removed profile renders, mapped to Publication."""
    from make_my_figure_core import examples

    info, aux, _ = examples.load_example("volcano_plot")
    aux_dfs = {k: v.dataframe for k, v in aux.items()} or None
    spec = make_spec("volcano_plot", info.source_name, legacy)
    result = render(spec, info.dataframe, aux=aux_dfs)
    assert result.figure is not None
    assert result.metadata["style_profile"] == "publication"
    assert any("Publication style" in w for w in result.warnings)


def test_desktop_controller_exposes_only_publication():
    styles = dict(DesktopController().styles())
    assert styles == {"publication": "Publication"}


# Internal dev docs that necessarily quote the removed names (plan / changelog).
_SCAN_SKIP = {"V0_6_IMPLEMENTATION_PLAN.md", "CHANGELOG.md"}


def _iter_user_facing_files():
    for rel in ["apps/desktop_app", "apps/streamlit_app", "docs"]:
        base = os.path.join(_ROOT, rel)
        for dirpath, _dirs, files in os.walk(base):
            for fn in files:
                if fn.endswith((".py", ".md")) and fn not in _SCAN_SKIP:
                    yield os.path.join(dirpath, fn)
    yield os.path.join(_ROOT, "README.md")


def test_no_journal_style_names_in_user_facing_text():
    offenders = []
    for path in _iter_user_facing_files():
        try:
            with open(path, encoding="utf-8") as fh:
                for i, line in enumerate(fh, 1):
                    if _FORBIDDEN.search(line) and not _ALLOW.search(line):
                        offenders.append(f"{os.path.relpath(path, _ROOT)}:{i}: {line.strip()}")
        except (OSError, UnicodeDecodeError):
            continue
    assert not offenders, "Journal-style names found in user-facing text:\n" + "\n".join(offenders)
