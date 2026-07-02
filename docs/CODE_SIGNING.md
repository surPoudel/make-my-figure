# Code Signing & Notarization (optional)

Signing is **optional**. Unsigned builds work but trigger OS security warnings on
first launch. The build scripts and CI **never fail** when signing secrets are
absent — they simply produce unsigned artifacts.

## What users see for unsigned apps

- **Windows**: SmartScreen "Windows protected your PC" → *More info* → *Run anyway*.
- **macOS**: "cannot be opened because the developer cannot be verified" →
  right-click the app → *Open*, or System Settings → Privacy & Security → *Open Anyway*.
- **Linux**: AppImages generally run without warnings; ensure the file is
  executable (`chmod +x MakeMyFigure.AppImage`).

## Windows (Authenticode) — optional

1. Obtain a code-signing certificate (`.pfx`).
2. Store as CI secrets: `WINDOWS_CERT_PFX_BASE64` (base64 of the `.pfx`) and
   `WINDOWS_CERT_PASSWORD`.
3. Sign with `signtool`:
   ```powershell
   signtool sign /f cert.pfx /p $env:WINDOWS_CERT_PASSWORD /fd sha256 `
     /tr http://timestamp.digicert.com /td sha256 dist\MakeMyFigure\MakeMyFigure.exe
   ```
4. To sign the installer, uncomment `SignTool=` in `packaging/windows_installer.iss`.

The provided `scripts/build_windows.ps1` detects these env vars and notes when
signing is configured; wiring the actual `signtool` call is left as a deliberate
placeholder so unsigned builds never break.

## macOS (Developer ID + notarization) — optional

Required Apple Developer secrets (set as CI secrets / local env):
`APPLE_DEVELOPER_ID` (e.g. "Developer ID Application: Name (TEAMID)"),
`APPLE_ID`, `APPLE_APP_PASSWORD` (app-specific password), `APPLE_TEAM_ID`.

```bash
codesign --deep --force --options runtime --timestamp \
  --sign "$APPLE_DEVELOPER_ID" dist/MakeMyFigure.app
xcrun notarytool submit dist/MakeMyFigure.dmg \
  --apple-id "$APPLE_ID" --password "$APPLE_APP_PASSWORD" --team-id "$APPLE_TEAM_ID" --wait
xcrun stapler staple dist/MakeMyFigure.dmg
```

`scripts/build_macos.sh` runs only the unsigned path by default and detects
`APPLE_DEVELOPER_ID` to indicate signing is configured (the `codesign` line is
commented as a placeholder).

## Security / secrets policy

- **Never commit certificates, passwords, or keys to the repository.** Use CI
  secrets or a local keychain only.
- This project does not access, store, or transmit any secrets. The signing
  hooks read environment variables that you provide.
