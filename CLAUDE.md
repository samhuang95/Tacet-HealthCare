# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Tacet HealthCare** — "Master the pause. Perfect the performance"

A Windows 11 desktop application that monitors eye blink activity via webcam. Alerts the user after 5 seconds without blinking. Runs as a system tray background app.

## Environment

- Python 3.12 + `.venv` (venv, never conda or global install)
- Always activate venv before running anything: `.venv\Scripts\activate`

## Commands

```powershell
# Run in development
.venv\Scripts\python.exe main.py

# Install dependencies (into venv only)
.venv\Scripts\pip.exe install -r requirements.txt

# Add a new package
.venv\Scripts\pip.exe install <package>
.venv\Scripts\pip.exe freeze > requirements.txt

# Package for distribution (produces dist\TacetHealthCare\)
.venv\Scripts\pyinstaller.exe --clean tacet.spec
```

## Stack

| Layer | Library |
|---|---|
| UI + System Tray | PyQt6 |
| Camera capture | OpenCV (`cv2`) |
| Face landmark detection | MediaPipe Tasks API (`mediapipe 0.10+`) |
| Blink algorithm | Eye Aspect Ratio (EAR) |
| Packaging | PyInstaller (`tacet.spec`) |

## Architecture

```
main.py                  ← entry point; wires QApplication, SystemTrayIcon, MainWindow
tacet.spec               ← PyInstaller spec; use --clean flag when rebuilding
src/
  main_window.py         ← QMainWindow; camera selector toolbar, video display, close→tray
  camera_thread.py       ← QThread; camera capture + MediaPipe + blink/alert signals
  alert_window.py        ← frameless always-on-top alert; shown on no_blink_alert, dismissed on blink
  camera_utils.py        ← scan_cameras() enumerates available webcams
  tray_icon.py           ← programmatic eye icon (no external asset file needed)
models/                  ← auto-downloaded face_landmarker.task (git-ignored)
dist/TacetHealthCare/    ← packaged output (git-ignored); distribute entire folder
```

**Key design decisions:**
- `app.setQuitOnLastWindowClosed(False)` keeps the process alive when the window is hidden.
- `MainWindow.closeEvent` intercepts the close button and calls `self.hide()` instead of quitting.
- Camera + MediaPipe run entirely inside `CameraThread` (a `QThread`) so the UI never blocks.
- Blink detection: **EAR < 0.25 for ≥ 2 consecutive frames** — tune `EAR_THRESHOLD` and `CONSEC_FRAMES` in `camera_thread.py`.
- No-blink alert fires after **5 seconds** of continuous face presence without a blink — tune `NO_BLINK_THRESHOLD` in `camera_thread.py`.
- Timer resets when: (a) a blink is detected, or (b) the face leaves the frame.
- MediaPipe model path uses `sys.executable` when frozen (PyInstaller) and `__file__` in dev mode.
- MediaPipe landmark indices for EAR: left eye `[33,160,158,133,153,144]`, right eye `[263,387,385,362,380,373]`.
