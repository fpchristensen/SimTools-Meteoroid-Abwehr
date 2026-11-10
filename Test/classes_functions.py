"""Physikalisches Modell und Asteroiden-Datenstrukturen.

Hier liegen alle Klassen und allgemeinen Funktionen für die Simulation:
Himmelskörper, Asteroiden-Einstellungen, Gravitationsmodell, Kollisionen,
Impulse und Zugriff auf die Katalogdaten aus values.py.

Dieses Modul benötigt KEIN PyQt6 und KEIN Matplotlib.
"""

from dataclasses import dataclass, field

import numpy as np
from values import (
    G, ASTEROIDEN_KATALOG,
    a_Ellipse, e_Ellipse, m_Sonne, radius_Sonne, m_Erde, radius_Erde,
    m_Meteorid1, radius_Meteorid1, r_Meteorid1, v_Meteorid1,
)


class CelestialBody:
    """Repräsentiert einen physikalischen Körper in der zweidimensionalen Simulation.

    Attributes:
        name (str): Eindeutiger Anzeigename.
        mass (float): Masse in kg.
        radius (float): Radius in m.
        r (np.ndarray): Zweidimensionale Position in m.
        v (np.ndarray): Zweidimensionale Geschwindigkeit in m/s.
    """

    def __init__(self, name, mass, radius, r, v):
        """Legt einen Himmelskoerper an und wandelt Position sowie Geschwindigkeit in NumPy-Arrays um.

        Args:
            name (str): Eindeutiger Name des Körpers.
            mass (float): Masse in kg.
            radius (float): Radius in m.
            r (Sequence[float]): Startposition [x, y] in m.
            v (Sequence[float]): Startgeschwindigkeit [vx, vy] in m/s.
        """
        self.name = name
        self.mass = mass
        self.radius = radius
        self.r = np.array(r, dtype=float)
        self.v = np.array(v, dtype=float)


def orbital_data(axis, eccentricity, central_mass):
    """Startposition und -geschwindigkeit im Perihel einer Keplerellipse.

    Args:
        axis (float): Große Halbachse der Ellipse in m.
        eccentricity (float): Numerische Exzentrizität der Ellipse.
        central_mass (float): Masse des Zentralgestirns in kg.

    Returns:
        tuple[np.ndarray, np.ndarray]: Perihelposition in m und Geschwindigkeit in m/s.
    """
    r = np.array([axis * (1 - eccentricity), 0.0], dtype=float)
    v = np.array([
        0.0,
        np.sqrt(G * central_mass * (1 + eccentricity)
                / (axis * (1 - eccentricity))),
    ], dtype=float)
    return r, v


def acceleration(body, other_bodies):
    """Resultierende Gravitationsbeschleunigung des Körpers in m/s².

    Args:
        body (CelestialBody): Körper, dessen Beschleunigung berechnet wird.
        other_bodies (list[CelestialBody]): Alle Himmelskoerper inklusive body.

    Returns:
        np.ndarray: Zweidimensionaler Beschleunigungsvektor in m/s^2.
    """
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
    """Liefert die Namen des ersten berührenden Körperpaars oder None.

    Args:
        bodies (list[CelestialBody]): Zu prüfende Körper.

    Returns:
        tuple[str, str] | None: Namen des ersten kollidierenden Paars oder None.
    """
    for i, body in enumerate(bodies):
        for other_body in bodies[i + 1:]:
            distance = np.linalg.norm(other_body.r - body.r)
            if distance <= body.radius + other_body.radius:
                return body.name, other_body.name
    return None


def deflect_meteorite(meteorite, impulse, angle):
    """Einmaliger Impuls: Delta-v = J / m, Winkel 0° rechts, 90° oben.

    Args:
        meteorite (CelestialBody): Asteroid, dessen Geschwindigkeit geändert wird.
        impulse (float): Betrag des Impulses in N s.
        angle (float): Richtung in Grad ab der positiven x-Achse, gegen den Uhrzeigersinn.

    Notes:
        Verändert nur die Geschwindigkeit des übergebenen Objekts.
        Delta-v = Impuls / Masse; der Impuls wirkt nur einmal.

    Raises:
        ValueError: Bei negativem Impuls oder nicht positiver Masse.
    """
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
                    meteorite=None, impulse=0, time=0, angle=0,
                    defense_actions=None):
    """Euler-Cromer-Simulation mit beliebig vielen einmaligen Impulsen.

    Args:
        bodies (list[CelestialBody]): Himmelskörper mit Startwerten. Diese Objekte
            werden während der Berechnung direkt verändert.
        N (int): Maximale Anzahl der Zeitschritte.
        dt (float): Dauer eines Zeitschritts in Sekunden.
        meteorite (CelestialBody | None): Zielkörper der älteren Einzelschritt-API.
        impulse (float): Impulsbetrag in N·s für ``meteorite``.
        time (float): Eingriffszeitpunkt in Sekunden für ``meteorite``.
        angle (float): Impulsrichtung in Grad ab der positiven x-Achse.
        defense_actions (list[dict] | None): Liste mit den Einträgen ``frame``
            (ganzer Simulationsschritt), ``target`` (Körpername), ``impulse``
            (in N·s) und ``angle`` (in Grad). Mehrere Aktionen sind möglich.

    Returns:
        tuple[np.ndarray, np.ndarray, tuple[str, str] | None]: Orts- und
            Geschwindigkeitsverlauf mit der Form (Frames, Körper, 2) sowie
            Namen des ersten kollidierenden Körperpaars oder ``None``.

    Notes:
        Das Euler-Cromer-Verfahren aktualisiert zuerst die Geschwindigkeit
        und danach die Position. Ein Impuls bei Frame k verändert deshalb
        erstmals die Position in Frame k+1.
        Die Simulation endet beim ersten Kontakt zweier Körper. Alle danach
        geplanten Impulse werden nicht mehr ausgeführt.

    Raises:
        ValueError: Bei ungültiger Zeit, ungültigen Impulsen, nicht vorhandenen
            Zielkörpern oder wenn zwei Körper bereits zum Start kollidieren.
    """
    if dt <= 0 or N < 0:
        raise ValueError("dt muss positiv und N darf nicht negativ sein.")
    if time < 0:
        raise ValueError("Der Ablenkungszeitpunkt darf nicht negativ sein.")
    if meteorite is not None and meteorite not in bodies:
        raise ValueError("Der abgelenkte Meteoroid muss in bodies stehen.")

    # Eine Aktion erhält ihre eigene Referenz auf den tatsächlich simulierten
    # Körper, damit verschiedene Asteroiden im selben Lauf abgelenkt werden.
    names = {body.name: body for body in bodies}
    if len(names) != len(bodies):
        raise ValueError("Alle Körper benötigen eindeutige Namen.")
    actions_by_frame = {}
    entries = list(defense_actions or [])
    if meteorite is not None:
        entries.append({
            "frame": int(np.ceil(time / dt)),
            "target": meteorite.name,
            "impulse": impulse,
            "angle": angle,
        })

    for entry in entries:
        frame = entry["frame"]
        if isinstance(frame, (bool, np.bool_)) or int(frame) != frame:
            raise ValueError("Ein Impuls-Frame muss eine ganze Zahl sein.")
        frame = int(frame)
        if not 0 <= frame <= N:
            raise ValueError(f"Impuls-Frame {frame} liegt außerhalb der Simulation.")
        target = entry["target"]
        if target not in names:
            raise ValueError(f"Unbekannter Impuls-Zielkörper: {target}")
        value = float(entry["impulse"])
        direction = float(entry["angle"])
        if not np.isfinite(value) or value < 0 or not np.isfinite(direction):
            raise ValueError("Impulsbetrag/-richtung muss endlich und gültig sein.")
        actions_by_frame.setdefault(frame, []).append(
            (names[target], value, direction)
        )

    collision = check_collision(bodies)
    if collision is not None:
        raise ValueError(
            f"Ungültige Startposition: {collision[0]} und {collision[1]} "
            "berühren sich bereits. Bitte Startwerte ändern."
        )

    for target, value, direction in actions_by_frame.get(0, []):
        deflect_meteorite(target, value, direction)

    r_list = [[body.r.copy() for body in bodies]]
    v_list = [[body.v.copy() for body in bodies]]

    for n in range(N):
        accelerations = [acceleration(body, bodies) for body in bodies]
        for i, body in enumerate(bodies):
            body.v += accelerations[i] * dt
            body.r += body.v * dt

        collision = check_collision(bodies)
        if collision is None:
            for target, value, direction in actions_by_frame.get(n + 1, []):
                deflect_meteorite(target, value, direction)

        r_list.append([body.r.copy() for body in bodies])
        v_list.append([body.v.copy() for body in bodies])

        if collision is not None:
            break

    return np.array(r_list), np.array(v_list), collision


def start_defense(frame, angle, impulse, meteorite_name,
                  create_bodies, N, dt):
    """Startet mit frischen Körpern eine Simulation mit ausgewähltem Impuls.

    Args:
        frame (int): Schritt, ab dem die Geschwindigkeitskorrektur gilt.
        angle (float): Impulswinkel in Grad.
        impulse (float): Impulsbetrag in N s.
        meteorite_name (str): Eindeutiger Name des Zielasteroiden.
        create_bodies (Callable): Funktion, die frische Himmelskoerper erstellt.
        N (int): Maximale Zahl der Schritte.
        dt (float): Dauer eines Schrittes in s.

    Returns:
        tuple[np.ndarray, tuple[str, str] | None]: Positionen und ggf. erste Kollision.
    """
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


@dataclass
class AsteroidSettings:
    """Speichert die von der Oberfläche konfigurierbaren Anfangswerte eines Asteroiden.

    Attributes:
        name (str): Individueller Name.
        scenario (str): "Kollision" oder "Vorbeiflug".
        profile (str): "Klein und Leicht", "Groß und Schwer" oder "Eigener Asteroid".
        catalog_id (str | None): ID des Katalogprofils, falls ausgewählt.
        diameter_m (float): Durchmesser in m; physikalischer Radius ist die Hälfte.
        mass_kg (float): Masse in kg.
        position (np.ndarray): Startposition [x, y] in m.
        velocity (np.ndarray): Startgeschwindigkeit [vx, vy] in m/s.
    """
    name: str
    scenario: str = "Kollision"
    profile: str = "Klein und Leicht"
    catalog_id: str | None = None
    diameter_m: float = 2 * radius_Meteorid1
    mass_kg: float = m_Meteorid1
    position: np.ndarray = field(
        default_factory=lambda: np.array(r_Meteorid1, dtype=float)
    )
    velocity: np.ndarray = field(
        default_factory=lambda: np.array(v_Meteorid1, dtype=float)
    )


# Der Katalog kommt ausschließlich aus values.py. Für den schnellen Zugriff
# wird einmal ein Index aus den dort definierten Einträgen erzeugt.
_KATALOG_INDEX = {entry["id"]: entry for entry in ASTEROIDEN_KATALOG}


def profiles(category):
    """Liefert die geprüften Katalogeinträge der Gruppe 'Leicht'/'Schwer'.

    Args:
        category (str): Entweder "Leicht" oder "Schwer".

    Returns:
        list[dict]: Alle Profile der angefragten Kategorie.
    """
    return [entry for entry in ASTEROIDEN_KATALOG if entry["category"] == category]


def entry_for(profile_id):
    """Liefert einen Katalogeintrag anhand seiner stabilen ID.

    Args:
        profile_id (str): Eindeutige Profilkennung, etwa "leicht_03".

    Returns:
        dict: Katalogeintrag zur Profilkennung.

    Raises:
        KeyError: Wenn die Profilkennung nicht im Katalog existiert.
    """
    return _KATALOG_INDEX[profile_id]


def catalog_settings(profile_id, name):
    """Erzeugt editierbare Anfangswerte aus einem geprüften Katalogeintrag.

    Args:
        profile_id (str): Eindeutige Katalogkennung.
        name (str): Frei vergebener Anzeigename des Asteroiden.

    Returns:
        AsteroidSettings: Unabhaengige Konfiguration aus den Katalogwerten.
    """
    entry = entry_for(profile_id)
    return AsteroidSettings(
        name=name,
        scenario="Kollision",
        profile=("Klein und Leicht" if entry["category"] == "Leicht"
                 else "Groß und Schwer"),
        catalog_id=profile_id,
        diameter_m=entry["diameter_m"],
        mass_kg=entry["mass_kg"],
        position=np.array(entry["position_m"], dtype=float),
        velocity=np.array(entry["velocity_m_s"], dtype=float),
    )


def create_bodies(asteroids):
    """Erzeugt Sonne, Erde und *frische* Körper aus AsteroidSettings.

    Jeder Simulationsversuch beginnt so garantiert wieder mit t=0.

    Args:
        asteroids (list[AsteroidSettings]): Startwerte der ausgewählten Körper.

    Returns:
        list[CelestialBody]: Sonne, Erde und dann Asteroiden in Listenreihenfolge.
    """
    sun = CelestialBody("Sonne", m_Sonne, radius_Sonne, [0, 0], [0, 0])
    earth_r, earth_v = orbital_data(a_Ellipse, e_Ellipse, m_Sonne)
    earth = CelestialBody("Erde", m_Erde, radius_Erde, earth_r, earth_v)
    bodies = [sun, earth]
    for asteroid in asteroids:
        bodies.append(CelestialBody(
            asteroid.name, asteroid.mass_kg, asteroid.diameter_m / 2,
            asteroid.position.copy(), asteroid.velocity.copy(),
        ))
    return bodies
