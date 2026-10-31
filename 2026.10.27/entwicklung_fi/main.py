from const_values import *
from flex_values import *
from functions_and_classes import CelestialBody, orbital_data
from simulation import simulate_system
from UI_and_animations import animate_system


def main():

    # Sonne
    sun = CelestialBody(
        "Sonne",
        M_SUN,
        R_SUN,
        [0, 0],
        [0, 0]
    )

    # Bahndaten der Erde berechnen
    r_earth, v_earth = orbital_data(
        A_EARTH,
        E_EARTH,
        sun.mass
    )

    # Erde
    earth = CelestialBody(
        "Erde",
        M_EARTH,
        R_EARTH,
        r_earth,
        v_earth
    )

    # Asteroid
    asteroid = CelestialBody(
        "Asteroid",
        M_Asteroid_4,
        R_Asteroid_4,
        r_Asteroid_4,
        v_Asteroid_4
    )

    # Alle Himmelskörper zusammenfassen
    bodies = [sun, earth, asteroid]

    # Simulation durchführen
    r_values, v_values = simulate_system(
        bodies, N, DT
    )

    # Animation starten
    animate_system(r_values, bodies)


if __name__ == "__main__":
    main()
