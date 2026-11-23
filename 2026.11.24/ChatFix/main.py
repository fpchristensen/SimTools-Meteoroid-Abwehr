"""Einstiegspunkt für die Simulation und die integrierten Physiktests.

Aufruf im Projektordner:
    py main.py          # Qt-Oberflaeche starten
    py main.py --test   # Alle enthaltenen Physiktests ohne Qt ausführen
"""

import importlib
import sys


TEST_MODULES = (
    "tests.test_closeup",
    "tests.test_adaptive",
)


def run_tests():
    """Führt die beiden enthaltenen, unabhängigen Physiktest-Dateien aus.

    Die Testmodule prüfen die Nahansicht, den Asteroidenkatalog, adaptive
    Zeitschritte, die beiden Kollisionsmodi und die Impulserhaltung. Ihre ``main()``-Funktionen verwenden ``assert``
    und verursachen bei einem Fehler einen fehlschlagenden Programmstart.
    Die Tests importieren bewusst keine Qt-Bibliotheken.

    Returns:
        int: 0, falls alle Tests ohne Ausnahme bestanden wurden.

    Raises:
        AssertionError: Falls eine physikalische Erwartung nicht erfüllt ist.
        Exception: Falls eine andere Ausnahme in einem Test auftritt.
    """
    print("=== SimTools: Physiktests ===", flush=True)
    for module_name in TEST_MODULES:
        print(f"\n--- {module_name} ---", flush=True)
        test_module = importlib.import_module(module_name)
        test_module.main()
    print("\n=== Alle enthaltenen Tests erfolgreich! ===", flush=True)
    return 0


def main(argv=None):
    """Startet entweder die Tests oder die Qt-Benutzeroberflaeche.

    Die Qt-Imports befinden sich absichtlich erst im GUI-Zweig, sodass
    ``py main.py --test`` auch ohne installierte PyQt6-Bibliothek läuft.

    Args:
        argv (list[str] | None): Kommandozeilenargumente ohne Skriptname;
            bei None werden die Argumente von sys.argv verwendet.

    Returns:
        int: 0 nach erfolgreichen Tests bzw. Exitcode der Qt-Ereignisschleife.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["--test"]:
        return run_tests()

    if "--test" in args:
        print("Bitte --test ohne weitere Argumente verwenden.", file=sys.stderr)
        return 2

    from PyQt6.QtWidgets import QApplication
    from aniUI import SimulationWindow

    app = QApplication([sys.argv[0], *args])
    window = SimulationWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
