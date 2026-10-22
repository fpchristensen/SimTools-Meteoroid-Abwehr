# Simulationsdauer
T = 365.25 * 24 * 60 * 60

# Anzahl der Simulationsschritte
N = int(365.25 * 24)

# Zeit zwischen zwei Schritten
DT = T / N



# Erster Asteroid
M_Asteroid = 1.0e10  # Masse in kg
R_Asteroid = 100     # Radius in m

# Anfangsbedingungen
r_Asteroid = [1.50e11, 1.0e10]
v_Asteroid = [-5000.0, 25000.0]

