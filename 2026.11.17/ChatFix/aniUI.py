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
from matplotlib.patches import FancyArrowPatch

from classes_functions import (
    MeteoroidSettings, catalog_settings, profiles,
    simulate_system, create_bodies as create_simulation_bodies,
)
from values import (
    N, dt, r_Meteorid1, v_Meteorid1, ABWEHR_METHODEN, PLAYBACK_SPEEDS,
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
        frame (int): Derzeit sichtbarer Zeitschritt.
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
        # 1× zeigt sechs physikalische Zeitschritte pro QTimer-Tick.
        self.playback_speed = 1.0
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
        self.canvas.mpl_connect("scroll_event", self.zoom_with_wheel)
        self.canvas.mpl_connect("button_press_event", self.on_mouse_press)
        self.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)
        self.canvas.mpl_connect("button_release_event", self.on_mouse_release)

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
        angle = int(round(np.degrees(np.arctan2(
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
        """Dreht nur den Geschwindigkeitsvektor, Betrag bleibt erhalten.

        Args:
            angle (int): Neue Bewegungsrichtung in Grad.
        """
        spec = self.selected_meteoroid()
        if spec is None or spec.profile != "Eigener Meteoroid":
            return
        speed = np.linalg.norm(spec.velocity)
        rad = np.radians(angle)
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
            positions, _, collision = simulate_system(bodies, N, dt)
        except ValueError as exc:
            self.positions = None
            self.baseline_positions = None
            self.bodies = []
            self.ax.clear()
            self.canvas.draw_idle()
            self.statusbar.showMessage(str(exc))
            return
        self.baseline_positions = positions
        self.baseline_collision = collision
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
                positions, _, collision = simulate_system(
                    bodies, N, dt, defense_actions=self.defense_actions
                )
            else:
                positions = self.baseline_positions
                collision = self.baseline_collision
        except ValueError as exc:
            self.positions = None
            self.statusbar.showMessage(str(exc), 9000)
            return
        self.bodies = self.create_bodies()  # Namen/Reihenfolge, frische Startwerte
        self.positions = positions
        self.collision = collision
        self.mode_text = (
            f"Mit {len(self.defense_actions)} Abwehraktion(en)"
            if self.defense_actions else "Ohne Abwehr"
        )
        self.playback_restart_requested = bool(self.defense_actions)
        # setMaximum kann bei kürzerer Bahn valueChanged auslösen.
        # Währenddessen gehören die alten Linien noch zum vorherigen Verlauf.
        # Daher erst nach prepare_plot ein neues Vorschaubild zeichnen.
        was_blocked = self.EingriffszeitpunktRegler.blockSignals(True)
        self.EingriffszeitpunktRegler.setMaximum(max(0, len(positions) - 2))
        self.EingriffszeitpunktRegler.blockSignals(was_blocked)
        day = self.EingriffszeitpunktRegler.value() * dt / 86400
        self.Eingriffszeitpunkt.setText(f"Eingriffszeitpunkt: Tag {day:.2f}")
        self.prepare_plot()
        if preview_frame is not None:
            self.draw_frame(min(int(preview_frame), len(positions) - 1))
        self.show_status_for_trajectory("Abwehrplan" if self.defense_actions else "Ausgangsversuch")

    def prepare_plot(self):
        """Erstellt Linien, Referenzbahnen, Impulsmarker und Richtungspfeil.
        """
        if self.positions is None:
            return
        self.ax.clear()
        self.trajectory_lines.clear()
        self.points.clear()
        colors = ["orange", "royalblue", "gray", "forestgreen", "firebrick",
                  "purple", "saddlebrown"]

        for i, body in enumerate(self.bodies):
            color = colors[i % len(colors)]
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
            if index is not None and frame < len(self.positions) - 1:
                at = self.positions[frame, index]
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
            frame (int): Aktuell angezeigter Simulationsschritt.
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
                and a["frame"] < len(self.positions) - 1
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
        if index is None or angle is None or frame >= len(self.positions):
            return
        x, y = self.positions[frame, index]
        # Der Pfeil hat unabhängig vom Mausrad-Zoom eine ähnliche Bildgröße.
        width = self.ax.get_xlim()[1] - self.ax.get_xlim()[0]
        height = self.ax.get_ylim()[1] - self.ax.get_ylim()[0]
        size = min(width, height) * 0.09
        rad = np.radians(angle)
        self.preview_arrow.set_positions(
            (x, y), (x + size * np.cos(rad), y + size * np.sin(rad))
        )
        self.preview_arrow.set_visible(True)

    def draw_frame(self, frame):
        """Zeichnet den ausgewählten Simulationsschritt und verfolgt ggf. einen Körper.

        Args:
            frame (int): Anzuzeigender Zeitschritt; auf den verfügbaren Bereich begrenzt.
        """
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

        center, half_width = self.camera_parameters(frame)
        center = center + self.pan_offset
        half_width *= self.zoom_scale
        self.ax.set_xlim(center[0] - half_width, center[0] + half_width)
        self.ax.set_ylim(center[1] - half_width, center[1] + half_width)

        self.update_preview_arrow(frame)
        day = frame * dt / 86400
        self.SimulationszeitLabel.setText(f"Simulation: Tag {day:.2f}")
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

    def camera_parameters(self, frame):
        """Bestimmt den Kameramittelpunkt und die unvergrößerte Ansicht.

        Args:
            frame (int): Simulationsschritt für die Kameraposition.

        Returns:
            tuple[np.ndarray, float]: Weltkoordinaten des Zentrums und halbe Ansichtsbreite in m.
        """
        if self.follow_mode == "Erde":
            return self.positions[frame, 1].copy(), 2e10
        if self.follow_mode == "Meteoroid" and self.selected_meteoroid() is not None:
            index = self.listWidget.currentRow() + 2
            if index < self.positions.shape[1]:
                return self.positions[frame, index].copy(), 2e10
        return np.zeros(2, dtype=float), max(
            1.6e11, float(np.max(np.abs(self.positions))) * 1.08
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
        available = len(self.positions) - 1
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
        if self.playback_restart_requested or self.frame >= len(self.positions) - 1:
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
            ``dt`` in values.py bleibt immer bei einer Stunde pro Frame.
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
        """Wird periodisch von QTimer aufgerufen und zeichnet das nächste Bild.
        """
        if self.positions is None:
            self.stop_playback()
            return
        last = len(self.positions) - 1
        # Sechs Frames pro Tick bei 1×; alle fünf Faktoren ergeben ganze
        # Frame-Schritte. Auch 4× durchläuft dieselben berechneten Bahnwerte.
        frames_per_tick = int(6 * self.playback_speed)
        next_index = min(self.frame + frames_per_tick, last)
        self.draw_frame(next_index)
        if next_index >= last:
            self.stop_playback()
            self.show_status_for_trajectory(self.mode_text)

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
        """Beschriftet den Impulswinkel (mathematisch ab positiver x-Achse).

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
        if frame >= len(self.positions) - 1:
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
