from PyInstaller.utils.hooks import collect_all

# Collect all mediapipe files (binaries, data, hidden imports)
mp_datas, mp_binaries, mp_hiddenimports = collect_all("mediapipe")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=mp_binaries,
    datas=mp_datas,
    hiddenimports=mp_hiddenimports + [
        "PyQt6.sip",
        "cv2",
    ],
    hookspath=[],
    runtime_hooks=[],
    # Exclude heavy packages pulled in by mediapipe that we don't use at runtime
    excludes=["scipy", "pandas", "IPython", "notebook"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TacetHealthCare",
    debug=False,
    strip=False,
    upx=False,          # UPX disabled — avoids antivirus false positives
    console=False,      # No terminal window
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="TacetHealthCare",
)
