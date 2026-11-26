"""Force-bench adapter; source geometry stays fixed while orbit and clock operators are varied."""
from collections import OrderedDict
import copy
import json
import math
import threading
import time

import numpy as np
from scipy.integrate import solve_ivp
import timelike_orbits as core

GM_SUN_NOMINAL = 1.3271244e20
_CACHE = OrderedDict()
_LOCK = threading.RLock()


def kernel_configuration(params):
    cycles = params['radial_cycles']
    core.require(type(cycles) in (int, float) and math.isfinite(cycles) and cycles == int(cycles), 'Escolha um número inteiro de ciclos.')
    core.require(params['orbit_kind'] in ['eccentric', 'circular'] and params['orientation'] in ['positive', 'negative'], 'Forma ou sentido da órbita inválido.')
    return core.configuration(dict(mu_m3_s2=GM_SUN_NOMINAL*params['mass_solar'],
                                   semi_latus_rectum_rs=params['semi_latus_rectum_rs'],
                                   eccentricity=0. if params['orbit_kind'] == 'circular' else params['eccentricity'],
                                   source_radius_rs=1., radial_cycles=int(cycles), output_samples=1025,
                                   orientation=1 if params['orientation'] == 'positive' else -1))


def straight_clock(times, radius0, tangent, kappa, *, cancelled=None, max_seconds=15., max_rhs=300000):
    """Proper clock on the coordinate-straight, accelerated worldline in the fixed reference metric."""
    start = time.perf_counter()
    calls = 0
    times = np.asarray(times, dtype=float)
    core.require(times.ndim == 1 and len(times) >= 2 and times[0] == 0 and np.all(np.diff(times) > 0), 'Grade de relógio inválida.')

    def check():
        if cancelled is not None and cancelled():
            raise core.Cancelled('Cálculo cancelado sem resultado parcial publicado.')
        if time.perf_counter()-start > max_seconds or calls > max_rhs:
            raise core.BudgetExceeded('Orçamento do relógio excedido.')

    def rates(tt):
        radius = np.sqrt(radius0*radius0+(tangent*tt)**2)
        lapse = 1-kappa/radius
        radial = tangent*tangent*tt/radius
        transverse = radius0*tangent/radius
        decrement = kappa*(1/radius+(radial*radial/lapse+transverse*transverse)/2)
        core.require(np.all(lapse > 0) and np.all(decrement >= 0) and np.all(decrement < 1), 'A linha de mundo deixou de ser temporal no exterior.')
        q = np.sqrt(1-decrement)
        return q, decrement/(1+q)

    def rhs(tt, _):
        nonlocal calls
        calls += 1
        check()
        return [float(rates(tt)[1])]

    check()
    solution = solve_ivp(rhs, (0, float(times[-1])), [0.], method='DOP853', rtol=2e-12, atol=2e-14,
                         dense_output=True, max_step=float(times[-1])/256)
    core.require(solution.success, 'Relógio não convergiu.')
    lag = solution.sol(times)[0]
    rate = rates(times)[0]
    check()
    return lag, rate, dict(rhs_calls=calls, nodes=solution.t.tolist(), lag=solution.y[0].tolist())


def experiment(params, controls, *, cancelled=None):
    began = time.perf_counter()
    cfg = kernel_configuration(params)
    key = core.digest(cfg)

    def check():
        if cancelled is not None and cancelled():
            raise core.Cancelled('Cálculo cancelado sem resultado parcial publicado.')
        if time.perf_counter()-began > 15:
            raise core.BudgetExceeded('Orçamento da bancada excedido.')

    check()
    with _LOCK:
        baseline = _CACHE.get(key)
        if baseline is not None:
            _CACHE.move_to_end(key)
    work = 0
    if baseline is None:
        baseline = core.experiment(cfg, cancelled=cancelled, max_seconds=max(.001, 15-(time.perf_counter()-began)))
        work = baseline['solver']['rhs_calls']
        # Execution wall time is diagnostic, not a physical quantity or part of a visibility comparison.
        baseline['solver'].pop('wall_seconds')
        with _LOCK:
            _CACHE[key] = baseline
            _CACHE.move_to_end(key)
            while len(_CACHE) > 4:
                _CACHE.popitem(last=False)
    gravity = controls['gravity']
    orbit_on = gravity['acting'] and gravity['effects']['orbital_acceleration']
    clock_on = gravity['acting'] and gravity['effects']['proper_clock_rate']
    tt = np.asarray(baseline['coordinate_time_scaled'])
    length, time_unit = baseline['units']['length_m'], baseline['units']['time_s']
    kappa = baseline['constants']['kappa']
    radius0 = baseline['gr']['radius_scaled'][0]
    tangent = baseline['gr']['velocities_coordinate_scaled'][0][1]
    clock_nodes = None
    if orbit_on:
        positions = copy.deepcopy(baseline['gr']['positions_scaled'])
        velocity = copy.deepcopy(baseline['gr']['velocities_coordinate_scaled'])
        radius = np.asarray(baseline['gr']['radius_scaled'])
        physical_lag = np.asarray(baseline['clock_lag_scaled'])
        physical_rate = np.asarray(baseline['gr']['proper_clock_rate'])
        trajectory_kind = 'schwarzschild_timelike_geodesic'
    else:
        positions = np.column_stack((np.full(len(tt), radius0), tangent*tt, np.zeros(len(tt)))).tolist()
        velocity = np.column_stack((np.zeros(len(tt)), np.full(len(tt), tangent), np.zeros(len(tt)))).tolist()
        radius = np.linalg.norm(positions, axis=1)
        physical_lag, physical_rate, clock_nodes = straight_clock(tt, radius0, tangent, kappa, cancelled=cancelled,
            max_seconds=max(.001, 15-(time.perf_counter()-began)), max_rhs=300000-work)
        trajectory_kind = 'coordinate_straight_intervention_not_geodesic'
    lag = physical_lag if clock_on else np.zeros(len(tt))
    rate = physical_rate if clock_on else np.ones(len(tt))
    actual_proper = (tt-lag)*time_unit
    samples = []
    for index in range(len(tt)):
        samples.append(dict(index=index, coordinate_time_s=float(tt[index]*time_unit),
                            applied_clock_time_s=float(actual_proper[index]), applied_lag_s=float(lag[index]*time_unit),
                            applied_clock_rate=float(rate[index]),
                            metric_worldline_proper_time_s=float((tt[index]-physical_lag[index])*time_unit),
                            metric_worldline_clock_rate=float(physical_rate[index]),
                            gr_reference_lag_s=float(baseline['clock_lag_scaled'][index]*time_unit),
                            radius_m=float(radius[index]*length),
                            velocity_coordinate_m_s=(np.asarray(velocity[index])*baseline['units']['speed_m_s']).tolist()))
    probes = []
    for shell in [1/(1+cfg['eccentricity']), 1., 1/(1-cfg['eccentricity'])]:
        for index in range(12):
            z = 1-2*(index+.5)/12
            angle = index*math.pi*(3-math.sqrt(5))
            physical_r = shell*length
            probes.append(dict(position=[shell*math.sqrt(1-z*z)*math.cos(angle), shell*math.sqrt(1-z*z)*math.sin(angle), shell*z],
                               radius_rs=physical_r/baseline['units']['schwarzschild_radius_m'],
                               static_clock_ratio=math.sqrt(1-baseline['units']['schwarzschild_radius_m']/physical_r),
                               kretschmann_m_minus4=12*baseline['units']['schwarzschild_radius_m']**2/physical_r**6))
    reference = dict(configuration_sha256=baseline['configuration_sha256'], constants=copy.deepcopy(baseline['constants']),
                     measurements=copy.deepcopy(baseline['measurements']), newton_elements={key: baseline['newton'][key] for key in [
                         'semi_major_scaled','eccentricity','radial_period_scaled','energy_scaled','angular_momentum_scaled']},
                     channel_dependencies='Newton e GR partem da mesma posição e velocidade coordenadas em t. As velocidades locais são distintas. Sem acoplamento aos corpos do Atlas.')
    advance = baseline['measurements']['apsidal_advance_rad_per_cycle']
    result = dict(model='Geodésica temporal Schwarzschild por DOP853; comparação Newtoniana por Kepler e relógio pela métrica.',
                  domain='Partícula-teste em campo fraco exterior a uma fonte esférica estática idealizada, sem spin/carga. Sem reação, outros corpos, radiação ou auto-força. A fonte não é um objeto observado do Atlas. Suprimir a atuação orbital cria uma reta coordenada hipotética, não uma geodésica. O relógio é calculado sobre a trajetória escolhida; suprimir seu efeito aplica ritmo1.',
                  influences=['gravity'], positions=positions, reference_positions=copy.deepcopy(baseline['newton']['positions_scaled']),
                  time_s=(tt*time_unit).tolist(), time_display=dict(unit='s',seconds_per_unit=1,symbol='t'),
                  position_unit_m=length, position_label='semilatus rectum relativístico', view_extent=3., field=[],
                  metric_probes=probes, reference=reference,
                  timelike=dict(format='c214.force-orbits/0.1.0', configuration=cfg, trajectory_kind=trajectory_kind,
                                orbit_effect_applied=orbit_on, clock_effect_applied=clock_on,
                                clock_kind='worldline_proper_time' if clock_on else 'rate_one_intervention',
                                readings=samples, source_radius_scaled=kappa, cycle_kind=baseline['measurements']['period_kind'],
                                apsides=copy.deepcopy(baseline['pericenters']) if orbit_on else [],
                                baseline_gr_positions=copy.deepcopy(baseline['gr']['positions_scaled']),
                                baseline_internal_nodes=copy.deepcopy(baseline['internal_nodes']),
                                intervention_clock_nodes=clock_nodes),
                  measurements=[dict(label='Precessão GR de referência por ciclo',value=advance,unit='rad'),
                                dict(label='Ciclos calculados de referência',value=cfg['radial_cycles'],unit='voltas' if cfg['eccentricity']==0 else 'ciclos radiais'),
                                dict(label='Tempo coordenado final · relógio no infinito',value=float(tt[-1]*time_unit),unit='s'),
                                dict(label='Tempo indicado pelo relógio aplicado',value=float(actual_proper[-1]),unit='s'),
                                dict(label='Atraso aplicado em relação a t',value=float(lag[-1]*time_unit),unit='s'),
                                dict(label='Atraso GR de referência',value=float(baseline['clock_lag_scaled'][-1]*time_unit),unit='s'),
                                dict(label='Ritmo final do relógio aplicado / t',value=float(rate[-1]),unit='s/s'),
                                dict(label='Resíduo máximo da energia radial GR',value=baseline['measurements']['maximum_radial_invariant_residual'],unit='adimensional')],
                  sources=list(core.SOURCES))
    check()
    json.dumps(result, allow_nan=False)
    check()
    return result
