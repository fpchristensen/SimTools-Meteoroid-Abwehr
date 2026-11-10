"""Konstanten, Anfangsbedingungen und Beispiel-Impulse (SI-Einheiten)."""

a_Ellipse = 1.496e11
e_Ellipse = 0.0167
G = 6.67430e-11

m_Sonne = 1.989e30
radius_Sonne = 6.9634e8
m_Erde = 5.972e24
radius_Erde = 6.371e6

m_Meteorid1 = 1.0e10
radius_Meteorid1 = 70
r_Meteorid1 = [-1.5e11, 8.0e10]
v_Meteorid1 = [14812.0, 22581.7]

# Der zweite Meteoroid ist im Modell derzeit optional.
m_Meteorid2 = 1.0e10
radius_Meteorid2 = 100
r_Meteorid2 = [1.5711168e11, 0.0]
v_Meteorid2 = [-5000.0, 30195.6]

T = 365.25 * 24 * 60 * 60
N = int(365.25 * 24)
dt = T / N  # 3600 s pro Schritt

ABWEHR_METHODEN = {
    "Satellitenstoß": 2.0e7,
    "Rakete": 2.4e8,
    "Explosion": 1.0e11,
}
