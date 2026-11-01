"""Startet die Meteoroiden-Simulation ohne und anschließend mit Abwehr."""

from values import (
    N, dt,
    a_Ellipse, e_Ellipse,
    m_Meteorid1, m_Meteorid2,
    m_Erde, m_Sonne,
    radius_Meteorid1, radius_Meteorid2,
    radius_Erde, radius_Sonne,
    r_Meteorid1, v_Meteorid1,
    r_Meteorid2, v_Meteorid2,
)
from classes_functions import CelestialBody, orbital_data, simulate_system
from aniUI import animate_system


def create_bodies():
    """Erstellt Sonne, Erde und Meteoroiden mit unveränderten Startwerten.

    Returns:
        list[CelestialBody]: Frische Objekte in der Reihenfolge Sonne,
            Erde, Meteoroid 1.
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
   
    return [sun, earth, meteoroid1]


def main():
    """Zeigt erst die Kollision und danach die interaktive Abwehr an.

    Der zweite Durchlauf startet erst nach Klick auf Play. Seine Werte
    werden aus Zeitregler, Drehregler und Abwehr-Dropdown übernommen.
    """
    # 1. Ohne Abwehr simulieren und animieren.
    bodies = create_bodies()
    r_values, _, collision = simulate_system(bodies, N, dt)

    animate_system(
        r_values, bodies, dt,
        collision=collision,
        title="1. Versuch: Ohne Abwehr",
        auto_close=True,
    )

    if collision is None:
        print("Keine Kollision: Es ist keine Abwehr notwendig.")
        return

    meteorite_name = next(
        (name for name in collision if name.startswith("Meteoroid")),
        None,
    )
    if meteorite_name is None:
        print("Keine Meteoroidenkollision gefunden.")
        return

    # 2. Wird erst beim Klick auf den Play-Button aufgerufen.
    def start_defense(frame, angle, impulse):
        """Berechnet den Abwehrversuch mit den drei gewählten Eingaben.

        Args:
            frame (int): Zeitschritt der Ablenkung (aus Zeitregler).
            angle (float): Ablenkwinkel in Grad (aus Drehregler).
            impulse (float): Impulsbetrag in N·s (aus Dropdown).

        Returns:
            tuple: Neuer Positionsverlauf und mögliche Kollision.
        """
        new_bodies = create_bodies()
        meteorite = next(
            body for body in new_bodies if body.name == meteorite_name
        )
        # Beispiel: Frame 192 * dt=3600 s -> Impuls an Tag 8.
        time = frame * dt
        new_r_values, _, new_collision = simulate_system(
            new_bodies, N, dt,
            meteorite=meteorite,
            impulse=impulse,
            time=time,
            angle=angle,
        )
        return new_r_values, new_collision

    # Zeigt zunächst den bekannten Verlauf zum freien Durchspulen.
    # Play startet die neue Simulation mit den gewählten Werten.
    animate_system(
        r_values, bodies, dt,
        collision=collision,
        title="2. Versuch: Mit Abwehr",
        controls=True,
        on_play=start_defense,
    )


if __name__ == "__main__":
    main()
