"""Tests der Nahbereichslogik ohne Qt: python -m tests.test_closeup."""
import numpy as np
from classes_functions import (
    create_bodies, catalog_settings, simulate_system, interpolate_positions,
    segment_radius_interval, earth_encounter_windows, collision_contact_frame,
    next_playback_frame,
)
from values import (N, dt, CLOSEUP_DISTANCE, CLOSEUP_MAX_FRAME_STEP,
                    CLOSEUP_DISTANCE_FRACTION, PLAYBACK_SPEEDS)


def walk(positions, windows, end, radius, speed):
    """Simuliert die Wiedergabe und prüft monotonen Fortschritt."""
    frames = [0.0]
    while frames[-1] < end - 1e-9:
        following = next_playback_frame(
            frames[-1], int(6 * speed), windows, positions, radius,
            CLOSEUP_MAX_FRAME_STEP, CLOSEUP_DISTANCE_FRACTION, end,
        )
        assert following > frames[-1]
        frames.append(following)
        assert len(frames) < 100_000
    assert np.isclose(frames[-1], end, rtol=0, atol=1e-9)
    return np.array(frames)


def main():
    """Prüft Standardkollision, Vorbeiflug, mehrere Körper und hohe Tempi."""
    bodies = create_bodies([catalog_settings('leicht_03', 'Meteoroid 1')])
    positions, _, collision = simulate_system(bodies, N, dt)
    assert collision == ('Erde', 'Meteoroid 1')
    end = collision_contact_frame(positions, bodies, collision)
    current = interpolate_positions(positions, end)
    assert abs(np.linalg.norm(current[2] - current[1]) - bodies[1].radius - bodies[2].radius) < 0.001
    windows = earth_encounter_windows(positions, CLOSEUP_DISTANCE, end)
    assert len(windows) == 1 and windows[0][1] == end
    for speed in PLAYBACK_SPEEDS:
        frames = walk(positions, windows, end, bodies[1].radius, speed)
        assert np.any(np.isclose(frames, windows[0][0], rtol=0, atol=1e-9))
        assert np.count_nonzero(frames >= windows[0][0] - 1e-9) > 30

    # Vorbeiflug vollständig zwischen zwei gespeicherten Zeitpunkten.
    positions = np.zeros((3, 4, 2))
    positions[:, 2, :] = [[-20., 2.], [20., 2.], [30., 2.]]
    positions[:, 3, :] = [[100., 0.], [100., 0.], [100., 0.]]
    windows = earth_encounter_windows(positions, 10.)
    assert len(windows) == 1 and 0 < windows[0][0] < windows[0][1] < 1
    frames = walk(positions, windows, 2., 1., 4.)
    assert np.any(np.isclose(frames, windows[0][0], rtol=0, atol=1e-9))
    assert np.any(np.isclose(frames, windows[0][1], rtol=0, atol=1e-9))
    assert len(frames) > 10
    assert earth_encounter_windows(positions[:, :2], 10.) == []
    assert segment_radius_interval(np.array([-2., 1.]), np.array([2., 1.]), 1.) == (0.5, 0.5)
    print('Alle Nahansicht-Tests bestanden.')


if __name__ == '__main__':
    main()
