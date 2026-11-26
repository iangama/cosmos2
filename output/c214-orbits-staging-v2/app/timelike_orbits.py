"""Bound Schwarzschild test-particle orbits; proper-time IVP and shared-coordinate Newton reference."""
import copy
import hashlib
import json
import math
import time

import numpy as np
from scipy.integrate import solve_ivp

C = 299792458.0
VERSION = 'c214.bound-timelike/0.1.0'
DEFAULTS = dict(mu_m3_s2=1.3271244e21, semi_latus_rectum_rs=10000., eccentricity=.2,
                source_radius_rs=1., radial_cycles=4, output_samples=1025, orientation=1)
SOURCES = ['https://arxiv.org/pdf/gr-qc/9712019', 'https://arxiv.org/pdf/1512.01556v2']


class DomainError(ValueError):
    pass


class BudgetExceeded(RuntimeError):
    pass


class Cancelled(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise DomainError(message)


def configuration(value=None):
    require(value is None or type(value) is dict, 'Objeto de parâmetros obrigatório.')
    value = {} if value is None else value
    require(not set(value)-set(DEFAULTS), 'Parâmetro desconhecido.')
    result = copy.deepcopy(DEFAULTS | value)
    for name in ['mu_m3_s2', 'semi_latus_rectum_rs', 'eccentricity', 'source_radius_rs']:
        number = result[name]
        require(type(number) in (int, float) and math.isfinite(number), 'Número finito obrigatório: '+name)
        result[name] = float(number)
    require(1e5 <= result['mu_m3_s2'] <= 1e32, 'GM fora do domínio adotado.')
    require(1e3 <= result['semi_latus_rectum_rs'] <= 1e8, 'Semilatus rectum fora do campo fraco adotado.')
    eccentricity = result['eccentricity']
    require(eccentricity == 0 or .05 <= eccentricity <= .8, 'Usar círculo ou excentricidade entre 0,05 e 0,8.')
    require(result['source_radius_rs'] >= 1 and result['semi_latus_rectum_rs']/(1+eccentricity) >= 1.001*result['source_radius_rs'],
            'Órbita fora do domínio exterior da fonte.')
    for name, lower, upper in [('radial_cycles', 1, 16), ('output_samples', 257, 4097)]:
        require(type(result[name]) is int and lower <= result[name] <= upper, 'Inteiro fora do orçamento: '+name)
    require(type(result['orientation']) is int and result['orientation'] in [-1, 1], 'Orientação deve ser+1 ou-1.')
    return result


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def newton_reference(times, radius0, tangent0, orientation):
    """Closed Kepler ellipse from the shared coordinate tangent, not the GR turning points."""
    angular = radius0*abs(tangent0)
    energy = tangent0*tangent0/2-1/radius0
    require(energy < 0, 'Referência Newtoniana não ligada.')
    semi_major = -1/(2*energy)
    eccentricity = angular*angular/radius0-1
    require(-1e-13 <= eccentricity < 1, 'Estado inicial Newtoniano não é periastro ligado.')
    eccentricity = max(0., eccentricity)
    mean = np.asarray(times)/semi_major**1.5
    winding = np.floor((mean+math.pi)/(2*math.pi))
    reduced = mean-winding*(2*math.pi)
    anomaly = reduced.copy()
    for _ in range(24):
        residual = anomaly-eccentricity*np.sin(anomaly)-reduced
        change = residual/(1-eccentricity*np.cos(anomaly))
        anomaly -= change
        if np.max(np.abs(change)) <= 4e-15:
            break
    require(np.max(np.abs(anomaly-eccentricity*np.sin(anomaly)-reduced)) < 2e-13, 'Equação de Kepler não convergiu.')
    cosine, sine = np.cos(anomaly), np.sin(anomaly)
    root = math.sqrt(1-eccentricity*eccentricity)
    positions = np.column_stack((semi_major*(cosine-eccentricity), orientation*semi_major*root*sine, np.zeros(len(times))))
    rate = semi_major**-1.5/(1-eccentricity*cosine)
    velocity = np.column_stack((-semi_major*sine*rate, orientation*semi_major*root*cosine*rate, np.zeros(len(times))))
    radius = np.linalg.norm(positions, axis=1)
    measured_energy = np.sum(velocity*velocity, axis=1)/2-1/radius
    measured_angular = np.cross(positions, velocity)[:, 2]
    return dict(positions_scaled=positions.tolist(), velocities_coordinate_scaled=velocity.tolist(),
                radius_scaled=radius.tolist(), phi_rad=(orientation*(np.arctan2(root*sine, cosine-eccentricity)+winding*2*math.pi)).tolist(),
                semi_major_scaled=semi_major, eccentricity=eccentricity, radial_period_scaled=2*math.pi*semi_major**1.5,
                energy_scaled=energy, angular_momentum_scaled=orientation*angular,
                maximum_energy_residual=float(np.max(np.abs(measured_energy-energy))),
                maximum_angular_residual=float(np.max(np.abs(measured_angular-orientation*angular))),
                time_kind='Newtonian absolute time, matched to the shared Schwarzschild coordinate-time grid')


def experiment(value=None, *, refined=False, cancelled=None, max_seconds=15., max_rhs=300000):
    cfg = configuration(value)
    require(type(refined) is bool, 'Refinamento deve ser booleano.')
    require(type(max_seconds) in (int, float) and math.isfinite(max_seconds) and 0 < max_seconds <= 15, 'Orçamento de tempo inválido.')
    require(type(max_rhs) is int and 1 <= max_rhs <= 300000, 'Orçamento RHS inválido.')
    require(cancelled is None or callable(cancelled), 'Cancelamento inválido.')
    began = time.perf_counter()
    calls = 0

    def budget():
        if cancelled is not None and cancelled():
            raise Cancelled('Cálculo cancelado sem resultado parcial publicado.')
        if time.perf_counter()-began > max_seconds or calls > max_rhs:
            raise BudgetExceeded('Orçamento de órbita excedido; resultado incompleto recusado.')

    budget()
    mu = cfg['mu_m3_s2']
    rs = 2*mu/C**2
    length = cfg['semi_latus_rectum_rs']*rs
    time_unit = length*math.sqrt(length/mu)
    speed_unit = length/time_unit
    kappa = 1/cfg['semi_latus_rectum_rs']
    eccentricity, direction = cfg['eccentricity'], cfg['orientation']
    cycles, count = cfg['radial_cycles'], cfg['output_samples']
    denominator = 1-(3+eccentricity*eccentricity)*kappa/2
    angular = direction/math.sqrt(denominator)
    energy = math.sqrt(((1-kappa)**2-(eccentricity*kappa)**2)/denominator)
    invariant = -(1-eccentricity*eccentricity)*(1-2*kappa)/(2*denominator)
    radius0 = 1/(1+eccentricity)
    source_radius = cfg['source_radius_rs']/cfg['semi_latus_rectum_rs']

    def lag_rate(radius):
        return kappa*(invariant/(energy+1)+1/radius)/(1-kappa/radius)

    def rhs(_, state):
        nonlocal calls
        calls += 1
        budget()
        radius, radial, _, _ = state
        require(math.isfinite(radius) and radius > source_radius, 'Solver deixou o domínio exterior da fonte.')
        square = angular*angular
        return [radial, -1/radius**2+square/radius**3-1.5*kappa*square/radius**4,
                angular/radius**2, lag_rate(radius)]

    if eccentricity == 0:
        clock_ratio = math.sqrt(denominator)
        coordinate_end = cycles*2*math.pi
        proper_end = coordinate_end*clock_ratio
        coordinate = np.linspace(0, coordinate_end, count)
        proper = coordinate*clock_ratio
        lag = coordinate*(1-clock_ratio)
        # Rationalize the small clock difference; do not subtract close clocks.
        lag = coordinate*(1.5*kappa)/(1+clock_ratio)
        radius = np.ones(count)
        radial = np.zeros(count)
        phi = direction*coordinate
        states = np.vstack((radius, radial, phi, lag))
        nodes = dict(proper_time_scaled=[0., proper_end], states_scaled=[states[:, 0].tolist(), states[:, -1].tolist()])
        pericenters, apocenters = [], []
        advance = None
        inverse_residual = float(np.max(np.abs(proper+lag-coordinate)))
        tangent0 = float(direction)
    else:
        period_guess = 2*math.pi/(1-eccentricity*eccentricity)**1.5

        def peri(_, state):
            return state[1]

        def apo(_, state):
            return state[1]

        peri.direction, peri.terminal = 1, cycles+1
        apo.direction = -1
        solution = solve_ivp(rhs, (0, 1.1*cycles*period_guess), [radius0, 0., 0., 0.], method='DOP853',
                             rtol=2e-13 if refined else 2e-12, atol=2e-15 if refined else 2e-14,
                             max_step=period_guess/(256 if refined else 128), dense_output=True, events=[peri, apo])
        require(solution.success and solution.status == 1 and len(solution.t_events[0]) == cycles+1 and solution.t_events[0][0] == 0,
                'Solver não completou os retornos apsidais declarados.')
        require(len(solution.t_events[1]) == cycles, 'Número de apoastros difere do orçamento.')
        proper_end = float(solution.t_events[0][-1])
        final = solution.y_events[0][-1]
        coordinate_end = proper_end+float(final[3])
        coordinate = np.linspace(0, coordinate_end, count)
        node_times = solution.t+solution.y[3]
        require(np.all(np.diff(node_times) > 0), 'Tempo coordenado deixou de ser monotônico.')
        proper = np.interp(coordinate, node_times, solution.t)
        for _ in range(12):
            budget()
            values = solution.sol(proper)
            residual = proper+values[3]-coordinate
            if np.max(np.abs(residual)) <= 2e-13*max(1., coordinate_end):
                break
            proper = np.clip(proper-residual/(1+lag_rate(values[0])), 0, proper_end)
        states = solution.sol(proper)
        radius, radial, phi, lag = states
        inverse_residual = float(np.max(np.abs(proper+lag-coordinate)))
        require(inverse_residual <= 2e-11*max(1., coordinate_end), 'Inversão do tempo coordenado não convergiu.')
        nodes = dict(proper_time_scaled=solution.t.tolist(), states_scaled=solution.y.T.tolist())

        def events(index):
            return [dict(proper_time_scaled=float(s), coordinate_time_scaled=float(s+y[3]),
                         radius_scaled=float(y[0]), phi_rad=float(y[2]), lag_scaled=float(y[3]))
                    for s, y in zip(solution.t_events[index], solution.y_events[index], strict=True)]

        pericenters, apocenters = events(0), events(1)
        advance = math.fsum([direction*float(final[2]), -cycles*2*math.pi])/cycles
        tangent0 = angular*(1-kappa/radius0)/(energy*radius0)

    budget()
    # Admit both internal solver nodes and the presentation grid.
    inspected = np.column_stack((states, np.asarray(nodes['states_scaled']).T))
    rr, uu, _, _ = inspected
    values_i = uu*uu/2+angular*angular/(2*rr*rr)-1/rr-kappa*angular*angular/(2*rr**3)
    lapse = 1-kappa/rr
    tdot = 1+lag_rate(rr)
    metric_residual = -lapse*tdot*tdot+kappa*uu*uu/(2*lapse)+kappa*angular*angular/(2*rr*rr)+1
    require(np.all(np.isfinite(inspected)) and np.all(rr > source_radius), 'Estado geodésico inválido/fora da fonte.')
    tdot_samples = 1+lag_rate(radius)
    radial_coordinate = radial/tdot_samples
    transverse_coordinate = angular/(radius*tdot_samples)
    cs, sn = np.cos(phi), np.sin(phi)
    positions = np.column_stack((radius*cs, radius*sn, np.zeros(count)))
    velocities = np.column_stack((radial_coordinate*cs-transverse_coordinate*sn,
                                  radial_coordinate*sn+transverse_coordinate*cs, np.zeros(count)))
    reference = newton_reference(coordinate, radius0, tangent0, direction)
    budget()
    result = dict(format=VERSION, completed=True, configuration=cfg, configuration_sha256=digest(cfg),
                  model=dict(id='Schwarzschild timelike geodesic, test-mass limit', coordinates='Schwarzschild areal radius, equatorial plane',
                             common_initial_state='Equal areal position and coordinate-time tangent; local measured speeds differ between metrics',
                             source='Idealized spherical static source with declared exterior boundary',
                             limits='Bound weak-field test particle only; no spin, charge, reaction, other bodies, self-force or radiation'),
                  units=dict(length_m=length, time_s=time_unit, speed_m_s=speed_unit, schwarzschild_radius_m=rs,
                             source_radius_m=cfg['source_radius_rs']*rs),
                  constants=dict(kappa=kappa, energy_per_c2=energy, angular_scaled=angular, radial_invariant=invariant),
                  coordinate_time_scaled=coordinate.tolist(), proper_time_scaled=proper.tolist(), clock_lag_scaled=lag.tolist(),
                  gr=dict(positions_scaled=positions.tolist(), velocities_coordinate_scaled=velocities.tolist(),
                          radius_scaled=radius.tolist(), phi_rad=phi.tolist(), proper_clock_rate=(1/tdot_samples).tolist(),
                          static_clock_rate=np.sqrt(1-kappa/radius).tolist(),
                          local_radial_speed_over_c=(math.sqrt(kappa/2)*radial/(tdot_samples*(1-kappa/radius))).tolist(),
                          local_transverse_speed_over_c=(math.sqrt(kappa/2)*angular/(radius*tdot_samples*np.sqrt(1-kappa/radius))).tolist()),
                  newton=reference, pericenters=pericenters, apocenters=apocenters,
                  measurements=dict(apsidal_advance_rad_per_cycle=advance, apsidal_defined=eccentricity != 0,
                                    period_kind='circular azimuthal revolution' if eccentricity == 0 else 'radial libration',
                                    cycle_period_coordinate_scaled=coordinate_end/cycles,
                                    cycle_period_proper_scaled=proper_end/cycles,
                                    radial_period_coordinate_scaled=coordinate_end/cycles if eccentricity else None,
                                    radial_period_proper_scaled=proper_end/cycles if eccentricity else None,
                                    accumulated_clock_lag_scaled=float(lag[-1]),
                                    average_proper_over_coordinate=1-float(lag[-1])/coordinate_end,
                                    maximum_radial_invariant_residual=float(np.max(np.abs(values_i-invariant))),
                                    maximum_metric_residual=float(np.max(np.abs(metric_residual))),
                                    maximum_time_inverse_residual=inverse_residual),
                  internal_nodes=nodes, solver=dict(method='closed circular geodesic' if eccentricity == 0 else 'DOP853 proper-time IVP',
                                                    refined=refined, rhs_calls=calls, wall_seconds=time.perf_counter()-began,
                                                    maximum_rhs=max_rhs, maximum_seconds=max_seconds), sources=SOURCES)
    # Reject a broken numerical solution rather than publishing it as a completed experiment.
    require(result['measurements']['maximum_radial_invariant_residual'] <= 2e-10 and
            result['measurements']['maximum_metric_residual'] <= 2e-12, 'Invariante geodésico excedeu o contrato.')
    json.dumps(result, allow_nan=False)
    budget()
    result['solver']['wall_seconds'] = time.perf_counter()-began
    return result
