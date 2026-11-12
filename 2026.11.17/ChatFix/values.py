"""Konstanten, Anfangsbedingungen und Meteoroidenkatalog der Simulation.

Einheiten:
    - Masse in Kilogramm (kg)
    - Position, Radius und Durchmesser in Metern (m)
    - Geschwindigkeit in Metern pro Sekunde (m/s)
    - Zeit in Sekunden (s)
    - Impuls in Newtonsekunden (N·s)

METEOROIDEN_KATALOG enthält je zehn leichte und schwere Beispielbahnen,
die in der vorhandenen Euler-Cromer-Simulation einzeln ohne Abwehr
mit der Erde kollidieren. Die Zahlen der Abwehrmethoden dienen nur
der anschaulichen Simulation, nicht der Prognose realer Missionen.
"""

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

# Demonstrationswerte, KEINE realistischen Missions- oder Waffenleistungen.
# Bei alten Werten (< 1e11 N·s) war Delta-v gerade bei schweren Meteoroiden
# kaum sichtbar. Die neuen Abstufungen zeigen den Masse-Effekt deutlicher.
# Wiedergabefaktoren der Qt-Animation (nur Anzeige, dt bleibt konstant).
PLAYBACK_SPEEDS = (0.5, 1.0, 1.5, 2.0, 4.0)

ABWEHR_METHODEN = {
    "Satellitenstoß": 1.0e10,
    "Rakete": 1.0e12,
    "Explosion": 1.0e14,
}


# =============================================================================
# Meteoroiden-Katalog: 20 geprüfte Beispielbahnen (10 leicht, 10 schwer)
# =============================================================================
# Jede Bahn wurde einzeln für Sonne + Erde + Meteoroid im Euler-Cromer-Modell
# mit dt=3600 s so gewählt, dass sie ohne Abwehr die Erde trifft.
# Bei mehreren Meteoroiden kann die erste Kollision die Simulation beenden.
# Alle Größen sind SI-Einheiten; target_impact_day bezeichnet den Referenztag.
# Diese Daten sind direkt in values.py enthalten – eine JSON-Datei ist
# nicht mehr nötig.

METEOROIDEN_KATALOG = [
    {
        'id': 'leicht_01',
        'name': 'Leicht 01',
        'category': 'Leicht',
        'mass_kg': 4000000000.0,
        'diameter_m': 70.0,
        'position_m': [84920643420.24898, -47015527765.6751],
        'velocity_m_s': [25286.423820630393, 37662.538939011436],
        'target_impact_day': 48,
    },
    {
        'id': 'leicht_02',
        'name': 'Leicht 02',
        'category': 'Leicht',
        'mass_kg': 8000000000.0,
        'diameter_m': 100.0,
        'position_m': [128385559810.25447, -92594569392.62808],
        'velocity_m_s': [6292.029811170575, 40030.81853685882],
        'target_impact_day': 65,
    },
    {
        'id': 'leicht_03',
        'name': 'Leicht 03',
        'category': 'Leicht',
        'mass_kg': 10000000000.0,
        'diameter_m': 140.0,
        'position_m': [258263915648.64102, -64042371532.67258],
        'velocity_m_s': [-23014.38527263707, 33482.24487657404],
        'target_impact_day': 80,
    },
    {
        'id': 'leicht_04',
        'name': 'Leicht 04',
        'category': 'Leicht',
        'mass_kg': 13000000000.0,
        'diameter_m': 150.0,
        'position_m': [59505231234.13813, 334912999484.26196],
        'velocity_m_s': [-8080.924883663682, -15827.79528856761],
        'target_impact_day': 94,
    },
    {
        'id': 'leicht_05',
        'name': 'Leicht 05',
        'category': 'Leicht',
        'mass_kg': 20000000000.0,
        'diameter_m': 160.0,
        'position_m': [-76778759974.9619, 306984743006.1544],
        'velocity_m_s': [-766.0545743924895, -8743.921880572512],
        'target_impact_day': 113,
    },
    {
        'id': 'leicht_06',
        'name': 'Leicht 06',
        'category': 'Leicht',
        'mass_kg': 6000000000.0,
        'diameter_m': 90.0,
        'position_m': [-164733437056.95465, 195339237197.35718],
        'velocity_m_s': [-2621.902338165925, 2423.970121068011],
        'target_impact_day': 132,
    },
    {
        'id': 'leicht_07',
        'name': 'Leicht 07',
        'category': 'Leicht',
        'mass_kg': 9000000000.0,
        'diameter_m': 120.0,
        'position_m': [79657496076.0745, 245467732380.9625],
        'velocity_m_s': [-17778.744419525217, 2647.0356590743418],
        'target_impact_day': 154,
    },
    {
        'id': 'leicht_08',
        'name': 'Leicht 08',
        'category': 'Leicht',
        'mass_kg': 15000000000.0,
        'diameter_m': 180.0,
        'position_m': [-10455951029.557037, 191303313879.77716],
        'velocity_m_s': [-20323.2413431903, 7837.5370190827425],
        'target_impact_day': 182,
    },
    {
        'id': 'leicht_09',
        'name': 'Leicht 09',
        'category': 'Leicht',
        'mass_kg': 7000000000.0,
        'diameter_m': 85.0,
        'position_m': [1958213282.143276, -65511524871.7118],
        'velocity_m_s': [44946.43345952145, 30204.39825120793],
        'target_impact_day': 215,
    },
    {
        'id': 'leicht_10',
        'name': 'Leicht 10',
        'category': 'Leicht',
        'mass_kg': 18000000000.0,
        'diameter_m': 170.0,
        'position_m': [-103100499460.16907, -150775382515.61252],
        'velocity_m_s': [14559.595444074523, -2069.44842397045],
        'target_impact_day': 255,
    },
    {
        'id': 'schwer_01',
        'name': 'Schwer 01',
        'category': 'Schwer',
        'mass_kg': 500000000000.0,
        'diameter_m': 350.0,
        'position_m': [75293308945.36299, -57046924895.77796],
        'velocity_m_s': [28336.519319359388, 36258.35131054903],
        'target_impact_day': 54,
    },
    {
        'id': 'schwer_02',
        'name': 'Schwer 02',
        'category': 'Schwer',
        'mass_kg': 900000000000.0,
        'diameter_m': 450.0,
        'position_m': [130825989248.50471, -101236193197.65929],
        'velocity_m_s': [5588.544353112409, 38796.3403514304],
        'target_impact_day': 72,
    },
    {
        'id': 'schwer_03',
        'name': 'Schwer 03',
        'category': 'Schwer',
        'mass_kg': 1500000000000.0,
        'diameter_m': 650.0,
        'position_m': [275949573885.877, -56930588205.85143],
        'velocity_m_s': [-24632.65680162187, 30694.580451475187],
        'target_impact_day': 89,
    },
    {
        'id': 'schwer_04',
        'name': 'Schwer 04',
        'category': 'Schwer',
        'mass_kg': 3000000000000.0,
        'diameter_m': 800.0,
        'position_m': [-63964494473.36968, 306193321755.76385],
        'velocity_m_s': [408.54664965635675, -9331.09035765642],
        'target_impact_day': 106,
    },
    {
        'id': 'schwer_05',
        'name': 'Schwer 05',
        'category': 'Schwer',
        'mass_kg': 4000000000000.0,
        'diameter_m': 1000.0,
        'position_m': [-161936929584.69, 199873791287.17926],
        'velocity_m_s': [-451.568753004206, 2577.2864418937597],
        'target_impact_day': 125,
    },
    {
        'id': 'schwer_06',
        'name': 'Schwer 06',
        'category': 'Schwer',
        'mass_kg': 7000000000000.0,
        'diameter_m': 1300.0,
        'position_m': [-265167776345.0976, 248117390601.6416],
        'velocity_m_s': [3538.790377129409, -7087.985788126798],
        'target_impact_day': 149,
    },
    {
        'id': 'schwer_07',
        'name': 'Schwer 07',
        'category': 'Schwer',
        'mass_kg': 9000000000000.0,
        'diameter_m': 1500.0,
        'position_m': [10353230173.419214, 323620218218.5739],
        'velocity_m_s': [-15898.950182332017, -7450.524001873468],
        'target_impact_day': 176,
    },
    {
        'id': 'schwer_08',
        'name': 'Schwer 08',
        'category': 'Schwer',
        'mass_kg': 13000000000000.0,
        'diameter_m': 1800.0,
        'position_m': [-151721915084.9144, 267106207418.8479],
        'velocity_m_s': [-11710.483869997905, -8872.666556874305],
        'target_impact_day': 205,
    },
    {
        'id': 'schwer_09',
        'name': 'Schwer 09',
        'category': 'Schwer',
        'mass_kg': 20000000000000.0,
        'diameter_m': 2300.0,
        'position_m': [-181013708875.97824, 124658018676.41203],
        'velocity_m_s': [-17742.24718156018, -8527.852030055012],
        'target_impact_day': 238,
    },
    {
        'id': 'schwer_10',
        'name': 'Schwer 10',
        'category': 'Schwer',
        'mass_kg': 30000000000000.0,
        'diameter_m': 3000.0,
        'position_m': [-228155097178.708, -53790787400.643456],
        'velocity_m_s': [-7447.436341286971, -17519.99382201141],
        'target_impact_day': 285,
    },
]
