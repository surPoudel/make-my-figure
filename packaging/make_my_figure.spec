# PyInstaller spec for Make My Figure desktop app.
# Build via:  python scripts/build_desktop.py   (recommended)
# or directly:  pyinstaller packaging/make_my_figure.spec
#
# Produces a one-folder app under dist/MakeMyFigure/ (and MakeMyFigure.app on macOS).
import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(SPEC)), ".."))

APP_NAME = "MakeMyFigure"

# Bundle the resource folders the core resolves via sys._MEIPASS at runtime.
datas = [
    (os.path.join(ROOT, "schemas"), "schemas"),
    (os.path.join(ROOT, "style_profiles"), "style_profiles"),
    (os.path.join(ROOT, "mock_data"), "mock_data"),
    (os.path.join(ROOT, "examples"), "examples"),
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
# Statistics engine dependencies (two-way / repeated-measures ANOVA, Cox).
# statsmodels imports many submodules lazily and ships data files; patsy is its
# formula dependency. Without these the built app crashes on those tests.
hiddenimports += collect_submodules("statsmodels")
hiddenimports += collect_submodules("patsy")
hiddenimports += ["pandas", "statsmodels.api", "statsmodels.formula.api",
                  "statsmodels.stats.anova", "statsmodels.duration.hazard_regression"]

# statsmodels/scipy bundle small data files needed at runtime.
datas += collect_data_files("statsmodels")

# Optional: bundle a self-contained R env (edgeR/limma/DESeq2) when the CI sets
# MMF_BUNDLE_R_ENV. Shipped as data under _MEIPASS/r_env; the app's
# rnaseq.r_setup.bundled_rscript_path() finds it at runtime. Off by default so
# the standard installers stay small (~100-230 MB vs ~1-1.5 GB bundled).
_r_env = os.environ.get("MMF_BUNDLE_R_ENV")
if _r_env and os.path.isdir(_r_env):
    for _root, _dirs, _files in os.walk(_r_env):
        for _f in _files:
            _abs = os.path.join(_root, _f)
            _rel = os.path.relpath(_abs, _r_env)
            datas.append((_abs, os.path.join("r_env", os.path.dirname(_rel))))

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
