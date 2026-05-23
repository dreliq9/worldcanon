# PyInstaller spec for the worldcanon-import CLI.
# Build with:  pyinstaller pyinstaller/importer.spec
# Output:      dist/worldcanon-import (single executable)

from pathlib import Path

HERE = Path(SPECPATH).resolve()
REPO_ROOT = HERE.parent

block_cipher = None

a = Analysis(
    [str(REPO_ROOT / "server" / "worldcanon" / "import_cli.py")],
    pathex=[str(REPO_ROOT / "server")],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=["pytest", "_pytest", "tkinter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="worldcanon-import",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
