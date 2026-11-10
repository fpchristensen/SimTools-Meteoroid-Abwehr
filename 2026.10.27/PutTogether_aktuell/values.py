

a_Ellipse = 1.496e11 #Große Halbachse der Umlaufbahn der Ellipse
e_Ellipse = 0.0167 #Exzentrizität
G = 6.67430e-11

m_Sonne = 1.989e30
radius_Sonne = 6.9634e8


m_Meteorid1 = 1.0e10
radius_Meteorid1 = 70
r_Meteorid1 = [-3.0 * a_Ellipse, 1.0 * a_Ellipse]
v_Meteorid1 = [35000.0, 0.0]


m_Meteorid2 = 1.0e10
radius_Meteorid2 = 100
r_Meteorid2 = [1.50e11, 1.0e10]
v_Meteorid2 = [-5000.0, 25000.0]

m_Erde = 5.972e24
radius_Erde = 6.371e6



T = 365.25 * 24 * 60 * 60 #Umlaufdauer in Sekunden
N = int(365.25 * 24) 

dt = T / N #Aktuell ist Delta T eine Stunde

t0 = 0


