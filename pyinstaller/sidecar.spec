# PyInstaller spec for the worldcanon sidecar.
# Build with:  pyinstaller pyinstaller/sidecar.spec
# Output:      dist/worldcanon-sidecar/  (folder containing the exe + libs)

from pathlib import Path

HERE = Path(SPECPATH).resolve()
REPO_ROOT = HERE.parent

block_cipher = None

a = Analysis(
    [str(HERE / "sidecar_entry.py")],
    pathex=[str(REPO_ROOT / "server")],
    binaries=[],
    datas=[
        (str(REPO_ROOT / "corpora.yaml"), "."),
        (str(REPO_ROOT / "server" / "worldcanon" / "prompts"), "worldcanon/prompts"),
    ],
    hiddenimports=[
        "worldcanon.main",
        "worldcanon.chunkers.prose",
        "worldcanon.chunkers.entity_sheet",
        "worldcanon.chunkers.system_sheet",
        "worldcanon.chunkers.naming_sheet",
        "worldcanon.chunkers.journal",
        "fastembed",
        "sqlite_vec",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "pytest",
        "_pytest",
        "tkinter",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="worldcanon-sidecar",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="worldcanon-sidecar",
)
