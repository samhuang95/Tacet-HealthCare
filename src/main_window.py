from PyQt6.QtWidgets import (
    QMainWindow, QLabel, QVBoxLayout, QHBoxLayout,
    QWidget, QSystemTrayIcon, QComboBox, QPushButton,
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from .camera_thread import CameraThread
from .camera_utils import scan_cameras
from .alert_window import AlertWindow

_TOOLBAR_STYLE = (
    "background:#111827; padding:6px 10px; border-bottom:1px solid #1e293b;"
)
_LABEL_STYLE = "color:#94a3b8; font-size:12px;"
_COMBO_STYLE = (
    "QComboBox{background:#1e293b; color:white; border:1px solid #334155;"
    "border-radius:4px; padding:3px 8px; min-width:160px;}"
    "QComboBox::drop-down{border:none;}"
    "QComboBox QAbstractItemView{background:#1e293b; color:white;}"
)
_BTN_STYLE = (
    "QPushButton{background:#1e40af; color:white; border:none;"
    "border-radius:4px; padding:4px 12px; font-size:12px;}"
    "QPushButton:hover{background:#2563eb;}"
    "QPushButton:pressed{background:#1d4ed8;}"
)


class MainWindow(QMainWindow):
    def __init__(self, tray: QSystemTrayIcon):
        super().__init__()
        self._tray   = tray
        self._thread = None
        self._alert = AlertWindow(
            color="#c0392b",
            title="Blink!",
            message="You haven't blinked in a while.",
            hint="Blink to dismiss",
        )
        self._break_alert = AlertWindow(
            color="#1a56db",
            title="Take a Break!",
            message="You've been sitting for 30 minutes.",
            hint="Click to dismiss",
            click_to_dismiss=True,
        )
        self.setWindowTitle("Tacet HealthCare — Blink Monitor")
        self.setMinimumSize(700, 580)
        self._setup_ui()
        self._scan_and_populate(auto_start=True)

    # ── UI construction ─────────────────────────────────────────────────────

    def _setup_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self._build_toolbar())

        self._video_label = QLabel()
        self._video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._video_label.setStyleSheet("background:#0d0d1a;")
        self._video_label.setMinimumHeight(460)
        layout.addWidget(self._video_label, stretch=1)

        self._status_label = QLabel("Initializing...")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet(
            "color:#4ade80; font-size:13px; padding:6px;"
            "background:#0d0d1a; border-top:1px solid #1e293b;"
        )
        layout.addWidget(self._status_label)

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet(_TOOLBAR_STYLE)
        row = QHBoxLayout(bar)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        lbl = QLabel("Camera:")
        lbl.setStyleSheet(_LABEL_STYLE)
        row.addWidget(lbl)

        self._camera_combo = QComboBox()
        self._camera_combo.setStyleSheet(_COMBO_STYLE)
        self._camera_combo.currentIndexChanged.connect(self._on_camera_changed)
        row.addWidget(self._camera_combo)

        scan_btn = QPushButton("Rescan")
        scan_btn.setStyleSheet(_BTN_STYLE)
        scan_btn.clicked.connect(lambda: self._scan_and_populate(auto_start=True))
        row.addWidget(scan_btn)

        row.addStretch()
        return bar

    # ── Camera management ────────────────────────────────────────────────────

    def _scan_and_populate(self, auto_start: bool = False):
        self._status_label.setText("Scanning cameras...")
        cameras = scan_cameras()

        self._camera_combo.blockSignals(True)
        self._camera_combo.clear()
        if cameras:
            for idx, label in cameras:
                self._camera_combo.addItem(label, userData=idx)
            self._status_label.setText(f"Found {len(cameras)} camera(s)")
        else:
            self._camera_combo.addItem("No cameras found", userData=None)
            self._status_label.setText("No cameras detected — connect a camera and rescan")
        self._camera_combo.blockSignals(False)

        if auto_start and cameras:
            self._start_camera(cameras[0][0])

    def _on_camera_changed(self, combo_index: int):
        camera_idx = self._camera_combo.itemData(combo_index)
        if camera_idx is not None:
            self._start_camera(camera_idx)

    def _start_camera(self, camera_index: int):
        if self._thread is not None:
            self._thread.stop()
            self._thread = None

        self._alert.dismiss()
        self._break_alert.dismiss()
        self._video_label.clear()
        self._status_label.setText(f"Connecting to camera {camera_index}...")

        self._thread = CameraThread(camera_index)
        self._thread.frame_ready.connect(self._update_frame)
        self._thread.blink_detected.connect(self._on_blink)
        self._thread.no_blink_alert.connect(self._alert.show_alert)
        self._thread.sit_break_alert.connect(self._break_alert.show_alert)
        self._thread.sit_break_away.connect(self._break_alert.dismiss)
        self._thread.status_changed.connect(self._status_label.setText)
        self._break_alert.dismissed.connect(self._thread.reset_sit_timer)
        self._thread.start()

    # ── Slots ────────────────────────────────────────────────────────────────

    def _update_frame(self, qimg):
        px = QPixmap.fromImage(qimg).scaled(
            self._video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._video_label.setPixmap(px)

    def _on_blink(self, total: int):
        self._alert.dismiss()
        self._status_label.setText(f"Blink detected!  Total: {total}")

    # ── Window behaviour ─────────────────────────────────────────────────────

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self._tray.showMessage(
            "Tacet HealthCare",
            "Running in the background",
            QSystemTrayIcon.MessageIcon.Information,
            2000,
        )

    def quit(self):
        self._alert.dismiss()
        self._break_alert.dismiss()
        if self._thread:
            self._thread.stop()
