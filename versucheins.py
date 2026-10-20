import numpy as np
import matplotlib.pyplot as plt

a = 1.496e11 #Große Halbachse der Umlaufbahn der Ellipse
e = 0.0167 #Exzentrizität
G = 6.67430e-11
Ms = 1.989e30

T = 365.25 * 24 * 60 * 60 #Umlaufdauer in Sekunden
N = int(365.25 * 24) 

dt = T / N #Aktuell ist Delta T eine Stunde

t0 = 0
r_Erde = np.array([a * (1 - e), 0]) #Ortsvektor zum Zeitpunkt t = 0
v_Erde = np.array([0, np.sqrt(G * Ms * (1 + e) / (a * (1 - e)))]) #Geschwindigkeisvektor zum Zeitpunkt t = 0

x_Werte = [r_Erde[0]]
y_Werte = [r_Erde[1]]
vx_Werte = [v_Erde[0]]
vy_Werte = [v_Erde[1]]

for n in range(N): #Idee ist das Euler-Verfahren zu benutzen
    tn = t0 + n * dt #Zeitpunkte an denen die Geschwindigkeit und der Standort berechnet wird

    abstand = np.linalg.norm(r_Erde) #Gibt aktuellen Abstand von Erde zur Sonne durch die 2-Norm an

    a_Erde = - G * Ms * r_Erde / (abstand**3)
    v_Erde = v_Erde + a_Erde * dt
    r_Erde = r_Erde + v_Erde * dt

    x_Werte.append(r_Erde[0])
    y_Werte.append(r_Erde[1])
    vx_Werte.append(v_Erde[0])
    vy_Werte.append(v_Erde[1])


plt.plot(x_Werte, y_Werte, label = "Erdbahn")
plt.plot(0, 0, "o", color = "orange", label = "Sonne")
plt.axis("equal")
plt.xlabel("x in m")
plt.ylabel("y in m")
plt.legend()
plt.show()