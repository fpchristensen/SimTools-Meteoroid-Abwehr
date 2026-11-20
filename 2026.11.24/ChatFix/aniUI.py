"""Komplette Qt-Oberfläche und Matplotlib-Animation für SimTools.

Die Widgets stammen aus der weiterhin in Qt Designer bearbeitbaren
mainwindow.ui. Die Physik wird aus classes_functions.py aufgerufen;
Anfangswerte und Katalogdaten kommen aus values.py.
"""

from pathlib import Path

import numpy as np
from PyQt6 import QtCore, QtWidgets, uic
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Circle, FancyArrowPatch

from classes_functions import (
    MeteoroidSettings, catalog_settings, profiles,
    simulate_trajectory, create_bodies as create_simulation_bodies,
    trajectory_windows, trajectory_next_frame,
)
from values import (
    N, dt, r_Meteorid1, v_Meteorid1, ABWEHR_METHODEN, PLAYBACK_SPEEDS,
    CLOSEUP_DISTANCE, CLOSEUP_MAX_FRAME_STEP, CLOSEUP_DISTANCE_FRACTION,
    ANIMATION_INTERVAL_MS, IMPACT_AFTERGLOW_SECONDS,
)


UI_DATEI = Path(__file__).with_name("mainwindow.ui")

# Variante zum Kollisionsszenario: gleicher Startort, anderes v_y.
VORBEIFLUG_V = [v_Meteorid1[0], -v_Meteorid1[1]]


class SimulationWindow(QtWidgets.QMainWindow):
    """Verbindet die Qt-Designer-Widgets mit den Physikfunktionen und der Animation.

    Attributes:
        meteoroids (list[MeteoroidSettings]): Derzeit konfigurierte Meteoroiden.
        defense_actions (list[dict]): Vorgemerkte Impulsaktionen.
        baseline_positions (np.ndarray | None): Referenzbahn ohne Abwehr.
        positions (np.ndarray | None): Aktuell animierter Positionsverlauf.
        frame (float): Derzeit sichtbarer Zeitschritt (ggf. interpoliert).
        follow_mode (str): Sonnen-, Erd- oder Meteoroidenverfolgung.
        zoom_scale (float): Zoomfaktor der Matplotlib-Kamera.
    """

    def __init__(self):
        """Lädt das Designer-Fenster und initialisiert Meteoroiden, Zeichenflaeche, Steuerung und Timer.
        """
        super().__init__()
        uic.loadUi(str(UI_DATEI), self)
        self.setWindowTitle("SimTools – Meteoroidenabwehr")
        self.resize(1360, 850)

        # Das bisherige Beispiel an Tag 80 ist im neuen Katalog Leicht 03.
        self.meteoroids = [catalog_settings("leicht_03", "Meteoroid 1")]
        # Laufende Nummer statt Listenlänge: keine doppelten Standardnamen
        # nach dem Löschen und erneuten Hinzufügen.
        self.next_meteoroid_number = 2
        self.positions = None
        self.baseline_positions = None
        self.trajectory = None
        self.baseline_trajectory = None
        self.closeup_enabled = True
        self.stop_on_impact = True
        self.bodies = []
        self.collision = None
        self.baseline_collision = None
        self.frame = 0
        self.follow_mode = "Sonne"  # Sonne, Erde, Meteoroid
        self.mode_text = "Ohne Abwehr"
        # Gespeicherte Abwehraktionen bleiben beim Wechsel des Meteoroiden
        # bestehen. Play spielt sie gemeinsam in EINER Simulation ab.
        self.defense_actions = []
        self.playback_restart_requested = False
        self.preview_arrow = None
        self._pan_anchor_px = None
        self._pan_initial_offset = None
        # Der Zoom bleibt beim Abspielen und bei Kameraverfolgung erhalten.
        self.zoom_scale = 1.0
        self.pan_offset = np.zeros(2, dtype=float)
        # 1× zeigt sechs simulierte Stunden pro QTimer-Tick.
        self.playback_speed = 1.0
        self.playing = False
        self.trajectory_lines = []
        self.points = []
        self.impact_markers = []
        self.encounter_windows = []
        self.display_end_frame = 0.0
        self.closeup_ax = None
        self.comparison_ax = None
        self.overview_position = None
        self.closeup_active = False

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
        self.canvas.mpl_connect("scroll_event", self.zoom_with_wheel)
        self.canvas.mpl_connect("button_press_event", self.on_mouse_press)
        self.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)
        self.canvas.mpl_connect("button_release_event", self.on_mouse_release)

        # Qt-Timer statt zweitem Fenster/FuncAnimation.
        self.animation_timer = QtCore.QTimer(self)
        self.animation_timer.setInterval(ANIMATION_INTERVAL_MS)
        self.animation_timer.timeout.connect(self.next_frame)

        # Berechnungen beim Schieben nicht nach jedem einzelnen Pixel neu starten.
        self.rebuild_timer = QtCore.QTimer(self)
        self.rebuild_timer.setSingleShot(True)
        self.rebuild_timer.timeout.connect(self.calculate_baseline)

        self.setup_widgets()
        self.connect_signals()
        self.listWidget.addItem("Meteoroid 1")
        self.listWidget.setCurrentRow(0)
        self.show_selected_meteoroid()
        self.calculate_baseline()

    def setup_widgets(self):
        """Setzt sinnvolle Bereiche und Einheiten für die Designer-Widgets.
        """
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

        # Das ist ein echter Auswahl-Button mit fünf Geschwindigkeitsstufen.
        # Der Zeitabstand dt und die Physik selbst werden NICHT verändert.
        self.speed_menu = QtWidgets.QMenu(self)
        self.speed_actions = {}
        for speed in PLAYBACK_SPEEDS:
            text = f"{speed:g}".replace(".", ",") + "×"
            action = self.speed_menu.addAction(text)
            action.setCheckable(True)
            action.triggered.connect(
                lambda checked=False, value=speed: self.set_playback_speed(value)
            )
            self.speed_actions[speed] = action
        self.SimulationTempoButton.setMenu(self.speed_menu)
        self.set_playback_speed(1.0)

        self.ErdeFolgenButton.setCheckable(True)
        self.MeteoroidFolgenButton.setCheckable(True)
        self.EigeneImpulsstaerke.setEnabled(False)
        self.update_impulse_text()
        self.update_time_text()
        self.MeteoroidNameEingabe.setMaxLength(40)
        self.MeteoroidNameEingabe.setPlaceholderText("Name des Meteoroiden")
        self.MeteoroidEntfernen.setEnabled(True)
        self.AbwehrDurchfuehrung.setText("Abwehr vormerken")
        self.AbwehrDurchfuehrung.setToolTip(
            "Speichert den Impuls. Mit Play werden alle Abwehren abgespielt."
        )
        self.GeplanteAbwehren.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        self.refresh_defense_queue()
        self.ZoomHinweis.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.ZoomHinweis.setStyleSheet("color: gray; font-size: 11px;")
        self.update_angle_text()

    def connect_signals(self):
        """Verbindet alle Steuerelemente der .ui-Datei mit Python-Funktionen.
        """
        # Linke Seite: Meteoroiden konfigurieren.
        self.listWidget.currentRowChanged.connect(self.show_selected_meteoroid)
        # Enter übernimmt den Namen. Beim einfachen Wechseln der Auswahl
        # wird noch nicht bestätigter Text wieder durch den echten Namen ersetzt.
        self.MeteoroidNameEingabe.returnPressed.connect(self.rename_meteoroid)
        self.SzenarioAuswahl.currentTextChanged.connect(self.change_scenario)
        self.MeteoroidenAuswahl.currentTextChanged.connect(self.change_profile)
        self.KatalogAuswahl.currentIndexChanged.connect(self.change_catalog)
        self.GroesseEingabe.valueChanged.connect(self.change_diameter)
        self.GewichtEingabe.valueChanged.connect(self.change_mass)
        self.GeschwindigkeitsRichtung.valueChanged.connect(self.change_direction)
        self.GeschwindigkeitRegler.valueChanged.connect(self.change_speed)
        self.MeteoroidHinzufuegen.clicked.connect(self.add_meteoroid)
        self.MeteoroidEntfernen.clicked.connect(self.remove_meteoroid)

        # Mitte: Simulation abspielen/pausieren und Kamera umstellen.
        self.PlayButton.clicked.connect(self.toggle_play)
        self.StopButton.clicked.connect(self.stop_playback)
        self.CloseupButton.toggled.connect(self.toggle_closeup)
        self.ImpactStopButton.toggled.connect(self.toggle_impact_stop)
        self.ZurueckButton.clicked.connect(self.rewind)
        self.ErdeFolgenButton.clicked.connect(
            lambda: self.toggle_follow("Erde")
        )
        self.MeteoroidFolgenButton.clicked.connect(
            lambda: self.toggle_follow("Meteoroid")
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
        self.AbwehrEntfernen.clicked.connect(self.remove_defense)
        self.AlleAbwehrenLoeschen.clicked.connect(self.clear_defenses)

    def selected_meteoroid(self):
        """Liefert den in der Liste markierten Meteoroiden oder None.

        Returns:
            MeteoroidSettings | None: Markierter Meteoroid oder None bei leerer Auswahl.
        """
        index = self.listWidget.currentRow()
        if 0 <= index < len(self.meteoroids):
            return self.meteoroids[index]
        return None

    @staticmethod
    def quietly_set(widget, method, value):
        """Setzt Widgetwerte, ohne dabei weitere Signale auszulösen.

        Args:
            widget (QWidget): Das zu verändernde Qt-Widget.
            method (str): Name einer Setter-Methode, beispielsweise setValue.
            value (object): Neuer Wert für diese Methode.
        """
        previous = widget.blockSignals(True)
        getattr(widget, method)(value)
        widget.blockSignals(previous)

    def show_selected_meteoroid(self, *_):
        """Zeigt die gespeicherten Werte des markierten Meteoroiden links an.

        Args:
            *_ (object): Nicht verwendete Qt-Signalargumente.
        """
        spec = self.selected_meteoroid()
        has_selection = spec is not None
        # Auch wenn alle Meteoroiden gelöscht sind, bleibt die GUI stabil.
        for widget in (self.MeteoroidNameEingabe, self.SzenarioAuswahl,
                       self.MeteoroidenAuswahl, self.MeteoroidFolgenButton):
            widget.setEnabled(has_selection)
        self.MeteoroidEntfernen.setEnabled(has_selection)
        self.MeteoroidHinzufuegen.setEnabled(len(self.meteoroids) < 5)
        if spec is None:
            self.quietly_set(self.MeteoroidNameEingabe, "setText", "")
            self.KatalogAuswahl.setEnabled(False)
            self.KatalogAuswahl.clear()
            for widget in (self.GroesseEingabe, self.GewichtEingabe,
                           self.GeschwindigkeitsRichtung, self.GeschwindigkeitRegler):
                widget.setEnabled(False)
            self.Geschwindigkeit.setText("Geschwindigkeitsrichtung")
            self.Geschwindigkeitsstaerke.setText("Geschwindigkeitsstärke")
            self.update_impulse_text()
            return
        self.quietly_set(self.MeteoroidNameEingabe, "setText", spec.name)
        self.quietly_set(self.SzenarioAuswahl, "setCurrentText", spec.scenario)
        self.quietly_set(self.MeteoroidenAuswahl, "setCurrentText", spec.profile)
        self.populate_catalog(spec)
        self.quietly_set(self.GroesseEingabe, "setValue", spec.diameter_m)
        self.quietly_set(self.GewichtEingabe, "setValue", spec.mass_kg / 1e10)
        angle = int(round(270 - np.degrees(np.arctan2(
            spec.velocity[1], spec.velocity[0]
        )))) % 360
        speed_hundredths = round(np.linalg.norm(spec.velocity) / 10.0)
        self.quietly_set(self.GeschwindigkeitsRichtung, "setValue", angle)
        self.quietly_set(
            self.GeschwindigkeitRegler, "setValue", speed_hundredths
        )
        editable = spec.profile == "Eigener Meteoroid"
        # Katalogbahnen sind absichtlich unveränderlich, damit sie
        # einzeln sicher mit der Erde kollidieren.
        self.SzenarioAuswahl.setEnabled(editable)
        self.GroesseEingabe.setEnabled(editable)
        self.GewichtEingabe.setEnabled(editable)
        # Vorgegebene Profile besitzen feste Geschwindigkeiten.
        # Nur beim eigenen Meteoroiden sind beide Regler aktiv.
        self.GeschwindigkeitsRichtung.setEnabled(editable)
        self.GeschwindigkeitRegler.setEnabled(editable)
        self.update_velocity_text()
        self.update_impulse_text()
        # Zeigt beim Wechsel auf den zweiten Meteoroiden dessen Ort zur
        # gewählten Abwehrzeit, statt den vorigen weiter anzuzeigen.
        if (not self.playing and self.positions is not None
                and self.positions.shape[1] == len(self.meteoroids) + 2):
            self.show_preview_time()
        # Beim Hinzufügen eines Körpers enthält der alte Verlauf noch weniger
        # Körper; erst nach der Neuberechnung wird erneut gezeichnet.
        if (self.positions is not None
                and self.positions.shape[1] == len(self.meteoroids) + 2):
            self.draw_frame(self.frame)

    def populate_catalog(self, spec):
        """Befüllt die linke Auswahl mit 10 leichten oder schweren Bahnen.

        Args:
            spec (MeteoroidSettings): Aktuell ausgewählte Meteoroidenkonfiguration.
        """
        own = spec.profile == "Eigener Meteoroid"
        group = "Schwer" if spec.profile == "Groß und Schwer" else "Leicht"
        self.KatalogLabel.setText(
            "Kollisionsbahn (einzeln geprüft)" if not own
            else "Kollisionsbahn (nur für Vorlagen)"
        )
        was_blocked = self.KatalogAuswahl.blockSignals(True)
        self.KatalogAuswahl.clear()
        if not own:
            for e in profiles(group):
                self.KatalogAuswahl.addItem(
                    f"{e['name']} – Einschlag Tag {e['target_impact_day']}",
                    e["id"],
                )
            index = self.KatalogAuswahl.findData(spec.catalog_id)
            self.KatalogAuswahl.setCurrentIndex(max(0, index))
        self.KatalogAuswahl.blockSignals(was_blocked)
        self.KatalogAuswahl.setEnabled(not own)

    def change_scenario(self, scenario):
        """Wechselt nur bei eigenen Meteoroiden den Beispieldatensatz.

        Args:
            scenario (str): "Kollision" oder "Vorbeiflug" aus der Combobox.
        """
        spec = self.selected_meteoroid()
        if spec is None or spec.profile != "Eigener Meteoroid":
            return
        self.drop_target_defenses(spec.name)
        spec.scenario = scenario
        spec.position = np.array(r_Meteorid1, dtype=float)
        if scenario == "Kollision":
            spec.velocity = np.array(v_Meteorid1, dtype=float)
        else:
            spec.velocity = np.array(VORBEIFLUG_V, dtype=float)
        self.show_selected_meteoroid()
        self.queue_baseline()

    def change_profile(self, profile):
        """Wählt einen geprüften Katalogeintrag oder freie Einstellungen.

        Args:
            profile (str): Vorlagenart oder "Eigener Meteoroid".
        """
        spec = self.selected_meteoroid()
        if spec is None:
            return
        self.drop_target_defenses(spec.name)
        if profile == "Eigener Meteoroid":
            # Bisherige Startwerte bleiben als editierbarer Ausgangspunkt.
            spec.profile = profile
            spec.catalog_id = None
        else:
            category = "Leicht" if profile == "Klein und Leicht" else "Schwer"
            self.apply_catalog(spec, profiles(category)[0]["id"])
            # Vorbeugend statt eines alten, womöglich fast zu späten Zeitpunkts.
            self.EingriffszeitpunktRegler.setValue(20 * 24)
        self.show_selected_meteoroid()
        self.queue_baseline()

    @staticmethod
    def apply_catalog(spec, profile_id):
        """Ersetzt einen Meteoroiden durch gespeicherte Anfangswerte.

        Args:
            spec (MeteoroidSettings): Vorhandene, zu aktualisierende Konfiguration.
            profile_id (str): ID des geprüften Katalogeintrags.
        """
        replacement = catalog_settings(profile_id, spec.name)
        spec.scenario = replacement.scenario
        spec.profile = replacement.profile
        spec.catalog_id = replacement.catalog_id
        spec.mass_kg = replacement.mass_kg
        spec.diameter_m = replacement.diameter_m
        spec.position = replacement.position
        spec.velocity = replacement.velocity

    def change_catalog(self, *_):
        """Nimmt die 1–10 ausgewählte Bahn für den aktiven Meteoroiden.

        Args:
            *_ (object): Von Qt übergebene, nicht benötigte Signalargumente.
        """
        spec = self.selected_meteoroid()
        profile_id = self.KatalogAuswahl.currentData()
        if spec is None or not profile_id:
            return
        self.drop_target_defenses(spec.name)
        self.apply_catalog(spec, profile_id)
        self.EingriffszeitpunktRegler.setValue(20 * 24)
        self.show_selected_meteoroid()
        self.queue_baseline()

    def change_diameter(self, diameter):
        """Übernimmt den Durchmesser des selbst definierten Meteoroiden.

        Args:
            diameter (float): Neuer Durchmesser in m.
        """
        spec = self.selected_meteoroid()
        if spec and spec.profile == "Eigener Meteoroid":
            self.drop_target_defenses(spec.name)
            spec.diameter_m = diameter
            self.queue_baseline()

    def change_mass(self, mass_units):
        """Übernimmt die Masse; GUI-Einheit ist 10^10 kg.

        Args:
            mass_units (float): Masse in Einheiten von 10^10 kg.
        """
        spec = self.selected_meteoroid()
        if spec and spec.profile == "Eigener Meteoroid":
            self.drop_target_defenses(spec.name)
            spec.mass_kg = mass_units * 1.0e10
            self.queue_baseline()

    def update_velocity_text(self):
        """Zeigt Richtung in Grad und Betrag in km/s an.
        """
        spec = self.selected_meteoroid()
        if spec is None:
            return
        angle = (270 - np.degrees(np.arctan2(
            spec.velocity[1], spec.velocity[0]
        ))) % 360
        speed = np.linalg.norm(spec.velocity) / 1000.0
        self.Geschwindigkeit.setText(
            f"Geschwindigkeitsrichtung: {angle:.1f}°"
        )
        self.Geschwindigkeitsstaerke.setText(
            f"Geschwindigkeitsstärke: {speed:.2f} km/s"
        )

    def change_direction(self, angle):
        """Dreht nur den Geschwindigkeitsvektor, Betrag bleibt erhalten.

        Args:
            angle (int): Reglerwinkel in Grad (0° unten, im Uhrzeigersinn).
        """
        spec = self.selected_meteoroid()
        if spec is None or spec.profile != "Eigener Meteoroid":
            return
        speed = np.linalg.norm(spec.velocity)
        rad = np.radians((270 - angle) % 360)
        self.drop_target_defenses(spec.name)
        spec.velocity = speed * np.array([np.cos(rad), np.sin(rad)])
        self.update_velocity_text()
        self.queue_baseline()

    def change_speed(self, slider_value):
        """Ändert nur den Betrag des Geschwindigkeitsvektors.

        Args:
            slider_value (int): Schieberwert; eine Einheit entspricht 10 m/s.
        """
        spec = self.selected_meteoroid()
        if spec is None or spec.profile != "Eigener Meteoroid":
            return
        angle = np.arctan2(spec.velocity[1], spec.velocity[0])
        speed = slider_value * 10.0  # 1 Schieberpunkt = 10 m/s
        self.drop_target_defenses(spec.name)
        spec.velocity = speed * np.array([np.cos(angle), np.sin(angle)])
        self.update_velocity_text()
        self.queue_baseline()

    def check_meteoroid_name(self, text, exclude=None):
        """Prüft Namen auf Leertext, Doppelungen und reservierte Namen.

        Args:
            text (str): Geplanter Name.
            exclude (MeteoroidSettings | None): Beim Umbenennen ignorierter Körper.

        Returns:
            tuple[str, str | None]: Bereinigter Name und Fehlermeldung.
        """
        name = text.strip()
        if not name:
            return name, "Bitte einen Namen eingeben."
        if len(name) > 40:
            return name, "Der Name darf höchstens 40 Zeichen lang sein."
        if name.casefold() in {"sonne", "erde"}:
            return name, "'Sonne' und 'Erde' sind bereits vergeben."
        if any(a is not exclude and a.name.casefold() == name.casefold()
               for a in self.meteoroids):
            return name, f"Der Name '{name}' wird bereits verwendet."
        return name, None

    def rename_meteoroid(self):
        """Übernimmt den links eingetragenen Namen per Enter.
        """
        spec = self.selected_meteoroid()
        if spec is None:
            return
        name, error = self.check_meteoroid_name(
            self.MeteoroidNameEingabe.text(), exclude=spec
        )
        if error:
            self.statusbar.showMessage(error, 6000)
            self.quietly_set(self.MeteoroidNameEingabe, "setText", spec.name)
            return
        if name == spec.name:
            return
        for action in self.defense_actions:
            if action["target"] == spec.name:
                action["target"] = name
        self.refresh_defense_queue()
        spec.name = name
        self.listWidget.currentItem().setText(name)
        self.quietly_set(self.MeteoroidNameEingabe, "setText", name)
        self.queue_baseline()

    def add_meteoroid(self):
        """Fragt den Namen ab und fügt einen Meteoroiden hinzu.
        """
        if len(self.meteoroids) >= 5:
            self.statusbar.showMessage("Maximal fünf Meteoroiden möglich.", 6000)
            return

        default_name = f"Meteoroid {self.next_meteoroid_number}"
        while True:
            # QInputDialog.getText enthält bereits ein bearbeitbares Namensfeld.
            chosen, ok = QtWidgets.QInputDialog.getText(
                self, "Meteoroid hinzufügen", "Name des neuen Meteoroiden:",
                QtWidgets.QLineEdit.EchoMode.Normal, default_name,
            )
            if not ok:  # 'Abbrechen': kein Meteoroid wird erstellt.
                return
            name, error = self.check_meteoroid_name(chosen)
            if not error:
                break
            QtWidgets.QMessageBox.warning(self, "Ungültiger Name", error)
            default_name = chosen

        base = (self.selected_meteoroid() or self.meteoroids[0]) if self.meteoroids else None
        if base is not None and base.profile != "Eigener Meteoroid":
            # Neue Katalog-Meteoroiden erhalten möglichst eine andere
            # validierte Bahn statt denselben Startpunkt zu überlagern.
            category = "Leicht" if base.profile == "Klein und Leicht" else "Schwer"
            choices = profiles(category)
            used = {a.catalog_id for a in self.meteoroids}
            choice = next((e for e in choices if e["id"] not in used), None)
            if choice is None:
                self.statusbar.showMessage(
                    "Alle zehn Katalogbahnen dieser Klasse sind bereits vergeben.", 6000
                )
                return
            new = catalog_settings(choice["id"], name)
        else:
            # Eigene Meteoroiden werden mit Abstand zur Vorlage kopiert;
            # diese frei editierbaren Startwerte haben KEINE Einschlaggarantie.
            offset = np.array([-3.5e10, 2.5e10]) * self.next_meteoroid_number
            new = MeteoroidSettings(
                name=name,
                scenario=base.scenario if base else "Vorbeiflug",
                profile="Eigener Meteoroid",
                diameter_m=base.diameter_m if base else 140,
                mass_kg=base.mass_kg if base else 1e10,
                position=(base.position.copy() if base else np.array(r_Meteorid1)) + offset,
                velocity=base.velocity.copy() if base else np.array(VORBEIFLUG_V),
            )
        self.next_meteoroid_number += 1
        self.meteoroids.append(new)
        self.listWidget.addItem(new.name)
        self.listWidget.setCurrentRow(len(self.meteoroids) - 1)
        self.queue_baseline()

    def remove_meteoroid(self):
        """Entfernt den markierten Meteoroiden aus Liste und Simulation.
        """
        index = self.listWidget.currentRow()
        if not 0 <= index < len(self.meteoroids):
            self.statusbar.showMessage("Bitte zuerst einen Meteoroiden auswählen.")
            return

        self.rebuild_timer.stop()
        self.stop_playback()
        removed = self.meteoroids.pop(index)
        self.drop_target_defenses(removed.name)
        # Liste kurz ohne currentRowChanged-Signale ändern; so entsteht
        # kein Zwischenbild mit alten Positionen und neuen Indizes.
        was_blocked = self.listWidget.blockSignals(True)
        self.listWidget.takeItem(index)
        self.listWidget.setCurrentRow(
            min(index, len(self.meteoroids) - 1) if self.meteoroids else -1
        )
        self.listWidget.blockSignals(was_blocked)

        if not self.meteoroids and self.follow_mode == "Meteoroid":
            self.follow_mode = "Sonne"
            self.MeteoroidFolgenButton.setChecked(False)
        self.positions = None  # Alter Verlauf darf nicht mehr angezeigt werden.
        self.show_selected_meteoroid()
        self.calculate_baseline()  # Mit den verbliebenen Körpern neu rechnen.
        self.statusbar.showMessage(f"'{removed.name}' wurde entfernt.", 6000)

    def create_bodies(self):
        """Wandelt die gewählten GUI-Einstellungen in frische Körper um.

        Returns:
            list[CelestialBody]: Neue Objekte für einen frischen Simulationslauf.
        """
        return create_simulation_bodies(self.meteoroids)

    def drop_target_defenses(self, target_name):
        """Änderungen an Startwerten machen alte Impulse dieses Ziels ungültig.

        Args:
            target_name (str): Name des veränderten oder gelöschten Meteoroiden.
        """
        old_count = len(self.defense_actions)
        self.defense_actions = [
            entry for entry in self.defense_actions
            if entry["target"] != target_name
        ]
        if len(self.defense_actions) != old_count:
            self.refresh_defense_queue()
            self.statusbar.showMessage(
                f"Abwehraktionen von {target_name} entfernt: Startwerte geändert.",
                7000,
            )

    def refresh_defense_queue(self):
        """Zeigt alle vorgemerkten Aktionen in chronologischer Reihenfolge.
        """
        self.GeplanteAbwehren.clear()
        for entry in sorted(
            enumerate(self.defense_actions),
            key=lambda pair: (pair[1]["frame"], pair[0]),
        ):
            original_index, action = entry
            day = action["frame"] * dt / 86400
            text = (
                f"Tag {day:.2f} | {action['target']} | "
                f"{action['angle']:.0f}° | {action['impulse']:.2e} N·s"
            )
            item = QtWidgets.QListWidgetItem(text)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, original_index)
            self.GeplanteAbwehren.addItem(item)
        self.AbwehrEntfernen.setEnabled(bool(self.defense_actions))
        self.AlleAbwehrenLoeschen.setEnabled(bool(self.defense_actions))
        self.GeplanteAbwehrenLabel.setText(
            f"Geplante Abwehren ({len(self.defense_actions)}) – Play zeigt alle"
        )

    def remove_defense(self):
        """Entfernt die markierte Aktion aus der Abwehrliste.
        """
        item = self.GeplanteAbwehren.currentItem()
        if item is None:
            self.statusbar.showMessage("Bitte eine geplante Abwehr markieren.", 4000)
            return
        index = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if index is None or not 0 <= index < len(self.defense_actions):
            return
        self.defense_actions.pop(index)
        self.refresh_defense_queue()
        self.calculate_combined(preview_frame=self.EingriffszeitpunktRegler.value())

    def clear_defenses(self):
        """Setzt nur die Abwehraktionen zurück, nicht die Meteoroiden.
        """
        self.defense_actions.clear()
        self.refresh_defense_queue()
        self.calculate_combined(preview_frame=self.EingriffszeitpunktRegler.value())

    def queue_baseline(self):
        """Plant eine Neuberechnung nach Änderungen an Anfangsbedingungen.
        """
        self.stop_playback()
        self.rebuild_timer.start(180)

    def calculate_baseline(self):
        """Berechnet die unveränderte Referenzbahn und alle gespeicherten Abwehren.

        Notes:
            Bei einer ungültigen Ausgangslage wird der Verlauf geloescht und
            eine Meldung in der Statusleiste ausgegeben.
        """
        self.stop_playback()
        try:
            bodies = self.create_bodies()
            trajectory = simulate_trajectory(bodies, N, dt, stop_on_impact=self.stop_on_impact)
        except ValueError as exc:
            self.positions = None
            self.baseline_positions = None
            self.bodies = []
            self.hide_closeup()
            self.ax.clear()
            self.canvas.draw_idle()
            self.statusbar.showMessage(str(exc))
            return
        self.baseline_trajectory = trajectory
        self.baseline_positions = trajectory.positions
        self.baseline_collision = tuple(bodies[i].name for i in trajectory.impacts[0].pair) if trajectory.impacts else None
        self.calculate_combined(preview_frame=self.EingriffszeitpunktRegler.value())

    def calculate_combined(self, preview_frame=None):
        """Alle vorgemerkten Impulse werden in EINEM Physiklauf angewandt.

        Args:
            preview_frame (int | None): Optionaler Schritt, der nach der Berechnung angezeigt wird.

        Notes:
            Jeder vorgemerkte Impuls wird in derselben Simulation angewandt.
            Eine bereits eingetretene Kollision kann spaetere Impulse verhindern.
        """
        self.stop_playback()
        if self.baseline_positions is None:
            return
        try:
            bodies = self.create_bodies()
            if self.defense_actions:
                trajectory = simulate_trajectory(
                    bodies, N, dt,
                    defense_actions=[dict(a, angle=(270 - a["angle"]) % 360)
                                     for a in self.defense_actions],
                    stop_on_impact=self.stop_on_impact,
                )
            else:
                trajectory = self.baseline_trajectory
        except ValueError as exc:
            self.positions = None
            self.hide_closeup()
            self.canvas.draw_idle()
            self.statusbar.showMessage(str(exc), 9000)
            return
        self.bodies = self.create_bodies()  # Namen/Reihenfolge, frische Startwerte
        self.trajectory = trajectory
        self.positions = trajectory.positions
        self.collision = tuple(self.bodies[i].name for i in trajectory.impacts[0].pair) if trajectory.impacts else None
        self.display_end_frame = float(trajectory.frames[-1])
        self.encounter_windows = trajectory_windows(
            trajectory, CLOSEUP_DISTANCE, dt, IMPACT_AFTERGLOW_SECONDS
        )
        self.mode_text = (
            f"Mit {len(self.defense_actions)} Abwehraktion(en)"
            if self.defense_actions else "Ohne Abwehr"
        )
        self.playback_restart_requested = bool(self.defense_actions)
        # setMaximum kann bei kürzerer Bahn valueChanged auslösen.
        # Währenddessen gehören die alten Linien noch zum vorherigen Verlauf.
        # Daher erst nach prepare_plot ein neues Vorschaubild zeichnen.
        was_blocked = self.EingriffszeitpunktRegler.blockSignals(True)
        self.EingriffszeitpunktRegler.setMaximum(max(0, min(N - 1, int(np.ceil(self.display_end_frame)) - 1)))
        self.EingriffszeitpunktRegler.blockSignals(was_blocked)
        day = self.EingriffszeitpunktRegler.value() * dt / 86400
        self.Eingriffszeitpunkt.setText(f"Eingriffszeitpunkt: Tag {day:.2f}")
        self.prepare_plot()
        if preview_frame is not None:
            self.draw_frame(min(int(preview_frame), self.display_end_frame))
        self.show_status_for_trajectory("Abwehrplan" if self.defense_actions else "Ausgangsversuch")

    def prepare_plot(self):
        """Erstellt Linien, Referenzbahnen, Impulsmarker und Richtungspfeil.
        """
        if self.positions is None:
            return
        self.hide_closeup()
        for extra in (self.closeup_ax, self.comparison_ax):
            if extra is not None:
                extra.remove()
        self.closeup_ax = self.comparison_ax = None
        self.ax.clear()
        self.trajectory_lines.clear()
        self.points.clear()
        self.impact_markers.clear()
        colors = ["orange", "royalblue", "gray", "forestgreen", "firebrick",
                  "purple", "saddlebrown"]

        display_path = self.positions
        for i, body in enumerate(self.bodies):
            color = colors[i % len(colors)]
            self.ax.plot(
                display_path[:, i, 0], display_path[:, i, 1],
                color=color, alpha=0.16, linewidth=0.8,
            )
            line, = self.ax.plot([], [], color=color, linewidth=1.5)
            point, = self.ax.plot(
                [], [], "o", color=color, markersize=11 if i == 0 else 7,
                label=body.name,
            )
            self.trajectory_lines.append(line)
            self.points.append(point)

        # Einschlagspunkte werden erst zur jeweiligen Kontaktzeit sichtbar.
        for event in self.trajectory.impacts:
            point, = self.ax.plot([], [], "*", color="firebrick", ms=9, zorder=10)
            point.set_visible(False)
            self.impact_markers.append((event, point))

        # Gestrichelte ursprüngliche Bahnen aller verteidigten Meteoroiden.
        defended_names = {action["target"] for action in self.defense_actions}
        for i, body in enumerate(self.bodies):
            if body.name not in defended_names:
                continue
            reference = self.baseline_positions[:, i]
            self.ax.plot(
                reference[:, 0], reference[:, 1], '--',
                color=colors[i % len(colors)], linewidth=1.3, alpha=0.85,
                label=f"{body.name} ohne Abwehr",
            )

        # Jeder gespeicherte und erreichte Impuls bekommt einen Stern.
        for action in self.defense_actions:
            frame = action["frame"]
            index = self.index_for_target(action["target"])
            if index is not None and frame < self.display_end_frame and not self.trajectory.absorbed_at(index, frame):
                at = self.trajectory.at(frame)[index]
                self.ax.plot(
                    at[0], at[1], marker="*", color="magenta",
                    markersize=9, linestyle="None", zorder=8,
                )

        self.preview_arrow = FancyArrowPatch(
            (0, 0), (0, 0), arrowstyle="-|>", mutation_scale=15,
            color="magenta", linewidth=2.1, zorder=12,
        )
        self.preview_arrow.set_visible(False)
        self.ax.add_patch(self.preview_arrow)
        self.ax.set_aspect("equal", adjustable="box")
        self.ax.set_xlabel("x (m)")
        self.ax.set_ylabel("y (m)")
        self.ax.legend(loc="upper right", fontsize=8)
        self.ax.grid(True, alpha=0.2)
        self.figure.tight_layout(pad=1.6)
        self.overview_position = self.ax.get_position(original=True).frozen()
        self.prepare_closeup()
        self.draw_frame(0)

    def index_for_target(self, target):
        """Liefert den aktuellen Körperindex anhand eines Namens.

        Args:
            target (str | None): Anzeigename des gesuchten Körpers.

        Returns:
            int | None: Körperindex oder None, wenn der Name unbekannt ist.
        """
        return next(
            (i for i, body in enumerate(self.bodies) if body.name == target),
            None,
        )

    def update_preview_arrow(self, frame):
        """Richtungspfeil am Meteoroiden: beim Einstellen oder bei Impulswirkung.

        Args:
            frame (float): Aktuell angezeigter Simulationsschritt.
        """
        if self.preview_arrow is None:
            return
        self.preview_arrow.set_visible(False)
        if self.positions is None:
            return

        target = None
        angle = None
        if self.playing:
            # In der Animation kurze Zeit nach einem ausgeführten Impuls.
            recent = [
                a for a in self.defense_actions
                if a["frame"] <= frame < a["frame"] + 24
                and a["frame"] < self.display_end_frame
            ]
            if recent:
                action = max(recent, key=lambda a: a["frame"])
                target, angle = action["target"], action["angle"]
        elif frame == self.EingriffszeitpunktRegler.value():
            # Vor dem Vormerken zeigen wir den aktuell gewählten Impuls.
            selected = self.selected_meteoroid()
            if selected is not None:
                target = selected.name
                angle = self.ImpulsrichtungRegler.value()

        index = self.index_for_target(target)
        if index is None or angle is None or frame > self.display_end_frame or self.trajectory.absorbed_at(index, frame):
            return
        x, y = self.trajectory.at(frame)[index]
        if not np.isfinite([x, y]).all():
            return
        # Der Pfeil hat unabhängig vom Mausrad-Zoom eine ähnliche Bildgröße.
        width = self.ax.get_xlim()[1] - self.ax.get_xlim()[0]
        height = self.ax.get_ylim()[1] - self.ax.get_ylim()[0]
        size = min(width, height) * 0.09
        rad = np.radians((270 - angle) % 360)
        self.preview_arrow.set_positions(
            (x, y), (x + size * np.cos(rad), y + size * np.sin(rad))
        )
        self.preview_arrow.set_visible(True)

    def prepare_closeup(self):
        """Erstellt Nahansicht und Maßstabsvergleich auf derselben Zeichenfläche."""
        self.closeup_ax = self.figure.add_axes([0.46, 0.16, 0.51, 0.68])
        self.comparison_ax = self.figure.add_axes([0.06, 0.10, 0.34, 0.25])
        ax = self.closeup_ax
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("x relativ zur Erde (km)", fontsize=8)
        ax.set_ylabel("y (km)", fontsize=8, labelpad=1)
        ax.tick_params(labelsize=7)
        ax.grid(alpha=0.18)
        ax.set_title("Nahansicht · Zeitlupe", fontsize=11)
        ax.set_facecolor("#f4f8ff")
        self.earth_circle = Circle((0, 0), 1, facecolor="royalblue", edgecolor="navy", alpha=0.30)
        self.meteoroid_circle = Circle((0, 0), 1, facecolor="dimgray", edgecolor="black")
        ax.add_patch(self.earth_circle)
        ax.add_patch(self.meteoroid_circle)
        self.earth_point, = ax.plot(0, 0, "o", color="royalblue", ms=3, zorder=4)
        self.meteoroid_point, = ax.plot([], [], "+", color="black", ms=6, zorder=5)
        self.closeup_trail, = ax.plot([], [], color="dimgray", lw=1.2, zorder=2)
        self.closeup_info = ax.text(0.02, 0.98, "", transform=ax.transAxes,
                                    va="top", fontsize=8, zorder=9,
                                    bbox=dict(fc="white", ec="none", alpha=0.9))
        self.contact_marker, = ax.plot([], [], "*", color="firebrick", ms=10, zorder=8)
        # Rein schematische Einschlagmarkierung, keine berechnete Druckwelle.
        self.impact_ring = Circle((0, 0), 0, fill=False, edgecolor="firebrick", lw=1.7, zorder=7)
        self.impact_ring.set_visible(False)
        ax.add_patch(self.impact_ring)

        comp = self.comparison_ax
        comp.set_aspect("equal", adjustable="box")
        comp.set_axis_off()
        comp.set_title("Größenvergleich\n(maßstabsgetreu)", fontsize=8)
        self.comparison_earth = Circle((0, 0), 1, facecolor="royalblue", edgecolor="navy", alpha=0.30)
        self.comparison_meteoroid = Circle((0, 0), 1, facecolor="dimgray", edgecolor="black")
        comp.add_patch(self.comparison_earth)
        comp.add_patch(self.comparison_meteoroid)
        self.comparison_point, = comp.plot([], [], "+", color="black", ms=5)
        self.comparison_info = comp.text(0.5, -0.03, "", transform=comp.transAxes,
                                         ha="center", va="top", fontsize=8)
        self.closeup_ax.set_visible(False)
        self.comparison_ax.set_visible(False)

    def hide_closeup(self):
        """Stellt die normale Sonnen-/Verfolgungsansicht wieder her."""
        if self.closeup_ax is not None:
            self.closeup_ax.set_visible(False)
            self.comparison_ax.set_visible(False)
        if self.closeup_active and self.overview_position is not None:
            self.ax.set_position(self.overview_position)
            self.ax.set_xlabel("x (m)")
            self.ax.set_ylabel("y (m)")
            self.ax.tick_params(labelbottom=True, labelleft=True)
            legend = self.ax.get_legend()
            if legend is not None:
                legend.set_visible(True)
        self.closeup_active = False

    def update_closeup(self, frame, current):
        """Zeigt den nächsten Meteoroiden in einem erdzentrierten Koordinatensystem.

        Kreise werden in km mit den echten Radien gezeichnet. Das Kreuz ist
        nur eine Positionsmarkierung und kein vergrößerter Meteoroidenradius.
        """
        if not self.closeup_enabled or self.closeup_ax is None or not any(
            entry - 1e-9 <= frame <= exit_ + 1e-9
            for entry, exit_ in self.encounter_windows
        ):
            self.hide_closeup()
            return
        if not self.closeup_active:
            self.ax.set_position([0.06, 0.53, 0.34, 0.34])
            self.ax.set_xlabel("")
            self.ax.set_ylabel("")
            self.ax.tick_params(labelbottom=False, labelleft=False)
            legend = self.ax.get_legend()
            if legend is not None:
                legend.set_visible(False)
            self.closeup_ax.set_visible(True)
            self.comparison_ax.set_visible(True)
            self.closeup_active = True

        relative_positions = current[2:] - current[1]
        distances = np.linalg.norm(relative_positions, axis=1)
        recent = [e for e in self.trajectory.impacts if e.survivor == 1 and e.absorbed >= 2
                  and e.frame - 1e-9 <= frame <= e.frame + IMPACT_AFTERGLOW_SECONDS / dt + 1e-9]
        event = recent[-1] if recent else None
        if event is not None:
            index = event.absorbed
        elif np.isfinite(distances).any():
            index = 2 + int(np.nanargmin(distances))
        else:
            self.hide_closeup()
            return
        earth, meteor = self.bodies[1], self.bodies[index]
        relative = (current[index] - current[1]) / 1000
        if event is not None:
            direction = event.contact / np.linalg.norm(event.contact)
            relative = direction * (earth.radius + meteor.radius) / 1000
        distance = float(np.linalg.norm(relative))
        earth_r, meteor_r = earth.radius / 1000, meteor.radius / 1000
        gap = distance - earth_r - meteor_r
        self.earth_circle.set_radius(earth_r)
        self.meteoroid_circle.set_radius(meteor_r)
        self.meteoroid_circle.set_center(relative)
        absorbed = event is not None and frame > event.frame + 1e-9
        self.meteoroid_circle.set_visible(not absorbed)
        self.meteoroid_point.set_visible(not absorbed)
        self.meteoroid_point.set_data([relative[0]], [relative[1]])
        lower = self.trajectory.index(event.frame if event is not None else frame)
        start = self.trajectory.index(max(0, frame - 6))
        trail = (self.positions[start:lower + 1, index] - self.positions[start:lower + 1, 1]) / 1000
        trail = np.vstack((trail, relative))
        self.closeup_trail.set_data(trail[:, 0], trail[:, 1])
        half_width = max(1.5 * earth_r, 1.2 * (distance + meteor_r))
        self.closeup_ax.set_xlim(-half_width, half_width)
        self.closeup_ax.set_ylim(-half_width, half_width)
        if event is not None:
            contact = event.contact / 1000
            self.contact_marker.set_data([contact[0]], [contact[1]])
            phase = "Einschlag · aufgenommen" if absorbed else "Einschlag"
            age = max(0.0, (frame - event.frame) * dt)
            progress = min(1.0, age / IMPACT_AFTERGLOW_SECONDS)
            self.impact_ring.set_visible(absorbed)
            self.impact_ring.set_center(contact)
            self.impact_ring.set_radius(earth_r * (0.04 + 0.36 * progress))
            self.impact_ring.set_alpha(0.85 * (1.0 - progress))
            info = (f"Stoßenergie: {event.energy:.2e} J\n"
                    f"Δv Erde: {np.linalg.norm(event.delta_v):.2e} m/s\n"
                    "Stern / Ring = schematische Markierung")
        else:
            self.contact_marker.set_data([], [])
            self.impact_ring.set_visible(False)
            velocity = self.trajectory.velocities[lower, index] - self.trajectory.velocities[lower, 1]
            phase = "Anflug" if np.dot(relative, velocity) < 0 else "Vorbeiflug / Entfernung"
            info = f"Oberflächenabstand: {max(0.0, gap):,.1f} km"
        self.closeup_info.set_text(f"{meteor.name} · {phase}\n{info}")
        self.comparison_earth.set_radius(earth_r)
        position = (1.7 * earth_r, 0)
        self.comparison_meteoroid.set_center(position)
        self.comparison_meteoroid.set_radius(meteor_r)
        self.comparison_point.set_data([position[0]], [position[1]])
        self.comparison_ax.set_xlim(-1.15 * earth_r, 2.1 * earth_r)
        self.comparison_ax.set_ylim(-1.15 * earth_r, 1.15 * earth_r)
        self.comparison_info.set_text(
            f"Erde: {2 * earth_r:,.0f} km Ø\n"
            f"Meteoroid: {2 * meteor.radius:g} m Ø\n"
            f"Erde ≈ {earth_r / meteor_r:,.0f}× größer (Ø)"
        )

    def draw_frame(self, frame):
        """Zeichnet einen ganzen oder interpolierten Zeitwert mit passender Kamera."""
        if self.positions is None:
            return
        frame = float(np.clip(frame, 0, self.display_end_frame))
        self.frame = frame
        current = self.trajectory.at(frame)
        lower = self.trajectory.index(frame)
        for i, (line, point) in enumerate(zip(self.trajectory_lines, self.points)):
            trail = np.vstack((self.positions[:lower + 1, i], current[i]))
            line.set_data(trail[:, 0], trail[:, 1])
            point.set_data([current[i, 0]], [current[i, 1]])
            point.set_visible(np.isfinite(current[i]).all())

        for event, marker in self.impact_markers:
            visible = frame >= event.frame - 1e-9 and np.isfinite(current[event.survivor]).all()
            marker.set_visible(visible)
            if visible:
                contact = current[event.survivor] + event.contact
                marker.set_data([contact[0]], [contact[1]])

        center, half_width = self.camera_parameters(frame)
        center = center + self.pan_offset
        half_width *= self.zoom_scale
        self.ax.set_xlim(center[0] - half_width, center[0] + half_width)
        self.ax.set_ylim(center[1] - half_width, center[1] + half_width)

        self.update_preview_arrow(frame)
        self.update_closeup(frame, current)
        day = frame * dt / 86400
        self.SimulationszeitLabel.setText(
            f"Simulation: Tag {day:.4f} · Nahansicht / Zeitlupe" if self.closeup_active
            else f"Simulation: Tag {day:.2f}"
        )
        if self.closeup_active:
            self.ax.set_title("Übersicht", fontsize=9)
        else:
            self.ax.set_title(f"{self.mode_text} – Tag {day:.2f}", fontsize=12)
        occurred = [e for e in self.trajectory.impacts if e.frame <= frame + 1e-9]
        if occurred and not self.closeup_active:
            e = occurred[-1]
            self.ax.set_title(f"{self.mode_text} – Tag {day:.2f}\n{self.bodies[e.absorbed].name}: Einschlag Tag {e.frame * dt / 86400:.3f}")
            self.SimulationszeitLabel.setText(f"Simulation: Tag {day:.2f} · Δv Empfänger: {np.linalg.norm(e.delta_v):.2e} m/s")
        if frame >= self.display_end_frame - 1e-9:
            if self.collision and self.stop_on_impact:
                if not self.closeup_active:
                    self.ax.set_title(f"{self.mode_text} – Kollision an Tag {day:.2f}\n"
                                      f"{self.collision[0]} mit {self.collision[1]}")
            elif not self.closeup_active and not self.collision:
                self.ax.set_title(f"{self.mode_text} – Ende ohne Kollision")
        self.canvas.draw_idle()

    def camera_parameters(self, frame):
        """Bestimmt Kameramittelpunkt und Ansichtsbreite auch für Zwischenbilder."""
        current = self.trajectory.at(frame)
        if self.follow_mode == "Erde" and np.isfinite(current[1]).all():
            return current[1].copy(), 2e10
        if self.follow_mode == "Meteoroid" and self.selected_meteoroid() is not None:
            index = self.listWidget.currentRow() + 2
            if index < self.positions.shape[1] and np.isfinite(current[index]).all():
                return current[index].copy(), 2e10
        return np.zeros(2, dtype=float), max(
            1.6e11, float(np.nanmax(np.abs(self.positions))) * 1.08
        )

    def zoom_with_wheel(self, event):
        """Zoomt mit dem Mausrad zum Mauszeiger, auch während Play läuft.

        Args:
            event (MouseEvent): Matplotlib-Mausradereignis mit Position und Schrittweite.
        """
        if event.inaxes is not self.ax or self.positions is None:
            return
        if event.xdata is None or event.ydata is None or event.step == 0:
            return
        old_zoom = self.zoom_scale
        new_zoom = float(np.clip(
            old_zoom * 0.8 ** event.step, 0.00001, 20.0
        ))
        ratio = new_zoom / old_zoom
        base_center, _ = self.camera_parameters(self.frame)
        current_center = base_center + self.pan_offset
        cursor = np.array([event.xdata, event.ydata], dtype=float)
        # Mausposition bleibt beim Zoomen möglichst an derselben Pixelstelle.
        new_center = cursor + (current_center - cursor) * ratio
        self.zoom_scale = new_zoom
        self.pan_offset = new_center - base_center
        self.draw_frame(self.frame)

    def reset_zoom_on_doubleclick(self, event):
        """Doppelklick auf das Diagramm stellt den Standardzoom wieder her.

        Args:
            event (MouseEvent): Matplotlib-Ereignis des Doppelklicks.
        """
        if event.inaxes is self.ax and event.dblclick:
            self.zoom_scale = 1.0
            self.pan_offset[:] = 0.0
            self.draw_frame(self.frame)

    def on_mouse_press(self, event):
        """Rechtsklick startet das Verschieben; Doppelklick setzt Zoom zurück.

        Args:
            event (MouseEvent): Maustastendruck mit Pixelkoordinaten.
        """
        if event.inaxes is not self.ax or self.positions is None:
            return
        if event.button == 3:  # Matplotlib: rechte Maustaste
            self._pan_anchor_px = np.array([event.x, event.y], dtype=float)
            self._pan_initial_offset = self.pan_offset.copy()
        elif event.dblclick and event.button == 1:
            self.reset_zoom_on_doubleclick(event)

    def on_mouse_move(self, event):
        """Verschiebt die Ansicht relativ zur Mausbewegung (Bildschirmpixel).

        Args:
            event (MouseEvent): Mausbewegung mit Pixelkoordinaten.
        """
        if self._pan_anchor_px is None or self.positions is None:
            return
        dx, dy = np.array([event.x, event.y]) - self._pan_anchor_px
        bounds = self.ax.bbox
        if bounds.width <= 0 or bounds.height <= 0:
            return
        width = self.ax.get_xlim()[1] - self.ax.get_xlim()[0]
        height = self.ax.get_ylim()[1] - self.ax.get_ylim()[0]
        self.pan_offset = self._pan_initial_offset - np.array([
            dx * width / bounds.width, dy * height / bounds.height
        ])
        self.draw_frame(self.frame)

    def on_mouse_release(self, event):
        """Beendet das Verschieben beim Loslassen der rechten Maustaste.

        Args:
            event (MouseEvent): Ereignis beim Loslassen einer Maustaste.
        """
        if event.button == 3:
            self._pan_anchor_px = None
            self._pan_initial_offset = None

    def show_preview_time(self):
        """Schieberegler zeigt sofort die Meteoroidenposition an Tag X.
        """
        if self.positions is None:
            return
        self.stop_playback()
        requested = self.EingriffszeitpunktRegler.value()
        available = self.display_end_frame
        self.draw_frame(min(requested, available))
        if requested > available:
            self.statusbar.showMessage(
                "Dieser Tag liegt nach der ersten Kollision. "
                "Erst den früheren Zusammenstoß abwehren.", 6500,
            )

    def show_status_for_trajectory(self, label):
        """Zeigt den berechneten Kollisionsausgang in der Statusleiste.

        Args:
            label (str): Beschreibung des gerade berechneten Versuchs.
        """
        if self.positions is None:
            return
        if self.collision:
            e = self.trajectory.impacts[0]
            day = e.frame * dt / 86400
            self.statusbar.showMessage(
                f"{label}: {self.collision[0]} / {self.collision[1]}, Tag {day:.3f} · "
                f"Δv Empfänger = {np.linalg.norm(e.delta_v):.2e} m/s · E = {e.energy:.2e} J"
                + (" · Abbruch" if self.stop_on_impact else f" · Weiterlauf, {len(self.trajectory.impacts)} Kontakt(e)")
            )
        else:
            self.statusbar.showMessage(
                f"{label}: In {N * dt / 86400:.1f} Tagen keine Kollision."
            )

    def toggle_play(self):
        """Startet oder pausiert die Anzeige des bereits berechneten Verlaufs.
        """
        if self.playing:
            self.stop_playback()
            return
        if self.rebuild_timer.isActive():
            self.rebuild_timer.stop()
            self.calculate_baseline()
        if self.positions is None:
            return
        if self.playback_restart_requested or self.frame >= self.display_end_frame - 1e-9:
            self.frame = 0
            self.draw_frame(0)
        self.playback_restart_requested = False
        self.playing = True
        self.PlayButton.setText("Pause")
        self.animation_timer.start()
        self.draw_frame(self.frame)  # Pfeil folgt jetzt den ausgeführten Impulsen.

    def stop_playback(self):
        """Pausiert die Wiedergabe, ohne das aktuelle Bild zu verwerfen.
        """
        self.animation_timer.stop()
        self.playing = False
        self.PlayButton.setText("Play")

    def rewind(self):
        """Stoppt und springt zu Tag 0 des aktuellen Verlaufs zurück.
        """
        self.stop_playback()
        self.playback_restart_requested = bool(self.defense_actions)
        self.draw_frame(0)

    def set_playback_speed(self, speed):
        """Wählt den Abspielfaktor, ohne das physikalische Modell zu ändern.

        Args:
            speed (float): Einer der Faktoren 0.5, 1, 1.5, 2 oder 4.

        Raises:
            ValueError: Wenn eine nicht vorgesehene Geschwindigkeit übergeben wird.

        Notes:
            Verändert nur die Anzahl dargestellter Frames je Timer-Tick.
            ``dt`` bleibt die Stundenbasis; die Physik nutzt adaptive Unterzeitschritte.
        """
        if speed not in PLAYBACK_SPEEDS:
            raise ValueError(f"Unbekannte Wiedergabegeschwindigkeit: {speed}")
        self.playback_speed = speed
        self.SimulationTempoButton.setText(
            f"Tempo: {speed:g}".replace(".", ",") + "×"
        )
        for value, action in self.speed_actions.items():
            action.setChecked(value == speed)

    def next_frame(self):
        """Spielt die Bahn ab, ohne Nahbegegnungen oder den Kontakt zu überspringen."""
        if self.positions is None:
            self.stop_playback()
            return
        next_index = trajectory_next_frame(
            self.trajectory, self.frame, int(6 * self.playback_speed),
            self.encounter_windows if self.closeup_enabled else [],
            self.bodies[1].radius, CLOSEUP_MAX_FRAME_STEP, CLOSEUP_DISTANCE_FRACTION, dt,
        )
        self.draw_frame(next_index)
        if next_index >= self.display_end_frame - 1e-9:
            self.stop_playback()
            self.show_status_for_trajectory(self.mode_text)

    def toggle_closeup(self, enabled):
        """Aktiviert die automatische Nahkamera und Zeitlupe ohne Neuberechnung."""
        self.closeup_enabled = enabled
        self.CloseupButton.setText("Close-up: An" if enabled else "Close-up: Aus")
        self.draw_frame(self.frame)

    def toggle_impact_stop(self, enabled):
        """Berechnet beim Wechsel des Kollisionsmodus einen neuen Verlauf."""
        self.stop_on_impact = enabled
        self.ImpactStopButton.setText("Abbruch bei Aufschlag: An" if enabled else "Abbruch bei Aufschlag: Aus")
        if self.rebuild_timer.isActive():
            self.rebuild_timer.stop()
        self.calculate_baseline()
        self.playback_restart_requested = True

    def toggle_follow(self, target):
        """Schaltet Erd-/Meteoroidenverfolgung oder Sonnenansicht ein.

        Args:
            target (str): "Erde" oder "Meteoroid"; erneutes Klicken wählt die Sonne.
        """
        if target == "Meteoroid" and self.selected_meteoroid() is None:
            return
        self.follow_mode = "Sonne" if self.follow_mode == target else target
        # Follow zentriert auf den gewählten Körper, der Zoom bleibt bestehen.
        self.pan_offset[:] = 0.0
        self.ErdeFolgenButton.setChecked(self.follow_mode == "Erde")
        self.MeteoroidFolgenButton.setChecked(self.follow_mode == "Meteoroid")
        self.draw_frame(self.frame)

    def update_impulse_text(self, *_):
        """Zeigt Impulsbetrag und damit bewirkte Geschwindigkeitsänderung.

        Args:
            *_ (object): Ignorierte Qt-Signalargumente.
        """
        own = self.ImpulsstaerkeAuswahl.currentIndex() == 3
        self.EigeneImpulsstaerke.setEnabled(own)
        impulse = self.selected_impulse()
        self.Impulsstaerke.setText(f"Impulsstärke: {impulse:.2e} N·s")
        spec = self.selected_meteoroid()
        if spec is not None and spec.mass_kg > 0:
            speed_change = impulse / spec.mass_kg
            self.ImpulswirkungLabel.setText(
                f"Δv = J/m: {speed_change:.3g} m/s"
            )
        else:
            self.ImpulswirkungLabel.setText("Δv: Meteoroid auswählen")
        if not self.playing:
            self.draw_frame(self.frame)

    def selected_impulse(self):
        """Ordnet den vier Einträgen die Impulsbeträge zu.

        Returns:
            float: Impulsbetrag der gewählten Methode in N s.
        """
        option = self.ImpulsstaerkeAuswahl.currentIndex()
        if option == 0:
            return ABWEHR_METHODEN["Explosion"]
        if option == 1:
            return ABWEHR_METHODEN["Rakete"]
        if option == 2:
            return ABWEHR_METHODEN["Satellitenstoß"]
        # 0..1000 entspricht 0..1e14 N·s (in Stufen von 1e11 N·s).
        return self.EigeneImpulsstaerke.value() * 1.0e11

    def update_angle_text(self, *_):
        """Beschriftet den Reglerwinkel (0° unten, im Uhrzeigersinn).

        Args:
            *_ (object): Ignorierte Qt-Signalargumente.
        """
        self.Impulsrichtung.setText(
            f"Impulsrichtung: {self.ImpulsrichtungRegler.value()}°"
        )
        if not self.playing:
            self.show_preview_time()

    def update_time_text(self, *_):
        """Wandelt den Zeitregler von Simulationsschritten in Tage um.

        Args:
            *_ (object): Ignorierte Qt-Signalargumente.
        """
        frame = self.EingriffszeitpunktRegler.value()
        day = frame * dt / 86400
        self.Eingriffszeitpunkt.setText(
            f"Eingriffszeitpunkt: Tag {day:.2f}"
        )
        self.show_preview_time()

    def run_defense(self):
        """Merkt einen Impuls vor; Play zeigt danach ALLE Impulse zusammen.

        Notes:
            Legt nur eine Aktion in der Warteschlange ab; Play spielt den
            dadurch neu berechneten Verlauf ab.
        """
        spec = self.selected_meteoroid()
        if spec is None:
            self.statusbar.showMessage("Bitte einen Meteoroiden auswählen.", 6000)
            return
        if self.rebuild_timer.isActive():
            self.rebuild_timer.stop()
            self.calculate_baseline()
        if self.positions is None:
            self.statusbar.showMessage("Keine gültige Simulation.", 8000)
            return

        self.stop_playback()
        frame = self.EingriffszeitpunktRegler.value()
        if frame >= self.display_end_frame or self.trajectory.absorbed_at(self.index_for_target(spec.name), frame):
            self.statusbar.showMessage(
                "Der Impuls liegt bei/nach der ersten Kollision. "
                "Bitte früher eingreifen.", 9000,
            )
            return
        angle = self.ImpulsrichtungRegler.value()
        impulse = self.selected_impulse()
        if impulse <= 0:
            self.statusbar.showMessage("Bitte eine positive Impulsstärke einstellen.", 5000)
            return
        action = {
            "target": spec.name,
            "frame": frame,
            "angle": angle,
            "impulse": impulse,
        }
        self.defense_actions.append(action)
        self.refresh_defense_queue()
        self.calculate_combined(preview_frame=frame)
        self.playback_restart_requested = True
        self.statusbar.showMessage(
            f"Abwehr {len(self.defense_actions)} gespeichert: "
            f"{spec.name}, Tag {frame*dt/86400:.2f}, "
            f"{angle}°, Δv={impulse/spec.mass_kg:.3g} m/s. "
            "Play führt alle vorgemerkten Abwehren vor.",
            0,
        )
