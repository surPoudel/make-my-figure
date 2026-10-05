# v1.2.0 — release source

## Decision

**Release source: `main`.** The audit below was taken at `932427e`; the release
commit is the one tagged `v1.2.0` ("Prepare v1.2.0"), which is that tree plus the version bump,
the changelog and release notes, this audit, and the quality fixes the audit found.

## Evidence

| Field | Value |
|---|---|
| Release branch | `main` |
| Release commit | the commit tagged `v1.2.0` (hash recorded in `release_history/v1.2.0.md`) |
| Commit subject | Merge evidence-derived journal presets, and make a requested width final |
| Parents | `06c804b` (branch line), `7f06d85` (evidence-derived journal presets) |
| Previous tag | `v1.1.1` → tag object `33f1bd5` → commit `8105769` |
| Commits since v1.1.1 | 51 non-merge commits |
| Diff from v1.1.1 | 1068 files changed, +78,684 / −709 |
| Plot types at v1.1.1 | 39 (queried from a `v1.1.1` worktree, not parsed) |
| Plot types at release source | 45 (queried from the live registry) |

## Why this branch is the release source

1. `main` is the repository's default branch (`origin/HEAD -> origin/main`) and is
   where every previous release tag was cut from.
2. It carries the complete approved software state: `git rev-list --count
   origin/feature/spatial-v2..origin/main` is 0 and the reverse is 0 — `main` and
   the development branch are identical, so nothing approved is left behind.
3. Its full test suite is green on both this machine and GitHub Actions
   (run 37140999143, `pytest (headless)`, 30m10s, conclusion success).
4. It contains **no** commit from `feature/desktop-tutorial`. Verified:

       git merge-base --is-ancestor origin/feature/desktop-tutorial origin/main
       → non-zero (not an ancestor)

   and all 6 tutorial-only commits remain exclusive to that branch.

## Tutorial branch exclusion

**Tutorial branch merged into release source: NO.**

`feature/desktop-tutorial` is out of scope for v1.2.0 by instruction. It is not an
ancestor of `932427e`, no tutorial commit was cherry-picked, and no tutorial file
was copied into the release source. Phase 3's file-level diff is the independent
check on this claim.

### File-level check (the independent one)

`feature/desktop-tutorial` touches 355 paths relative to `main`. Of those, exactly
one — `.gitignore` — also exists in the release commit, and it exists there
independently: both branches maintain their own. The other **354 paths, which are
the entire tutorial corpus** (`tutorial/`, `presentation/`, `plots/_TEMPLATE.md`,
the recording scripts and the review PDFs), are absent from the release commit.

Checked with `git cat-file -e origin/main:<path>` for every one of the 355 paths,
not by inspection.
