# Windows build

Wrapper: `scripts/build_windows.ps1` (PowerShell) -> `scripts/build_desktop.py --clean` -> `Compress-Archive`
portable zip -> Inno Setup (`iscc.exe /DMyAppVersion=<v> packaging\windows_installer.iss`) when on PATH ->
optional signing only if `WINDOWS_CERT_PFX_BASE64` / `WINDOWS_CERT_PASSWORD` exist (they do not; releases are unsigned).
Agent: `build_current_platform.py` run **from a Windows Python** (`py -3.11` or a venv); it invokes
`powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1` with the clean build venv first on PATH.

## Requirements on the Windows machine
- Python 3.11 x64 (CI uses 3.11); the agent creates `%LOCALAPPDATA%\makemyfigure-release\venv-windows-py3.11`.
- Inno Setup 6 (`choco install innosetup` in CI). Without it only `MakeMyFigure-<v>-windows.zip` is produced and
  the `-Setup.exe` is reported as not produced. The St. Jude Windows host used for the tutorial work has no Inno Setup.
- Run outside OneDrive if possible: PyInstaller writes tens of thousands of files under `build/` and `dist/`,
  which OneDrive tries to sync. Cloning the tagged commit to `C:\src\make_my_figure` is the fastest path.

## From WSL (done 2026-09-23)
The Windows interpreter at `/mnt/c/Users/<user>/mmf_winpy311/Scripts/python.exe` drove a native Windows
build of commit b08be20: `git clone --branch <branch> <worktree> /mnt/c/src/mmf_release_<commit>` (a plain
path: `git.exe` cannot read a WSL worktree, and OneDrive is avoided), then
`python.exe C:\src\mmf_release_<commit>\.agents\makemyfigure-release-manager\scripts\build_current_platform.py --version <v>`.
The agent created `%LOCALAPPDATA%\makemyfigure-release\venv-windows-py3.11`, installed `.[desktop,build]`
(PyInstaller 6.22.3, PySide6 6.11.2), ran `scripts\build_windows.ps1`, self-tested `MakeMyFigure.exe`
(39 plot types OK) and staged `MakeMyFigure-1.1.1-windows.zip` 147.5 MB (v1.1.0: 152 MB, 0.97x) from a
333 MB / 2270-file app folder in 352 s. No `-Setup.exe` because Inno Setup is not installed. Copy
`release_staging\<v>\windows\` into the coordinating checkout's `release_staging/<v>/` and reconcile.

## Verification
`dist\MakeMyFigure\MakeMyFigure.exe --selftest` (run by the agent). SmartScreen shows "unrecognized app"
for the unsigned installer; `docs/CODE_SIGNING.md` documents the signing path if a certificate is ever bought.

## Artefacts
`MakeMyFigure-<v>-windows.zip` (always), `MakeMyFigure-<v>-Setup.exe` (Inno Setup present). Historical
sizes: v1.1.0 zip 152 MB, Setup.exe 104 MB.
