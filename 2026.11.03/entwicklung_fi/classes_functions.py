"""Physikalisches Modell für die Meteoroidenabwehr.

Berechnet Gravitation, Kollisionen und Impulsablenkung mit dem
Euler-Cromer-Verfahren. Enthält keine Benutzeroberfläche.
"""

import numpy as np
from values import G


class CelestialBody:
    """Repräsentiert einen Himmelskörper mit Masse, Radius, Ort und Geschwindigkeit.

    Attributes:
        name (str): Name des Himmelskörpers.
        mass (float): Masse in kg.
        radius (float): Radius in m.
        r (numpy.ndarray): Positionsvektor [x, y] in m.
        v (numpy.ndarray): Geschwindigkeitsvektor [vx, vy] in m/s.
    """

    def __init__(self, name, mass, radius, r, v):
        """Speichert die Eigenschaften und wandelt r und v in Arrays um.

        Args:
            name (str): Anzeigename.
            mass (float): Masse in kg.
            radius (float): Radius in m.
            r (list | numpy.ndarray): Startposition [x, y] in m.
            v (list | numpy.ndarray): Startgeschwindigkeit [vx, vy] in m/s.
        """
        self.name = name
        self.mass = mass
        self.radius = radius
        self.r = np.array(r, dtype=float)
        self.v = np.array(v, dtype=float)


def orbital_data(axis, eccentricity, central_mass):
    """Berechnet Startposition und -geschwindigkeit im Perihel einer Keplerellipse.

    Args:
        axis (float): Große Halbachse der Bahn in m.
        eccentricity (float): Numerische Exzentrizität.
        central_mass (float): Masse des zentralen Körpers in kg.

    Returns:
        tuple[numpy.ndarray, numpy.ndarray]: Position in m und Geschwindigkeit in m/s.
    """
    r = np.array([axis * (1 - eccentricity), 0], dtype=float)
    v = np.array([
        0,
        np.sqrt(G * central_mass * (1 + eccentricity)
                / (axis * (1 - eccentricity))),
    ], dtype=float)
    return r, v


def acceleration(body, other_bodies):
    """Summiert die Gravitationsbeschleunigungen anderer Körper.

    Args:
        body (CelestialBody): Körper, für den die Beschleunigung gilt.
        other_bodies (list[CelestialBody]): Alle Körper, einschließlich body.

    Returns:
        numpy.ndarray: Beschleunigung [ax, ay] in m/s².

    Raises:
        ValueError: Wenn sich zwei verschiedene Mittelpunkte decken.
    """
    a = np.array([0.0, 0.0])
    for other_body in other_bodies:
        if other_body is body:
            continue
        direction = other_body.r - body.r
        distance = np.linalg.norm(direction)
        if distance == 0:
            raise ValueError("Zwei Koerper befinden sich am selben Ort.") #sicherheit das wir nicht durch 0 Teilen
        a += G * other_body.mass * direction / distance**3
    return a


def check_collision(bodies): #damit wir weiter machen können nach kollision nicht einfach fehler haben.
    """Sucht das erste Körperpaar, dessen Radien sich berühren.

    Args:
        bodies (list[CelestialBody]): Zu prüfende Himmelskörper.

    Returns:
        tuple[str, str] | None: Namen des kollidierenden Paars oder None.
    """
    for i, body in enumerate(bodies):
        for other_body in bodies[i + 1:]:
            distance = np.linalg.norm(other_body.r - body.r)
            if distance <= body.radius + other_body.radius:
                return body.name, other_body.name
    return None


def deflect_meteorite(meteorite, impulse, angle):
    """Verändert die Geschwindigkeit des Meteoroiden durch einen gerichteten Impuls.

    Es gilt Delta-v = Impulsvektor / Masse; 0° zeigt nach rechts,
    90° nach oben.

    Args:
        meteorite (CelestialBody): Abzulen­kender Körper.
        impulse (float): Impulsbetrag in N·s.
        angle (float): Richtung gegen den Uhrzeigersinn in Grad.

    Raises:
        ValueError: Bei negativem Impuls oder nicht positiver Masse.
    """
    if impulse < 0:
        raise ValueError("Der Impulsbetrag darf nicht negativ sein.")
    if meteorite.mass <= 0:
        raise ValueError("Die Masse des Meteoriten muss positiv sein.")

    angle_rad = np.radians(angle)       #bogenmaß umrechnen
    impulse_vector = impulse * np.array([
        np.cos(angle_rad), np.sin(angle_rad)
    ])
    meteorite.v += impulse_vector / meteorite.mass 


def simulate_system(bodies, N, dt,
                    meteorite=None, impulse=0, time=0, angle=0):
    """Simuliert Körperbewegungen bis zur Kollision oder bis Schritt N.

    Das Euler-Cromer-Verfahren aktualisiert zunächst die Geschwindigkeiten
    und dann die Positionen. Optional wirkt ein Impuls genau einmal am
    angegebenen Simulationsschritt. Die Körper werden direkt verändert.

    Args:
        bodies (list[CelestialBody]): Körper mit Startpositionen und -geschwindigkeiten.
        N (int): Maximale Anzahl an Zeitschritten.
        dt (float): Länge eines Zeitschritts in s.
        meteorite (CelestialBody | None): Optional abzulenkender Meteoroid.
        impulse (float): Impulsbetrag in N·s.
        time (float): Gewünschter Zeitpunkt in s.
        angle (float): Impulsrichtung in Grad.

    Returns:
        tuple: Positionsverlauf, Geschwindigkeitsverlauf und Kollision.
            Beide Verläufe haben Form (Zeitschritte, Körper, 2).

    Raises:
        ValueError: Bei ungültiger Zeit, ungültigem dt, unbekanntem
            Meteoroiden oder sich bereits am Start berührenden Körpern.
    """
    #sicherheits checks
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
            f"Ungültige Startposition! {collision[0]} und {collision[1]} "
            "berühren sich bereits. Bitte die Startposition in values.py ändern."
        )

    if meteorite is not None and impulse_step == 0:
        deflect_meteorite(meteorite, impulse, angle)

    r_list = [[body.r.copy() for body in bodies]]
    v_list = [[body.v.copy() for body in bodies]]

    for n in range(N):
        accelerations = [acceleration(body, bodies) for body in bodies]

        # Euler-Cromer: zuerst Geschwindigkeit, dann Position aktualisieren.
        for i, body in enumerate(bodies):
            body.v += accelerations[i] * dt
            body.r += body.v * dt

        collision = check_collision(bodies)

        # Der Impuls wirkt nach genau dem gewünschten Zeitschritt.
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



def start_defense(frame, angle, impulse, meteorite_name,
                  create_bodies, N, dt):
    """Berechnet den Abwehrversuch mit den gewählten Eingaben."""

    new_bodies = create_bodies()

    meteorite = next(
        body for body in new_bodies if body.name == meteorite_name
    )

    time = frame * dt

    new_r_values, _, new_collision = simulate_system(
        new_bodies, N, dt,
        meteorite=meteorite,
        impulse=impulse,
        time=time,
        angle=angle,
    )

    return new_r_values, new_collision