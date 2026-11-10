# SimTools – Meteoroidenabwehr

Die Projektstruktur trennt Physik, Werte, Benutzeroberfläche und Programmstart.

## Projektdateien

| Datei | Inhalt |
|---|---|
| `main.py` | Startet das Qt-Fenster oder führt auf Wunsch die Physiktests aus. |
| `classes_functions.py` | `CelestialBody`, `AsteroidSettings`, Gravitationsbeschleunigung, Euler-Cromer-Simulation, Kollision und Impulse. |
| `values.py` | Konstanten (SI-Einheiten), Anfangswerte, Impulsstärken und 20 Asteroidenprofile. |
| `aniUI.py` | Alle Qt-Widgets und Matplotlib-Visualisierungen (Mehrfachabwehr, Pfeil, Zeitvorschau, Zoom und Verschieben). |
| `mainwindow.ui` | Mit Qt Designer editierbares Layout; muss neben `aniUI.py` liegen. |
| `tests/` | Drei unabhängig ausführbare Physiktests ohne Benutzeroberfläche. |

Zusätzliche Dateien aus früheren Versionen (`qt_gui.py`, `asteroid_catalog.py`, `asteroid_catalog.json`) werden **nicht** benötigt.

## Installation und Start (Windows / PowerShell)

Einmalig, falls noch nicht installiert:

```powershell
py -m pip install numpy matplotlib PyQt6
```

Programm starten:

```powershell
py main.py
```

## Alle Tests integriertermaßen ausführen

```powershell
py main.py --test
```

Der Befehl startet **alle drei** Testmodule der Reihe nach:

1. `tests/test_modell.py`: Kollision von Meteoroid 1 um Tag 80 und Abwehr.
2. `tests/test_katalog_abwehr.py`: 20 einzeln geprüfte Kollisionsprofile sowie Stärke, Richtung und Zeitpunkt des Impulses.
3. `tests/test_mehrfachabwehr.py`: Zwei Asteroiden, zwei vorgemerkte Abwehren und mehrfacher Impuls auf denselben Asteroiden.

Die Tests öffnen kein Qt-Fenster. Sie verwenden `assert` und brechen bei einem Fehler mit einem Fehlercode ab. Eine Erfolgsmeldung am Ende bedeutet, dass alle drei Prüfläufe bestanden wurden. Sie sind **nicht Teil des normalen GUI-Starts**, damit das Fenster schnell öffnet und das Testen gezielt erfolgen kann.

Alternativ lassen sich die Module einzeln starten:

```powershell
py -m tests.test_modell
py -m tests.test_katalog_abwehr
py -m tests.test_mehrfachabwehr
```

## Wichtige Hinweise zum physikalischen Modell

- Beim Euler-Cromer-Verfahren wird zuerst die Geschwindigkeit und danach die Position aktualisiert.
- Ein einmaliger Impuls zum Frame `k` verändert den Ort erstmals im Frame `k+1`.
- Die Simulation stoppt bei der **ersten** Kollision. Spätere Impulse werden dann nicht mehr ausgeführt.
- Katalogbahnen wurden jeweils **einzeln ohne Abwehr** geprüft; bei mehreren Asteroiden gilt die Einschlaggarantie nicht unverändert.
- Die Impulsstärken sind **didaktische Demonstrationswerte** und keine realistische Missionsprognose.
- Geplante Impulse sind während der Laufzeit gespeichert, aber noch nicht dauerhaft auf der Festplatte.

## Docstrings

Alle Funktionen, Methoden und Klassen sind in den Python-Dateien dokumentiert, mit Beschreibung, bei Bedarf `Args`, `Returns`, `Raises` und Hinweisen. In VS Code erscheinen diese Informationen beim Darüberfahren mit der Maus oder beim Aufruf einer Funktion.
