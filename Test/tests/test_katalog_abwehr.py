"""20 Katalogbahnen und Impulsmechanik ohne Qt automatisch überprüfen.

Ausführen: py test_katalog_abwehr.py
"""

import numpy as np

from classes_functions import profiles
from classes_functions import CelestialBody, orbital_data, simulate_system, start_defense
from values import (
    G, N, dt, a_Ellipse, e_Ellipse, m_Sonne, m_Erde,
    radius_Sonne, radius_Erde, ABWEHR_METHODEN,
)


def create_bodies(entry):
    """Erstellt das exakt gleiche Sonne-Erde-Asteroid-System wie die GUI.

    Args:
        entry (dict): Katalogeintrag mit Masse, Durchmesser, Ort und Geschwindigkeit.

    Returns:
        list[CelestialBody]: Frisches Drei-Körper-System mit Katalogwerten.
    """
    re, ve = orbital_data(a_Ellipse, e_Ellipse, m_Sonne)
    return [
        CelestialBody("Sonne", m_Sonne, radius_Sonne, [0, 0], [0, 0]),
        CelestialBody("Erde", m_Erde, radius_Erde, re, ve),
        CelestialBody(
            "Testasteroid", entry["mass_kg"], entry["diameter_m"] / 2,
            entry["position_m"], entry["velocity_m_s"],
        ),
    ]


def main():
    """Testet alle Katalogeinschlaege und die Richtung/Zeit des Abwehrimpulses.
    """
    entries = profiles("Leicht") + profiles("Schwer")
    assert len(profiles("Leicht")) == 10
    assert len(profiles("Schwer")) == 10
    assert len({entry["id"] for entry in entries}) == 20
    print("Teste alle 20 Katalog-Asteroiden einzeln:")

    for entry in entries:
        positions, _, collision = simulate_system(create_bodies(entry), N, dt)
        day = (len(positions) - 1) * dt / 86400
        assert collision == ("Erde", "Testasteroid"), (entry["id"], collision)
        assert abs(day - entry["target_impact_day"]) <= dt / 86400, (
            entry["id"], day
        )
        print(f"  {entry['name']:10s}: Einschlag Tag {day:.2f} OK")

    entry = profiles("Leicht")[2]  # Leicht 03 / Tag 80
    baseline, _, _ = simulate_system(create_bodies(entry), N, dt)
    frame = 20 * 24
    impulse = ABWEHR_METHODEN["Explosion"]
    defended, collision = start_defense(
        frame, 0, impulse, "Testasteroid",
        lambda: create_bodies(entry), N, dt,
    )
    assert collision is None, collision
    # Impuls an genau diesem Frame: erst Geschwindigkeit, dann beim nächsten
    # Schritt die Position. Der Positionsunterschied ist deshalb J/m * dt.
    assert np.allclose(defended[frame, 2], baseline[frame, 2], atol=1e-3, rtol=0)
    displacement = defended[frame + 1, 2] - baseline[frame + 1, 2]
    expected = impulse / entry["mass_kg"] * dt
    assert np.isclose(displacement[0], expected, atol=1e-2, rtol=1e-10)
    assert abs(displacement[1]) < 1e-2

    # 90 Grad bedeutet nach oben (+y), nicht nach rechts (+x).
    defended_up, _ = start_defense(
        frame, 90, impulse, "Testasteroid",
        lambda: create_bodies(entry), N, dt,
    )
    displacement_up = defended_up[frame + 1, 2] - baseline[frame + 1, 2]
    assert np.isclose(displacement_up[1], expected, atol=1e-2, rtol=1e-10)
    assert abs(displacement_up[0]) < 1e-2
    print("OK: Impuls wirkt exakt einmal am richtigen Frame in der gewählten Richtung.")
    print("OK: Starke Abwehr bei Leicht 03 an Tag 20 vermeidet den Einschlag.")

    for name in ("Schwer 05", "Schwer 10"):
        e = next(e for e in entries if e["name"] == name)
        _, result = start_defense(
            frame, 0, impulse, "Testasteroid", lambda e=e: create_bodies(e), N, dt,
        )
        assert result is None, (e["id"], result)
        print(f"OK: Starke Abwehr bei {name} an Tag 20 vermeidet den Einschlag.")

    print("Alle Tests bestanden.")


if __name__ == "__main__":
    main()
