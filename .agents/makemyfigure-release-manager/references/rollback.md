# Rollback and recovery

Principle: a published release is history. Fix forward with a PATCH release; never delete or move
a public tag that a release page or a user may reference.

| Situation | Action |
|---|---|
| Preflight STOP | Fix the cause in the working tree, re-run. Nothing to roll back. |
| Build failed | `clean_build_outputs.py --version <v>` removes `build/`, `dist/MakeMyFigure*`, `release_staging/<v>/`; fix; rebuild. |
| Wrong artefact staged | delete the file from `release_staging/<v>/<os>/`, rebuild that platform, regenerate checksums. |
| Version text edited (PREPARE RC --execute) but the release is postponed | `git checkout -- make_my_figure_core/version.py README.md` (and remove the notes draft) if uncommitted; otherwise a revert commit. |
| Tag created locally, not pushed | `git tag -d v<v>` |
| Tag pushed, **no** GitHub release, CI possibly running | `git push origin :refs/tags/v<v>` then `git tag -d v<v>`; cancel the workflow run (`gh run cancel <id>`). Record in the ledger why. |
| GitHub release created with a wrong asset | `gh release upload v<v> <file> --clobber` for the corrected file, regenerate and re-upload `SHA256SUMS.txt`, add an "Updated" line to the release notes. The tag stays. |
| Release is fundamentally broken (app does not start) | Mark the release as pre-release / edit notes to say "superseded", publish `vX.Y.(Z+1)`. |
| Private material discovered in the repository history | Stop everything; tell the author. Removal requires history rewrite + force push + GitHub support to purge caches; not an agent action. |
| Pushed a branch that must stay private | `git push origin --delete <branch>` immediately; tell the author (precedent: manuscript branches pushed and removed 2026-09-2x). |

Never: `git push --force` to `main`, `git tag -f` on a public tag, deleting a release that has downloads.
