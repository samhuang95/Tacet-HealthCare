# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Tacet HealthCare** — "Master the pause. Perfect the performance"

A Windows 11 desktop application that detects eye blinks via webcam using computer vision. Runs as a system tray background app.

## Environment

- Python 3.12 + `.venv` (venv, never conda or global install)
- Always activate venv before running anything: `.venv\Scripts\activate`

## Commands

```powershell
# Run the app
.venv\Scripts\python.exe main.py

# Install dependencies (into venv only)
.venv\Scripts\pip.exe install -r requirements.txt

# Add a new package
.venv\Scripts\pip.exe install <package>
.venv\Scripts\pip.exe freeze > requirements.txt
```

## Stack

| Layer | Library |
|---|---|
| UI + System Tray | PyQt6 |
| Camera capture | OpenCV (`cv2`) |
| Face / eye landmarks | MediaPipe Face Mesh |
| Blink algorithm | Eye Aspect Ratio (EAR) |

## Architecture

```
main.py                  ← entry point; wires QApplication, SystemTrayIcon, MainWindow
src/
  main_window.py         ← QMainWindow; video display, status bar, close→tray behaviour
  camera_thread.py       ← QThread; captures frames, runs MediaPipe, emits blink signal
  tray_icon.py           ← programmatic eye icon (no external asset needed)
```

**Key design decisions:**
- `app.setQuitOnLastWindowClosed(False)` keeps the process alive when the window is hidden.
- `MainWindow.closeEvent` intercepts the close button and calls `self.hide()` instead.
- Camera + MediaPipe run entirely inside `CameraThread` (a `QThread`) so the UI never blocks.
- Blink detection uses **Eye Aspect Ratio (EAR) < 0.25 for ≥ 2 consecutive frames** — tune `EAR_THRESHOLD` and `CONSEC_FRAMES` in `camera_thread.py`.
- MediaPipe landmark indices for EAR: left eye `[33,160,158,133,153,144]`, right eye `[263,387,385,362,380,373]`.
