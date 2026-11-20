"""Physikalisches Modell und Meteoroiden-Datenstrukturen.

Hier liegen alle Klassen und allgemeinen Funktionen für die Simulation:
Himmelskörper, Meteoroiden-Einstellungen, Gravitationsmodell, Kollisionen,
Impulse und Zugriff auf die Katalogdaten aus values.py.

Dieses Modul benötigt KEIN PyQt6 und KEIN Matplotlib.
"""

from dataclasses import dataclass, field

import numpy as np
from values import (
    G, METEOROIDEN_KATALOG,
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
        meteorite (CelestialBody): Meteoroid, dessen Geschwindigkeit geändert wird.
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
    """Historisches Stundenmodell mit beliebig vielen einmaligen Impulsen.

    Für die adaptive Simulation der GUI siehe ``simulate_trajectory``.
    Diese Funktion bleibt für ältere Aufrufe und Vergleichstests erhalten.

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
    # Körper, damit verschiedene Meteoroiden im selben Lauf abgelenkt werden.
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
        meteorite_name (str): Eindeutiger Name des Zielmeteoroiden.
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
class MeteoroidSettings:
    """Speichert die von der Oberfläche konfigurierbaren Anfangswerte eines Meteoroiden.

    Attributes:
        name (str): Individueller Name.
        scenario (str): "Kollision" oder "Vorbeiflug".
        profile (str): "Klein und Leicht", "Groß und Schwer" oder "Eigener Meteoroid".
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
_KATALOG_INDEX = {entry["id"]: entry for entry in METEOROIDEN_KATALOG}


def profiles(category):
    """Liefert die geprüften Katalogeinträge der Gruppe 'Leicht'/'Schwer'.

    Args:
        category (str): Entweder "Leicht" oder "Schwer".

    Returns:
        list[dict]: Alle Profile der angefragten Kategorie.
    """
    return [entry for entry in METEOROIDEN_KATALOG if entry["category"] == category]


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
        name (str): Frei vergebener Anzeigename des Meteoroiden.

    Returns:
        MeteoroidSettings: Unabhaengige Konfiguration aus den Katalogwerten.
    """
    entry = entry_for(profile_id)
    return MeteoroidSettings(
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


def create_bodies(meteoroids):
    """Erzeugt Sonne, Erde und *frische* Körper aus MeteoroidSettings.

    Jeder Simulationsversuch beginnt so garantiert wieder mit t=0.

    Args:
        meteoroids (list[MeteoroidSettings]): Startwerte der ausgewählten Körper.

    Returns:
        list[CelestialBody]: Sonne, Erde und dann Meteoroiden in Listenreihenfolge.
    """
    sun = CelestialBody("Sonne", m_Sonne, radius_Sonne, [0, 0], [0, 0])
    earth_r, earth_v = orbital_data(a_Ellipse, e_Ellipse, m_Sonne)
    earth = CelestialBody("Erde", m_Erde, radius_Erde, earth_r, earth_v)
    bodies = [sun, earth]
    for meteoroid in meteoroids:
        bodies.append(CelestialBody(
            meteoroid.name, meteoroid.mass_kg, meteoroid.diameter_m / 2,
            meteoroid.position.copy(), meteoroid.velocity.copy(),
        ))
    return bodies


def interpolate_positions(positions, frame):
    """Interpoliert die Positionen zwischen zwei gespeicherten Euler-Schritten.

    Args:
        positions (np.ndarray): Positionsverlauf (Frames, Körper, 2).
        frame (float): Auch gebrochene Frame-Nummern sind erlaubt.

    Returns:
        np.ndarray: Positionen aller Körper zum angezeigten Zwischenzeitpunkt.
    """
    frame = float(np.clip(frame, 0, len(positions) - 1))
    lower = int(frame)
    upper = min(lower + 1, len(positions) - 1)
    fraction = frame - lower
    return (1 - fraction) * positions[lower] + fraction * positions[upper]


def segment_radius_interval(start, end, radius):
    """Bestimmt den Teil einer relativen geraden Strecke innerhalb eines Kreises.

    Returns:
        tuple[float, float] | None: Eintritt und Austritt als Bruchteile
            des Zeitschritts (0 bis 1), oder None bei keinem Kontakt.
    """
    delta = end - start
    length_squared = float(np.dot(delta, delta))
    if length_squared == 0:
        return (0.0, 1.0) if np.linalg.norm(start) <= radius else None
    projection = -float(np.dot(start, delta)) / length_squared
    nearest = start + projection * delta
    remaining = radius**2 - float(np.dot(nearest, nearest))
    if remaining < -radius**2 * 1e-12:
        return None
    span = np.sqrt(max(0.0, remaining) / length_squared)
    entry = max(0.0, projection - span)
    exit_ = min(1.0, projection + span)
    return (float(entry), float(exit_)) if entry <= exit_ else None


def earth_encounter_windows(positions, radius, end_frame=None):
    """Findet und vereinigt alle Nahbereiche zwischen Erde und Meteoroiden.

    Auch Begegnungen zwischen zwei Stundenwerten werden berücksichtigt,
    sodass die Wiedergabe sie bei hohen Tempofaktoren nicht überspringt.
    Die Körperreihenfolge ist Sonne, Erde, anschließend Meteoroiden.
    """
    last = len(positions) - 1 if end_frame is None else float(end_frame)
    intervals = []
    for index in range(2, positions.shape[1]):
        relative = positions[:, index] - positions[:, 1]
        if len(relative) == 1:
            if np.linalg.norm(relative[0]) <= radius:
                intervals.append((0.0, 0.0))
            continue
        starts, ends = relative[:-1], relative[1:]
        delta = ends - starts
        length_sq = np.sum(delta * delta, axis=1)
        projection = np.divide(-np.sum(starts * delta, axis=1), length_sq,
                               out=np.zeros_like(length_sq), where=length_sq > 0)
        closest = starts + np.clip(projection, 0, 1)[:, None] * delta
        candidates = np.flatnonzero(np.linalg.norm(closest, axis=1) <= radius * (1 + 1e-12))
        for step in candidates:
            interval = segment_radius_interval(starts[step], ends[step], radius)
            if interval is not None:
                entry, exit_ = step + interval[0], min(last, step + interval[1])
                if entry <= exit_:
                    intervals.append((entry, exit_))
    merged = []
    for entry, exit_ in sorted(intervals):
        if merged and entry <= merged[-1][1] + 1e-9:
            merged[-1] = (merged[-1][0], max(merged[-1][1], exit_))
        else:
            merged.append((entry, exit_))
    return merged


def collision_contact_frame(positions, bodies, collision):
    """Schätzt für eine vom Modell erkannte Kollision den ersten Oberflächenkontakt.

    Nur die Anzeige endet früher im letzten Euler-Schritt. Die berechneten
    Stundenwerte, die Abwehrzeitpunkte und die Kollisionslogik bleiben gleich.
    """
    last = len(positions) - 1
    if collision is None or last == 0:
        return float(last)
    names = {body.name: i for i, body in enumerate(bodies)}
    i, j = (names[name] for name in collision)
    relative = positions[-2:, j] - positions[-2:, i]
    interval = segment_radius_interval(relative[0], relative[1], bodies[i].radius + bodies[j].radius)
    return last - 1 + interval[0] if interval is not None else float(last)


def next_playback_frame(frame, normal_step, windows, positions, earth_radius,
                        max_closeup_step, distance_fraction, end_frame):
    """Wählt das nächste Anzeigebild ohne Überspringen einer Nahbegegnung.

    In der Nahansicht wird der relative Weg pro Bild begrenzt. Dadurch
    verlangsamt sich der Anflug in Erdnähe zusätzlich, während die normalen
    Geschwindigkeitsstufen außerhalb der Nahansicht erhalten bleiben.
    """
    epsilon = 1e-9
    for entry, exit_ in windows:
        if frame < entry - epsilon:
            return min(frame + normal_step, entry, end_frame)
        if frame < exit_ - epsilon:
            lower = int(frame)
            upper = min(lower + 1, len(positions) - 1)
            current = interpolate_positions(positions, frame)
            distances = np.linalg.norm(current[2:] - current[1], axis=1)
            relative_step = ((positions[upper, 2:] - positions[upper, 1])
                             - (positions[lower, 2:] - positions[lower, 1]))
            speeds = np.linalg.norm(relative_step, axis=1)
            # Der zeitlich strengste Körper bestimmt den nächsten Bildschritt.
            allowed = np.divide(distance_fraction * np.maximum(distances, earth_radius),
                                speeds, out=np.full_like(speeds, np.inf), where=speeds > 0)
            step = min(max_closeup_step, float(np.min(allowed)))
            return min(frame + max(step, epsilon * 10), float(upper), exit_, end_frame)
    return min(frame + normal_step, end_frame)


@dataclass
class Impact:
    """Kontaktzeit (in Stundenframes), Körperindizes und idealisierte Stoßgrößen."""
    frame: float
    pair: tuple[int, int]
    survivor: int
    absorbed: int
    contact: np.ndarray
    energy: float
    delta_v: np.ndarray
    relative_speed: float


@dataclass
class Trajectory:
    """Zeitgestempelte Physikzustände; nicht mehr aktive Körper werden NaN."""
    frames: np.ndarray
    positions: np.ndarray
    velocities: np.ndarray
    impacts: list[Impact]

    def at(self, frame):
        """Interpoliert zwischen tatsächlich berechneten, ungleich langen Schritten."""
        i = self.index(frame)
        if i == len(self.frames) - 1 or frame <= self.frames[i]:
            return self.positions[i].copy()
        f = (frame - self.frames[i]) / (self.frames[i + 1] - self.frames[i])
        return self.positions[i] + f * (self.positions[i + 1] - self.positions[i])

    def index(self, frame):
        """Index des letzten gespeicherten Zustands bis zum angefragten Zeitpunkt."""
        return int(np.clip(np.searchsorted(self.frames, frame, side='right') - 1,
                           0, len(self.frames) - 1))

    def absorbed_at(self, index, frame):
        """Ob ein Körper bis zu diesem Zeitpunkt aufgenommen wurde (nach Kontakt)."""
        return any(e.absorbed == index and frame > e.frame + 1e-10 for e in self.impacts)


def simulate_trajectory(bodies, N, dt, defense_actions=None, stop_on_impact=True):
    """Euler-Cromer mit adaptiven Unterzeitschritten und kontinuierlicher Kontaktprüfung.

    Die Stundenmarken bleiben für Impulse erhalten. Vorhersage der relativen
    geraden Strecke verhindert, dass ein großer Schritt einen Nahbereich
    überspringt. Innerhalb eines kleinen Schritts wird der erste Kontakt
    geometrisch bestimmt. Bei Weiterlauf verschmelzen Körper vollständig
    unelastisch; die Impulserhaltung bestimmt die neue Geschwindigkeit.
    Radius des größeren Körpers bleibt konstant (vereinfachtes Modell).
    Returns: Trajectory mit echten Zeitstempeln und Stoßereignissen.
    """
    from values import ADAPTIVE_STEPS
    if dt <= 0 or N < 0:
        raise ValueError('dt muss positiv und N darf nicht negativ sein.')
    names = {b.name: i for i, b in enumerate(bodies)}
    if len(names) != len(bodies):
        raise ValueError('Alle Körper benötigen eindeutige Namen.')
    initial = check_collision(bodies)
    if initial:
        raise ValueError(f'Ungültige Startposition: {initial[0]} und {initial[1]} berühren sich bereits.')
    actions = {}
    for a in defense_actions or []:
        k = a['frame']
        if int(k) != k or not 0 <= k <= N or a['target'] not in names:
            raise ValueError('Ungültiger Impulszeitpunkt oder Zielkörper.')
        if not np.isfinite(a['impulse']) or a['impulse'] < 0 or not np.isfinite(a['angle']):
            raise ValueError('Ungültiger Impulsbetrag oder Winkel.')
        actions.setdefault(int(k), []).append(a)
    r = np.array([b.r for b in bodies], dtype=float)
    v = np.array([b.v for b in bodies], dtype=float)
    mass = np.array([b.mass for b in bodies], dtype=float)
    rad = np.array([b.radius for b in bodies], dtype=float)
    active = np.ones(len(bodies), dtype=bool)
    frames, positions, velocities, impacts = [], [], [], []
    earth = names.get('Erde')
    sun = names.get('Sonne')
    t = 0.0

    def save(contact_index=None):
        """Speichert einen Zustand mit stabilen Körperindizes."""
        visible = active.copy()
        if contact_index is not None:
            visible[contact_index] = True
        rp, vp = r.copy(), v.copy()
        rp[~visible] = np.nan
        vp[~visible] = np.nan
        f = t / dt
        if frames and abs(f - frames[-1]) < 1e-12:
            frames[-1], positions[-1], velocities[-1] = f, rp, vp
        else:
            frames.append(f); positions.append(rp); velocities.append(vp)

    def apply_actions(k):
        """Wendet vorgemerkte Impulse nur auf noch existierende Körper an."""
        for a in actions.get(k, []):
            i = names[a['target']]
            if active[i]:
                a_rad = np.radians(a['angle'])
                v[i] += a['impulse'] / mass[i] * np.array([np.cos(a_rad), np.sin(a_rad)])

    def result():
        """Packt die gespeicherten Zeitreihen und aktualisiert die Körperobjekte."""
        for i, b in enumerate(bodies):
            b.r, b.v, b.mass = r[i].copy(), v[i].copy(), float(mass[i])
        return Trajectory(np.array(frames), np.array(positions), np.array(velocities), impacts)

    apply_actions(0)
    save()
    for k in range(1, N + 1):
        boundary = k * dt
        while t < boundary - 1e-7:
            ids = np.flatnonzero(active)
            a = np.zeros_like(r)
            # Nur aktive Körper erzeugen und erfahren Gravitation.
            for i in ids:
                others = ids[ids != i]
                if len(others):
                    d = r[others] - r[i]
                    norm = np.linalg.norm(d, axis=1)
                    a[i] = G * np.sum(mass[others, None] * d / norm[:, None]**3, axis=0)
            h = boundary - t
            # Vorhersage mit demselben Euler-Cromer-Schritt wie die Integration.
            if earth is not None and active[earth]:
                for i in ids:
                    if i == earth or i == sun:
                        continue
                    rel = r[i] - r[earth]
                    # Von außen nach innen: die nächste Stufe erst mit der
                    # bereits verkürzten Schrittweite vorhersagen.
                    for limit, small_h in reversed(ADAPTIVE_STEPS):
                        end = rel + (v[i] - v[earth] + (a[i] - a[earth]) * h) * h
                        if segment_radius_interval(rel, end, limit) is not None:
                            h = min(h, small_h)
            new_v = v + a * h
            new_r = r + new_v * h
            hit = None
            for p, i in enumerate(ids):
                for j in ids[p + 1:]:
                    interval = segment_radius_interval(r[j] - r[i], new_r[j] - new_r[i], rad[i] + rad[j])
                    if interval is not None and (hit is None or interval[0] < hit[0]):
                        hit = (interval[0], int(i), int(j))
            if hit is None:
                r, v = new_r, new_v
                t += h
                if abs(t - boundary) < 1e-7:
                    t = boundary
                    apply_actions(k)
                save()
                continue
            fraction, i, j = hit
            r += fraction * (new_r - r)
            v += fraction * (new_v - v)
            t += h * fraction
            survivor, absorbed = (i, j) if mass[i] >= mass[j] else (j, i)
            relative = v[absorbed] - v[survivor]
            speed = float(np.linalg.norm(relative))
            factor = mass[absorbed] / (mass[survivor] + mass[absorbed])
            delta_v = factor * relative
            direction = r[absorbed] - r[survivor]
            contact = direction / max(np.linalg.norm(direction), 1e-30) * rad[survivor]
            impacts.append(Impact(t / dt, (i, j), survivor, absorbed, contact,
                                  0.5 * mass[survivor] * factor * speed**2, delta_v.copy(), speed))
            if stop_on_impact:
                save()
                return result()
            # Impulsübertragung ohne Subtraktion fast gleicher großer Zahlen.
            v[survivor] += delta_v
            mass[survivor] += mass[absorbed]
            active[absorbed] = False
            save(absorbed)
            # Rest des Schritts wird mit der neuen Masse erneut integriert.
            if abs(t - boundary) < 1e-7:
                t = boundary
                apply_actions(k)
                save(absorbed)
    return result()


def trajectory_windows(trajectory, radius, dt, afterglow=0.0):
    """Nahbereichsintervalle auf der realen Zeitachse, inklusive Aufschlaganzeige."""
    frames = trajectory.frames
    intervals = []
    for i in range(2, trajectory.positions.shape[1]):
        relative = trajectory.positions[:, i] - trajectory.positions[:, 1]
        for k in range(len(frames) - 1):
            if not np.isfinite(relative[k:k+2]).all():
                continue
            # Schnelle Vorauswahl für weit entfernte Schritte.
            if min(np.linalg.norm(relative[k]), np.linalg.norm(relative[k+1])) > radius + np.linalg.norm(relative[k+1]-relative[k]):
                continue
            window = segment_radius_interval(relative[k], relative[k+1], radius)
            if window is not None:
                a, b = window
                width = frames[k+1] - frames[k]
                intervals.append((frames[k] + a*width, frames[k] + b*width))
    for event in trajectory.impacts:
        if 1 in event.pair and max(event.pair) >= 2:
            intervals.append((event.frame, min(frames[-1], event.frame + afterglow/dt)))
    merged = []
    for a, b in sorted(intervals):
        if merged and a <= merged[-1][1] + 1e-9:
            merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
        else:
            merged.append((a, b))
    return merged


def trajectory_next_frame(trajectory, frame, normal_step, windows, earth_radius,
                          max_closeup_step, distance_fraction, dt):
    """Zeitlupe auf echter Zeitachse; erzwingt jedes sichtbare Kontaktbild."""
    from values import IMPACT_AFTERGLOW_SECONDS
    end = trajectory.frames[-1]
    step = normal_step
    for a, b in windows:
        if frame < a - 1e-9:
            return min(frame + step, a, end)
        if frame < b - 1e-9:
            current = trajectory.at(frame)
            k = trajectory.index(frame)
            relative = current[2:] - current[1]
            vel = trajectory.velocities[k, 2:] - trajectory.velocities[k, 1]
            distances = np.linalg.norm(relative, axis=1)
            speed = np.linalg.norm(vel, axis=1)
            allowed = distance_fraction * np.maximum(distances, earth_radius) / np.maximum(speed, 1e-30) / dt
            valid = allowed[np.isfinite(allowed)]
            step = min(max_closeup_step, float(np.min(valid)) if len(valid) else 3/dt)
            for event in trajectory.impacts:
                if event.frame - 1e-9 <= frame < event.frame + IMPACT_AFTERGLOW_SECONDS/dt - 1e-9:
                    step = min(step, 3/dt)
            upcoming = [e.frame for e in trajectory.impacts if frame + 1e-9 < e.frame <= b]
            return min(frame + max(step, 1e-8), b, end, *upcoming) if upcoming else min(frame + max(step, 1e-8), b, end)
    return min(frame + step, end)
