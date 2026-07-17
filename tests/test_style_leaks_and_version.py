"""Release guards: only 'Publication' is user-visible; legacy journal names never
leak; a build/version banner is available so users can confirm the running code.
"""

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
_FORBIDDEN = ("nature_like", "science_like", "cell_like", "nature-like",
              "science-like", "cell-like", "journal-like")


def test_list_profiles_only_publication():
    from make_my_figure_core.styles.engine import list_profiles
    profiles = list_profiles()
    assert profiles[0] == "publication"
    for p in profiles:
        low = p.lower()
        assert not any(tok in low for tok in
                       ("nature", "science", "cell", "journal", "jama", "nejm", "lancet"))


def test_legacy_names_map_to_publication():
    from make_my_figure_core.styles.engine import normalize_style_name
    for legacy in ("nature_like", "science_like", "cell_like", "nature_like_learned",
                   "science_like_learned", "cell_like_learned", "journal_like"):
        assert normalize_style_name(legacy) == "publication"


def test_load_profile_migrates_legacy():
    from make_my_figure_core.styles.engine import load_profile
    prof = load_profile("nature_like")   # must not raise; migrates to publication
    assert prof is not None


def test_style_display_uses_publication_label():
    # Any learned publication profiles are labeled/renamed for display; no journal token.
    from make_my_figure_core.styles.engine import list_profiles
    assert all("publication" in p or not any(t in p.lower() for t in ("nature", "science", "cell"))
               for p in list_profiles())


def test_no_forbidden_style_names_in_visible_ui_option_lists():
    """The active UI modules must not present journal-named style choices.

    Scans app modules for forbidden style tokens appearing inside a selectbox/addItem/
    option list (not in comments/docstrings/disclaimers)."""
    ui_files = [
        ROOT / "apps" / "streamlit_app" / "streamlit_app.py",
        ROOT / "apps" / "streamlit_app" / "matrix_wizard.py",
        ROOT / "apps" / "desktop_app" / "main.py",
        ROOT / "apps" / "desktop_app" / "matrix_wizard.py",
    ]
    # widget calls that could present options to the user
    widget_re = re.compile(r"(selectbox|radio|addItems|addItem|options\s*=|pills|segmented_control)",
                           re.I)
    offenders = []
    for f in ui_files:
        if not f.exists():
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"') or stripped.startswith("'"):
                continue
            low = line.lower()
            if widget_re.search(line) and any(tok in low for tok in _FORBIDDEN):
                offenders.append(f"{f.name}:{i}: {stripped[:80]}")
    assert not offenders, "forbidden style names in UI option lists:\n" + "\n".join(offenders)


def test_user_palettes_have_no_forbidden_names():
    # NAMED_PALETTES keeps journal-named entries for backward compat, but the
    # user-facing USER_PALETTES must never contain them.
    from make_my_figure_core.styles.engine import NAMED_PALETTES, USER_PALETTES
    for p in USER_PALETTES:
        assert not any(t in p.lower() for t in ("nature", "science", "cell", "journal"))
    # sanity: NAMED_PALETTES still holds the legacy entries (they exist, just hidden)
    assert "publication" in NAMED_PALETTES


def test_apps_do_not_expose_named_palettes_directly():
    """The palette widget must use USER_PALETTES, not list(NAMED_PALETTES) — the exact
    anti-pattern that leaked nature_like/science_like/cell_like into the UI dropdown."""
    for rel in ("apps/streamlit_app/streamlit_app.py",
                "apps/streamlit_app/matrix_wizard.py",
                "apps/desktop_app/main.py",
                "apps/desktop_app/matrix_wizard.py"):
        text = (ROOT / rel).read_text(encoding="utf-8", errors="ignore")
        assert "list(NAMED_PALETTES)" not in text, f"{rel} lists NAMED_PALETTES in the UI"


def test_build_info_reports_module_path_and_commit():
    from make_my_figure_core.version import build_banner, build_info
    info = build_info()
    assert info["version"] and info["module_path"]
    # module_path should point at the repo we are testing (not a stray site-packages)
    assert str(ROOT) in info["module_path"] or info["module_path"] in str(ROOT)
    banner = build_banner()
    assert "Make My Figure" in banner and info["version"] in banner
