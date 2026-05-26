import sys
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QAction
from src.tray_icon import create_app_icon
from src.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Tacet HealthCare")
    app.setQuitOnLastWindowClosed(False)

    icon = create_app_icon()

    tray = QSystemTrayIcon(icon, app)
    tray.setToolTip("Tacet HealthCare — Blink Monitor")

    window = MainWindow(tray)

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
    main()
