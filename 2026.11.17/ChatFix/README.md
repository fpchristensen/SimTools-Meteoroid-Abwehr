# SimTools – Meteoroidenabwehr

Die Projektstruktur trennt Physik, Werte, Benutzeroberfläche und Programmstart.

## Projektdateien

| Datei | Inhalt |
|---|---|
| `main.py` | Startet das Qt-Fenster oder führt auf Wunsch die Physiktests aus. |
| `classes_functions.py` | `CelestialBody`, `MeteoroidSettings`, Gravitationsbeschleunigung, Euler-Cromer-Simulation, Kollision und Impulse. |
| `values.py` | Konstanten (SI-Einheiten), Anfangswerte, Impulsstärken und 20 Meteoroidenprofile. |
| `aniUI.py` | Alle Qt-Widgets und Matplotlib-Visualisierungen (Mehrfachabwehr, Pfeil, Zeitvorschau, Zoom, Verschieben und wählbares Wiedergabetempo). |
| `mainwindow.ui` | Mit Qt Designer editierbares Layout; muss neben `aniUI.py` liegen. |
| `tests/` | Drei unabhängig ausführbare Physiktests ohne Benutzeroberfläche. |

Zusätzliche Dateien aus früheren Versionen (`qt_gui.py`, `meteoroid_catalog.py`, `meteoroid_catalog.json`) werden **nicht** benötigt.

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
3. `tests/test_mehrfachabwehr.py`: Zwei Meteoroiden, zwei vorgemerkte Abwehren und mehrfacher Impuls auf denselben Meteoroiden.

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
- Katalogbahnen wurden jeweils **einzeln ohne Abwehr** geprüft; bei mehreren Meteoroiden gilt die Einschlaggarantie nicht unverändert.
- Die Impulsstärken sind **didaktische Demonstrationswerte** und keine realistische Missionsprognose.
- Geplante Impulse sind während der Laufzeit gespeichert, aber noch nicht dauerhaft auf der Festplatte.

## Docstrings

Alle Funktionen, Methoden und Klassen sind in den Python-Dateien dokumentiert, mit Beschreibung, bei Bedarf `Args`, `Returns`, `Raises` und Hinweisen. In VS Code erscheinen diese Informationen beim Darüberfahren mit der Maus oder beim Aufruf einer Funktion.

## Layout und Wiedergabegeschwindigkeit

- **Tempo-Button** rechts von **Meteoroid folgen**: 0,5×, 1×, 1,5×, 2× und 4× im Auswahlmenü. Standard ist 1×. Diese Einstellung verändert die **Abspielgeschwindigkeit**, nicht den physikalischen Zeitschritt (`dt = 3600 s`).
- **Feste Seitenleisten**: Breite und Steuerelemente von Meteoroiden und Abwehrplan ändern sich beim Ziehen des Fensters nicht. Die beiden Listen sind kompakt; Spacer halten einen kleinen Abstand frei.
- **Mitte flexibel**: Das Matplotlib-Diagramm passt sich der Fenstergröße an. Play, Zurück, Stop, Erde folgen, Meteoroid folgen und Tempo behalten ihre kompakte Größe und bleiben mittig angeordnet.
- Das Fenster kann bis zu einer Mindestgröße von **1120 × 735** verkleinert werden, damit die fest dimensionierten Steuerelemente noch Platz finden.
