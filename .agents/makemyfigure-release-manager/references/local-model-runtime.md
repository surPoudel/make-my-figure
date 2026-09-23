# Running the agent with a local or different model, and on this WSL host

The agent is a set of scripts plus this documentation. A model operating it only needs to (1) read
`AGENT.md`, (2) run scripts, (3) read the JSON/Markdown they produce, (4) relay results and stop at the
gates. No API is called by the scripts; nothing depends on the model vendor.

## Minimal operator loop (any model, or a human)
```
python .agents/makemyfigure-release-manager/scripts/release_manager.py audit
python .agents/makemyfigure-release-manager/scripts/release_manager.py build-local
cat release_staging/<v>/RELEASE_REPORT.md
```
If a step fails, read the matching `reports/*.json`, fix, re-run. Do not skip a failing step by editing
the script.

## Host specifics (author's St. Jude WSL2, Ubuntu 22.04, glibc 2.35)
- Interpreter: `python` (miniconda 3.11.8); the repo's `.venv` is a broken stub. The agent's build venv is
  separate: `~/.cache/makemyfigure-release/venv-linux-py3.11`.
- Qt offscreen on this WSL needs system libraries not installed: they were unpacked from Ubuntu debs to
  `/tmp/qtdeb/root/usr/lib/x86_64-linux-gnu`. Before `--selftest` or GUI tests:
  `export LD_LIBRARY_PATH=/tmp/qtdeb/root/usr/lib/x86_64-linux-gnu QT_QPA_PLATFORM=offscreen`.
  `/tmp` does not survive a reboot; re-create by extracting the debs (libxkbcommon0, libxcb-*, libgl1,
  libegl1, libfontconfig1, libdbus-1-3, libxkbcommon-x11-0, libxcb-cursor0) with `dpkg-deb -x` into that root.
- `appimagetool` at `/tmp/rmtools/appimagetool` (download AppImageKit continuous x86_64, `chmod +x`;
  put `/tmp/rmtools` on PATH). Same reboot caveat.
- Windows Python for native Windows work: `/mnt/c/Users/<user>/mmf_winpy311/Scripts/python.exe`
  (PySide6, pywin32, PyInstaller 6.x installed 2026-09-23). No Inno Setup on the Windows host.
- OneDrive: worktrees live under OneDrive. Large build trees sync slowly; `build/` and `dist/` are
  git-ignored but still synced by OneDrive. Prefer building in a clone outside OneDrive when speed matters.
- Repository paths contain an apostrophe ("St. Jude Children's ..."): shell snippets must quote paths and
  must not embed them inside Python one-liners (fixed in `scripts/build_*.sh|ps1` on 2026-09-23).
- `git push` from the assistant is blocked by the permission classifier; the author runs pushes.

## Model-independence checklist
- Every fact in a report comes from a script output in the same run.
- Every mutating action is a listed mode with a listed gate.
- Numbers in documentation carry a date and a commit; re-derive before quoting.
