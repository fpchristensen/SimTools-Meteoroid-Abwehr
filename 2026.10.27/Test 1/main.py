from const_values import (
    A_EARTH,
    E_EARTH,
    M_Asteroid,
    M_EARTH,
    M_SUN,
    N,
    R_Asteroid,
    R_EARTH,
    R_SUN,
    DT,
)
from functions_and_classes import CelestialBody, orbital_data
from simulation import simulate_system
from UI_and_animations import animate_system


def main():
    sun = CelestialBody("Sonne", M_SUN, R_SUN, [0.0, 0.0], [0.0, 0.0])

    earth_position, earth_velocity = orbital_data(A_EARTH, E_EARTH, M_SUN)
    earth = CelestialBody(
        "Erde", M_EARTH, R_EARTH, earth_position, earth_velocity
    )

    meteoroid = CelestialBody(
        "Meteoroid",
        M_Asteroid,
        R_Asteroid,
        [-3.0 * A_EARTH, 1.0 * A_EARTH],
        [35000.0, 0.0],
    )

    bodies = [sun, earth, meteoroid]
    r_values, _ = simulate_system(bodies, N, DT)
    animation = animate_system(r_values, bodies)
    return animation


if __name__ == "__main__":
    main()
