# release_history — the MakeMyFigure release ledger

One file per published tag, `release_history/<tag>.md`. Each file is a record of what
was actually shipped, written from evidence that can be re-checked (git objects, the
GitHub release as reported by `gh`, the release audit under `docs/releases/<tag>/`,
`CHANGELOG.md`, `docs/RELEASE_NOTES_<tag>.md`). The ledger is not a changelog and not
release notes; those live in `CHANGELOG.md` and `docs/`.

## Rules

1. **Never rewrite an old entry.** If something about a past release changes (assets
   rebuilt, a defect discovered), add a dated **Addendum** section at the bottom of that
   file. The v1.1.0 asset rebuild of 2026-09-17 is the model.
2. **Do not guess.** Every field is either backed by a named source or reads
   `not recorded`. A number remembered from conversation is not evidence.
3. **Cite the source next to the value** (a path, a command, a `gh` query, a commit
   hash). Prefer commands the reader can run.
4. One entry per tag that has a GitHub release. Tags without a reconstructed entry are
   listed below as "not reconstructed" rather than filled in loosely.
5. Entries are written **after** the release is verified (step 23 of
   `.agents/makemyfigure-developer/references/release-workflow.md`), never before.

## Fields

| Field | Meaning | Typical source |
|---|---|---|
| Version | `__version__` in `make_my_figure_core/version.py` at the tagged commit | `git show <tag>:make_my_figure_core/version.py` |
| Date | tag date (tagger date for annotated tags) and GitHub `publishedAt` | `git for-each-ref refs/tags/<tag> --format='%(taggerdate:short)'`; `gh release view <tag> --json publishedAt` |
| Source commit | commit the tag points to (`<tag>^{commit}`), plus tag object id and type | `git rev-parse <tag> <tag>^{commit}`; `git cat-file -t <tag>` |
| Merged branches | branches or commit classes integrated since the previous release | `git log --merges <prev>..<tag>`; `docs/releases/<tag>/*_branch_audit.csv` |
| Test results | exact pytest command(s) and `N passed, M skipped` | `docs/releases/<tag>/release_<tag>_audit.md` §5 or `reports/*/baseline_test_results.md` |
| Plot count | `len(available_plot_types())` at the tag | audit, README badge at the tag, `--selftest` output |
| Statistics count | `len(make_my_figure_core.statistics.TESTS)` | audit |
| Windows / macOS / Linux artifacts | asset file names on the GitHub release | `gh release view <tag> --json assets` |
| SHA-256 | per-asset digest | `SHA256SUMS.txt` on the release; `gh ... --json assets -q '.assets[].digest'`; audit §7 |
| Manual version | version stamped in the User Manual / Quick Start (from `scripts/build_manuals.py`) | audit §6, PDF assets |
| Tag | tag name, type (annotated/lightweight), message | `git tag -l --format='%(objecttype) %(contents:subject)' <tag>` |
| GitHub release URL | `https://github.com/surPoudel/make-my-figure/releases/tag/<tag>` | `gh release view <tag> --json url` |
| Known limitations | limitations stated in the release notes / body at release time | `docs/RELEASE_NOTES_<tag>.md`, release body |
| Workflow run | GitHub Actions run id(s) that built the assets | `gh run list --workflow build_desktop_releases.yml` |

## Entries

| Tag | File | Basis |
|---|---|---|
| v1.1.0 | `v1.1.0.md` | full: audit doc, `gh`, git, CHANGELOG, release notes |
| v1.0.0 | `v1.0.0.md` | `gh`, git, CHANGELOG, `docs/RELEASE_NOTES_v1.0.0.md` (written at rc1 status); no per-release audit exists |
| v1.0.0-rc1 | `v1.0.0-rc1.md` | `gh`, git, CHANGELOG, release notes; test results only as stated in the notes |
| v0.6.1 | `v0.6.1.md` | `gh`, git, CHANGELOG; most operational fields `not recorded` |

## Not reconstructed

`v0.1.0`, `v0.2.0`, `v0.3.0`, `v0.4.0`, `v0.5.0`, `v0.5.1`, `v0.5.2`, `v0.5.3`
(lightweight tags, 2026-07-02 to 2026-07-12). GitHub releases with installers exist for
each (`gh release list`) and `CHANGELOG.md` has a section for each, but there is no
test record, no checksum record and no audit, so no ledger entry is written. Anyone
who needs one should build it from `gh release view <tag> --json assets,publishedAt`
and `git log <prev>..<tag>` and mark every other field `not recorded`.

Note: for `v0.1.0`-`v0.5.3` the repository also carries `remote-check-v*` tags, which
for `v0.3.0`, `v0.5.0` and `v0.5.1` point at different commits than the `v*` tag of the
same version. Treat the `v*` tag as authoritative and record the discrepancy if an
entry is ever written.

## Verify the ledger against reality

```bash
gh release list
for t in v0.6.1 v1.0.0-rc1 v1.0.0 v1.1.0; do echo "$t $(git cat-file -t $t) $(git rev-parse --short $t^{commit})"; done
gh release view v1.1.0 --json assets -q '.assets[]|.name+"  "+.digest'
```
