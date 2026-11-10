"""Tests für zwei Asteroiden, mehrere Impulse und rückwärtskompatiblen Aufruf.

Ohne Qt ausführbar: py test_mehrfachabwehr.py
"""
import numpy as np

from classes_functions import entry_for
from classes_functions import CelestialBody, orbital_data, simulate_system
from values import (
    N, dt, a_Ellipse, e_Ellipse, m_Erde, m_Sonne,
    radius_Erde, radius_Sonne, ABWEHR_METHODEN,
)


def make_bodies():
    """Erstellt frische Körper für die zwei gleichzeitigen Asteroidenbahnen.

    Returns:
        list[CelestialBody]: Frisches System mit Sonne, Erde und zwei Asteroiden.
    """
    re, ve = orbital_data(a_Ellipse, e_Ellipse, m_Sonne)
    result = [
        CelestialBody('Sonne', m_Sonne, radius_Sonne, [0, 0], [0, 0]),
        CelestialBody('Erde', m_Erde, radius_Erde, re, ve),
    ]
    for name, profile_id in [('Asteroid A', 'leicht_03'),
                             ('Asteroid B', 'schwer_05')]:
        e = entry_for(profile_id)
        result.append(CelestialBody(
            name, e['mass_kg'], e['diameter_m'] / 2,
            e['position_m'], e['velocity_m_s'],
        ))
    return result


def main():
    """Prüft Kollisionen ohne Abwehr, beide Abwehren und mehrere Impulse pro Ziel.
    """
    action_a = {'target': 'Asteroid A', 'frame': 20 * 24,
                'angle': 0, 'impulse': ABWEHR_METHODEN['Explosion']}
    action_b = {'target': 'Asteroid B', 'frame': 30 * 24,
                'angle': 0, 'impulse': ABWEHR_METHODEN['Explosion']}

    alone, _, initial_collision = simulate_system(make_bodies(), N, dt)
    assert initial_collision == ('Erde', 'Asteroid A')
    assert 79 < (len(alone) - 1) * dt / 86400 < 81

    with_one, _, one_collision = simulate_system(
        make_bodies(), N, dt, defense_actions=[action_a]
    )
    assert one_collision == ('Erde', 'Asteroid B')
    assert 124 < (len(with_one) - 1) * dt / 86400 < 126

    with_two, with_two_velocities, two_collision = simulate_system(
        make_bodies(), N, dt, defense_actions=[action_b, action_a]
    )
    assert two_collision is None
    assert len(with_two) == N + 1

    # Die zweite Abwehr verändert B erst nach ihrem ausgewählten Frame.
    t_b = action_b['frame']
    assert np.allclose(with_two[t_b, 3], with_one[t_b, 3], atol=0.01, rtol=0)
    next_step_delta = with_two[t_b + 1, 3] - with_one[t_b + 1, 3]
    expected = action_b['impulse'] / entry_for('schwer_05')['mass_kg'] * dt
    assert np.isclose(next_step_delta[0], expected, atol=0.02, rtol=1e-9)
    assert abs(next_step_delta[1]) < 0.02

    # Nicht nur unterschiedliche Asteroiden: zwei Impulse auf A sind erlaubt.
    duplicate = dict(action_a, frame=action_a['frame'] + 1, angle=90)
    doubled, _, _ = simulate_system(
        make_bodies(), N, dt, defense_actions=[action_a, duplicate]
    )
    assert len(doubled) > action_a['frame'] + 2

    print('OK: Ohne Abwehr kollidiert A um Tag 80.')
    print('OK: Nach A-Abwehr kollidiert B um Tag 125.')
    print('OK: Mit beiden Impulsen keine Kollision im simulierten Jahr.')
    print('OK: Der zweite Impuls wirkt am richtigen Frame auf B.')
    print('OK: Auch mehrere Impulse für denselben Asteroiden sind zulässig.')


if __name__ == '__main__':
    main()
