"""Release-candidate guardrails (v0.2 candidate).

Static invariants that must hold for every build: no R/rpy2 dependency, no
committed font files, no journal-named style options, and no RNA-seq-branded
labels in the matrix-workflow UIs. These are cheap text/AST checks — they do not
require private data, a GUI, or Streamlit.
"""

import pathlib
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORE = ROOT / "make_my_figure_core"
APPS = ROOT / "apps"


def _py_files(*roots):
    for root in roots:
        for p in root.rglob("*.py"):
            if "__pycache__" in p.parts:
                continue
            yield p


def test_no_rpy2_or_r_runtime_dependency():
    # No R bridge anywhere in shipped code, and no Rscript subprocess calls.
    offenders = []
    for p in _py_files(CORE, APPS):
        text = p.read_text(encoding="utf-8", errors="ignore")
        if "import rpy2" in text or "from rpy2" in text or "Rscript" in text:
            offenders.append(str(p.relative_to(ROOT)))
    assert not offenders, f"R/rpy2 usage found in: {offenders}"


def test_no_rpy2_in_dependencies():
    # Strip comments first: a "# no R, no rpy2" disclaimer is allowed; a real
    # rpy2 requirement is not.
    def _uncommented(path):
        return "\n".join(line.split("#", 1)[0] for line in path.read_text().splitlines())
    txt = (_uncommented(ROOT / "requirements.txt")
           + _uncommented(ROOT / "pyproject.toml")).lower()
    assert "rpy2" not in txt, "rpy2 must not be a dependency"


def test_no_font_files_committed():
    # "Committed" == tracked by git. Ask git directly (fast, and ignores the
    # 9 worktrees / OneDrive sync / vendored skill assets a tree walk would hit).
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "ls-files"],
                             capture_output=True, text=True, timeout=60, check=True).stdout
    except (subprocess.SubprocessError, FileNotFoundError):
        pytest.skip("git not available to enumerate tracked files")
    bad = [line for line in out.splitlines()
           if line.lower().endswith((".ttf", ".otf", ".woff", ".woff2"))]
    assert not bad, f"font files must not be committed: {bad}"


def test_publication_is_the_only_visible_style_and_journal_names_migrate():
    from make_my_figure_core.styles.engine import LEGACY_STYLE_ALIASES, load_profile
    # Legacy journal-named profiles migrate to publication rather than being offered.
    for legacy in ("nature_like", "science_like", "cell_like",
                   "nature_like_learned", "science_like_learned", "cell_like_learned"):
        assert LEGACY_STYLE_ALIASES.get(legacy) == "publication", legacy
    # The default profile resolves and identifies as Publication.
    prof = load_profile("publication")
    assert prof is not None


def test_matrix_workflow_uis_have_no_rnaseq_or_journal_labels():
    targets = [APPS / "streamlit_app" / "matrix_wizard.py",
               APPS / "desktop_app" / "matrix_wizard.py"]
    for p in targets:
        low = p.read_text(encoding="utf-8", errors="ignore").lower()
        assert "rna-seq" not in low and "rnaseq" not in low, f"RNA-seq label in {p.name}"
        for journal in ("nature_like", "science_like", "cell_like"):
            assert journal not in low, f"journal-named style in {p.name}: {journal}"


def test_matrix_value_types_are_generic():
    from make_my_figure_core.matrix_workflow import VALUE_TYPES
    joined = " ".join(VALUE_TYPES).lower()
    assert "rna" not in joined and "seq" not in joined


def test_build_wrappers_do_not_embed_the_repo_path_in_python_one_liners():
    # The per-OS build wrappers read the version with a Python one-liner. Embedding the
    # repository path inside that quoted string breaks for paths containing quotes or
    # apostrophes (e.g. OneDrive "... Children's Research Hospital ..." folders): the
    # wrappers must `cd` to the repo root instead (fixed 2026-09-23).
    offenders = []
    for name in ("build_linux.sh", "build_macos.sh", "build_windows.ps1"):
        text = (ROOT / "scripts" / name).read_text(encoding="utf-8", errors="ignore")
        if "sys.path.insert(0, '$ROOT')" in text or "sys.path.insert(0, r'$Root')" in text:
            offenders.append(name)
    assert not offenders, f"repo path embedded in a Python one-liner: {offenders}"
