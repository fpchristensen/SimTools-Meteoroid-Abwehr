"""Physikalisches Modell: Gravitation, Kollisionen und Impulsablenkung."""

import numpy as np
from values import G


class CelestialBody:
    """Himmelskörper mit Name, Masse, Radius, Position und Geschwindigkeit."""

    def __init__(self, name, mass, radius, r, v):
        self.name = name
        self.mass = mass
        self.radius = radius
        self.r = np.array(r, dtype=float)
        self.v = np.array(v, dtype=float)


def orbital_data(axis, eccentricity, central_mass):
    """Startposition und -geschwindigkeit im Perihel einer Keplerellipse."""
    r = np.array([axis * (1 - eccentricity), 0.0], dtype=float)
    v = np.array([
        0.0,
        np.sqrt(G * central_mass * (1 + eccentricity)
                / (axis * (1 - eccentricity))),
    ], dtype=float)
    return r, v


def acceleration(body, other_bodies):
    """Resultierende Gravitationsbeschleunigung des Körpers in m/s²."""
    a = np.array([0.0, 0.0])
    for other_body in other_bodies:
        if other_body is body:
            continue
        direction = other_body.r - body.r
        distance = np.linalg.norm(direction)
        if distance == 0:
            raise ValueError("Zwei Körper befinden sich am selben Ort.")
        a += G * other_body.mass * direction / distance**3
    return a


def check_collision(bodies):
    """Liefert die Namen des ersten berührenden Körperpaars oder None."""
    for i, body in enumerate(bodies):
        for other_body in bodies[i + 1:]:
            distance = np.linalg.norm(other_body.r - body.r)
            if distance <= body.radius + other_body.radius:
                return body.name, other_body.name
    return None


def deflect_meteorite(meteorite, impulse, angle):
    """Einmaliger Impuls: Delta-v = J / m, Winkel 0° rechts, 90° oben."""
    if impulse < 0:
        raise ValueError("Der Impulsbetrag darf nicht negativ sein.")
    if meteorite.mass <= 0:
        raise ValueError("Die Masse des Meteoroiden muss positiv sein.")

    angle_rad = np.radians(angle)
    impulse_vector = impulse * np.array([
        np.cos(angle_rad), np.sin(angle_rad)
    ])
    meteorite.v += impulse_vector / meteorite.mass


def simulate_system(bodies, N, dt,
                    meteorite=None, impulse=0, time=0, angle=0):
    """Euler-Cromer-Simulation mit optionalem einmaligem Impuls.

    Gibt (Positionen, Geschwindigkeiten, Kollision) zurück.
    Positionen/Geschwindigkeiten: (Schritte, Körper, 2).
    """
    if time < 0:
        raise ValueError("Der Ablenkungszeitpunkt darf nicht negativ sein.")
    if dt <= 0:
        raise ValueError("dt muss positiv sein.")
    if meteorite is not None and meteorite not in bodies:
        raise ValueError("Der abgelenkte Meteoroid muss in bodies stehen.")

    impulse_step = int(np.ceil(time / dt))
    collision = check_collision(bodies)
    if collision is not None:
        raise ValueError(
            f"Ungültige Startposition: {collision[0]} und {collision[1]} "
            "berühren sich bereits. Bitte Startwerte ändern."
        )

    if meteorite is not None and impulse_step == 0:
        deflect_meteorite(meteorite, impulse, angle)

    r_list = [[body.r.copy() for body in bodies]]
    v_list = [[body.v.copy() for body in bodies]]

    for n in range(N):
        accelerations = [acceleration(body, bodies) for body in bodies]
        for i, body in enumerate(bodies):
            body.v += accelerations[i] * dt
            body.r += body.v * dt

        collision = check_collision(bodies)
        if collision is None and meteorite is not None and n + 1 == impulse_step:
            deflect_meteorite(meteorite, impulse, angle)

        r_list.append([body.r.copy() for body in bodies])
        v_list.append([body.v.copy() for body in bodies])

        if collision is not None:
            break

    return np.array(r_list), np.array(v_list), collision


def start_defense(frame, angle, impulse, meteorite_name,
                  create_bodies, N, dt):
    """Startet mit frischen Körpern eine Simulation mit ausgewähltem Impuls."""
    new_bodies = create_bodies()
    meteorite = next(
        (body for body in new_bodies if body.name == meteorite_name), None
    )
    if meteorite is None:
        raise ValueError(f"Unbekannter Meteoroid: {meteorite_name}")

    time = frame * dt
    new_r_values, _, new_collision = simulate_system(
        new_bodies, N, dt,
        meteorite=meteorite,
        impulse=impulse,
        time=time,
        angle=angle,
    )
    return new_r_values, new_collision
