# Linux build

Wrapper: `scripts/build_linux.sh` -> `scripts/build_desktop.py --clean` (PyInstaller) -> tar.gz of
`dist/MakeMyFigure/` -> AppDir (`AppRun`, `.desktop`, icon) -> `appimagetool` if on PATH.
Agent: `build_current_platform.py` (creates the clean venv, runs the wrapper, self-tests, stages).

## Clean interpreter is mandatory
PyInstaller bundles whatever the interpreter can import. On 2026-09-23 the same commit built from the
WSL miniconda base produced a **929 MB** app folder (llvmlite 160 MB, pyarrow 142 MB, pymupdf 51 MB,
numcodecs, botocore ...) against a **188 MB** compressed tarball for v1.1.0 from CI. The agent therefore
builds inside `~/.cache/makemyfigure-release/venv-linux-py3.11` with only `.[desktop,build]`, exactly
like CI. `--system-python` exists for diagnosis and is recorded in the manifest as such.

## glibc
A PyInstaller bundle needs the build host's glibc or newer at runtime. CI (`ubuntu-latest`, 24.04)
gives glibc 2.39-class binaries: the v1.1.0 Linux assets do not start on glibc 2.35 (Ubuntu 22.04,
this WSL). A bundle built on this WSL host (glibc 2.35) runs on more systems. Whichever host builds
the published Linux asset, its glibc is recorded in `platform_build_manifest.json -> host.glibc` and
`release_notes_draft.py` prints the requirement.

## Headless self-test on WSL
No display: `QT_QPA_PLATFORM=offscreen`. The Qt xcb/offscreen plugins still need system libraries
(libxkbcommon, libGL, fontconfig ...) that this WSL lacks; they were unpacked from Ubuntu .deb files to
`/tmp/qtdeb/root/usr/lib/x86_64-linux-gnu` and exported via `LD_LIBRARY_PATH` (see
`local-model-runtime.md`). On a normal desktop Linux none of this is needed.

## AppImage
`appimagetool` (AppImageKit continuous, x86_64) is not packaged by apt; CI downloads it. Locally it was
placed at `/tmp/rmtools/appimagetool` and put on PATH for the wrapper. If absent the wrapper skips the
AppImage and the tar.gz is still produced; `reconcile_platforms.py` lists `MakeMyFigure-<v>.AppImage`
as "not produced". FUSE is not required to *build*; users of old distributions may need
`--appimage-extract-and-run`.

## Artefacts
`MakeMyFigure-<v>-linux-x86_64.tar.gz` (always), `MakeMyFigure-<v>.AppImage` (when appimagetool is
available). Both go to `release_staging/<v>/linux/`.
