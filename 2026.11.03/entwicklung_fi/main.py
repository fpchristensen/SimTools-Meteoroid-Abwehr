"""Startpunkt der Simulation zur Meteoroidenabwehr.

Vergleicht einen ersten Durchlauf ohne Abwehr mit einem zweiten Durchlauf,
bei dem ein vorgegebener Impuls auf den betroffenen Meteoroiden wirkt.
"""

from values import (
    N, dt,
    a_Ellipse, e_Ellipse,
    m_Meteorid1, m_Meteorid2,
    m_Erde, m_Sonne,
    radius_Meteorid1, radius_Meteorid2,
    radius_Erde, radius_Sonne,
    r_Meteorid1, v_Meteorid1,
    r_Meteorid2, v_Meteorid2
)

from classes_functions import (
    CelestialBody,
    orbital_data,
    simulate_system,
    ask_deflection
)

from aniUI import animate_system


def create_bodies():
    # Neue Himmelskoerper, damit der zweite Durchlauf
    # mit genau denselben Anfangswerten startet.
    """Erzeugt Sonne, Erde und zwei Meteoroiden mit ihren Anfangswerten.
    
    Für jeden Simulationsdurchlauf werden neue Objekte angelegt, damit die
    beiden Versuche mit denselben Startbedingungen beginnen.
    
    Returns:
        list[CelestialBody]: Sonne, Erde, Meteoroid 1 und Meteoroid 2.
    """

    sun = CelestialBody(
        "Sonne", m_Sonne, radius_Sonne, [0.0, 0.0], [0.0, 0.0]
    )

    earth_position, earth_velocity = orbital_data(
        a_Ellipse, e_Ellipse, m_Sonne
    )
    earth = CelestialBody(
        "Erde", m_Erde, radius_Erde, earth_position, earth_velocity
    )

    meteoroid1 = CelestialBody(
        "Meteoroid 1", m_Meteorid1, radius_Meteorid1,
        r_Meteorid1, v_Meteorid1
    )
    meteoroid2 = CelestialBody(
        "Meteoroid 2", m_Meteorid2, radius_Meteorid2,
        r_Meteorid2, v_Meteorid2
    )

    return [sun, earth, meteoroid1, meteoroid2]



def main():
    # 1. Simulation ohne Abwehr
    """Steuert den Vergleich zwischen einer Simulation ohne und mit Abwehr.
    
    Startet zuerst die Simulation ohne Impuls und zeigt deren Animation.
    Bei einer Meteoroidenkollision werden Eingaben für die Ablenkung
    abgefragt. Anschließend startet eine neue Simulation mit identischen
    Anfangswerten und der gewünschten Impulsablenkung.
    """

    bodies = create_bodies()
    r_values, v_values, collision = simulate_system(bodies, N, dt)

    animate_system(
        r_values, bodies, dt,
        collision=collision,
        title="1. Versuch: Ohne Abwehr",
        auto_close=True
    )

    if collision is None:
        print("Keine Kollision: Es ist keine Abwehr notwendig.")
        return

    # Betroffenen Meteoroiden bestimmen
    meteorite_name = next(
        (name for name in collision if name.startswith("Meteoroid")),
        None
    )
    if meteorite_name is None:
        print("Keine Meteoroidenkollision gefunden.")
        return

    # 2. Ablenkungswerte erfragen
    collision_days = (len(r_values) - 1) * dt / 86400
    settings = ask_deflection(collision_days, meteorite_name)
    if settings is None:
        print("Abwehr abgebrochen.")
        return

    angle, time, impulse = settings

    # 3. Neu starten - wieder mit den urspruenglichen Werten
    bodies = create_bodies()
    meteorite = next(
        body for body in bodies if body.name == meteorite_name
    )
    r_values, v_values, collision = simulate_system(
        bodies, N, dt,
        meteorite=meteorite,
        impulse=impulse,
        time=time,
        angle=angle
    )

    animate_system(
        r_values, bodies, dt,
        collision=collision,
        title="2. Versuch: Mit Abwehr"
    )


if __name__ == "__main__":
    main()
