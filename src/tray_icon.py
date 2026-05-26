from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen
from PyQt6.QtCore import Qt


def create_app_icon(size: int = 64) -> QIcon:
    """Draw a simple eye icon programmatically — no external asset needed."""
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)

    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Background circle
    p.setBrush(QColor("#1857a4"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(2, 2, size - 4, size - 4)

    # Eye outline
    cx, cy = size // 2, size // 2
    p.setBrush(QColor("white"))
    p.setPen(QPen(QColor("white"), 1))
    p.drawEllipse(cx - 18, cy - 8, 36, 16)

    # Pupil
    p.setBrush(QColor("#1857a4"))
    p.drawEllipse(cx - 6, cy - 6, 12, 12)

    # Highlight
    p.setBrush(QColor("white"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(cx + 1, cy - 4, 4, 4)

    p.end()
    return QIcon(px)
