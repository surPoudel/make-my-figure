# Versioning rules

- Scheme: semantic versioning `MAJOR.MINOR.PATCH`; pre-releases as PEP 440 `X.Y.ZrcN` in
  `version.py` and `vX.Y.Z-rcN` as the tag (precedent: `1.0.0rc1` / `v1.0.0-rc1`).
  `_common.pep440_to_tag()` / `tag_to_pep440()` convert.
- The tag is always `"v" + version.py` at the tagged commit. `verify_tag.py` enforces it.
- A version is used once. If `vX.Y.Z` exists (locally or on origin), the version must be bumped;
  never move or delete a public tag (`rollback.md`).
- Since v0.6.1 tags are **annotated** (`git tag -a vX -m "MakeMyFigure vX"`); v0.1.0-v0.5.3 were
  lightweight. Keep annotated.
- Tags are cut from `main`. v1.1.0 was assembled on `release/v1.1.0-integration`, fast-forwarded
  into `main`, then tagged on `main` (3da8563).

## Every place the version appears (kept in step)
| Location | Updated by |
|---|---|
| `make_my_figure_core/version.py` | PREPARE RC `--execute` |
| `CHANGELOG.md` `## [X.Y.Z] - title` (first heading below `## [Unreleased]`) | author |
| `README.md` version badge `badge/version-X.Y.Z-`, installer names in the install table, wheel name | PREPARE RC `--execute` (plain text replacement of the previous version) |
| `docs/manuals/*/…​.md` banners `**MakeMyFigure version:** X.Y.Z` (+ generated .docx/.pdf) | `python scripts/build_manuals.py` |
| `docs/RELEASE_NOTES_vX.Y.Z.md` | author (draft from `release_notes_draft.py`) |
| GitHub release title `MakeMyFigure vX.Y.Z` | RELEASE mode |

`verify_version.py --expect X.Y.Z` exits 1 when any of them disagrees; `release_preflight.py`
includes the same check.

## Bumping
PATCH for fixes and compatibility work (1.1.0 -> 1.1.1: figure packages were added too, the
author chose PATCH; the agent does not second-guess the author's choice, it records it).
MINOR for new plot types / statistics / workflows; MAJOR for breaking PlotSpec or package formats.
