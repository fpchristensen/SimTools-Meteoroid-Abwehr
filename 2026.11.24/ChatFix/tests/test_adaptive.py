"""Physik, Kontakt, Impulserhaltung und adaptive Zeitachse ohne Qt testen."""
import numpy as np
from classes_functions import (CelestialBody, create_bodies, catalog_settings,
                               simulate_trajectory, trajectory_windows, trajectory_next_frame)
from values import (N, dt, METEOROIDEN_KATALOG, CLOSEUP_DISTANCE,
                    CLOSEUP_MAX_FRAME_STEP, CLOSEUP_DISTANCE_FRACTION, IMPACT_AFTERGLOW_SECONDS)


def verify_catalog():
    """Alle 20 ursprünglich auf Stundenwerte abgestimmten Bahnen prüfen."""
    for entry in METEOROIDEN_KATALOG:
        bodies = create_bodies([catalog_settings(entry['id'], 'M')])
        tr = simulate_trajectory(bodies, N, dt)
        assert len(tr.impacts) == 1 and tr.impacts[0].pair == (1, 2), entry['id']
        assert abs(tr.frames[-1]*dt/86400-entry['target_impact_day']) < 0.05, entry['id']
        assert abs(np.linalg.norm(tr.positions[-1, 2]-tr.positions[-1, 1]) - bodies[1].radius - bodies[2].radius) < 0.01
    print('20/20 Katalogbahnen treffen zum vorgesehenen Tag.')


def main():
    """Prüft beide Kollisionsmodi, Vorbeiflug und Wiedergabe; danach den Katalog."""
    spec = catalog_settings('leicht_03', 'M')
    bodies = create_bodies([spec])
    tr = simulate_trajectory(bodies, N, dt, stop_on_impact=False)
    event = tr.impacts[0]
    assert tr.frames[-1] == N and event.frame < N
    assert np.all(np.diff(tr.frames)>0)
    i = tr.index(event.frame)
    assert np.isfinite(tr.positions[i, 2]).all()
    assert np.isnan(tr.positions[i+1:, 2]).all()
    assert np.isfinite(tr.positions[:, 1]).all()
    assert event.energy > 0 and np.linalg.norm(event.delta_v)>0
    assert np.isclose(bodies[1].mass, 5.972e24 + spec.mass_kg, rtol=0, atol=1e9)
    delta = np.diff(tr.frames)*dt
    assert np.any(np.isclose(delta, 3600, atol=1e-6))
    for step in (60,10,1):
        assert np.any(np.isclose(delta,step,atol=1e-6)), step
    windows = trajectory_windows(tr, CLOSEUP_DISTANCE, dt, IMPACT_AFTERGLOW_SECONDS)
    seen=[]; f=0.
    while f < N-1e-9:
        nxt = trajectory_next_frame(tr,f,24,windows,bodies[1].radius,
                                    CLOSEUP_MAX_FRAME_STEP,CLOSEUP_DISTANCE_FRACTION,dt)
        assert nxt>f
        seen.append(nxt); f=nxt
        assert len(seen)<20000
    assert any(abs(f-event.frame)<1e-8 for f in seen)
    assert sum(event.frame<f<event.frame+IMPACT_AFTERGLOW_SECONDS/dt for f in seen)>20
    # Close-up aus: gleiche Physik, normale Geschwindigkeit, Kontakt bleibt registriert.
    assert trajectory_next_frame(tr,0,24,[],bodies[1].radius,.2,.06,dt)==24
    # Kleine Abwehr: enger Vorbeiflug mit gekrümmter Bahn statt Stunden-Knick.
    fly = simulate_trajectory(create_bodies([spec]),N,dt,[dict(frame=0,target='M',impulse=1e10,angle=50)])
    assert not fly.impacts
    rel = fly.positions[:,2]-fly.positions[:,1]
    assert np.min(np.linalg.norm(rel,axis=1)) < CLOSEUP_DISTANCE
    assert np.any(np.isclose(np.diff(fly.frames)*dt,1,atol=1e-6)) or np.any(np.isclose(np.diff(fly.frames)*dt,10,atol=1e-6))
    # Analytisch kontrollierbarer kleiner Stoß; spätere Abwehr auf aufgenommenen Körper ignorieren.
    b = [CelestialBody('Erde',1000.,10.,[0,0],[0,0]), CelestialBody('M',100.,1.,[-100,0],[20,0])]
    simple = simulate_trajectory(b,3,10,[dict(frame=1,target='M',impulse=1000.,angle=0)],False)
    e = simple.impacts[0]
    assert abs(e.frame*10-4.45) < 1e-5
    assert np.allclose(b[0].v,[2000/1100,0],rtol=1e-8)
    assert b[0].mass==1100
    assert np.isclose(e.energy,0.5*(1000*100/1100)*20**2,rtol=1e-8)
    verify_catalog()
    print('Adaptive Physik, Aufschlag und Playback erfolgreich.')

if __name__=='__main__':
    main()
