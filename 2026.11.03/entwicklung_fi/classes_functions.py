"""Datenmodell, Bahnberechnung und Benutzereingabe der Meteoroiden-Simulation.

Enthält die Berechnung der Gravitation, die Kollisionserkennung, die
Impulsablenkung und die numerische Simulation mit dem Euler-Cromer-Verfahren.
"""

import numpy as np
import tkinter as tk
from tkinter import simpledialog

from values import G, dt

class CelestialBody:
    """Beschreibt einen Himmelskörper mit seinen physikalischen Eigenschaften.
    
    Attributes:
        name (str): Name des Himmelskörpers.
        mass (float): Masse in Kilogramm.
        radius (float): Radius in Metern.
        r (numpy.ndarray): Zweidimensionaler Ortsvektor in Metern.
        v (numpy.ndarray): Zweidimensionaler Geschwindigkeitsvektor in m/s.
    """

    def __init__(self, name, mass, radius, r, v):
        """Legt einen Himmelskörper mit seinen Anfangswerten an.
        
        Args:
            name (str): Name des Körpers.
            mass (float): Masse in Kilogramm.
            radius (float): Radius in Metern.
            r (list | numpy.ndarray): Anfangsposition [x, y] in Metern.
            v (list | numpy.ndarray): Anfangsgeschwindigkeit [vx, vy] in m/s.
        """

        self.name = name
        self.mass = mass
        self.radius = radius
        self.r = np.array(r, dtype=float)
        self.v = np.array(v, dtype=float)


def orbital_data(axis, eccentricity, central_mass):
    """Berechnet Anfangsposition und -geschwindigkeit einer elliptischen Bahn.
    
    Der Körper startet im Perihel auf der positiven x-Achse. Die
    Anfangsgeschwindigkeit zeigt in positive y-Richtung. Verwendet wird
    eine Keplerbahn um die angegebene Zentralmasse.
    
    Args:
        axis (float): Große Halbachse der Ellipse in Metern.
        eccentricity (float): Numerische Exzentrizität der Ellipse.
        central_mass (float): Masse des Zentralkörpers in Kilogramm.
    
    Returns:
        tuple[numpy.ndarray, numpy.ndarray]: Ortsvektor [x, y] in Metern
            und Geschwindigkeitsvektor [vx, vy] in m/s.
    """

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
    """Berechnet die gesamte Gravitationsbeschleunigung eines Körpers.
    
    Die Beiträge aller anderen Körper werden mithilfe des Newtonschen
    Gravitationsgesetzes addiert. Der Körper selbst wird übersprungen.
    
    Args:
        body (CelestialBody): Körper, dessen Beschleunigung berechnet wird.
        other_bodies (list[CelestialBody]): Alle zu berücksichtigenden Körper.
    
    Returns:
        numpy.ndarray: Beschleunigungsvektor [ax, ay] in m/s².
    
    Raises:
        ValueError: Wenn zwei verschiedene Körper am selben Ort liegen.
    """

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
    """Prüft alle Körperpaare auf Berührung oder Überschneidung.
    
    Eine Kollision liegt vor, wenn der Mittelpunktabstand kleiner oder
    gleich der Summe beider Radien ist.
    
    Args:
        bodies (list[CelestialBody]): Zu überprüfende Himmelskörper.
    
    Returns:
        tuple[str, str] | None: Namen des ersten kollidierenden Körperpaars
            oder None, falls keine Kollision vorliegt.
    """

    for i, body in enumerate(bodies):
        for other_body in bodies[i + 1:]:
            distance = np.linalg.norm(other_body.r - body.r)

            if distance <= body.radius + other_body.radius:
                return body.name, other_body.name

    return None


def deflect_meteorite(meteorite, impulse, angle):
    """Verändert die Geschwindigkeit eines Meteoroiden durch einen Impuls.
    
    Der Impuls wird anhand seines Winkels in x- und y-Richtung zerlegt.
    Nach Δv = Impuls / Masse wird die Geschwindigkeitsänderung direkt
    zum Geschwindigkeitsvektor des Meteoroiden addiert.
    
    Args:
        meteorite (CelestialBody): Meteoroid, der abgelenkt werden soll.
        impulse (float): Betrag des Impulses in Newtonsekunden (N·s).
        angle (float): Richtung des Impulses in Grad, gemessen von der
            positiven x-Achse gegen den Uhrzeigersinn.
    
    Raises:
        ValueError: Wenn der Impuls negativ oder die Masse nicht positiv ist.
    """

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
    """Simuliert die Bewegung aller Körper mit dem Euler-Cromer-Verfahren.
    
    Berechnet in jedem Zeitschritt die gegenseitige Gravitation, aktualisiert
    Geschwindigkeiten und Orte und prüft auf Kollisionen. Optional wird einem
    Meteoroiden einmalig zum angegebenen Zeitpunkt ein Impuls verliehen.
    Bei einer Kollision endet die Simulation vorzeitig.
    Die übergebenen Körper werden dabei direkt verändert.
    
    Args:
        bodies (list[CelestialBody]): Himmelskörper mit Anfangsbedingungen.
        N (int): Maximale Anzahl der Simulationsschritte.
        dt (float): Dauer eines Zeitschritts in Sekunden.
        meteorite (CelestialBody | None): Optional abzulenkender Meteoroid,
            der in bodies enthalten sein muss.
        impulse (float): Betrag des Ablenkungsimpulses in N·s.
        time (float): Gewünschter Ablenkungszeitpunkt in Sekunden.
        angle (float): Ablenkrichtung in Grad zur positiven x-Achse.
    
    Returns:
        tuple[numpy.ndarray, numpy.ndarray, tuple[str, str] | None]:
            Positionsverlauf, Geschwindigkeitsverlauf und gegebenenfalls das
            erste kollidierende Körperpaar. Beide Verläufe besitzen die Form
            (gespeicherte Zeitschritte, Körper, 2).
    
    Raises:
        ValueError: Bei negativem Ablenkungszeitpunkt, nicht positivem dt,
            unbekanntem Meteoroiden oder sich anfangs berührenden Körpern.
    """

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
    """Fragt Winkel, Zeitpunkt und Stärke des Abwehrimpulses in Dialogen ab.
    
    Zeigt nacheinander drei Tkinter-Eingabefenster. Der Ablenkungszeitpunkt
    wird in Tagen eingegeben und für die Simulation in Sekunden umgerechnet.
    Bei einem Abbruch wird None zurückgegeben.
    
    Args:
        collision_days (float): Zeitpunkt der Kollision ohne Abwehr in Tagen.
        meteorite_name (str): Name des abzulenkenden Meteoroiden.
    
    Returns:
        tuple[float, float, float] | None: Winkel in Grad, Zeitpunkt in
            Sekunden und Impuls in N·s oder None bei Abbruch.
    """

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
