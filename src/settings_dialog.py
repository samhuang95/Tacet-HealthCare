from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QCheckBox, QLabel, QSpinBox, QDoubleSpinBox,
    QPushButton, QDialogButtonBox,
)
from PyQt6.QtCore import Qt
from .settings import AppSettings

_DIALOG_STYLE = """
QDialog {
    background: #0f172a;
    color: white;
}
QGroupBox {
    color: #94a3b8;
    border: 1px solid #334155;
    border-radius: 6px;
    margin-top: 10px;
    padding: 12px 10px 10px 10px;
    font-size: 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QCheckBox {
    color: white;
    font-size: 13px;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1px solid #475569;
    border-radius: 3px;
    background: #1e293b;
}
QCheckBox::indicator:checked {
    background: #2563eb;
    border-color: #2563eb;
}
QLabel {
    color: #94a3b8;
    font-size: 12px;
}
QSpinBox, QDoubleSpinBox {
    background: #1e293b;
    color: white;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 3px 6px;
    min-width: 80px;
}
QSpinBox:disabled, QDoubleSpinBox:disabled {
    color: #475569;
    border-color: #1e293b;
}
"""

_BTN_SAVE = (
    "QPushButton { background:#2563eb; color:white; border:none;"
    "border-radius:4px; padding:6px 20px; font-size:13px; }"
    "QPushButton:hover { background:#3b82f6; }"
)
_BTN_CANCEL = (
    "QPushButton { background:#1e293b; color:#94a3b8; border:1px solid #334155;"
    "border-radius:4px; padding:6px 20px; font-size:13px; }"
    "QPushButton:hover { background:#334155; }"
)


class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self._s = settings
        self.setWindowTitle("Settings")
        self.setFixedWidth(340)
        self.setStyleSheet(_DIALOG_STYLE)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        layout.addWidget(self._build_blink_group())
        layout.addWidget(self._build_sit_group())
        layout.addWidget(self._build_water_group())

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setStyleSheet(_BTN_CANCEL)
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save")
        save.setStyleSheet(_BTN_SAVE)
        save.clicked.connect(self._on_save)
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)

    # ── group builders ───────────────────────────────────────────────────────

    def _build_blink_group(self) -> QGroupBox:
        box = QGroupBox("Blink Reminder")
        v = QVBoxLayout(box)
        v.setSpacing(8)

        self._blink_cb = QCheckBox("Enable")
        self._blink_cb.setChecked(self._s.blink_enabled)
        v.addWidget(self._blink_cb)

        row = QHBoxLayout()
        row.addWidget(QLabel("Alert after(3~60 sec):"))
        self._blink_spin = QDoubleSpinBox()
        self._blink_spin.setRange(3, 60)
        self._blink_spin.setSingleStep(1)
        self._blink_spin.setDecimals(0)
        self._blink_spin.setSuffix(" sec")
        self._blink_spin.setValue(self._s.blink_threshold)
        row.addWidget(self._blink_spin)
        row.addStretch()
        v.addLayout(row)

        self._blink_cb.toggled.connect(self._blink_spin.setEnabled)
        self._blink_spin.setEnabled(self._s.blink_enabled)
        return box

    def _build_sit_group(self) -> QGroupBox:
        box = QGroupBox("Sit Break Reminder")
        v = QVBoxLayout(box)
        v.setSpacing(8)

        self._sit_cb = QCheckBox("Enable")
        self._sit_cb.setChecked(self._s.sit_enabled)
        v.addWidget(self._sit_cb)

        row = QHBoxLayout()
        row.addWidget(QLabel("Alert after(5~120 min):"))
        self._sit_spin = QSpinBox()
        self._sit_spin.setRange(5, 120)
        self._sit_spin.setSuffix(" min")
        self._sit_spin.setValue(self._s.sit_threshold)
        row.addWidget(self._sit_spin)
        row.addStretch()
        v.addLayout(row)

        self._sit_cb.toggled.connect(self._sit_spin.setEnabled)
        self._sit_spin.setEnabled(self._s.sit_enabled)
        return box

    def _build_water_group(self) -> QGroupBox:
        box = QGroupBox("Water Reminder")
        v = QVBoxLayout(box)
        v.setSpacing(8)

        self._water_cb = QCheckBox("Enable")
        self._water_cb.setChecked(self._s.water_enabled)
        v.addWidget(self._water_cb)

        row = QHBoxLayout()
        row.addWidget(QLabel("Alert after(5~120 min):"))
        self._water_spin = QSpinBox()
        self._water_spin.setRange(5, 120)
        self._water_spin.setSuffix(" min")
        self._water_spin.setValue(self._s.water_threshold)
        row.addWidget(self._water_spin)
        row.addStretch()
        v.addLayout(row)

        self._water_cb.toggled.connect(self._water_spin.setEnabled)
        self._water_spin.setEnabled(self._s.water_enabled)
        return box

    # ── save ─────────────────────────────────────────────────────────────────

    def _on_save(self):
        self._s.blink_enabled   = self._blink_cb.isChecked()
        self._s.blink_threshold = self._blink_spin.value()
        self._s.sit_enabled     = self._sit_cb.isChecked()
        self._s.sit_threshold   = self._sit_spin.value()
        self._s.water_enabled   = self._water_cb.isChecked()
        self._s.water_threshold = self._water_spin.value()
        self._s.save()
        self.accept()
