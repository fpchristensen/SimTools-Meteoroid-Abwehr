"""Qt-Designer-Oberfläche für die Meteoroidenabwehr.

Die GUI wird aus mainwindow.ui geladen. Alle Buttons, Regler und
Auswahlfelder steuern dasselbe eingebettete Matplotlib-Diagramm.
"""

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PyQt6 import QtCore, QtWidgets, uic
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from classes_functions import (
    CelestialBody, orbital_data, simulate_system, start_defense
)
from values import (
    N, dt, a_Ellipse, e_Ellipse,
    m_Erde, m_Sonne, radius_Erde, radius_Sonne,
    m_Meteorid1, radius_Meteorid1, r_Meteorid1, v_Meteorid1,
    ABWEHR_METHODEN,
)


UI_DATEI = Path(__file__).with_name("mainwindow.ui")

# Gegenbeispiel zum Kollisionsszenario: derselbe Startort, anderer vy-Wert.
VORBEIFLUG_V = [v_Meteorid1[0], -v_Meteorid1[1]]


@dataclass
class AsteroidSettings:
    """Editierbare Anfangswerte genau eines Asteroiden in der GUI."""
    name: str
    scenario: str = "Vorbeiflug"
    profile: str = "Klein und Leicht"
    diameter_m: float = 2 * radius_Meteorid1
    mass_kg: float = m_Meteorid1
    position: np.ndarray = field(
        default_factory=lambda: np.array(r_Meteorid1, dtype=float)
    )
    velocity: np.ndarray = field(
        default_factory=lambda: np.array(VORBEIFLUG_V, dtype=float)
    )


class SimulationWindow(QtWidgets.QMainWindow):
    """Verbindet die Qt-Widgets mit der Physiksimulation und Animation."""

    def __init__(self):
        super().__init__()
        uic.loadUi(str(UI_DATEI), self)
        self.setWindowTitle("SimTools – Meteoroidenabwehr")
        self.resize(1360, 850)

        self.asteroids = [AsteroidSettings(name="Meteoroid 1")]
        self.positions = None
        self.bodies = []
        self.collision = None
        self.baseline_collision = None
        self.frame = 0
        self.follow_mode = "Sonne"  # Sonne, Erde, Asteroid
        self.mode_text = "Ohne Abwehr"
        self.playing = False
        self.trajectory_lines = []
        self.points = []

        # Matplotlib als echtes Qt-Widget in den Platzhalter 'widget'.
        self.figure = Figure(figsize=(8, 6))
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self.plot_layout = QtWidgets.QVBoxLayout(self.widget)
        self.plot_layout.setContentsMargins(0, 0, 0, 0)
        self.plot_layout.addWidget(self.canvas)

        # Qt-Timer statt zweitem Fenster/FuncAnimation.
        self.animation_timer = QtCore.QTimer(self)
        self.animation_timer.setInterval(45)
        self.animation_timer.timeout.connect(self.next_frame)

        # Berechnungen beim Schieben nicht nach jedem einzelnen Pixel neu starten.
        self.rebuild_timer = QtCore.QTimer(self)
        self.rebuild_timer.setSingleShot(True)
        self.rebuild_timer.timeout.connect(self.calculate_baseline)

        self.setup_widgets()
        self.connect_signals()
        self.listWidget.addItem("Meteoroid 1")
        self.listWidget.setCurrentRow(0)
        self.show_selected_asteroid()
        self.calculate_baseline()

    def setup_widgets(self):
        """Setzt sinnvolle Bereiche und Einheiten für die Designer-Widgets."""
        # Das GUI-Feld für die Masse zeigt Werte in Einheiten 10^10 kg.
        # Dadurch kann der QDoubleSpinBox große Massen gut darstellen.
        self.Masse.setText("Masse (× 10¹⁰ kg)")
        self.GewichtEingabe.setRange(0.001, 1_000_000.0)
        self.GewichtEingabe.setDecimals(3)
        self.GewichtEingabe.setSingleStep(0.1)

        self.Durchmesser.setText("Durchmesser (m)")
        self.GroesseEingabe.setRange(1.0, 100_000.0)
        self.GroesseEingabe.setDecimals(1)
        self.GroesseEingabe.setSingleStep(10.0)

        self.GeschwindigkeitsRichtung.setRange(0, 359)
        self.GeschwindigkeitsRichtung.setWrapping(True)
        # Sliderwert / 100 entspricht km/s; 2700 = 27,00 km/s.
        self.GeschwindigkeitRegler.setRange(0, 8000)
        self.GeschwindigkeitRegler.setSingleStep(1)

        self.ImpulsrichtungRegler.setRange(0, 359)
        self.ImpulsrichtungRegler.setWrapping(True)
        self.EigeneImpulsstaerke.setRange(0, 1000)
        self.EigeneImpulsstaerke.setValue(100)
        self.EingriffszeitpunktRegler.setRange(0, N - 1)
        self.EingriffszeitpunktRegler.setValue(20 * 24)  # zunächst Tag 20

        self.ErdeFolgenButton.setCheckable(True)
        self.AsteroidFolgenButton.setCheckable(True)
        self.EigeneImpulsstaerke.setEnabled(False)
        self.update_impulse_text()
        self.update_time_text()

    def connect_signals(self):
        """Verbindet alle Steuerelemente der .ui-Datei mit Python-Funktionen."""
        # Linke Seite: Asteroiden konfigurieren.
        self.listWidget.currentRowChanged.connect(self.show_selected_asteroid)
        self.SzenarioAuswahl.currentTextChanged.connect(self.change_scenario)
        self.AsteroidenAuswahl.currentTextChanged.connect(self.change_profile)
        self.GroesseEingabe.valueChanged.connect(self.change_diameter)
        self.GewichtEingabe.valueChanged.connect(self.change_mass)
        self.GeschwindigkeitsRichtung.valueChanged.connect(self.change_direction)
        self.GeschwindigkeitRegler.valueChanged.connect(self.change_speed)
        self.AsteroidHinzufuegen.clicked.connect(self.add_asteroid)

        # Mitte: Simulation abspielen/pausieren und Kamera umstellen.
        self.PlayButton.clicked.connect(self.toggle_play)
        self.StopButton.clicked.connect(self.stop_playback)
        self.ZurueckButton.clicked.connect(self.rewind)
        self.ErdeFolgenButton.clicked.connect(
            lambda: self.toggle_follow("Erde")
        )
        self.AsteroidFolgenButton.clicked.connect(
            lambda: self.toggle_follow("Asteroid")
        )

        # Rechte Seite: Abwehr auswählen und einmaligen Impuls anwenden.
        self.ImpulsstaerkeAuswahl.currentIndexChanged.connect(
            self.update_impulse_text
        )
        self.EigeneImpulsstaerke.valueChanged.connect(
            self.update_impulse_text
        )
        self.ImpulsrichtungRegler.valueChanged.connect(
            self.update_angle_text
        )
        self.EingriffszeitpunktRegler.valueChanged.connect(
            self.update_time_text
        )
        self.AbwehrDurchfuehrung.clicked.connect(self.run_defense)

    def selected_asteroid(self):
        """Liefert den in der Liste markierten Asteroiden oder None."""
        index = self.listWidget.currentRow()
        if 0 <= index < len(self.asteroids):
            return self.asteroids[index]
        return None

    @staticmethod
    def quietly_set(widget, method, value):
        """Setzt Widgetwerte, ohne dabei weitere Signale auszulösen."""
        previous = widget.blockSignals(True)
        getattr(widget, method)(value)
        widget.blockSignals(previous)

    def show_selected_asteroid(self, *_):
        """Zeigt die gespeicherten Werte des markierten Asteroiden links an."""
        spec = self.selected_asteroid()
        if spec is None:
            return
        self.quietly_set(self.SzenarioAuswahl, "setCurrentText", spec.scenario)
        self.quietly_set(self.AsteroidenAuswahl, "setCurrentText", spec.profile)
        self.quietly_set(self.GroesseEingabe, "setValue", spec.diameter_m)
        self.quietly_set(self.GewichtEingabe, "setValue", spec.mass_kg / 1e10)
        angle = int(round(np.degrees(np.arctan2(
            spec.velocity[1], spec.velocity[0]
        )))) % 360
        speed_hundredths = round(np.linalg.norm(spec.velocity) / 10.0)
        self.quietly_set(self.GeschwindigkeitsRichtung, "setValue", angle)
        self.quietly_set(
            self.GeschwindigkeitRegler, "setValue", speed_hundredths
        )
        editable = spec.profile == "Eigener Asteroid"
        self.GroesseEingabe.setEnabled(editable)
        self.GewichtEingabe.setEnabled(editable)
        self.update_velocity_text()
        # Beim Hinzufügen eines Körpers enthält der alte Verlauf noch weniger
        # Körper; erst nach der Neuberechnung wird erneut gezeichnet.
        if (self.positions is not None
                and self.positions.shape[1] == len(self.asteroids) + 2):
            self.draw_frame(self.frame)

    def change_scenario(self, scenario):
        """Wechselt zwischen den konkreten Bahnen Vorbeiflug und Kollision."""
        spec = self.selected_asteroid()
        if spec is None:
            return
        spec.scenario = scenario
        if scenario == "Kollision":
            spec.velocity = np.array(v_Meteorid1, dtype=float)
        else:
            spec.velocity = np.array(VORBEIFLUG_V, dtype=float)
        self.show_selected_asteroid()
        self.queue_baseline()

    def change_profile(self, profile):
        """Wählt Standardmasse/-durchmesser oder erlaubt eigene Werte."""
        spec = self.selected_asteroid()
        if spec is None:
            return
        spec.profile = profile
        if profile == "Klein und Leicht":
            spec.mass_kg = m_Meteorid1
            spec.diameter_m = 2 * radius_Meteorid1
        elif profile == "Groß und Schwer":
            spec.mass_kg = 1.0e13
            spec.diameter_m = 1000.0
        self.show_selected_asteroid()
        self.queue_baseline()

    def change_diameter(self, diameter):
        """Übernimmt den Durchmesser des selbst definierten Asteroiden."""
        spec = self.selected_asteroid()
        if spec and spec.profile == "Eigener Asteroid":
            spec.diameter_m = diameter
            self.queue_baseline()

    def change_mass(self, mass_units):
        """Übernimmt die Masse; GUI-Einheit ist 10^10 kg."""
        spec = self.selected_asteroid()
        if spec and spec.profile == "Eigener Asteroid":
            spec.mass_kg = mass_units * 1.0e10
            self.queue_baseline()

    def update_velocity_text(self):
        """Zeigt Richtung in Grad und Betrag in km/s an."""
        spec = self.selected_asteroid()
        if spec is None:
            return
        angle = np.degrees(np.arctan2(
            spec.velocity[1], spec.velocity[0]
        )) % 360
        speed = np.linalg.norm(spec.velocity) / 1000.0
        self.Geschwindigkeit.setText(
            f"Geschwindigkeitsrichtung: {angle:.1f}°"
        )
        self.Geschwindigkeitsstaerke.setText(
            f"Geschwindigkeitsstärke: {speed:.2f} km/s"
        )

    def change_direction(self, angle):
        """Dreht nur den Geschwindigkeitsvektor, Betrag bleibt erhalten."""
        spec = self.selected_asteroid()
        if spec is None:
            return
        speed = np.linalg.norm(spec.velocity)
        rad = np.radians(angle)
        spec.velocity = speed * np.array([np.cos(rad), np.sin(rad)])
        self.update_velocity_text()
        self.queue_baseline()

    def change_speed(self, slider_value):
        """Ändert nur den Betrag des Geschwindigkeitsvektors."""
        spec = self.selected_asteroid()
        if spec is None:
            return
        angle = np.arctan2(spec.velocity[1], spec.velocity[0])
        speed = slider_value * 10.0  # 1 Schieberpunkt = 10 m/s
        spec.velocity = speed * np.array([np.cos(angle), np.sin(angle)])
        self.update_velocity_text()
        self.queue_baseline()

    def add_asteroid(self):
        """Fügt einen weiteren Asteroiden mit eigener Startposition hinzu."""
        if len(self.asteroids) >= 5:
            self.statusbar.showMessage(
                "Für diese Demonstration sind höchstens fünf Asteroiden vorgesehen."
            )
            return
        base = self.selected_asteroid() or self.asteroids[0]
        index = len(self.asteroids)
        # Abstand zum ersten Startort verhindert eine Anfangskollision.
        # Nur Asteroid 1 ist für die voreingestellte Tag-80-Kollision kalibriert.
        offset = np.array([-3.5e10 * index, 2.5e10 * index])
        new = AsteroidSettings(
            name=f"Meteoroid {index + 1}",
            scenario=base.scenario,
            profile=base.profile,
            diameter_m=base.diameter_m,
            mass_kg=base.mass_kg,
            position=np.array(r_Meteorid1, dtype=float) + offset,
            velocity=base.velocity.copy(),
        )
        self.asteroids.append(new)
        self.listWidget.addItem(new.name)
        self.listWidget.setCurrentRow(index)
        self.queue_baseline()

    def create_bodies(self):
        """Erzeugt neue Himmelskörper, damit jeder Versuch bei t=0 beginnt."""
        sun = CelestialBody(
            "Sonne", m_Sonne, radius_Sonne, [0, 0], [0, 0]
        )
        r_earth, v_earth = orbital_data(a_Ellipse, e_Ellipse, m_Sonne)
        earth = CelestialBody(
            "Erde", m_Erde, radius_Erde, r_earth, v_earth
        )
        result = [sun, earth]
        for spec in self.asteroids:
            result.append(CelestialBody(
                spec.name,
                spec.mass_kg,
                spec.diameter_m / 2,
                spec.position.copy(),
                spec.velocity.copy(),
            ))
        return result

    def queue_baseline(self):
        """Plant eine Neuberechnung nach Änderungen am Asteroiden."""
        self.stop_playback()
        self.rebuild_timer.start(180)

    def calculate_baseline(self):
        """Berechnet ohne Abwehr; legt den Verlauf für Play fest."""
        self.stop_playback()
        try:
            bodies = self.create_bodies()
            positions, _, collision = simulate_system(bodies, N, dt)
        except ValueError as exc:
            self.positions = None
            self.bodies = []
            self.ax.clear()
            self.canvas.draw_idle()
            self.statusbar.showMessage(str(exc))
            return
        self.bodies = bodies
        self.positions = positions
        self.collision = collision
        self.baseline_collision = collision
        self.mode_text = "Ohne Abwehr"
        self.frame = 0
        self.EingriffszeitpunktRegler.setMaximum(
            max(0, len(positions) - 2)
        )
        self.prepare_plot()
        self.show_status_for_trajectory("Ausgangsversuch")

    def prepare_plot(self):
        """Erstellt Bahnen und Markierungen für alle Körper im Qt-Canvas."""
        if self.positions is None:
            return
        self.ax.clear()
        self.trajectory_lines.clear()
        self.points.clear()
        colors = ["orange", "royalblue", "gray", "forestgreen", "firebrick",
                  "purple", "saddlebrown"]

        for i, body in enumerate(self.bodies):
            color = colors[i % len(colors)]
            # Schwache Linie: vollständige errechnete Flugbahn als Vorschau.
            self.ax.plot(
                self.positions[:, i, 0], self.positions[:, i, 1],
                color=color, alpha=0.16, linewidth=0.8,
            )
            line, = self.ax.plot([], [], color=color, linewidth=1.5)
            point, = self.ax.plot(
                [], [], "o", color=color, markersize=11 if i == 0 else 7,
                label=body.name,
            )
            self.trajectory_lines.append(line)
            self.points.append(point)

        self.ax.set_aspect("equal", adjustable="box")
        self.ax.set_xlabel("x (m)")
        self.ax.set_ylabel("y (m)")
        self.ax.legend(loc="upper right", fontsize=8)
        self.ax.grid(True, alpha=0.2)
        self.figure.tight_layout(pad=1.6)
        self.draw_frame(0)

    def draw_frame(self, frame):
        """Zeichnet den ausgewählten Simulationsschritt und verfolgt ggf. einen Körper."""
        if self.positions is None:
            return
        frame = max(0, min(int(frame), len(self.positions) - 1))
        self.frame = frame
        for i, (line, point) in enumerate(zip(self.trajectory_lines, self.points)):
            line.set_data(
                self.positions[:frame + 1, i, 0],
                self.positions[:frame + 1, i, 1],
            )
            point.set_data(
                [self.positions[frame, i, 0]],
                [self.positions[frame, i, 1]],
            )

        if self.follow_mode == "Erde":
            center = self.positions[frame, 1]
            half_width = 2.0e10
        elif self.follow_mode == "Asteroid":
            asteroid_index = max(0, self.listWidget.currentRow()) + 2
            center = self.positions[frame, asteroid_index]
            half_width = 2.0e10
        else:
            center = np.array([0.0, 0.0])
            half_width = max(
                1.6e11, float(np.max(np.abs(self.positions))) * 1.08
            )
        self.ax.set_xlim(center[0] - half_width, center[0] + half_width)
        self.ax.set_ylim(center[1] - half_width, center[1] + half_width)

        day = frame * dt / 86400
        self.ax.set_title(f"{self.mode_text} – Tag {day:.2f}")
        if frame == len(self.positions) - 1:
            if self.collision:
                self.ax.set_title(
                    f"{self.mode_text} – Kollision an Tag {day:.2f}\n"
                    f"{self.collision[0]} mit {self.collision[1]}"
                )
            else:
                self.ax.set_title(f"{self.mode_text} – Ende ohne Kollision")
        self.canvas.draw_idle()

    def show_status_for_trajectory(self, label):
        """Zeigt den berechneten Kollisionsausgang in der Statusleiste."""
        if self.positions is None:
            return
        if self.collision:
            day = (len(self.positions) - 1) * dt / 86400
            self.statusbar.showMessage(
                f"{label}: {self.collision[0]} trifft {self.collision[1]} "
                f"an Tag {day:.2f}."
            )
        else:
            self.statusbar.showMessage(
                f"{label}: In {N * dt / 86400:.1f} Tagen keine Kollision."
            )

    def toggle_play(self):
        """Startet oder pausiert die Anzeige des bereits berechneten Verlaufs."""
        if self.playing:
            self.stop_playback()
            return
        if self.rebuild_timer.isActive():
            self.rebuild_timer.stop()
            self.calculate_baseline()
        if self.positions is None:
            return
        if self.frame >= len(self.positions) - 1:
            self.frame = 0
        self.playing = True
        self.PlayButton.setText("Pause")
        self.animation_timer.start()

    def stop_playback(self):
        """Pausiert die Wiedergabe, ohne das aktuelle Bild zu verwerfen."""
        self.animation_timer.stop()
        self.playing = False
        self.PlayButton.setText("Play")

    def rewind(self):
        """Stoppt und springt zu Tag 0 des aktuellen Verlaufs zurück."""
        self.stop_playback()
        self.draw_frame(0)

    def next_frame(self):
        """Wird periodisch von QTimer aufgerufen und zeichnet das nächste Bild."""
        if self.positions is None:
            self.stop_playback()
            return
        last = len(self.positions) - 1
        next_index = min(self.frame + 6, last)
        self.draw_frame(next_index)
        if next_index >= last:
            self.stop_playback()
            self.show_status_for_trajectory(self.mode_text)

    def toggle_follow(self, target):
        """Schaltet Erd-/Asteroidenverfolgung oder Sonnenansicht ein."""
        self.follow_mode = "Sonne" if self.follow_mode == target else target
        self.ErdeFolgenButton.setChecked(self.follow_mode == "Erde")
        self.AsteroidFolgenButton.setChecked(self.follow_mode == "Asteroid")
        self.draw_frame(self.frame)

    def update_impulse_text(self, *_):
        """Zeigt den tatsächlich verwendeten Impulsbetrag in N·s."""
        own = self.ImpulsstaerkeAuswahl.currentIndex() == 3
        self.EigeneImpulsstaerke.setEnabled(own)
        impulse = self.selected_impulse()
        self.Impulsstaerke.setText(f"Impulsstärke: {impulse:.2e} N·s")

    def selected_impulse(self):
        """Ordnet den vier Einträgen die Impulsbeträge zu."""
        option = self.ImpulsstaerkeAuswahl.currentIndex()
        if option == 0:
            return ABWEHR_METHODEN["Explosion"]
        if option == 1:
            return ABWEHR_METHODEN["Rakete"]
        if option == 2:
            return ABWEHR_METHODEN["Satellitenstoß"]
        return self.EigeneImpulsstaerke.value() * 1.0e8

    def update_angle_text(self, *_):
        """Beschriftet den Impulswinkel (mathematisch ab positiver x-Achse)."""
        self.Impulsrichtung.setText(
            f"Impulsrichtung: {self.ImpulsrichtungRegler.value()}°"
        )

    def update_time_text(self, *_):
        """Wandelt den Zeitregler von Simulationsschritten in Tage um."""
        frame = self.EingriffszeitpunktRegler.value()
        day = frame * dt / 86400
        self.Eingriffszeitpunkt.setText(
            f"Eingriffszeitpunkt: Tag {day:.2f}"
        )

    def run_defense(self):
        """Berechnet die Abwehr neu und spielt den neuen Verlauf ab Tag 0 ab."""
        spec = self.selected_asteroid()
        if spec is None or self.positions is None:
            self.statusbar.showMessage("Bitte einen Asteroiden auswählen.")
            return
        self.rebuild_timer.stop()
        self.stop_playback()
        frame = self.EingriffszeitpunktRegler.value()
        angle = self.ImpulsrichtungRegler.value()
        impulse = self.selected_impulse()
        try:
            positions, collision = start_defense(
                frame, angle, impulse, spec.name, self.create_bodies, N, dt
            )
        except ValueError as exc:
            self.statusbar.showMessage(str(exc))
            return
        self.bodies = self.create_bodies()
        self.positions = positions
        self.collision = collision
        self.mode_text = f"Mit Abwehr ({spec.name})"
        self.prepare_plot()
        self.show_status_for_trajectory("Abwehrversuch")
        self.toggle_play()
