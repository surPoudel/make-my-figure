; Inno Setup script for Make My Figure (Windows installer).
; Build:  iscc /DMyAppVersion=0.1.0 packaging\windows_installer.iss
; Produces dist\MakeMyFigure-<version>-Setup.exe
; Requires the PyInstaller output at dist\MakeMyFigure\ (run build_windows.ps1 first).

#ifndef MyAppVersion
  #define MyAppVersion "0.1.0"
#endif
#define MyAppName "Make My Figure"
#define MyAppPublisher "Make My Figure contributors"
#define MyAppURL "https://github.com/surPoudel/make-my-figure"
#define MyAppExeName "MakeMyFigure.exe"

[Setup]
LicenseFile=..\LICENSE
AppId={{B6E3F2A1-MMF0-4C2A-9D1E-MAKEMYFIGURE01}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\MakeMyFigure
DefaultGroupName=Make My Figure
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=MakeMyFigure-{#MyAppVersion}-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; SignTool=signtool $f   ; enable when a signing tool is configured (see docs/CODE_SIGNING.md)
SetupIconFile=..\assets\icons\icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "..\dist\MakeMyFigure\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Make My Figure"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Make My Figure"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Make My Figure"; Flags: nowait postinstall skipifsilent
