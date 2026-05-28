import sys
import os
import ctypes
import traceback

# In PyInstaller no-console mode sys.stdout/stderr are None.
# Redirect them to a log file before any other import so mediapipe
# (and other libs) that write to stdout don't crash on startup.
if getattr(sys, "frozen", False) and sys.stdout is None:
    _LOG = os.path.join(os.path.dirname(sys.executable), "error.log")
    _logfile = open(_LOG, "w", buffering=1)
    sys.stdout = _logfile
    sys.stderr = _logfile

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QAction
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from src.tray_icon import create_app_icon
from src.main_window import MainWindow

_INSTANCE_KEY = "TacetHealthCare_v1"


def _try_wake_existing() -> bool:
    """Return True if another instance is already running (and was told to show)."""
    sock = QLocalSocket()
    sock.connectToServer(_INSTANCE_KEY)
    if sock.waitForConnected(500):
        sock.write(b"show")
        sock.flush()
        sock.waitForBytesWritten(500)
        sock.disconnectFromServer()
        return True
    return False


def main():
    # Tell Windows this is its own app (not a Python subprocess) so the
    # taskbar button gets our icon instead of the generic Python icon.
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("TacetHealthCare")

    app = QApplication(sys.argv)
    app.setApplicationName("Tacet HealthCare")
    app.setQuitOnLastWindowClosed(False)

    # Single-instance guard: if another process answers the socket, wake it and exit.
    if _try_wake_existing():
        sys.exit(0)

    icon = create_app_icon()
    app.setWindowIcon(icon)

    tray = QSystemTrayIcon(icon, app)
    tray.setToolTip("Tacet HealthCare — Blink Monitor")

    window = MainWindow(tray)
    window.setWindowIcon(icon)

    # Start the local server so future instances can find and wake this one.
    QLocalServer.removeServer(_INSTANCE_KEY)  # clean up any stale socket
    server = QLocalServer(app)
    server.listen(_INSTANCE_KEY)

    def _on_new_connection():
        conn = server.nextPendingConnection()
        if conn:
            conn.waitForReadyRead(300)
            conn.readAll()          # consume the "show" message
            conn.disconnectFromServer()
        window.show()
        window.raise_()
        window.activateWindow()

    server.newConnection.connect(_on_new_connection)

    menu = QMenu()

    show_act = QAction("Show Window", app)
    show_act.triggered.connect(window.show)
    show_act.triggered.connect(window.raise_)
    show_act.triggered.connect(window.activateWindow)
    menu.addAction(show_act)

    menu.addSeparator()

    quit_act = QAction("Quit", app)
    quit_act.triggered.connect(window.quit)
    quit_act.triggered.connect(app.quit)
    menu.addAction(quit_act)

    tray.setContextMenu(menu)
    tray.activated.connect(
        lambda reason: (window.show(), window.raise_(), window.activateWindow())
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick
        else None
    )
    tray.show()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()   # goes to sys.stderr (our log file in frozen mode)
        sys.exit(1)
