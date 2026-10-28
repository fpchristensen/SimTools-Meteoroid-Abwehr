import numpy as np
from simulation import bewegung
import matplotlib.pyplot as plt
from darstellung import sonne_zeichnen, bahnen_zeichnen, animieren

a_Ellipse = 1.496e11 #Große Halbachse der Umlaufbahn der Ellipse
e_Ellipse = 0.0167 #Exzentrizität
G = 6.67430e-11
m_Sonne = 1.989e30
m_Meteorid = 1.0e10 
m_Erde = 5.972e24  


T = 365.25 * 24 * 60 * 60 #Umlaufdauer in Sekunden
N = int(365.25 * 24) 

dt = T / N #Aktuell ist Delta T eine Stunde

t0 = 0
r_Erde = np.array([a_Ellipse * (1 - e_Ellipse), 0]) #Ortsvektor zum Zeitpunkt t = 0
v_Erde = np.array([0, np.sqrt(G * m_Sonne * (1 + e_Ellipse) / (a_Ellipse * (1 - e_Ellipse)))]) #Geschwindigkeisvektor zum Zeitpunkt t = 0

r_Sonne = np.array([0, 0])

# r_Meteorid = np.array([1.2 * a_Ellipse, 0.0])  
# v_Meteorid = np.array([0.0, 24000.0])
r_Meteorid = np.array([-3.0 * a_Ellipse, 1.0 * a_Ellipse])
v_Meteorid = np.array([35000.0, 0.0])  

fig, ax = plt.subplots()

sonne_zeichnen(ax, r_Sonne)

t_Erde, r_Erde, v_Erde = bewegung(N, dt, t0, r_Sonne, r_Erde, v_Erde, G, m_Sonne) #Bekommt Ergebnisse aus Funktion Bewegung mit den Paramtern für die Erde
t_Meteorid,r_Meteorid, v_Meteorid = bewegung(N, dt, t0, r_Sonne, r_Meteorid, v_Meteorid, G, m_Sonne, t_Erde, r_Erde, m_Erde)

erdpunkt = bahnen_zeichnen(ax, r_Erde, "blue", "Erde")
meteoridenpunkt = bahnen_zeichnen(ax, r_Meteorid, "gray", "Meteorid")

koerper = [(t_Erde, r_Erde, erdpunkt),(t_Meteorid, r_Meteorid, meteoridenpunkt)]

ax.set_aspect("equal")
ax.legend(loc="upper right")

#
start = max(t_Erde[0], t_Meteorid[0])
ende = min(t_Erde[-1], t_Meteorid[-1])
animationszeiten = np.arange(start, ende, 24 * 60 * 60)

animation = animieren(fig, koerper, animationszeiten)
#

plt.show()

#Zeitschritte müssen bei nahmen erdvorbeiflug von Asteroid kürzer sein
