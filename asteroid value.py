import numpy as np

M_Asteroid = 1.0e10     #Masse in kg
R_Asteroid =100         #Radius in m

#Anfangsbedingungen für den Asteroiden:
r_Asteroid = np.array([1.50e11, 1.0e10], dtype=float) #Ortsvektor zum Zeitpunkt t = 0
v_Asteroid = np.array([-5000.0, 25000.0], dtype=float) #Geschwindigkeitsvektor zum Zeitpunkt t = 0

def bescheunigung(position, other_objects):
  
    G = 6.67430e-11  # Gravitationskonstante
    a = np.array([0.0, 0.0])

    for objekt in other_objects:
       direction = objekt["position"] - position  #Ortsvektor im Bezug auf andere Himmelskörper
       distance = np.linalg.norm(direction)

       if distance == 0:
           raise ValueError("Zusammenstoß beim start!!!")
    a += (G * objekt["masse"] * direction / distance**3) #Gravitationsberechnung
    return a 
       