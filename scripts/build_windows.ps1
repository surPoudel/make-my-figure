# Build the Windows desktop app and (optionally) an installer.
# Run from the repo root in PowerShell:
#   .\scripts\build_windows.ps1
#
# Requires: Python 3.9+ with build deps installed:
#   python -m pip install -e ".[desktop,build]"
# Optional installer: Inno Setup (iscc.exe) on PATH produces MakeMyFigure-<version>-Setup.exe.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "==> Building app folder with PyInstaller"
python "$Root\scripts\build_desktop.py" --clean

$Ver = (python -c "import sys; sys.path.insert(0, r'$Root'); from make_my_figure_core.version import __version__; print(__version__)").Trim()
$AppDir = Join-Path $Root "dist\MakeMyFigure"
if (-Not (Test-Path $AppDir)) { throw "Build failed: $AppDir not found" }

# Always produce a portable ZIP as a fallback artifact.
$Zip = Join-Path $Root "dist\MakeMyFigure-$Ver-windows.zip"
Write-Host "==> Creating portable ZIP: $Zip"
if (Test-Path $Zip) { Remove-Item $Zip }
Compress-Archive -Path "$AppDir\*" -DestinationPath $Zip

# Optional: build a setup .exe with Inno Setup if available.
$Iscc = Get-Command iscc.exe -ErrorAction SilentlyContinue
if ($Iscc) {
    Write-Host "==> Inno Setup found; building MakeMyFigure-$Ver-Setup.exe"
    & $Iscc.Path "/DMyAppVersion=$Ver" "$Root\packaging\windows_installer.iss"
} else {
    Write-Host "==> Inno Setup (iscc.exe) not found; skipping .exe installer."
    Write-Host "    Portable ZIP is available at $Zip"
}

# Optional code signing (only if a cert is provided via env vars).
if ($env:WINDOWS_CERT_PFX_BASE64 -and $env:WINDOWS_CERT_PASSWORD) {
    Write-Host "==> Signing is configured; see docs/CODE_SIGNING.md (signtool)."
} else {
    Write-Host "==> No signing secrets present; producing UNSIGNED build (expected)."
}
Write-Host "Done."
