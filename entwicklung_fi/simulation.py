import numpy as np
from const_values import G
from functions_and_classes import berechne_acceleration



def simulate_system(bodies, N, dt):

    # Speicher für alle Positionen und Geschwindigkeiten, dreidimensionales Array: (Zeitschritte, Körper, Koordinaten)
    r_values = np.zeros((N + 1, len(bodies), 2))
    v_values = np.zeros((N + 1, len(bodies), 2))

    # Anfangswerte speichern
    for i, body in enumerate(bodies):
        r_values[0, i] = body.r
        v_values[0, i] = body.v

    # Simulation
    for n in range(N):

        # Beschleunigungen aller Körper berechnen
        accelerations = []

        for body in bodies:
            a = berechne_acceleration(body, bodies)
            accelerations.append(a)

        # Alle Körper bewegen
        for i, body in enumerate(bodies):

            # Euler-Cromer-Verfahren
            body.v = body.v + accelerations[i] * dt
            body.r = body.r + body.v * dt

            # Neue Werte speichern
            r_values[n + 1, i] = body.r
            v_values[n + 1, i] = body.v

    return r_values, v_values
