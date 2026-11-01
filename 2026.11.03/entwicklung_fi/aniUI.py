"""Matplotlib-Oberfläche für Animation und interaktive Meteoroidenabwehr.

Erster Durchlauf: Animation und Button zur Erdverfolgung.
Zweiter Durchlauf: zusätzlich Zeitregler, Drehregler, Dropdown und Play.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button, Slider, RadioButtons
from matplotlib.patches import Circle, FancyArrowPatch

from values import ABWEHR_METHODEN


def animate_system(r_values, bodies, dt, collision=None,
                   title="Simulation", auto_close=False,
                   controls=False, on_play=None):
    """Zeigt die Flugbahnen und bei Bedarf die Abwehr-Bedienelemente.

    Args:
        r_values (numpy.ndarray): Positionen mit Form (Schritte, Körper, 2).
        bodies (list[CelestialBody]): Körper in derselben Reihenfolge.
        dt (float): Simulationsschritt in Sekunden.
        collision (tuple[str, str] | None): Kollisionspartner oder None.
        title (str): Titel der Animation.
        auto_close (bool): Schließt das erste Fenster nach dem Ende.
        controls (bool): Zeigt Zeitregler, Winkel, Dropdown und Play.
        on_play (callable | None): Erhält (frame, angle, impulse) und gibt
            (neue_positionen, neue_kollision) zurück.

    Returns:
        FuncAnimation | None: Aktuelles Animationsobjekt, falls angelegt.
    """
    if controls and on_play is None:
        raise ValueError("Mit controls=True wird eine on_play-Funktion benötigt.")

    fig, ax = plt.subplots()
    fig.subplots_adjust(bottom=0.40 if controls else 0.20)

    colors = ["orange", "blue", "gray", "green", "red"]
    orbit_lines = []
    object_points = []

    for i, body in enumerate(bodies):
        color = colors[i % len(colors)]
        line, = ax.plot([], [], color=color, linewidth=1)
        point, = ax.plot(
            [], [], "o", color=color,
            markersize=10 if i == 0 else 7,
            label=body.name,
        )
        orbit_lines.append(line)
        object_points.append(point)

    earth_index = next(
        (i for i, body in enumerate(bodies) if body.name == "Erde"),
        None,
    )
    earth_limit = 2e10
    limit = max(1.6e11, np.max(np.abs(r_values)) * 1.08)

    follow_earth = False
    current_frame = 0
    animation = None
    playing = False
    finished = False

    def make_frames(values):
        """Erstellt Animationsframes inklusive des letzten Zeitschritts."""
        result = list(range(0, len(values), 6))
        if result[-1] != len(values) - 1:
            result.append(len(values) - 1)
        return result

    frames = make_frames(r_values)
    last_frame = frames[-1]

    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.legend(loc="upper right")

    def update_camera(frame):
        """Zentriert die Ansicht auf die Erde oder auf die Sonne."""
        if follow_earth and earth_index is not None:
            x, y = r_values[frame, earth_index]
            ax.set_xlim(x - earth_limit, x + earth_limit)
            ax.set_ylim(y - earth_limit, y + earth_limit)
        else:
            ax.set_xlim(-limit, limit)
            ax.set_ylim(-limit, limit)

    update_camera(0)

    # Button zur Erdverfolgung (in beiden Fenstern).
    earth_ax = fig.add_axes(
        [0.35, 0.13, 0.30, 0.06] if controls
        else [0.35, 0.05, 0.30, 0.07]
    )
    earth_button = Button(earth_ax, "Erde folgen: AUS")

    def toggle_camera(event):
        """Schaltet die Kamera auf die Erdposition oder zurück zur Sonne."""
        nonlocal follow_earth
        follow_earth = not follow_earth
        earth_button.label.set_text(
            "Erde folgen: AN" if follow_earth else "Erde folgen: AUS"
        )
        update_camera(current_frame)
        fig.canvas.draw_idle()

    earth_button.on_clicked(toggle_camera)
    fig._earth_button = earth_button

    def update(frame):
        """Aktualisiert Bahnen, Positionen, Kamera und Kollisionsanzeige."""
        nonlocal current_frame, finished, playing
        current_frame = frame

        for i, point in enumerate(object_points):
            orbit_lines[i].set_data(
                r_values[:frame + 1, i, 0],
                r_values[:frame + 1, i, 1],
            )
            point.set_data(
                [r_values[frame, i, 0]],
                [r_values[frame, i, 1]],
            )

        update_camera(frame)
        days = frame * dt / 86400
        ax.set_title(f"{title} – Tag {days:.2f}")

        # Nur bei laufender Animation das Ende als solches behandeln.
        if playing and frame == last_frame and not finished:
            finished = True
            playing = False

            if collision is not None:
                ax.set_title(
                    f"{title} – KOLLISION nach {days:.2f} Tagen\n"
                    f"{collision[0]} mit {collision[1]}"
                )
            else:
                ax.set_title(f"{title} – Ende ohne Kollision")

            if animation is not None and animation.event_source is not None:
                animation.event_source.stop()

            if auto_close:
                close_timer = fig.canvas.new_timer(interval=1800)
                close_timer.single_shot = True
                close_timer.add_callback(lambda: plt.close(fig))
                fig._close_timer = close_timer
                close_timer.start()

        return orbit_lines + object_points

    if controls:
        # Zeitregler: direkt in Simulationsframes, nicht in Tagen.
        slider_ax = fig.add_axes([0.20, 0.27, 0.67, 0.03])
        time_slider = Slider(
            slider_ax, "Frame", valmin=0,
            valmax=max(1, len(r_values) - 2),
            valinit=0, valstep=1,
        )

        def slider_update(frame):
            """Stoppt ggf. die Wiedergabe und zeigt den gewählten Frame."""
            nonlocal playing
            if animation is not None and animation.event_source is not None:
                animation.event_source.stop()
            playing = False
            # Nach einem Abwehrversuch kann der neue Verlauf kürzer sein.
            update(min(int(frame), len(r_values) - 1))
            fig.canvas.draw_idle()

        time_slider.on_changed(slider_update)

        # Drehregler für den Ablenkwinkel.
        dial_ax = fig.add_axes([0.82, 0.025, 0.15, 0.15])
        dial_ax.set_xlim(-1.2, 1.2)
        dial_ax.set_ylim(-1.2, 1.2)
        dial_ax.set_aspect("equal")
        dial_ax.axis("off")
        dial_ax.add_patch(Circle((0, 0), 1, fill=False))
        arrow = FancyArrowPatch(
            (0, 0), (0.8, 0),
            arrowstyle="->", mutation_scale=15, color="red",
        )
        dial_ax.add_patch(arrow)

        angle = 0.0
        dragging = False

        def rotate(event):
            """Berechnet den Winkel aus der Mausposition im Drehregler."""
            nonlocal angle
            if event.inaxes != dial_ax or event.xdata is None or event.ydata is None:
                return
            angle = np.degrees(np.arctan2(event.ydata, event.xdata)) % 360
            rad = np.radians(angle)
            arrow.set_positions(
                (0, 0), (0.8 * np.cos(rad), 0.8 * np.sin(rad))
            )
            fig.canvas.draw_idle()

        def on_press(event):
            """Beginnt das Drehen bei einem Mausklick im Kreis."""
            nonlocal dragging
            if event.inaxes == dial_ax:
                dragging = True
                rotate(event)

        def on_move(event):
            """Dreht den Pfeil bei gedrückter Maustaste."""
            if dragging:
                rotate(event)

        def on_release(event):
            """Beendet das Drehen nach dem Loslassen der Maustaste."""
            nonlocal dragging
            dragging = False

        fig.canvas.mpl_connect("button_press_event", on_press)
        fig.canvas.mpl_connect("motion_notify_event", on_move)
        fig.canvas.mpl_connect("button_release_event", on_release)

        # Dropdown für Impulswerte aus values.py.
        methods = list(ABWEHR_METHODEN)
        selected_method = methods[0]
        dropdown_ax = fig.add_axes([0.03, 0.04, 0.26, 0.065])
        dropdown_button = Button(dropdown_ax, selected_method + " ▼")

        options_ax = fig.add_axes([0.03, 0.39, 0.26, 0.20])
        options_ax.set_zorder(10)
        options_ax.set_visible(False)
        options = RadioButtons(options_ax, methods)

        def toggle_dropdown(event):
            """Öffnet oder schließt die Auswahl der Abwehrmethoden."""
            options_ax.set_visible(not options_ax.get_visible())
            fig.canvas.draw_idle()

        def select_method(label):
            """Speichert die gewählte Methode und schließt das Dropdown."""
            nonlocal selected_method
            selected_method = label
            dropdown_button.label.set_text(label + " ▼")
            options_ax.set_visible(False)
            fig.canvas.draw_idle()

        dropdown_button.on_clicked(toggle_dropdown)
        options.on_clicked(select_method)

        # Play berechnet den neuen Verlauf und spielt ihn ab Tag 0 ab.
        play_ax = fig.add_axes([0.41, 0.04, 0.17, 0.065])
        play_button = Button(play_ax, "Play")

        def start_animation(event):
            """Liest drei Reglerwerte und startet die Abwehrsimulation."""
            nonlocal animation, r_values, collision
            nonlocal frames, last_frame, limit, finished, playing

            frame = int(time_slider.val)
            impulse = ABWEHR_METHODEN[selected_method]

            if animation is not None and animation.event_source is not None:
                animation.event_source.stop()

            # Wichtig: Frame * dt ist der Ablenkungszeitpunkt in Sekunden.
            r_values, collision = on_play(frame, angle, impulse)
            frames = make_frames(r_values)
            last_frame = frames[-1]
            limit = max(1.6e11, np.max(np.abs(r_values)) * 1.08)
            finished = False
            playing = True

            # Vor der Wiedergabe zum Anfang zurückspringen.
            update(0)
            animation = FuncAnimation(
                fig, update, frames=frames, interval=50,
                blit=False, repeat=False,
            )
            fig._animation = animation
            fig.canvas.draw_idle()

        play_button.on_clicked(start_animation)
        fig._controls = (time_slider, arrow, dropdown_button, options, play_button)

        # Im Einstellungsfenster wird zunächst nur Frame 0 angezeigt.
        update(0)

    else:
        # Erstes Fenster startet ohne weitere Eingaben sofort.
        playing = True
        animation = FuncAnimation(
            fig, update, frames=frames, interval=50,
            blit=False, repeat=False,
        )
        fig._animation = animation

    plt.show()
    return animation
