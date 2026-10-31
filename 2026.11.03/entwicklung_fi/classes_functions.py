import numpy as np
import tkinter as tk
from tkinter import simpledialog

from values import G, dt

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

        if distance == 0:
            raise ValueError("Zwei Koerper befinden sich am selben Ort.")

        a += G * other_body.mass * direction / distance**3

    return a


def check_collision(bodies):
    for i, body in enumerate(bodies):
        for other_body in bodies[i + 1:]:
            distance = np.linalg.norm(other_body.r - body.r)

            if distance <= body.radius + other_body.radius:
                return body.name, other_body.name

    return None


def deflect_meteorite(meteorite, impulse, angle):
    if impulse < 0:
        raise ValueError("Der Impulsbetrag darf nicht negativ sein.")

    if meteorite.mass <= 0:
        raise ValueError("Die Masse des Meteoriten muss positiv sein.")

    angle_rad = np.radians(angle)
    impulse_vector = impulse * np.array([
        np.cos(angle_rad),
        np.sin(angle_rad)
    ])

    meteorite.v += impulse_vector / meteorite.mass


def simulate_system(bodies, N, dt,
                    meteorite=None, impulse=0, time=0, angle=0):
    if time < 0:
        raise ValueError("Der Ablenkungszeitpunkt darf nicht negativ sein.")
    if dt <= 0:
        raise ValueError("dt muss positiv sein.")
    if meteorite is not None and meteorite not in bodies:
        raise ValueError("Der abgelenkte Meteoroid muss in bodies stehen.")

    impulse_step = int(np.ceil(time / dt))
    # Überprüfen, ob sich Körper bereits am Anfang berühren
    collision = check_collision(bodies)

    if collision is not None:
        raise ValueError(
            f"Ungültige Startposition! "
            f"{collision[0]} und {collision[1]} berühren sich bereits. "
            f"Bitte die Startposition in values.py ändern."
        )

    if collision is None and meteorite is not None and impulse_step == 0:
        deflect_meteorite(meteorite, impulse, angle)

    r_list = [[body.r.copy() for body in bodies]]
    v_list = [[body.v.copy() for body in bodies]]

    for n in range(N):
        if collision is not None:
            break

        accelerations = [acceleration(body, bodies) for body in bodies]

        # Euler-Cromer-Verfahren
        for i, body in enumerate(bodies):
            body.v += accelerations[i] * dt
            body.r += body.v * dt

        collision = check_collision(bodies)

        # Impuls genau einmal nach dem angegebenen Zeitschritt
        if collision is None and meteorite is not None and n + 1 == impulse_step:
            deflect_meteorite(meteorite, impulse, angle)
            print(
                f"Impuls auf {meteorite.name} nach "
                f"{(n + 1) * dt / 86400:.2f} Tagen angewendet."
            )

        r_list.append([body.r.copy() for body in bodies])
        v_list.append([body.v.copy() for body in bodies])

        if collision is not None:
            print(
                f"Kollision: {collision[0]} und {collision[1]} "
                f"nach {(n + 1) * dt / 86400:.2f} Tagen."
            )
            break

    return np.array(r_list), np.array(v_list), collision


def ask_deflection(collision_days, meteorite_name):
    root = tk.Tk()
    root.withdraw()

    try:
        angle = simpledialog.askfloat(
            "Meteoritenabwehr – Winkel",
            f"Ablenkwinkel fuer {meteorite_name} in Grad\n"
            "(0° = rechts, 90° = oben):",
            initialvalue=45.0,
            parent=root
        )
        if angle is None:
            return None

        days = simpledialog.askfloat(
            "Meteoritenabwehr – Zeitpunkt",
            "Zeitpunkt der Ablenkung in Tagen\n"
            f"(Kollision ohne Abwehr: Tag {collision_days:.2f}):",
            initialvalue=min(15.0, collision_days / 2),
            minvalue=0.0,
            maxvalue=max(0.0, collision_days - dt / 86400),
            parent=root
        )
        if days is None:
            return None

        impulse = simpledialog.askfloat(
            "Meteoritenabwehr – Impuls",
            "Impulsbetrag in N·s (z. B. 1e13):",
            initialvalue=1e13,
            minvalue=0.0,
            parent=root
        )
        if impulse is None:
            return None

        return angle, days * 86400, impulse

    finally:
        root.destroy()


