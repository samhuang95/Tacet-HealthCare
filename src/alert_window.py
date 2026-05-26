from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont


def _darken(hex_color: str) -> str:
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f"#{int(r*0.68):02x}{int(g*0.68):02x}{int(b*0.68):02x}"


class AlertWindow(QWidget):
    dismissed = pyqtSignal()

    def __init__(
        self,
        color: str,
        title: str,
        message: str,
        hint: str,
        click_to_dismiss: bool = False,
    ):
        super().__init__()
        self._color     = color
        self._color_alt = _darken(color)
        self._click_dismiss = click_to_dismiss

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(420, 200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 32, 36, 32)
        layout.setSpacing(10)

        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setStyleSheet("color:white;")
        layout.addWidget(title_lbl)

        msg_lbl = QLabel(message)
        msg_lbl.setFont(QFont("Segoe UI", 12))
        msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_lbl.setStyleSheet("color:rgba(255,255,255,0.82);")
        layout.addWidget(msg_lbl)

        hint_lbl = QLabel(hint)
        hint_lbl.setFont(QFont("Segoe UI", 10))
        hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_lbl.setStyleSheet("color:rgba(255,255,255,0.5);")
        layout.addWidget(hint_lbl)

        self._pulse_state = False
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse)
        self._apply_color()

    def _pulse(self):
        self._pulse_state = not self._pulse_state
        self._apply_color()

    def _apply_color(self):
        color = self._color if self._pulse_state else self._color_alt
        self.setStyleSheet(
            f"background:{color}; border-radius:14px;"
            "border: 2px solid rgba(255,255,255,0.25);"
        )

    def mousePressEvent(self, event):
        if self._click_dismiss:
            self.dismiss()

    def show_alert(self):
        from PyQt6.QtWidgets import QApplication
        geo = QApplication.primaryScreen().availableGeometry()
        self.move(
            geo.center().x() - self.width() // 2,
            geo.center().y() - self.height() // 2,
        )
        self._pulse_timer.start(500)
        self.show()
        self.raise_()

    def dismiss(self):
        self._pulse_timer.stop()
        self.hide()
        self.dismissed.emit()
