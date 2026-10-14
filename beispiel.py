
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# ==========================================
# 1. KONSTANTEN
# ==========================================

G = 6.67430e-11           # Gravitationskonstante
TAG = 24 * 60 * 60        # Sekunden pro Tag
AE = 1.496e11             # Astronomische Einheit (m)

# ==========================================
# 2. HIMMELSKÖRPER
# ==========================================

koerper = [
    {
        "name": "Sonne",
        "masse": 1.989e30,
        "position": [0, 0],
        "geschwindigkeit": [0, 0],
        "farbe": "orange",
        "groesse": 18
    },
    {
        "name": "Erde",
        "masse": 5.972e24,
        "position": [1.471e11, 0],
        "geschwindigkeit": [0, 30290],
        "farbe": "royalblue",
        "groesse": 9
    }
]

# Listen in NumPy-Arrays umwandeln
for k in koerper:
    k["position"] = np.array(k["position"], dtype=float)
    k["geschwindigkeit"] = np.array(
        k["geschwindigkeit"], dtype=float
    )

# ==========================================
# 3. GRAVITATION
# ==========================================

def berechne_beschleunigungen():
    """Berechnet die Gravitation zwischen allen Körpern."""

    beschleunigungen = []

    for i, k1 in enumerate(koerper):
        a = np.zeros(2)

        for j, k2 in enumerate(koerper):

            if i == j:
                continue

            richtung = k2["position"] - k1["position"]
            abstand = np.linalg.norm(richtung)

            if abstand == 0:
                raise ValueError(
                    "Zwei Körper befinden sich am selben Ort."
                )

            a += (
                G * k2["masse"] * richtung / abstand**3
            )

        beschleunigungen.append(a)

    return beschleunigungen


# ==========================================
# 4. NUMERISCHE SIMULATION
# ==========================================

dt = TAG / 24  # Zeitschritt: 1 Stunde
zeit = 0

def simulationsschritt():
    """Ein Schritt mit dem Velocity-Verlet-Verfahren."""
    global zeit

    # Beschleunigung zum aktuellen Zeitpunkt
    a_alt = berechne_beschleunigungen()

    # Positionen aktualisieren
    for k, a in zip(koerper, a_alt):
        k["position"] += (
            k["geschwindigkeit"] * dt
            + 0.5 * a * dt**2
        )

    # Neue Beschleunigung
    a_neu = berechne_beschleunigungen()

    # Geschwindigkeiten aktualisieren
    for k, alt, neu in zip(koerper, a_alt, a_neu):
        k["geschwindigkeit"] += 0.5 * (alt + neu) * dt

    zeit += dt


# ==========================================
# 5. ANIMATION
# ==========================================

fig, ax = plt.subplots(figsize=(9, 9))

ax.set_facecolor("#080e1e")
fig.patch.set_facecolor("#111827")

ax.set_aspect("equal")
ax.set_xlim(-1.3 * AE, 1.3 * AE)
ax.set_ylim(-1.3 * AE, 1.3 * AE)

ax.set_xlabel("x (m)", color="white")
ax.set_ylabel("y (m)", color="white")
ax.tick_params(colors="white")
ax.grid(alpha=0.15)

punkte = []
bahnen = []
verlauf = []

for k in koerper:
    punkt, = ax.plot(
        [], [], "o",
        color=k["farbe"],
        markersize=k["groesse"],
        label=k["name"]
    )

    bahn, = ax.plot(
        [], [],
        color=k["farbe"],
        alpha=0.5,
        linewidth=1
    )

    punkte.append(punkt)
    bahnen.append(bahn)
    verlauf.append([])

ax.legend(loc="upper right")

titel = ax.set_title(
    "",
    color="white",
    fontsize=14
)


def update(frame):
    # Pro Bild 24 Stunden simulieren
    for _ in range(24):
        simulationsschritt()

    for i, k in enumerate(koerper):
        x, y = k["position"]

        punkte[i].set_data([x], [y])

        verlauf[i].append((x, y))

        # Maximal 500 Positionen speichern
        if len(verlauf[i]) > 500:
            verlauf[i].pop(0)

        punkte_verlauf = np.array(verlauf[i])

        bahnen[i].set_data(
            punkte_verlauf[:, 0],
            punkte_verlauf[:, 1]
        )

    titel.set_text(
        f"N-Körper-Simulation | Tag {zeit / TAG:.0f}"
    )

    return punkte + bahnen + [titel]


ani = FuncAnimation(
    fig,
    update,
    interval=30,
    blit=False,
    cache_frame_data=False
)

plt.show()
