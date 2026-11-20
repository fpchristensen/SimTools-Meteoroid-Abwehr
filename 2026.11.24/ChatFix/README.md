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
| `tests/` | Zwei unabhängig ausführbare Physiktestmodule ohne Benutzeroberfläche. |

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

## Tests

```powershell
py main.py --test
```

Dieser Aufruf startet die zwei enthaltenen Testmodule `tests.test_closeup`
(Referenzmodell) und `tests.test_adaptive` (adaptive Physik, Kontaktzeit,
beide Kollisionsmodi, Impulserhaltung, Wiedergabe und sämtliche 20 Katalogbahnen).
Die drei ursprünglich in main.py referenzierten Testdateien waren im gelieferten
ZIP nicht enthalten. Es werden keine fehlenden Module mehr importiert.

## Adaptive Physik und Zeitlupe

Die GUI nutzt `simulate_trajectory` in `classes_functions.py`. Der bisherige
Stundenrhythmus `dt = 3600 s` bleibt für den Eingriffszeitpunkt und außerhalb
von Begegnungen erhalten. In Erdnähe wird Euler-Cromer für alle aktiven Körper
mit feineren Unterzeitschritten ausgeführt. Die Positionen werden zusammen mit
ihren Zeitstempeln gespeichert. Eine Vorhersage der relativen Strecke verhindert,
dass die Simulation einen Nahbereich in einem großen Schritt überspringt.

| Mittelpunktabstand | maximale Schrittweite |
|---|---:|
| außerhalb 300.000 km | 3600 s |
| bis 300.000 km | 60 s |
| bis 50.000 km | 10 s |
| bis 10.000 km | 1 s |

Die Schwellen stehen in `ADAPTIVE_STEPS` in `values.py`. Schritte können bereits
vor dem Erreichen einer Distanzgrenze verkürzt werden und werden zusätzlich
an Stundenmarken und beim ersten Oberflächenkontakt unterteilt. Die 20 bisherigen
Katalogwerte mussten bei den gewählten Einstellungen nicht geändert werden:
alle treffen einzeln weiterhin am vorgesehenen Tag (bis auf wenige Minuten).

Die Darstellung verwendet die berechneten Zustände und interpoliert nur noch
zwischen benachbarten, in Erdnähe eng aufeinanderfolgenden Physikwerten. Der
historische Solver `simulate_system` bleibt für ältere Skripte und Vergleichstests
erhalten; die GUI verwendet ihn nicht mehr.

## Neue Schalter (Qt Designer)

- **Close-up: An/Aus** rechts neben Tempo. Standard ist An. Aus deaktiviert
  die Nahkamera und die automatische Zeitlupe, aber nicht die adaptive Physik.
  Der Schalter funktioniert auch während der Wiedergabe.
- **Abbruch bei Aufschlag: An/Aus** in der Zeile darüber neben Stop. Standard
  ist An. Ein Wechsel berechnet den Verlauf neu; Play beginnt wieder am Start.
- Beide Widgets sind in `mainwindow.ui` gespeichert und behalten ihre kompakte
  Größe. Die Seitenleisten bleiben unverändert.
- `CLOSEUP_DISTANCE` (in Metern) steuert nur die automatische Nahkamera und
  ist unabhängig von `ADAPTIVE_STEPS`.
- Die Winkel der beiden Drehregler werden mit `(270 - angle) % 360` in
  mathematische Winkel umgerechnet: 0° unten, 90° links, 180° oben, 270° rechts.
  Die gespeicherten Abwehraktionen werden beim Aufruf der Physik ebenfalls
  umgerechnet. Die ältere physikalische API verwendet weiterhin mathematische Winkel.

## Aufschlagmodell

Bei Abbruch An endet die Rechnung beim ersten Oberflächenkontakt. Bei Aus
werden die Körper vollständig unelastisch vereinigt. Der massereichere Körper
behält seinen Radius, erhält die Masse des anderen und seine Geschwindigkeit
ändert sich um `delta_v = m_klein/(m_gross+m_klein) * (v_klein - v_gross)`.
Aufgenommene Körper werden aus der weiteren Gravitation entfernt; spätere
Abwehraktionen auf diese Körper werden ignoriert. Andere Körper laufen weiter.

In der Nahansicht zeigen ein roter Stern und ein sich ausbreitender Ring den
Kontakt an. Der Ring ist rein schematisch, keine berechnete Druckwelle. Die
abgegebene Stoßenergie und die Geschwindigkeitsänderung des Empfängers werden
angezeigt. Die Bahn des Empfängers wird mit der neuen Geschwindigkeit und Masse
weiterberechnet. Bei den katalogisierten Meteoroiden bleibt die Änderung der
Erdbahn aufgrund des enormen Massenunterschieds sehr klein. Eine Atmosphäre,
Krater, Fragmentierung, Rotation, Wärmeausbreitung oder eine realistische
Schadenssimulation sind nicht Bestandteil dieses Modells.

Die Impulsstärken sind didaktische Demonstrationswerte. Der eingeschränkte
Euler-Cromer-Solver ist kein Präzisionsmodell für planetare Missionen. Alle
Python-Skripte enthalten Docstrings.
