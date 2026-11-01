"""Visualisierung der Himmelskörpersimulation mit Matplotlib.

Zeigt die berechneten Bahnen als Animation an. Über einen Button kann die
Kamera zwischen der sonnenzentrierten Ansicht und der Erdverfolgung wechseln.
"""


import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button


def animate_system(r_values, bodies, dt, collision=None,
                   title="Simulation", auto_close=False):

    """Animiert die berechneten Bahnen der Himmelskörper.
    
    Zeigt die bisher zurückgelegten Umlaufbahnen und Positionen an. Mit dem
    Button „Erde folgen“ wird zwischen der Gesamtansicht um die Sonne und
    einer erdzentrierten Ansicht umgeschaltet. Bei einer Kollision wird diese
    am Ende der Animation im Titel angezeigt.
    
    Args:
        r_values (numpy.ndarray): Positionen mit Form (Zeitschritte, Körper, 2)
            in Metern. Die letzte Dimension enthält x- und y-Koordinaten.
        bodies (list[CelestialBody]): Himmelskörper in derselben Reihenfolge
            wie die zweite Achse von r_values.
        dt (float): Dauer eines Simulationsschritts in Sekunden.
        collision (tuple[str, str] | None): Namen der beiden kollidierenden
            Körper; None, wenn keine Kollision stattgefunden hat.
        title (str): Titel der Simulation.
        auto_close (bool): Schließt das Animationsfenster etwa 1,8 Sekunden
            nach dem Ende automatisch, wenn True.
    
    Returns:
        matplotlib.animation.FuncAnimation: Das Animationsobjekt.
    """

    fig, ax = plt.subplots()
    fig.subplots_adjust(bottom=0.2)

    colors = ["orange", "blue", "gray", "green", "red"]
    orbit_lines = []
    object_points = []

    for i, body in enumerate(bodies):
        color = colors[i % len(colors)]

        line, = ax.plot([], [], color=color, linewidth=1)

        point, = ax.plot(
            [], [], "o",
            color=color,
            markersize=10 if i == 0 else 7,
            label=body.name
        )

        orbit_lines.append(line)
        object_points.append(point)

    # Kameraeinstellungen
    limit = max(1.6e11, np.max(np.abs(r_values)) * 1.08)
    earth_limit = 2e10

    earth_index = next(
        (i for i, body in enumerate(bodies)
         if body.name == "Erde"),
        None
    )

    follow_earth = False
    current_frame = 0

    ax.set_xlim(-limit, limit)
    ax.set_ylim(-limit, limit)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.legend(loc="upper right")

    # Kamera bewegen
    def update_camera(frame):

        """Passt den sichtbaren Koordinatenbereich an die gewählte Kamera an.
        
        Args:
            frame (int): Index des aktuellen Simulationszeitschritts.
        """

        if follow_earth and earth_index is not None:
            # Position der Erde im aktuellen Frame
            x = r_values[frame, earth_index, 0]
            y = r_values[frame, earth_index, 1]

            ax.set_xlim(x - earth_limit, x + earth_limit)
            ax.set_ylim(y - earth_limit, y + earth_limit)

        else:
            # Sonne bleibt im Zentrum
            ax.set_xlim(-limit, limit)
            ax.set_ylim(-limit, limit)

    # Button erstellen
    button_ax = fig.add_axes([0.35, 0.05, 0.3, 0.07])
    button = Button(button_ax, "Erde folgen: AUS")

    # Button-Funktion
    def toggle_camera(event):
        """Schaltet bei einem Button-Klick die Erdverfolgung ein oder aus.
        
        Args:
            event: Von Matplotlib übergebenes Klickereignis (hier nicht genutzt).
        """

        nonlocal follow_earth

        follow_earth = not follow_earth

        if follow_earth:
            button.label.set_text("Erde folgen: AN")
        else:
            button.label.set_text("Erde folgen: AUS")

        update_camera(current_frame)
        fig.canvas.draw_idle()

    button.on_clicked(toggle_camera)

    # Referenz speichern
    fig._earth_button = button

    frames = list(range(0, len(r_values), 6))

    if frames[-1] != len(r_values) - 1:
        frames.append(len(r_values) - 1)

    last_frame = frames[-1]
    finished = False

    def update(frame):
        """Zeichnet für einen Animationsschritt Bahnen, Positionen und Titel neu.
        
        Beendet die Wiedergabe am letzten Frame und schließt gegebenenfalls
        automatisch das Fenster.
        
        Args:
            frame (int): Index des anzuzeigenden Simulationszeitschritts.
        
        Returns:
            list: Die aktualisierten Matplotlib-Linien und Positionsmarker.
        """

        nonlocal finished, current_frame

        current_frame = frame

        for i, point in enumerate(object_points):
            orbit_lines[i].set_data(
                r_values[:frame + 1, i, 0],
                r_values[:frame + 1, i, 1]
            )

            point.set_data(
                [r_values[frame, i, 0]],
                [r_values[frame, i, 1]]
            )

        # Kamera aktualisieren
        if follow_earth:
            update_camera(frame)

        days = frame * dt / 86400
        ax.set_title(f"{title} – Tag {days:.1f}")

        if frame == last_frame and not finished:
            finished = True

            if collision is not None:
                ax.set_title(
                    f"{title} – KOLLISION nach {days:.2f} Tagen\n"
                    f"{collision[0]} mit {collision[1]}"
                )
            else:
                ax.set_title(f"{title} – Ende ohne Kollision")

            animation.event_source.stop()

            if auto_close:
                close_timer = fig.canvas.new_timer(interval=1800)
                close_timer.single_shot = True
                close_timer.add_callback(lambda: plt.close(fig))
                fig._close_timer = close_timer
                close_timer.start()

        return orbit_lines + object_points

    animation = FuncAnimation(
        fig, update,
        frames=frames,
        interval=50,
        blit=False,
        repeat=False
    )

    plt.show()
    return animation
