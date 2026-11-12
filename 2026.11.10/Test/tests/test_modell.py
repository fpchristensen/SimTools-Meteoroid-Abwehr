"""Einfacher Test des physikalischen Modells – ohne Qt-Oberfläche ausführbar.
"""

from classes_functions import CelestialBody, orbital_data, simulate_system, start_defense
from values import (
    N, dt, a_Ellipse, e_Ellipse,
    m_Erde, m_Sonne, radius_Erde, radius_Sonne,
    m_Meteorid1, radius_Meteorid1, r_Meteorid1, v_Meteorid1,
    ABWEHR_METHODEN,
)


def create_bodies():
    """Erzeugt genau die drei Körper für die Tag-80-Kollision.

    Returns:
        list[CelestialBody]: Sonne, Erde und Beispielasteroid.
    """
    earth_r, earth_v = orbital_data(a_Ellipse, e_Ellipse, m_Sonne)
    return [
        CelestialBody("Sonne", m_Sonne, radius_Sonne, [0, 0], [0, 0]),
        CelestialBody("Erde", m_Erde, radius_Erde, earth_r, earth_v),
        CelestialBody(
            "Meteoroid 1", m_Meteorid1, radius_Meteorid1,
            r_Meteorid1, v_Meteorid1
        ),
    ]


def main():
    """Prüft Basiskollision und Abwehr mit großem Impuls an Tag 20.
    """
    r, _, collision = simulate_system(create_bodies(), N, dt)
    day = (len(r) - 1) * dt / 86400
    assert collision == ("Erde", "Meteoroid 1")
    assert abs(day - 80.0) < 0.1
    print(f"OK: Kollision Erde/Meteoroid 1 an Tag {day:.2f}")

    r, collision = start_defense(
        20 * 24, 0, ABWEHR_METHODEN["Explosion"],
        "Meteoroid 1", create_bodies, N, dt,
    )
    assert collision is None
    print(f"OK: Mit Abwehr kein Aufprall bis Tag {(len(r)-1)*dt/86400:.2f}")


if __name__ == "__main__":
    main()
