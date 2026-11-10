import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

def animate_system(r_values, bodies):
    fig, ax = plt.subplots()

    colors = ["orange", "blue", "gray", "green", "red"]

    object_points = []

    for index, body in enumerate(bodies):
        color = colors[index % len(colors)]
        ax.plot(r_values[:, index, 0], r_values[:, index, 1], color=color, linewidth=1)
        point, = ax.plot([], [], "o", color=color, label=body.name)
        object_points.append(point)

    ax.set_aspect("equal", adjustable="datalim")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title("Meteoroiden-Abwehr: Sonne, Erde und Meteoroid")
    ax.legend(loc="upper right")

    def update(frame):
        for index, point in enumerate(object_points):
            point.set_data([r_values[frame, index, 0]], [r_values[frame, index, 1]])
        return object_points

    animation = FuncAnimation(
        fig,
        update,
        frames=range(0, len(r_values), 24),
        interval=30,
        blit=False,
        repeat=True,
    )
    plt.show()
    return animation