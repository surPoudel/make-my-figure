# v1.2.0 — branch state at release audit

Audited 2026-10-05. Every value below was read from the repository, not assumed.

## Branch names (not assumed — read from `git branch -a`)

| Role | Exact name | Remote HEAD | Local HEAD |
|---|---|---|---|
| Main / release branch | `main` | `932427e` | `932427e` |
| Release-candidate work branch | `feature/spatial-v2` | `932427e` | `932427e` |
| **Tutorial branch (OUT OF SCOPE for v1.2.0)** | `feature/desktop-tutorial` | `a758520` | `5b0ab70` |

`main` and `feature/spatial-v2` are the same commit: `main` was fast-forwarded to the
branch on 2026-10-03 and both were pushed. There is nothing on `main` that the
branch lacks.

## Tutorial branch — untouched

- 6 commits on `feature/desktop-tutorial` that are not on `main`
- 53 commits on `main` that are not on the tutorial branch
- **The local tutorial branch (`5b0ab70`) is one commit *ahead* of its own remote
  (`a758520`), not behind.** `5b0ab70`'s parent is exactly `a758520`. The commit is
  "Master replay: one continuous action script covering the main capabilities in a
  single window (48 checks PASS)" of 2026-09-23, 35 files including screenshots and
  a driver log. An earlier revision of this document said "behind", which inverted
  the risk: this is unpushed work that exists in one place only, not stale local
  state that can be discarded.
- No tutorial commit is an ancestor of the release commit. Verified in
  RELEASE_SOURCE.md.

## Tags

Latest stable tag: `v1.1.1`
- annotated tag object `33f1bd5`
- → commit `8105769`

No `v1.2.0` tag or candidate exists (`git tag -l "v1.2*"` is empty).

## Working tree

- tracked modifications: 0 (clean)
- untracked: 8 paths, none of which are part of the release source

The untracked paths are local scratch — two private publication PDFs, an xlsx, a
pptx, a screenshot, generated report directories and a benchmark output folder.
They are **not** tracked, so they cannot enter the wheel, the sdist or the tag.
Phase 14 re-checks this against the built artifacts rather than trusting it here.

## Existing release artifacts

`dist/` holds only build staging from previous local runs (`dist/MakeMyFigure`,
`dist/MakeMyFigure.AppDir`). There is no `dist/v1.1.1/` or `release_history/`
directory in this tree, so nothing historical can be destroyed by creating
`dist/v1.2.0/`.
