# Git workflow for releases

## Branches
- `main`: the only branch that gets tagged. Protected by convention, not by GitHub settings.
- Development branches (`feature/*`, `fix/*`, `release/<v>-integration`) are pushed freely.
- **Never pushed** (public repository): `manuscript/*`, `feature/makemyfigure-developer-agent`,
  `feature/circos-plot` (built on the agent branch), anything containing manuscript material,
  private data, or paths under the author's home / OneDrive. `private_file_check.py` catches files;
  the branch rule is a human rule the operating model must obey (memory rule "never push manuscript branches").
- Worktrees: the author works in several git worktrees under OneDrive (`make_my_plot`,
  `make_my_plot_journal_presets`, `make_my_plot_tutorial`, `make_my_plot_release_manager` ...).
  Run the agent from the worktree whose HEAD you intend to build; the manifests record branch and commit.

## Integration pattern used for v1.1.0 (`docs/releases/v1.1.0/release_v1.1.0_audit.md`)
`release/v1.1.0-integration` from `main`; software commits fast-forwarded or cherry-picked with `-x`;
manuscript-only commits excluded; a branch audit CSV listing every candidate commit; merge into
`main`, tag on `main`. `git log <prev-tag>..HEAD --stat` is the input for the branch audit.

## Commits the agent may make
Only in COMMIT-PUSH mode and only these files: `make_my_figure_core/version.py`, `CHANGELOG.md`,
`README.md`, `docs/RELEASE_NOTES_v<v>.md`, the two manual `.md` files (and their generated docx/pdf if
the author regenerated them). Message: `Prepare v<v>: version bump, changelog, release notes`.
The agent never amends, rebases, force-pushes, or merges.

## Tags
Annotated: `git tag -a v<v> -m "MakeMyFigure v<v>"`; pushed with `git push origin v<v>`; the CI
workflow starts on the tag push. `verify_tag.py` before (`--pre-check`) and after.

## Remote pushes from an assistant session
In the author's Claude Code setup a bare `git push` from the assistant is blocked by the permission
classifier. The author runs it: `! cd "<worktree>" && git push`. The gated modes print the exact
command so the author can run it themselves when that happens.

## Local-only observations (2026-09-23)
Early lightweight tags differ between this clone and origin for v0.3.0, v0.5.0 and v0.5.1 (the
`remote-check-*` tags are local copies of origin's tags fetched for comparison). Cause: those tags
were re-pointed after a failed CI run (v0.5.1 has one failed and one successful run). Annotated
tags since v0.6.1 agree. Do not "fix" the old tags; note it in the ledger.
