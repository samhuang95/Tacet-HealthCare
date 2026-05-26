from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont


class AlertWindow(QWidget):
    def __init__(self):
        super().__init__()
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

        self._title = QLabel("Remember to Blink!")
        self._title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setStyleSheet("color:white;")
        layout.addWidget(self._title)

        sub = QLabel("You have not blinked in over 5 seconds.")
        sub.setFont(QFont("Segoe UI", 12))
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color:rgba(255,255,255,0.82);")
        layout.addWidget(sub)

        hint = QLabel("Blink to dismiss")
        hint.setFont(QFont("Segoe UI", 10))
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color:rgba(255,255,255,0.5);")
        layout.addWidget(hint)

        # Pulse animation: alternate between two red shades
        self._pulse_state = False
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse)
        self._apply_color()

    def _pulse(self):
        self._pulse_state = not self._pulse_state
        self._apply_color()

    def _apply_color(self):
        color = "#dc2626" if self._pulse_state else "#991b1b"
        self.setStyleSheet(
            f"background:{color}; border-radius:14px;"
            "border: 2px solid rgba(255,255,255,0.25);"
        )

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
