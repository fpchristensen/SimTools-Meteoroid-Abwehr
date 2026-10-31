# Meteoroiden-Abwehr – Test 1

Eigenständige Zusammenführung der modularen Mehrkörper-Simulation aus `entwicklung_fi` und der Meteoroiden-Anfangswerte samt Bahndarstellung aus `entwicklung_lu`.

## Start

Voraussetzungen: Python mit NumPy und Matplotlib.

Im Ordner `Test 1` ausführen:

```powershell
python main.py
```

## Module

- `const_values.py`: physikalische Konstanten und Simulationsdauer
- `functions_and_classes.py`: Himmelskörper, Erdorbit und Gravitationsbeschleunigung
- `simulation.py`: Mehrkörper-Simulation mit Euler-Cromer-Verfahren
- `UI_and_animations.py`: Bahnlinien und Animation
- `main.py`: Anfangswerte für Sonne, Erde und Meteoroid
