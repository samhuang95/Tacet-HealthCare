<div align="center">

<img src="assets/logo.png" alt="Tacet HealthCare Logo" width="120" />

# Tacet HealthCare

**Master the pause. Perfect the performance.**

A Windows desktop app that quietly watches over your health while you work —  
blink reminders, sit break alerts, and hydration nudges, all powered by your webcam.

[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%2F%2011-0078D4?style=flat-square&logo=windows)](https://www.microsoft.com/windows)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org)
[![PyQt6](https://img.shields.io/badge/UI-PyQt6-41CD52?style=flat-square)](https://www.riverbankcomputing.com/software/pyqt/)
[![MediaPipe](https://img.shields.io/badge/AI-MediaPipe-0097A7?style=flat-square)](https://ai.google.dev/edge/mediapipe)

</div>

---

## What It Does

Tacet HealthCare runs silently in your system tray and monitors three health indicators in real time using your webcam — no wearables, no subscriptions.

| | Feature | How it works | How to dismiss |
|---|---|---|---|
| 🔴 | **Blink Reminder** | Alerts after N seconds without a detected blink | Blink naturally |
| 🔵 | **Sit Break Reminder** | Alerts after N continuous minutes of sitting | Click the alert or stand up |
| 🩵 | **Hydration Reminder** | Alerts after N minutes without a drinking gesture | Click the alert, raise a cup to your lips, or step away |

All thresholds are fully configurable. Features can be toggled on or off independently via the **⚙ Settings** panel.

---

## How Detection Works

- **Blink** — Measures Eye Aspect Ratio (EAR) from 12 facial landmarks. EAR drops below 0.25 for 2+ consecutive frames → blink confirmed.
- **Sitting** — Continuous face presence in the frame is used as a proxy for sitting at the desk. A 3-second face absence dismisses the sit alert; 5+ minutes resets the timer.
- **Drinking** — Tracks the position of your hand's knuckle joints relative to your mouth. Hold a cup near your lips for 1 second → drink confirmed.

All AI inference runs locally on your machine. No data is sent anywhere.

---

## Requirements

- Windows 10 / 11
- Python 3.10+
- A connected webcam

---

## Getting Started

### 1. Clone the repository

```powershell
git clone https://github.com/samhuang95/Tacet-HealthCare.git
cd Tacet-HealthCare
```

### 2. Create the virtual environment

```powershell
python -m venv .venv
```

### 3. Activate the virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

> If you see an execution policy error, run this once in an admin PowerShell:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### 4. Install dependencies

```powershell
pip install -r requirements.txt
```

### 5. Run the app

```powershell
.\scripts\run.ps1
```

On first launch, the app downloads the MediaPipe face and hand landmark models (~12 MB total) automatically and saves them to `models/`. Subsequent launches skip the download.

---

## Project Structure

```
Tacet-HealthCare/
├── main.py                  # Entry point — QApplication, tray, single-instance guard
├── requirements.txt
├── tacet.spec               # PyInstaller packaging config
├── assets/                  # Logo (PNG + ICO)
├── models/                  # Auto-downloaded AI models (git-ignored)
└── src/
    ├── main_window.py       # Main window + camera selector UI
    ├── camera_thread.py     # QThread: camera capture + AI detection + alert signals
    ├── alert_window.py      # Frameless always-on-top alert overlay
    ├── camera_utils.py      # Camera enumeration helper
    ├── settings.py          # AppSettings dataclass + JSON persistence
    ├── settings_dialog.py   # Settings UI dialog
    └── tray_icon.py         # System tray icon (logo or programmatic fallback)
```

---

## Packaging

Produces a standalone folder (`release\`) that runs on any Windows machine without Python installed.

```powershell
.\scripts\build.ps1
```

The script handles everything in one step:
1. Runs PyInstaller with `tacet.spec`
2. Stops any running instance of the app
3. Replaces `release\` with the new build
4. Cleans up temporary `build\` and `dist\` folders

> `release\` contains `TacetHealthCare.exe` and `_internal\`. Both must be distributed together. The app downloads AI models on first launch and stores them next to the exe.

---

## Stack

| Layer | Library |
|---|---|
| UI & system tray | PyQt6 |
| Camera capture | OpenCV (`opencv-python`) |
| Face & hand detection | MediaPipe Tasks (`mediapipe`) |
| Blink algorithm | Eye Aspect Ratio (EAR) |
| Packaging | PyInstaller |
