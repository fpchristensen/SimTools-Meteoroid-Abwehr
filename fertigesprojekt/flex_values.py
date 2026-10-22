
# Simulationsdauer
T = 365.25 * 24 * 60 * 60

# Anzahl der Simulationsschritte
N = int(365.25 * 24)

# Zeit zwischen zwei Schritten
DT = T / N


A_EARTH = 1.496e11
E_EARTH = 0.0167

# Erster Asteroid
M_Asteroid = 1.0e10  # Masse in kg
R_Asteroid = 100     # Radius in m

# Anfangsbedingungen
r_Asteroid = [1.50e11, 1.0e10]
v_Asteroid = [-5000.0, 25000.0]




# Asteroid 2: Sonnenvorbeiflug
M_Asteroid_2 = 1.0e10
R_Asteroid_2 = 100

r_Asteroid_2 = [0.0, 5.0e11]
v_Asteroid_2 = [-8000.0, -35000.0]




# Asteroid 3: Goldener Schnitt, Einschlag in die Sonne - klappt noch nicht
M_Asteroid_3 = 1.0e10
R_Asteroid_3 = 100

phi = (1 + 5**0.5) / 2

r_Asteroid_3 = [A_EARTH * (1 - E_EARTH) / phi, 0.0]
v_Asteroid_3 = [-15000.0, 0.0]


# Asteroid 4: Kollision mit der Erde - klappt auch noch nicht weil ja dann ne kolision ist und da brichts ab bevor es zeigt 
M_Asteroid_4 = 1.0e10
R_Asteroid_4 = 100

r_Asteroid_4 = [-2.0e11, 2.5e11]
v_Asteroid_4 = [26719.45, -7489.37]
#laut chat an tag 83
