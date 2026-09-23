# GitHub release publication

Repository: `surPoudel/make-my-figure` (PUBLIC since at least 2026-09-22). `gh` is authenticated as
the author on the WSL host (`gh auth status`); the agent never stores a token.

## Sequence (RELEASE mode, after the gate)
1. `git tag -a v<v> -m "MakeMyFigure v<v>"`
2. `git push origin v<v>`  -> triggers `.github/workflows/build_desktop_releases.yml`
3. `gh release create v<v> --title "MakeMyFigure v<v>" --notes-file release_staging/<v>/RELEASE_NOTES_DRAFT.md --verify-tag <assets...> SHA256SUMS.txt`
   Assets: everything staged under `release_staging/<v>/{python,windows,macos,linux,manuals}/` plus
   `checksums/SHA256SUMS.txt` (10 files for v1.1.0). `--verify-tag` refuses if the tag is not on the remote.
4. `verify_tag.py --tag v<v>` (tag exists, annotated, on origin, same commit, release present).
5. `record_release.py --tag v<v>` (ledger).

## CI interaction
The workflow also uploads its own installer builds to a release created by the tag push (CI-built
Windows/macOS/Linux assets). Decide *before* publishing which artefacts are authoritative:
- **Option A (v1.1.0 precedent):** let CI build the three installers, download them, validate and
  checksum them locally (`release_staging/<v>/<os>/` + hand-written manifest with the run's commit),
  then upload wheel/sdist/manuals/SHA256SUMS.txt by hand.
- **Option B:** upload locally built installers; if CI also attaches files with the same names it will
  fail on the clash - re-run the release upload with `gh release upload --clobber` for the intended set.
Either way `SHA256SUMS.txt` must describe the files that are finally attached; `generate_checksums.py
--verify` after downloading the attached assets is the final check (`gh release download v<v> -D <dir>`).

## Release text
`docs/RELEASE_NOTES_v<v>.md` is the canonical body (v1.0.0, v1.1.0, v1.1.1 exist);
`release_notes_draft.py` appends the download table with hashes, the unsigned-app guidance, the glibc
line and the live counts. The author approves the draft before RELEASE mode reads it.

## Pre-releases
`X.Y.ZrcN` -> tag `vX.Y.Z-rcN`; pass `--prerelease` to `gh release create` (add it to the command in
`release_manager.py` when the version has an rc suffix - it currently prints the command for review).

## Post-release checklist
Download one asset per OS and launch; `sha256sum -c`; README download table names; ledger notes;
consider bumping `version.py` to the next development version on `main` (project checklist section 6).
