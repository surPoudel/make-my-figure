# Release workflow reference — MakeMyFigure

Reconstructed on 2026-09-17 from `docs/RELEASE_CHECKLIST.md`, `docs/BUILD_INSTALLERS.md`,
`.github/workflows/build_desktop_releases.yml`, `docs/releases/v1.1.0/release_v1.1.0_audit.md`,
`docs/RELEASE_NOTES_v1.0.0.md` / `docs/RELEASE_NOTES_v1.1.0.md`, `CHANGELOG.md`, the git
tags, `gh release view`, `gh run list`, and `reports/fable5_release_audit/`. Where the
checked-in checklist and what was actually done disagree, this file follows what was
done and says so (§6).

## 1. Facts about the existing releases

- Tags `v0.1.0`-`v0.5.3` are **lightweight** (`git cat-file -t` → `commit`); `v0.6.1`,
  `v1.0.0-rc1`, `v1.0.0`, `v1.1.0` are **annotated** (`→ tag`, tagger "Make My Figure",
  message `MakeMyFigure v1.1.0` / `Make My Figure v1.0.0`). New tags are annotated.
- `git rev-parse v1.1.0` gives the tag object (31e6097); `v1.1.0^{commit}` = 3da8563.
  The v1.1.0 audit quotes 52360b9 for v1.0.0 — that is the tag object; the commit is f815f41.
- Every `v*` tag push has triggered `.github/workflows/build_desktop_releases.yml`
  (`gh run list --workflow build_desktop_releases.yml`): v1.1.0 run 34048384960
  (8m47s), v1.0.0 run 29668187818, rc1 run 29589167501, v0.6.1 run 29459104776.
- GitHub releases exist for all 12 tags (`gh release list`). The v1.1.0 release
  carries 10 assets; rc1, v1.0.0 carry 5 (installers only); v0.6.1 carries 7
  (installers + a wheel/sdist that predate the resource-staging fix).
- Version convention: `MAJOR.MINOR.PATCH`, tag `vX.Y.Z`. Minor bumps for features
  (1.0.0 → 1.1.0: presets, histogram, R validation), patch bumps for fixes
  (0.5.1, 0.5.2, 0.5.3). Pre-release: tag `v1.0.0-rc1`, `__version__ = "1.0.0rc1"`
  (PEP 440 form in code, hyphenated in the tag). `version.py` stays at the last
  release between releases (no `.dev` suffix); pending items sit under
  `## Unreleased` in `CHANGELOG.md` (present today).

## 2. What the workflow automates

`.github/workflows/build_desktop_releases.yml`, triggers `push: tags: v*` and
`workflow_dispatch` (input `publish_release_tag`, added in PR #11, commit 2a69cab):

1. Matrix `windows-latest`, `macos-latest`, `ubuntu-latest`; Python 3.11;
   `pip install -e ".[desktop,build]"`; `python scripts/make_icons.py`.
2. Runs `scripts/build_linux.sh` (+ appimagetool), `scripts/build_macos.sh`,
   `scripts/build_windows.ps1` (after `choco install innosetup`).
3. Smoke test: `./dist/MakeMyFigure/MakeMyFigure --selftest` (`QT_QPA_PLATFORM=offscreen`);
   `MakeMyFigure.exe --selftest` on Windows.
4. **On a tag push, or a dispatch with `publish_release_tag` set**:
   `gh release create <tag> --title "Make My Figure <tag>" --notes "Automated build..." --verify-tag || true`
   then `gh release upload <tag> dist/{*.dmg,*.AppImage,*.exe,*-windows.zip,*-macos.zip,*-linux-*.tar.gz} --clobber`.
   The three OS jobs race to create the release; the generic notes are meant to be
   replaced afterwards with `gh release edit`.
5. A dispatch **without** `publish_release_tag` builds and smoke-tests only.

The workflow does **not**: run the test suite, build the wheel/sdist, upload the
manuals, compute `SHA256SUMS.txt`, or write release notes. Those are manual (§3).
Signing steps run only if secrets exist; all releases so far are unsigned.

## 3. Runbook (deterministic, numbered)

Legend: **[M]** manual, **[CI]** done by the workflow, **[M→CI]** manual action that
triggers automation. Stop at the first failed step; do not skip a gate.

**A. Decide and prepare**

1. **[M]** Confirm the maintainer has approved the work to ship and has named the
   **exact target version** (RELEASE mode in `git-workflow.md`). Never infer it.
2. **[M]** Verify the semantic bump against §1: new plot types / features → minor;
   fixes only → patch; pre-release → `-rcN` tag with `X.Y.ZrcN` in `version.py`.
3. **[M]** `git status --short` is empty on `main`; `git fetch origin && git status -sb`
   shows `main` even with `origin/main`.
4. **[M]** Create the branch: `git switch -c release/vX.Y.Z-integration main`
   (the v1.1.0 name). Integrate approved branches by fast-forward merge or
   `git cherry-pick -x`; never merge a `manuscript/` branch. Record every candidate
   commit and its disposition in `docs/releases/vX.Y.Z/release_vX.Y.Z_branch_audit.csv`
   (columns as in the v1.1.0 file: 91 rows across 18 branches).

**B. Gates**

5. **[M]** Full suite, headless:
   `MPLBACKEND=Agg python -m pytest -q -p no:pytest-qt --ignore=tests/test_desktop_gui.py`
   → 0 failed. Then the GUI module where Qt runs
   (`QT_QPA_PLATFORM=offscreen python -m pytest tests/test_desktop_gui.py -v`). Record
   the exact `N passed, M skipped (time)` lines.
6. **[M]** Targeted gates: `tests/test_r_validation_regressions.py`,
   `tests/test_release_guardrails.py`, `tests/test_packaging.py`, `tests/test_package_data.py`.
   If statistics code changed, re-run `benchmarks/r_validation/` and confirm
   0 FAIL / 0 NEEDS_REVIEW (audit §4).
7. **[M]** Counts from code, not memory:
   `python -c "from make_my_figure_core.plots.registry import available_plot_types as a; from make_my_figure_core import statistics as s; print(len(a()), len(s.TESTS))"`
   (38 and 18 at v1.1.0). Bump `tests/test_renderers_m2.py` / `tests/test_desktop_controller.py`
   if the plot count changed.
8. **[M]** Privacy grep (audit §8):
   `git ls-files | grep -i -E "manuscript|Concerns|EndNote|\.enl|claude|prompt|\.ttf|\.otf"` and
   `git grep -n -i -E "manuscriptv[0-9]|OneDrive|/mnt/c/Users"` return nothing private.

**C. Version and documentation**

9. **[M]** Set the version in every authoritative location
   (`git grep -n -E '\b1\.1\.0\b' -- '*.py' '*.toml' '*.md' '*.iss'` lists them):
   - `make_my_figure_core/version.py` — the only *code* location; `pyproject.toml`,
     the About dialog, `build_banner()`, the PyInstaller `MMF_VERSION`, Inno Setup
     `/DMyAppVersion` and every artefact file name derive from it.
   - `README.md` — version badge (line 6), download table file names (lines 34-40),
     banner example (43), wheel name (65), citation (204-205).
   - `CHANGELOG.md` — turn `## Unreleased` into `## [X.Y.Z] — <title>`.
   - `docs/RELEASE_NOTES_vX.Y.Z.md` — new file modelled on `docs/RELEASE_NOTES_v1.1.0.md`
     (status line, highlights, downloads table, glibc note, known limitations,
     verification commands).
   - `docs/manuals/` — regenerate with `python scripts/build_manuals.py` (injects
     `__version__` + commit into the Quick Start and User Manual MD/DOCX/PDF); rerun
     `python scripts/validate_documented_workflows.py` and update
     `docs/manuals/audit/*.csv|md`.
   - `docs/releases/vX.Y.Z/release_vX.Y.Z_audit.md` — the gate record (sections 1-9 as
     in v1.1.0); fill in test results from step 5.
10. **[M]** Commit as `Release X.Y.Z: version, changelog, README, ...`
    (pattern of f68a2f3) with the co-author trailer.

**D. Python distribution**

11. **[M]** `rm -rf dist build && python -m build`; fresh-venv install of the wheel;
    check `resources.missing_bundled_dirs() == []`, version, plot count, one export per
    format (audit §7). Keep `dist/` untracked.

**E. Merge, tag, build**

12. **[M]** Merge to `main`: fast-forward (`git switch main && git merge --ff-only
    release/vX.Y.Z-integration`) as for v1.1.0, or a PR if review is wanted.
13. **[M]** `git push origin main`.
14. **[M]** Annotated tag on the merge commit:
    `git tag -a vX.Y.Z -m "MakeMyFigure vX.Y.Z"`; verify `git cat-file -t vX.Y.Z` → `tag`.
15. **[M→CI]** `git push origin vX.Y.Z`. This starts the workflow.
16. **[CI]** Three OS builds, `--selftest`, `gh release create` with placeholder notes,
    upload of `.dmg`, `.AppImage`, `-Setup.exe`, `-windows.zip`, `-linux-x86_64.tar.gz`.
    Watch with `gh run list --workflow build_desktop_releases.yml -L 3` and
    `gh run watch <id>`; every job must be `success`.

**F. Finish the GitHub release**

17. **[M]** Replace the placeholder notes:
    `gh release edit vX.Y.Z --title "MakeMyFigure vX.Y.Z" --notes-file docs/RELEASE_NOTES_vX.Y.Z.md`
    (the v1.1.0 body = release notes + downloads table + changelog excerpt).
18. **[M]** Upload the hand-built assets. Copy the manual PDFs to versioned names
    first (v1.1.0 attached byte copies `MakeMyFigure_v1.1.0_Quick_Start.pdf` and
    `MakeMyFigure_v1.1.0_User_Manual.pdf`; `gh`'s `file#text` form sets a label, not the
    file name):
    `cp docs/manuals/Quick_Start/MakeMyFigure_Quick_Start.pdf dist/MakeMyFigure_vX.Y.Z_Quick_Start.pdf`
    (same for the User Manual), then
    `gh release upload vX.Y.Z dist/*.whl dist/make_my_figure_core-*.tar.gz dist/MakeMyFigure_vX.Y.Z_*.pdf`.
19. **[M]** Install/launch smoke test of the *downloaded* installers on at least the
    host OS: install, open an example, change plot type, export PNG/SVG/PDF + PlotSpec
    (`docs/RELEASE_CHECKLIST.md` §2 bullet 4). Check the status-bar banner shows the
    tag's short commit.
20. **[M]** Checksums from the downloaded assets, never from local builds:
    `mkdir -p /tmp/rel && gh release download vX.Y.Z -D /tmp/rel && (cd /tmp/rel && sha256sum * > SHA256SUMS.txt) && gh release upload vX.Y.Z /tmp/rel/SHA256SUMS.txt --clobber`.
    Compare with `gh release view vX.Y.Z --json assets -q '.assets[]|.name+" "+.digest'`.
21. **[M]** Verify: `gh release view vX.Y.Z --json url,tagName,publishedAt,assets`
    lists every expected file; tag resolves to the merge commit.

**G. Record**

22. **[M]** Append the checksums and any post-release notes to
    `docs/releases/vX.Y.Z/release_vX.Y.Z_audit.md` (v1.1.0 did this in commits 5686c42,
    e57cb68 glibc note, ce022c7 rebuild addendum), commit via a `docs/` branch + PR.
23. **[M]** Write `release_history/vX.Y.Z.md` with the ledger fields in
    `release_history/README.md`, evidence-only.

**Republishing assets without a new version** (used 2026-09-17): run the workflow
manually with `publish_release_tag=vX.Y.Z` from the ref to build
(`gh workflow run build_desktop_releases.yml -f publish_release_tag=vX.Y.Z --ref main`);
installers are replaced with `--clobber`. Rebuild and re-upload the wheel/sdist by hand,
regenerate `SHA256SUMS.txt` (step 20), and add an addendum to the audit saying which
commit the assets came from and that no application code changed (run 35180683713,
`main` at f7f1f46, audit §7 addendum). The tag is not moved.

## 4. Version-bearing locations (grep result, 2026-09-17)

`git grep -c -E '\b1\.1\.0\b' -- ':!*.csv' ':!*.pdf' ':!*.png' ':!*.json'`:
`make_my_figure_core/version.py` (1, the source), `README.md` (5), `CHANGELOG.md` (1),
`docs/RELEASE_NOTES_v1.1.0.md` (4), `docs/releases/v1.1.0/release_v1.1.0_audit.md` (15),
`docs/manuals/User_Manual/MakeMyFigure_User_Manual.md` (6),
`docs/manuals/User_Manual/parts/01_introduction_installation_interface_data.md` (5),
`docs/manuals/Quick_Start/MakeMyFigure_Quick_Start.md` (4) and `.src.md` (3),
`docs/manuals/audit/current_capabilities.md` (3),
`docs/manuals/audit/known_documentation_limitations.md` (1). No `.toml`, `.iss`,
`.spec`, `.sh`, `.ps1` or `.yml` file carries the version.

## 5. Are builds CI-only?

No, but effectively yes for a release: the per-OS scripts build locally on their own
OS and `docs/RELEASE_CHECKLIST.md` §2 asks for a local build per OS "ideally"; no
tracked record shows local installers being published. All published installers were
built by the GitHub Actions runners (audit §7, run ids above). The wheel/sdist are the
opposite: always built locally with `python -m build` and uploaded by hand.

## 6. Where `docs/RELEASE_CHECKLIST.md` (and `docs/BUILD_INSTALLERS.md`) are out of date

1. Both say CI "does not create a public GitHub Release on its own". Since the
   `ci/release-attach` work (v0.3.0, PR #2) the workflow runs `gh release create` and
   uploads installers on every `v*` tag push, and since PR #11 a manual run with
   `publish_release_tag` replaces assets on an existing release.
2. Asset names listed (`MakeMyFigure-Setup.exe`, `MakeMyFigure.dmg`, `MakeMyFigure.AppImage`)
   are the pre-1.1.0 unversioned names; since f68a2f3 they are
   `MakeMyFigure-<ver>-Setup.exe`, `MakeMyFigure-<ver>.dmg`, `MakeMyFigure-<ver>.AppImage`,
   `MakeMyFigure-<ver>-windows.zip`, `MakeMyFigure-<ver>-linux-<arch>.tar.gz`.
3. `MakeMyFigure-macos.zip` is described as a normal fallback; it is produced only when
   `hdiutil` fails and has never been on a release (commit 8fc78e9).
4. The checklist has no step for the wheel/sdist, the manuals, `SHA256SUMS.txt`,
   `docs/RELEASE_NOTES_vX.Y.Z.md`, `docs/releases/<tag>/` audits, the README version
   references, or the privacy grep — all of which v1.1.0 did.
5. `pytest -q` alone cannot collect on a headless machine with PySide6 installed;
   the audit used `-p no:pytest-qt --ignore=tests/test_desktop_gui.py` plus a separate
   GUI run.
6. "Bump `version.py` to the next dev version if desired" has never been done;
   `version.py` equals the last release and `CHANGELOG.md` uses `## Unreleased`.
7. The checklist treats a manual workflow run as equivalent to a tag push; it is
   build-only unless `publish_release_tag` is given.

## Verify this is still current

```bash
git cat-file -t v1.1.0; git tag -l --format='%(refname:short) %(objecttype)' | tail -4
gh release list -L 3 && gh run list --workflow build_desktop_releases.yml -L 3
grep -n 'publish_release_tag\|gh release' .github/workflows/build_desktop_releases.yml
git grep -c -E '\b1\.1\.0\b' -- ':!*.csv' ':!*.pdf' ':!*.png' ':!*.json'
```
