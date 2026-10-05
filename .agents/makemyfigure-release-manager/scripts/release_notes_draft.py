"""Draft GitHub release notes from the repository's own text. Writes a DRAFT only.

    python .agents/makemyfigure-release-manager/scripts/release_notes_draft.py --version X.Y.Z

Body: docs/RELEASE_NOTES_vX.Y.Z.md when it exists, otherwise the "## [X.Y.Z]" CHANGELOG section.
Appended: a Downloads table (file, size, SHA-256) from release_staging/<v>/checksums/release_artifacts.json
when checksums exist, the live plot-type / statistics counts, and the standing installation notes
(unsigned desktop apps; Linux glibc requirement taken from the Linux build manifest when present).
Output: release_staging/<v>/RELEASE_NOTES_DRAFT.md - the author edits and approves it before publication.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

INSTALL_NOTES = """
### Installation notes

- **Windows:** run `MakeMyFigure-{v}-Setup.exe` (or unzip `MakeMyFigure-{v}-windows.zip` and start `MakeMyFigure.exe`).
  The app is not code-signed: Windows SmartScreen shows "unrecognized app" - choose *More info -> Run anyway*.
- **macOS:** open `MakeMyFigure-{v}.dmg`, drag *Make My Figure* to Applications. Unsigned: on first launch use
  right-click -> *Open*, or *System Settings -> Privacy & Security -> Open Anyway*.
- **Linux:** `chmod +x MakeMyFigure-{v}.AppImage && ./MakeMyFigure-{v}.AppImage`, or unpack the tar.gz and run `MakeMyFigure/MakeMyFigure`.{glibc}
- **Python package:** `pip install make_my_figure_core-{v}-py3-none-any.whl` (core renderer, no GUI); add `PySide6` for the desktop app from source.
- Verify downloads with `sha256sum -c SHA256SUMS.txt`.
"""


def changelog_section(v: str) -> str:
    chg = open(os.path.join(C.ROOT, "CHANGELOG.md"), encoding="utf-8").read()
    m = re.search(rf"^## \[{re.escape(v)}\][^\n]*\n(.*?)(?=^## \[|\Z)", chg, re.M | re.S)
    return m.group(1).strip() if m else ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", default=C.version_py())
    a = ap.parse_args()
    v = a.version.lstrip("v")
    notes = os.path.join(C.ROOT, "docs", f"RELEASE_NOTES_v{v}.md")
    if os.path.exists(notes):
        body = open(notes, encoding="utf-8").read().strip(); source = os.path.relpath(notes, C.ROOT)
    else:
        body = changelog_section(v); source = f"CHANGELOG.md section [{v}]"
        if body:
            body = f"# Make My Figure v{v} - release notes\n\n{body}"
    if not body:
        print(f"no release text found for {v} (neither docs/RELEASE_NOTES_v{v}.md nor a CHANGELOG section)"); return 1
    facts = C.project_facts()
    parts = [body, "", f"_Live counts at build time: {facts.get('plot_types')} plot types, {facts.get('statistical_procedures')} statistical procedures._"]
    arts_path = os.path.join(C.STAGING_ROOT, v, "checksums", "release_artifacts.json")
    if os.path.exists(arts_path):
        arts = C.read_json(arts_path)["artifacts"]
        parts += ["", "### Downloads", "", "| File | Size | SHA-256 |", "|---|---|---|"]
        parts += [f"| `{x['filename']}` | {x['size'] / 1e6:.1f} MB | `{x['sha256']}` |" for x in arts]
    glibc = ""
    lm = os.path.join(C.STAGING_ROOT, v, "linux", "platform_build_manifest.json")
    if os.path.exists(lm):
        g = (C.read_json(lm).get("host") or {}).get("glibc")
        if g:
            glibc = f" Built against glibc {g}; needs a distribution with glibc >= {g}."
    parts.append(INSTALL_NOTES.format(v=v, glibc=glibc))
    out = os.path.join(C.staging_dir(v), "RELEASE_NOTES_DRAFT.md")
    open(out, "w", encoding="utf-8").write("\n".join(parts).strip() + "\n")
    print(f"draft written from {source} -> {os.path.relpath(out, C.ROOT)} ({len(parts)} blocks; {'with' if os.path.exists(arts_path) else 'without'} download table)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
