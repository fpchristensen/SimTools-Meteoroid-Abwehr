import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

def sonne_zeichnen(ax, r_Sonne):
    ax.plot(r_Sonne[0], r_Sonne[1], "o", color = "orange", label = "Sonne")

def bahnen_zeichnen(ax, r, farbe, name):
    ax.plot(r[:, 0], r[:, 1], color = farbe)
    punkt, = ax.plot(r[0, 0], r[0, 1], "o", color = farbe, label = name)
    return punkt

def körper_laufen(t, t_Werte, r, punkt):
    r = position_zur_zeit(t, t_Werte, r)
    punkt.set_data([r[0]], [r[1]])

def position_zur_zeit(t, t_Werte, r):
    x = np.interp(t, t_Werte, r[:, 0])
    y = np.interp(t, t_Werte, r[:, 1])
    return np.array([x, y])

def animieren(fig, koerper, animationszeiten):
    def update(t):
        for t_Werte, r, punkt in koerper:
            körper_laufen(t, t_Werte, r, punkt)

    animation = FuncAnimation(
        fig, update,
        frames=animationszeiten,
        interval=30
    )
    return animation