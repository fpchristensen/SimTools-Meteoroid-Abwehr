import numpy as np
from const_values import G


class CelestialBody:

    def __init__(self, name, mass, radius, r, v):
        self.name = name
        self.mass = mass
        self.radius = radius
        self.r = np.array(r, dtype=float)
        self.v = np.array(v, dtype=float)


def orbital_data(axis, eccentricity, central_mass):

    r = np.array([
        axis * (1 - eccentricity),
        0
    ], dtype=float)

    v = np.array([
        0,
        np.sqrt(G * central_mass * (1 + eccentricity)
                / (axis * (1 - eccentricity)))
    ], dtype=float)

    return r, v


def berechne_acceleration(body, other_bodies):

    a = np.array([0.0, 0.0])

    for other_body in other_bodies:

        # Eigene Gravitation ignorieren
        if other_body is body:
            continue

        # Richtungsvektor
        direction = other_body.r - body.r

        # Abstand der Mittelpunkte
        distance = np.linalg.norm(direction)

        # Kollision überprüfen
        if distance <= body.radius + other_body.radius: #verbesserung zu == 0 aus letzter besprechung
            raise ValueError(
                f"Kollision zwischen {body.name} und {other_body.name}!"
            )

        # Gravitationsbeschleunigung
        a += G * other_body.mass * direction / distance**3 #addition aller gravitationen

    return a