
import numpy as np
from values import G


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


def acceleration(body, other_bodies):
    a = np.array([0.0, 0.0])

    for other_body in other_bodies:
        if other_body is body:
            continue

        direction = other_body.r - body.r
        distance = np.linalg.norm(direction)

        if distance <= body.radius + other_body.radius:
            raise ValueError(
                f"Kollision zwischen {body.name} und {other_body.name}!"
            )

        a += G * other_body.mass * direction / distance**3

    return a


def simulate_system(bodies, N, dt):

    # Listen für alle Positionen und Geschwindigkeiten
    r_list = []
    v_list = []

    # Anfangswerte speichern
    r_list.append([body.r.copy() for body in bodies])
    v_list.append([body.v.copy() for body in bodies])

    for n in range(N):

        # Beschleunigungen aller Körper berechnen
        accelerations = []

        try:
            for body in bodies:
                a = acceleration(body, bodies)
                accelerations.append(a)

        except ValueError as e:
            print(f"Fehler in Zeitschritt {n}: {e}")
            break

        # Alle Körper bewegen
        for i, body in enumerate(bodies):

            # Euler-Cromer-Verfahren
            body.v = body.v + accelerations[i] * dt
            body.r = body.r + body.v * dt

        # Neue Werte in den Listen speichern
        r_list.append([body.r.copy() for body in bodies])
        v_list.append([body.v.copy() for body in bodies])

    # Listen in NumPy-Arrays umwandeln
    r_values = np.array(r_list)
    v_values = np.array(v_list)

    return r_values, v_values
