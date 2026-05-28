import os
import sys
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen
from PyQt6.QtCore import Qt

# Packed assets live inside _internal/ (sys._MEIPASS); dev assets are at project root.
_BASE_DIR  = getattr(sys, "_MEIPASS", None) or \
             os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_LOGO_PATH = os.path.join(_BASE_DIR, "assets", "logo.png")


def create_app_icon() -> QIcon:
    if os.path.exists(_LOGO_PATH):
        return QIcon(QPixmap(_LOGO_PATH))

    # Fallback: programmatic eye icon (used only if assets/logo.png is missing)
    size = 64
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor("#1857a4"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(2, 2, size - 4, size - 4)
    cx, cy = size // 2, size // 2
    p.setBrush(QColor("white"))
    p.setPen(QPen(QColor("white"), 1))
    p.drawEllipse(cx - 18, cy - 8, 36, 16)
    p.setBrush(QColor("#1857a4"))
    p.drawEllipse(cx - 6, cy - 6, 12, 12)
    p.setBrush(QColor("white"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(cx + 1, cy - 4, 4, 4)
    p.end()
    return QIcon(px)
