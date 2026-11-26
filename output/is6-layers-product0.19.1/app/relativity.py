"""Schwarzschild null geodesics outside a nonrotating, uncharged black hole.

R=r/r_s; affine parameter L=c*lambda/r_s is normalized to unit conserved
energy at infinity. It is not coordinate time or a photon's proper time.
The counterfactual removes the curvature term with identical initial
coordinate position/tangent; the displayed reference metric stays fixed.
"""
import math
import numpy as np
from scipy.integrate import quad, solve_ivp
from scipy.constants import c

GM_SUN = 1.3271244e20
CRITICAL_B = 3*math.sqrt(3)/2
INNER_R = 1.001
SOURCE = 'https://ned.ipac.caltech.edu/level5/March01/Carroll3/Carroll7.html'


def trace_ray(impact_rs, *, tolerance=1e-11):
    """Integrate a ray arriving from infinity, starting on a finite shell.

    dR/dL=v, dv/dL=b²/R³-3b²/(2R⁴), dphi/dL=b/R².
    Invariant: v²+b²/R²-b²/R³=1. The initial angle includes the
    infinity-to-shell tail, so b retains its asymptotic definition.
    """
    b = float(impact_rs)
    start = max(100., 20*b)
    u0 = 1/start
    tail = quad(lambda u: 1/math.sqrt(1/b**2-u*u+u**3), 0, u0,
                epsabs=1e-13, epsrel=1e-12)[0]
    velocity = -math.sqrt(1-b*b/start**2+b*b/start**3)
    def rhs(_, y):
        radius, radial, _ = y
        return [radial, b*b/radius**3-1.5*b*b/radius**4, b/radius**2]
    def outer(_, y): return y[0]-start
    def inner(_, y): return y[0]-INNER_R
    def angular(_, y): return y[2]-tail-12*math.pi
    def periapsis(_, y): return y[1]
    outer.direction, outer.terminal = 1, True
    inner.direction, inner.terminal = -1, True
    angular.direction, angular.terminal = 1, True
    periapsis.direction, periapsis.terminal = 1, False
    solution = solve_ivp(rhs, (0, 4*start+80*math.pi*b), [start, velocity, tail],
                         method='DOP853', rtol=tolerance, atol=tolerance*.01,
                         events=(outer, inner, angular, periapsis), dense_output=True)
    if not solution.success:
        raise RuntimeError('A geodésica não convergiu no domínio exterior.')
    status = next((name for name, events in zip(('escaped', 'captured', 'angular_limit'),
                                                solution.t_events[:3]) if len(events)), 'affine_limit')
    if abs(b/CRITICAL_B-1) < 1e-8:
        status = 'near_critical_unresolved'
    times = np.linspace(0, solution.t[-1], 241)
    radius, radial, angle = solution.sol(times)
    # Include solver nodes in invariant check: the plotted 241 states are not
    # sufficient to detect an error hidden between animation frames.
    rr, vv, _ = solution.y
    invariant = vv*vv+b*b/rr**2-b*b/rr**3
    closest = float(solution.y_events[3][0][0]) if len(solution.y_events[3]) else float(radius.min())
    return {'positions': np.column_stack((radius*np.cos(angle), radius*np.sin(angle), radius*0)).tolist(),
            'affine_rs': times.tolist(), 'radii_rs': radius.tolist(),
            'status': status, 'minimum_radius_rs': closest,
            'deflection_rad': float(angle[-1]-tail+2*tail-math.pi) if status == 'escaped' else None,
            'invariant_error': float(np.max(np.abs(invariant-1))),
            'start_radius_rs': start, 'initial_angle_rad': tail, 'initial_radial_derivative': velocity}


def straight_ray(reference, impact_rs):
    """Exact line with the same initial coordinate tangent; no integration."""
    r, phi, v = (reference[key] for key in ('start_radius_rs', 'initial_angle_rad', 'initial_radial_derivative'))
    b = impact_rs
    position = np.array([r*math.cos(phi), r*math.sin(phi), 0.])
    velocity = np.array([v*math.cos(phi)-b/r*math.sin(phi),
                         v*math.sin(phi)+b/r*math.cos(phi), 0.])
    duration = -2*np.dot(position, velocity)/np.dot(velocity, velocity)
    times = np.linspace(0, duration, 241)
    points = position+times[:, None]*velocity
    closest = np.linalg.norm(np.cross(position, velocity))/np.linalg.norm(velocity)
    return {'positions': points.tolist(), 'affine_rs': times.tolist(),
            'radii_rs': np.linalg.norm(points, axis=1).tolist(), 'status': 'straight_counterfactual',
            'minimum_radius_rs': float(closest), 'deflection_rad': 0., 'invariant_error': 0.}


def experiment(params, controls):
    mass, b, probe = (params[key] for key in ('mass_solar', 'impact_rs', 'probe_rs'))
    gravity = controls['gravity']
    bending = gravity['acting'] and gravity['effects']['ray_bending']
    clock = gravity['acting'] and gravity['effects']['static_clock_rate']
    baseline = trace_ray(b)
    actual = baseline if bending else straight_ray(baseline, b)
    rs = 2*GM_SUN*mass/c**2
    ratio = math.sqrt(1-1/probe)
    probes = []
    for shell in (2., 3., 5.):
        for i in range(24):
            z = 1-2*(i+.5)/24
            angle = i*math.pi*(3-math.sqrt(5))
            position = [shell*math.sqrt(1-z*z)*math.cos(angle),
                        shell*math.sqrt(1-z*z)*math.sin(angle), shell*z]
            probes.append({'position': position, 'radius_rs': shell,
                           'static_clock_ratio': math.sqrt(1-1/shell),
                           'kretschmann_m_minus4': 12/(rs**4*shell**6)})
    measurements = [
        {'label': 'Raio de Schwarzschild', 'value': rs, 'unit': 'm'},
        {'label': 'Ritmo aplicado do relógio estático / infinito', 'value': ratio if clock else 1., 'unit': 's/s'},
        {'label': 'Menor raio da trajetória', 'value': actual['minimum_radius_rs'], 'unit': 'rₛ'},
        {'label': 'Desvio assintótico da luz', 'value': actual['deflection_rad'], 'unit': 'rad'},
        {'label': 'Resíduo da constante de movimento', 'value': actual['invariant_error'], 'unit': 'absoluto'},
        {'label': 'Curvatura de Kretschmann na sonda', 'value': 12/(rs**4*probe**6), 'unit': 'm⁻⁴'},
    ]
    return {'model': 'Geodésica nula da métrica de Schwarzschild; integração DOP853 e relógio estático exato.',
            'domain': 'Buraco negro esférico sem rotação/carga; raio exterior r ≥ 1,001 rₛ. Captura termina nessa fronteira. Limites de 12π em ângulo e duração afim finita; faixa relativa de 10⁻⁸ ao impacto crítico tem destino não resolvido. Sem Kerr, disco, plasma ou imagem completa. Suprimir o termo de curvatura mantém o estado inicial e a referência: hipótese, não solução de Einstein.',
            'influences': ['gravity'], 'positions': actual['positions'],
            'reference_positions': baseline['positions'],
            'time_s': (np.array(actual['affine_rs'])*rs/c).tolist(),
            'time_display': {'unit': 's de parâmetro afim', 'seconds_per_unit': 1, 'symbol': 'λ'},
            'parameter_note': 'λ é um parâmetro afim normalizado por E∞=1; não é tempo de observador nem tempo próprio da luz. A evolução mantém c local.',
            'position_unit_m': rs, 'position_label': 'raio de Schwarzschild',
            'view_extent': max(6., 2.5*b), 'field': [], 'metric_probes': probes,
            'reference': {'schwarzschild_radius_m': rs, 'photon_sphere_rs': 1.5,
                          'critical_impact_rs': CRITICAL_B, 'static_clock_ratio': ratio,
                          'probe_radius_m': probe*rs, 'kretschmann_m_minus4': 12/(rs**4*probe**6),
                          'deflection_rad': baseline['deflection_rad'], 'status': baseline['status']},
            'ray': {'status': actual['status'], 'reference_status': baseline['status'],
                    'curvature_term_applied': bending, 'clock_effect_applied': clock,
                    'impact_rs': b, 'minimum_radius_rs': actual['minimum_radius_rs'],
                    'inner_boundary_rs': INNER_R, 'affine_normalization': 'E at infinity = 1'},
            'measurements': measurements, 'sources': [SOURCE]}
