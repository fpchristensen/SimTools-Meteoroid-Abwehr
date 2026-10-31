

from values import (
    a_Ellipse,
    e_Ellipse,
    m_Meteorid1,
    m_Meteorid2,
    m_Erde,
    m_Sonne,
    N,
    radius_Meteorid1,
    radius_Meteorid2,
    radius_Erde,
    radius_Sonne,
    dt,
    r_Meteorid1,
    v_Meteorid1,
    r_Meteorid2,
    v_Meteorid2
)
from classes_functions import CelestialBody, orbital_data, simulate_system
from aniUI import animate_system


def main():
    sun = CelestialBody("Sonne", m_Sonne, radius_Sonne, [0.0, 0.0], [0.0, 0.0])

    earth_position, earth_velocity = orbital_data(a_Ellipse, e_Ellipse, m_Sonne)
    earth = CelestialBody(
        "Erde", m_Erde, radius_Erde, earth_position, earth_velocity
    )

    meteoroid1= CelestialBody(
        "Meteoroid",
        m_Meteorid1,
        radius_Meteorid1,
        r_Meteorid1,
        v_Meteorid1
    )

    meteoroid2 = CelestialBody(
            "Meteoroid",
            m_Meteorid2,
            radius_Meteorid2,
            r_Meteorid2,
            v_Meteorid2
        )


    bodies = [sun, earth, meteoroid1, meteoroid2]
    r_values, _ = simulate_system(bodies, N, dt)
    animation = animate_system(r_values, bodies)
    return animation


if __name__ == "__main__":
    main()