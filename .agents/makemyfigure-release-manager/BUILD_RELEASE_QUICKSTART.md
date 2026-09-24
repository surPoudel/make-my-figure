# Build and release quick start (author's path)

All commands from the repository root, in the environment where `pip install -e ".[desktop,build,dev]"`
has been done (the build itself uses a separate clean venv automatically).

## 1. Where do we stand? (30 s)

```
python .agents/makemyfigure-release-manager/scripts/release_manager.py audit
```

Shows branch, uncommitted changes, latest tag, commits since, version agreement, live plot and
statistics counts, latest GitHub release, and a private-file scan. Nothing is modified.

## 2. Build and test locally (15-25 min on this OS)

```
python .agents/makemyfigure-release-manager/scripts/release_manager.py build-local
```

Produces under `release_staging/<version>/`:

- `python/` wheel + sdist (twine-checked, installed into a throw-away venv and exercised),
- `<this-os>/` the native app built by the project's own `scripts/build_*.{sh,ps1}` inside a clean
  build venv, self-tested with `MakeMyFigure --selftest`, packaged (tar.gz/AppImage, zip/Setup.exe, dmg),
- `checksums/SHA256SUMS.txt` + `release_artifacts.json`,
- `RELEASE_NOTES_DRAFT.md` and `RELEASE_REPORT.md`.

Nothing is committed, tagged or pushed. Repeat on the other operating systems at the same commit,
copy their `release_staging/<version>/<os>/` folders here, then:

```
python .agents/makemyfigure-release-manager/scripts/reconcile_platforms.py --version <v> --require python,windows,macos,linux
python .agents/makemyfigure-release-manager/scripts/generate_checksums.py --version <v>
```

Alternative for the other platforms: GitHub Actions `Build desktop releases` (`workflow_dispatch`),
download the artefacts, drop them into the platform folders and write a manifest by hand from the
run's commit (or let `reconcile_platforms.py` report them as missing manifests).

## 3. Start a new version

```
python .agents/makemyfigure-release-manager/scripts/release_manager.py prepare-rc --version 1.2.0            # dry run, shows the plan
python .agents/makemyfigure-release-manager/scripts/release_manager.py prepare-rc --version 1.2.0 --execute  # edits version.py + README
```

Then by hand: `## [1.2.0]` section in `CHANGELOG.md`, `docs/RELEASE_NOTES_v1.2.0.md`,
`python scripts/build_manuals.py` (manual banners and PDFs). Re-run step 1 until every version
location agrees; run step 2.

## 4. Publish (only you)

```
python .agents/makemyfigure-release-manager/scripts/release_manager.py commit-push --version 1.2.0 --dry-run
MMF_RELEASE_AUTHORIZED=yes python .agents/makemyfigure-release-manager/scripts/release_manager.py commit-push --version 1.2.0 --authorize "I authorize commit-push for v1.2.0"

python .agents/makemyfigure-release-manager/scripts/release_manager.py release --version 1.2.0 --dry-run
MMF_RELEASE_AUTHORIZED=yes python .agents/makemyfigure-release-manager/scripts/release_manager.py release --version 1.2.0 --authorize "I authorize release for v1.2.0"
```

`release` re-runs preflight in release strictness (on `main`, clean, pushed, tests passing), the
tag pre-check, reconciliation, checksum verification and artefact validation; then creates the
annotated tag, pushes it, creates the GitHub release with every staged asset and `SHA256SUMS.txt`,
verifies the tag and writes `release_history/v1.2.0.json`.

## 5. After publishing

Download one installer per OS from the release page and launch it; `sha256sum -c SHA256SUMS.txt`;
add free-text notes to the ledger record; update the README download table if names changed.

## If something is wrong

`references/rollback.md`. Short version: a tag that was pushed by mistake but has no release yet
can be deleted (`git push origin :refs/tags/vX`); a published release is never deleted, it is
followed by a patch release.
