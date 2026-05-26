# Tacet HealthCare
> Master the pause. Perfect the performance.

A Windows 11 desktop application that monitors eye blink activity via webcam. When the user goes 5 seconds without blinking, an alert window appears and auto-dismisses on the next detected blink. The app runs continuously in the system tray.

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
python main.py
```

On first launch, the app downloads the MediaPipe face landmark model (~3.7 MB) automatically and saves it to `models/`. Subsequent launches skip the download.

---

## Project Structure

```
Tacet-HealthCare/
├── main.py                  # Entry point
├── requirements.txt
├── models/                  # Auto-downloaded model (git-ignored)
└── src/
    ├── main_window.py       # Main window + camera selector UI
    ├── camera_thread.py     # QThread: camera capture + blink detection
    ├── alert_window.py      # Always-on-top blink reminder overlay
    ├── camera_utils.py      # Camera enumeration helper
    └── tray_icon.py         # Programmatic system tray icon
```

---

## Stack

| Layer | Library |
|---|---|
| UI & system tray | PyQt6 |
| Camera capture | OpenCV (`opencv-python`) |
| Face landmark detection | MediaPipe Tasks (`mediapipe`) |
| Blink algorithm | Eye Aspect Ratio (EAR) |
