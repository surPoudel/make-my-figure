# PyInstaller spec for Make My Figure desktop app.
# Build via:  python scripts/build_desktop.py   (recommended)
# or directly:  pyinstaller packaging/make_my_figure.spec
#
# Produces a one-folder app under dist/MakeMyFigure/ (and MakeMyFigure.app on macOS).
import os
import sys

from PyInstaller.utils.hooks import collect_submodules

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(SPEC)), ".."))

APP_NAME = "MakeMyFigure"

# Bundle the resource folders the core resolves via sys._MEIPASS at runtime.
datas = [
    (os.path.join(ROOT, "schemas"), "schemas"),
    (os.path.join(ROOT, "style_profiles"), "style_profiles"),
    (os.path.join(ROOT, "mock_data"), "mock_data"),
    (os.path.join(ROOT, "assets", "icons"), os.path.join("assets", "icons")),
]

hiddenimports = [
    # Matplotlib backends are imported lazily by format; bundle the ones we export.
    "matplotlib.backends.backend_agg",
    "matplotlib.backends.backend_svg",
    "matplotlib.backends.backend_pdf",
    "matplotlib.backends.backend_ps",
    "matplotlib.backends.backend_qtagg",
    "PIL",
]
hiddenimports += collect_submodules("scipy")

# Per-platform icon: Windows .ico, macOS .icns (if present), Linux uses PNG at runtime.
icon = None
if sys.platform.startswith("win"):
    ico = os.path.join(ROOT, "assets", "icons", "icon.ico")
    icon = ico if os.path.exists(ico) else None
elif sys.platform == "darwin":
    icns = os.path.join(ROOT, "assets", "icons", "icon.icns")
    icon = icns if os.path.exists(icns) else None

block_cipher = None

a = Analysis(
    [os.path.join(ROOT, "apps", "desktop_app", "main.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter"],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,           # GUI app: no console window
    icon=icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name=APP_NAME,
)

# macOS application bundle.
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        icon=icon,
        bundle_identifier="com.makemyfigure.desktop",
        info_plist={
            "CFBundleName": "Make My Figure",
            "CFBundleDisplayName": "Make My Figure",
            "CFBundleShortVersionString": os.environ.get("MMF_VERSION", "0.1.0"),
            "NSHighResolutionCapable": True,
        },
    )
