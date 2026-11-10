"""Starte die Meteoroiden-Simulation mit Qt Designer als Oberfläche."""

import sys
from PyQt6.QtWidgets import QApplication
from qt_gui import SimulationWindow


def main():
    """Erstellt das Qt-Fenster und startet die GUI-Ereignisschleife."""
    app = QApplication(sys.argv)
    window = SimulationWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
