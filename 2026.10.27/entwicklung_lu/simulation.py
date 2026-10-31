import numpy as np

def beschleunigung(r_anziehend, r, G, m_anziehend):
    richtung = r_anziehend - r
    abstand = np.linalg.norm(richtung) #Gibt aktuellen Abstand von Erde zur Sonne durch die 2-Norm an
    a = G * m_anziehend * richtung / (abstand**3)
    return a

def bewegung(N, dt, t0, r_anziehend, r, v, G, m_anziehend,
             t_Erde = None, r_Erde = None, m_Erde = None):
    t_Werte = [t0]
    r_Werte = [r]
    v_Werte = [v]
    for n in range(N): #Idee ist das Euler-Cromer-Verfahren zu benutzen
        t_aktuell = t0 + n * dt
        a = beschleunigung(r_anziehend, r, G, m_anziehend)
        if m_Erde is not None:
            r_Erde_aktuell = erdposition(t_aktuell, t_Erde, r_Erde)
            a = a + beschleunigung(r_Erde_aktuell, r, G, m_Erde)
        v = v + a * dt
        r = r + v * dt

        t = t0 + (n + 1) * dt

        t_Werte.append(t) 
        r_Werte.append(r)
        v_Werte.append(v)

    return np.array(t_Werte), np.array(r_Werte), np.array(v_Werte)

def erdposition(t, t_Erde, r_Erde):
    x = np.interp(t, t_Erde, r_Erde[:, 0])
    y = np.interp(t, t_Erde, r_Erde[:, 1])
    return np.array([x, y])