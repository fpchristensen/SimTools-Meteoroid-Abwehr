
import matplotlib.pyplot as plt


def animate_system(r_values, bodies):

    fig, ax = plt.subplots()

    colors = ["orange", "blue", "gray", "green", "red"]

    points = []

    # Umlaufbahnen zeichnen
    for i, body in enumerate(bodies):

        color = colors[i % len(colors)] #farbzuordnung der liste 

        ax.plot(
            r_values[:, i, 0],
            r_values[:, i, 1],
            color=color
        )

        # Beweglichen Punkt erstellen
        point, = ax.plot(
            [], [],
            "o",
            color=color,
            label=body.name
        )

        points.append(point)

    ax.axis("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.legend(loc="upper right")

    # Animation
    for n in range(0, len(r_values), 24):

        for i, point in enumerate(points):

            point.set_data(
                [r_values[n, i, 0]],
                [r_values[n, i, 1]]
            )

        plt.pause(0.01)

    plt.show()
