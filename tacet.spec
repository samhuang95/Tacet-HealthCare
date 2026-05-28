from PyInstaller.utils.hooks import collect_all

# Collect all mediapipe files (binaries, data, hidden imports)
mp_datas, mp_binaries, mp_hiddenimports = collect_all("mediapipe")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=mp_binaries,
    datas=mp_datas + [("assets", "assets")],
    hiddenimports=mp_hiddenimports + [
        "PyQt6.sip",
        "cv2",
    ],
    hookspath=[],
    runtime_hooks=[],
    # Exclude heavy packages pulled in by mediapipe that we don't use at runtime
    excludes=[
        "scipy", "pandas", "IPython", "notebook",
        "matplotlib", "contourpy", "cycler", "fonttools",
        "kiwisolver", "pyparsing", "python_dateutil", "six",
        "sounddevice", "PIL", "Pillow",
        "PyQt6.QtWebEngine", "PyQt6.QtWebEngineCore", "PyQt6.QtWebEngineWidgets",
        "PyQt6.QtSql", "PyQt6.QtTest", "PyQt6.QtBluetooth",
        "PyQt6.QtNfc", "PyQt6.QtSerialPort", "PyQt6.QtLocation",
        "PyQt6.QtMultimedia", "PyQt6.QtMultimediaWidgets",
        "PyQt6.QtPdf", "PyQt6.QtPdfWidgets",
    ],
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
    icon="assets/logo.ico",
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
