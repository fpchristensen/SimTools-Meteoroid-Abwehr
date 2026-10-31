import numpy as np
from values import G

class CelestialBody:
    def __init__(self, name, mass, radius, r, v):       #Körper initialisiert, Anleitung
        self.name = name
        self.mass = mass
        self.radius = radius
        self.r = np.array(r, dtype = float)
        self.v = np.array(v, dtype = float)

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
        if other_body is body:  # Eigener Körper zieht sich nicht an
            continue

        direction = other_body.r - body.r
        distance = np.linalg.norm(direction)

        if distance <= body.radius + other_body.radius:
            raise ValueError(
                f"Kollision zwischen {body.name} und {other_body.name}!"
            )

        a += G * other_body.mass * direction / distance**3

    return a

def simulate_system(bodies, N, dt):          #Bewegung, sprich Orts- und Geschwindigkeitsvektoren
    
    r_values = np.zeros((N + 1, len(bodies), 2))        # Speicher für alle Positionen und Geschwindigkeiten, dreidimensionales Array: (Zeitschritte, Körper, Koordinaten)
    v_values = np.zeros((N + 1, len(bodies), 2))

    for i, body in enumerate(bodies):
        r_values[0, i] = body.r
        v_values[0, i] = body.v

    for n in range(N):

        # Beschleunigungen aller Körper berechnen
        accelerations = []

        for body in bodies:
            a = acceleration(body, bodies)
            accelerations.append(a)

        # Alle Körper bewegen
        for i, body in enumerate(bodies):

            # Euler-Cromer-Verfahren
            body.v = body.v + accelerations[i] * dt
            body.r = body.r + body.v * dt

            # Neue Werte speichern
            r_values[n + 1, i] = body.r
            v_values[n + 1, i] = body.v

    return r_values, v_values

