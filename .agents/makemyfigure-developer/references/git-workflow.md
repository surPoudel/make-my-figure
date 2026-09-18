# Git workflow reference — MakeMyFigure

Reconstructed on 2026-09-17 from `git log`, `git branch -a`, `git worktree list`,
`.gitignore`, `.git/info/exclude` and `docs/REPO_EXCLUSIONS.md` in the checkout at
`make_my_plot_agent` (branch `feature/makemyfigure-developer-agent`). Remote:
`origin = https://github.com/surPoudel/make-my-figure.git` (private). `gh` was
authenticated as `surPoudel` when this was written.

## 1. Branch naming actually used

From `git branch -a` and the merge subjects (`git log --merges --format=%s`):

| Prefix | Examples | Purpose |
|---|---|---|
| `feature/` | `feature/matrix-workflow`, `feature/statistics-annotations-multipanel`, `feature/portable-figure-package-v1.1.1`, `feature/evidence-derived-journal-presets` | new capability; the current standard |
| `feat/` | `feat/v0.4-plot-types`, `feat/v0.5-click-annotate`, `feat/v0.5.2-memory-guards` | older (v0.4-v0.5) spelling; do not start new ones |
| `fix/` | `fix/package-data-resources`, `fix/collaborator-concerns-c1-c3`, `fix/pick-identify-float-dtype` | bug fixes |
| `chore/` | `chore/release-workflow-republish`, `chore/license-in-bundles-and-dependency-bounds` | packaging, CI, dependency housekeeping |
| `docs/` | `docs/v1.1.0-asset-rebuild-checksums` | documentation-only changes |
| `release/` | `release/v1.1.0-integration` | integration branch that becomes a tag (see `release-workflow.md`) |
| `manuscript/` | `manuscript/figure3`, `manuscript/figure4`, `manuscript/figure5` | paper-figure work; **never merged into `main`** (v1.1.0 audit §1: "No manuscript branch was merged") |
| `benchmarks/`, `ci/` | `benchmarks/ten-publication`, `ci/release-attach` | benchmark data and CI experiments |

Branches always fork from `main`. `main` is the only long-lived branch and is the
base for PRs.

## 2. How work reaches `main`

`git log --merges` shows two patterns:

1. **GitHub pull request merges** (current practice, PRs #1-#12):
   `Merge pull request #12 from surPoudel/docs/v1.1.0-asset-rebuild-checksums`.
   Each PR carried one or two focused commits. Small PRs (#10, #11, #12 on 2026-09-16)
   were opened and merged the same day.
2. **Local merge commits with a descriptive subject** (mid-2026):
   `Merge feature/matrix-workflow: matrix workflow, wizards, and default-quality fixes`,
   `Merge the packaging fix so a built wheel can actually render`.
3. **Fast-forward integration** for the v1.1.0 release:
   `release/v1.1.0-integration` was fast-forwarded onto `main`
   (`git rev-list --count --merges v1.0.0..v1.1.0` = 1, and that merge is the
   packaging fix, not the integration branch). The audit CSV
   `docs/releases/v1.1.0/release_v1.1.0_branch_audit.csv` records how each of the 91
   candidate commits was handled (fast-forward, `cherry-pick -x`, partial port, excluded).

PR titles are the commit subject; PR bodies end with
`🤖 Generated with [Claude Code](https://claude.com/claude-code)` per the attribution
rule in force for this agent.

## 3. Commit message style

Observed on the last ~40 commits (`git log --format='%s' -40`):

- Subject in **imperative or plain descriptive English**, capitalised, no trailing
  period, no conventional-commit prefix on recent commits
  (`Add a histogram plot type`, `Bundle the MIT LICENSE in every build and bound
  dependency versions`, `Release audit: record the 2026-09-17 asset rebuild and new
  SHA256 checksums`). Older commits used `fix:`, `ci:`, `chore(release):` prefixes
  and `vX.Y.Z:` prefixes on release-ish commits; either is acceptable, but match the
  recent plain style.
- A colon-prefixed area label is common for scoped changes
  (`Release workflow: ...`, `R validation: ...`, `Release notes: ...`).
- Body (when present): a short paragraph or `-` bullets explaining *why* and listing
  the touched surfaces; see `git show -s --format=%B 2a69cab` and `f68a2f3`.
- Release commits are named `Release v1.0.0` / `Release 1.1.0: version, changelog, ...`
  and touch `make_my_figure_core/version.py` + `CHANGELOG.md` (+ README, About dialog,
  build scripts for 1.1.0).

### Co-author trailer

116 of the commits carry a `Co-Authored-By:` trailer
(`git log --format=%b | grep -c Co-Authored-By`). The trailer names the model that
produced the change; the most recent 21 commits use:

```
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

Use exactly the trailer the current session's attribution instruction gives (today:
the line above), as the last line of the body, preceded by a blank line.

## 4. Worktrees

`git worktree list` shows the project is developed with **one worktree per branch**,
all siblings of the primary checkout:

```
.../make_my_plot            main
.../make_my_plot_agent      feature/makemyfigure-developer-agent   (this checkout)
.../make_my_plot_figure3/4/5   manuscript/figure3|4|5
.../make_my_plot_v111       feature/portable-figure-package-v1.1.1
.../make_my_plot_task2      task2-parallel
```

Rules that follow from the audit and memory notes:

- Create a worktree with `git worktree add ../make_my_plot_<slug> -b <branch> main`;
  never `git checkout` a different branch inside another agent's worktree.
- Manuscript worktrees may contain uncommitted renderer edits; software changes made
  there must be ported to a `feature/` or `fix/` branch with tests before release
  (v1.1.0 audit §1, commit 92fd71e).
- An editable install (`pip install -e .`) points at exactly one worktree; the
  status-bar banner (`build_banner()`) shows which commit is actually imported
  (memory note "Figure 5 render engine"). Check it before trusting a render.
- The `.git` directory is shared; `.git/info/exclude` applies to every worktree.

## 5. What must never be committed

From `.gitignore`, `.git/info/exclude` and `docs/REPO_EXCLUSIONS.md`:

- **Manuscript material**: `manuscript/`, `prompts/`, `scripts/*manuscript*.py`,
  `REFERENCE_AND_OUTLINE_AUDIT.md`, anything from `manuscriptv3/`, `manuscriptV2/`,
  `Concerns/` (all currently untracked in the primary checkout — leave them that way).
- **Assistant/tooling files**: `CLAUDE.md`, `claude_code/`, `.claude/`, `.idea/`,
  `.vscode/`. `.git/info/exclude` (shared by every worktree) additionally excludes
  `/.agents/skills/` locally; `.agents/makemyfigure-developer/references/` and
  `release_history/` are ordinary untracked files (`git status` shows `??`) and are
  committed only on an explicit maintainer decision.
- **Third-party paper content**: `figure_library/` (regenerable via
  `scripts/harvest_library.py`), publisher figures, EndNote libraries, font files
  (`tests/test_release_guardrails.py::test_no_font_files_committed`).
- **Private data**: root-level `*.xlsx|xls|xlsm`, root-level `*.png`/`Screenshot*.png`,
  `GREEN-*.txt`, `voom_norm_annot*`, `meta_info_detail.csv`,
  `reports/collaborator_concerns/`, `benchmarks/r_validation/reports/METHODS_FOR_MANUSCRIPT.md`.
- **Build and environment artefacts**: `.venv/`, `build/`, `dist/`, `*.egg-info/`,
  caches, `*.log`, `outputs/**` images, large QC images under `reports/`,
  `docs/manuals/assets/_pdf_cache/`, `benchmarks/r_validation/results/R/*.rds`.
- **Secrets**: certificates, passwords, tokens (`docs/CODE_SIGNING.md`, "Security /
  secrets policy"). CI signing uses repository secrets only.
- **Local paths**: `/mnt/c/Users/...`, `OneDrive` user paths, `<local-user>` — the
  v1.1.0 audit §8 grepped for these and redacted them; `git grep -n -i -E
  'OneDrive|/mnt/c/Users'` should return only generic advice.

Before any commit: `git status --short` must show only the intended files, and
`git diff --cached --stat` must not list anything from the lists above.

## 6. Permission model for the development agent

The agent operates in one of four modes. Each mode is entered only by the explicit
request named in the second column; the agent never escalates on its own.

| Mode | Entered by | Allowed | Not allowed |
|---|---|---|---|
| **DEVELOP** (default) | any development task | edit files, run tests, build locally, read history, `git stash`/`git diff` | `git commit`, `git push`, `git tag`, editing `version.py`, `CHANGELOG.md` release sections |
| **COMMIT** | user says "commit" (or equivalent) for specific work | `git add <named files>`, `git commit` on the current non-`main` branch with the style in §3 and the co-author trailer; one logical change per commit | committing on `main`; `git add -A`/`.` without reviewing the file list; touching excluded paths; amending pushed commits |
| **PUSH** | user says "push" | `git push -u origin <feature-branch>` after the pre-push gate below; opening a PR with `gh pr create` if asked | pushing `main`; force-push; pushing tags |
| **RELEASE** | user names an exact target version (`release v1.2.0`) | the numbered runbook in `release-workflow.md`, including version bump, tag and GitHub release | inferring a version; releasing from an unclean tree; skipping the test gate |

Pre-push gate (PUSH and RELEASE):

```bash
git status --short                                    # empty except intended files
MPLBACKEND=Agg python -m pytest -q -p no:pytest-qt --ignore=tests/test_desktop_gui.py   # 0 failed
python -m pytest tests/test_release_guardrails.py tests/test_packaging.py tests/test_package_data.py -q
```

If the environment cannot run the Qt module, say so in the PR body rather than
claiming a full run; the v1.1.0 audit did the same (§5a).

Always announce the mode you believe you are in when a request is ambiguous, and
ask before crossing into COMMIT, PUSH or RELEASE.

## Verify this is still current

```bash
git log --merges --format='%h %ad %s' --date=short | head -10          # merge pattern and branch prefixes
git log --format='%b' -30 | grep 'Co-Authored-By' | sort | uniq -c      # trailer in current use
git worktree list; git check-ignore -v .agents/ CLAUDE.md dist/          # worktrees and local excludes
git branch -a | sed -E 's#^[* +]*(remotes/origin/)?##' | cut -d/ -f1 | sort | uniq -c   # prefix census
```
