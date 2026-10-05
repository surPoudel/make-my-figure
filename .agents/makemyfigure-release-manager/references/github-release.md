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

## CI interaction (read the workflow's last step before every release)
`build_desktop_releases.yml` ends with: `gh release create <tag> ... || true` (generic notes; fails
harmlessly when the release already exists) and `gh release upload <tag> dist/*.{dmg,AppImage,exe,
-windows.zip,-macos.zip,-linux-*.tar.gz} --clobber`. Consequences:

- Create the release from WSL **before or right after** pushing the tag: then the notes are yours, not
  "Automated build ...". RELEASE mode does tag -> push -> create in one go, so the create wins.
- CI **replaces** same-named files. The WSL-built Linux tar.gz and AppImage (glibc 2.35, runs on more
  distributions) are overwritten by the runner's glibc-2.39 builds. Decide which to keep; the FINALIZE
  step re-uploads the local ones with `--prefer-local linux` (default) after CI finishes.
- The macOS runner (`macos-latest`) is Apple silicon: the CI dmg is arm64 only (as for v1.1.0).
- `SHA256SUMS.txt` published at release time cannot describe CI's files. FINALIZE downloads the final
  asset set, regenerates the checksum file, uploads it with `--clobber`, downloads again and verifies.

The WSL-driven release is therefore: `build-local` -> `release --platforms python,linux` -> wait for the
CI run (`gh run watch <id>`; ~20 min) -> `finalize --prefer-local linux` -> download one installer per OS
and launch it. This mirrors the v1.1.0 process (installers from CI, everything else attached by hand),
with the checksum gap closed.

## Release text
`docs/RELEASE_NOTES_v<v>.md` is the canonical body (v1.0.0, v1.1.0, v1.1.1 exist);
`release_notes_draft.py` appends the download table with hashes, the unsigned-app guidance, the glibc
line and the live counts. The author approves the draft before RELEASE mode reads it.

## Pre-releases
`X.Y.ZrcN` -> tag `vX.Y.Z-rcN`; pass `--prerelease` to `gh release create` (add it to the command in
`release_manager.py` when the version has an rc suffix - it currently prints the command for review).

## Post-release checklist
`finalize` (above); download one asset per OS and launch; `sha256sum -c`; README download table names; ledger notes;
consider bumping `version.py` to the next development version on `main` (project checklist section 6).
