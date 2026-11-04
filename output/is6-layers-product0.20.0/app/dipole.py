"""Full classical gyro-orbits in prescribed static dipole and Newton gravity.

The magnetic moment is an adiabatic diagnostic, never an applied mirror force.
There is no IGRF, atmosphere, collective plasma or Earth rotation in this model.
"""
import math
import time

import numpy as np
from scipy.constants import elementary_charge, proton_mass, c
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

RADIUS_M = 6.371e6  # Prescribed spherical radius, not a geodetic ellipsoid
GM_EARTH = 3.986004e14  # IAU2015 nominal terrestrial mass parameter
OUTER_RADIUS = 10.0
MAX_TRACE = 12001
MAX_EVALUATIONS = 180000
SOURCES = [
    'https://farside.ph.utexas.edu/teaching/jk1/Electromagnetism/node52.html',
    'https://farside.ph.utexas.edu/teaching/plasma/lectures/node24.html',
    'https://iauarchive.eso.org/static/resolutions/IAU2015_English.pdf',
]


def basis(tilt_deg):
    angle = math.radians(tilt_deg)
    return np.array([math.cos(angle), 0., -math.sin(angle)]), np.array([0., 1., 0.]), np.array([math.sin(angle), 0., math.cos(angle)])


def field(position_r, equatorial_T, axis):
    """Cartesian B in tesla; position is in prescribed planetary radii."""
    x = np.asarray(position_r, dtype=float)
    radius = np.linalg.norm(x, axis=-1)
    if np.any(radius == 0):
        raise ValueError('O dipolo não admite avaliação na origem.')
    return equatorial_T * (3*np.sum(x*axis, axis=-1)[..., None]*x/radius[..., None]**5 - axis/radius[..., None]**3)


def gravity(position_r, gm):
    x = np.asarray(position_r, dtype=float)
    return -gm/RADIUS_M**2*x/np.linalg.norm(x, axis=-1)[..., None]**3


def initial_state(params):
    e1, e2, axis = basis(params['tilt_deg'])
    speed = math.sqrt(2*params['energy_keV']*1e3*elementary_charge/proton_mass)
    angle = math.radians(params['pitch_deg'])
    # At the magnetic equator B points opposite the chosen dipole axis.
    velocity = -axis*math.cos(angle) + e2*math.sin(angle)
    return np.concatenate([params['initial_radius_R']*e1, velocity]), speed


def integrate(params, magnetic=True, gravitational=True, rtol=2e-10):
    initial, speed = initial_state(params)
    _, _, axis = basis(params['tilt_deg'])
    eq = params['B_equator_uT']*1e-6
    gm = GM_EARTH*params['mass_earth']
    scale_t = RADIUS_M/speed
    duration = params['duration_s']/scale_t
    magnet = params['charge_sign']*elementary_charge/proton_mass*scale_t*eq*magnetic
    grav = gm/(RADIUS_M*speed**2)*gravitational
    ax, ay, az = axis
    evaluations = 0
    started = time.monotonic()

    def derivative(t, state):
        nonlocal evaluations
        evaluations += 1
        if evaluations > MAX_EVALUATIONS or (evaluations % 512 == 0 and time.monotonic()-started > 12):
            raise ValueError('Esta combinação excede o orçamento de giro-órbitas. Reduza duração ou campo, ou aumente o raio inicial.')
        x, y, z, u, v, w = state
        r2 = x*x+y*y+z*z
        inv3 = r2**-1.5
        dot = 3*(ax*x+ay*y+az*z)/r2
        bx, by, bz = magnet*inv3*(dot*x-ax), magnet*inv3*(dot*y-ay), magnet*inv3*(dot*z-az)
        return [u, v, w, v*bz-w*by-grav*x*inv3, w*bx-u*bz-grav*y*inv3, u*by-v*bx-grav*z*inv3]

    def inner(t, state):
        return np.linalg.norm(state[:3])-1
    def outer(t, state):
        return np.linalg.norm(state[:3])-OUTER_RADIUS
    inner.terminal = outer.terminal = True
    inner.direction, outer.direction = -1, 1
    omega0 = abs(magnet)/params['initial_radius_R']**3
    step = min(.05, 2*math.pi/(5*omega0)) if omega0 else .05
    solution = solve_ivp(derivative, [0, duration], initial, method='DOP853',
                         rtol=rtol, atol=rtol*.01, max_step=step,
                         dense_output=True, events=(inner, outer))
    if not solution.success:
        raise ValueError('A integração da partícula não convergiu: '+solution.message)
    status = 'inner_boundary' if len(solution.t_events[0]) else 'outer_boundary' if len(solution.t_events[1]) else 'duration'
    finish = float(solution.t[-1]*scale_t)
    times = np.linspace(0, finish, 241)
    states = solution.sol(times/scale_t).T
    # Resolve each interval locally, avoiding waste from applying the near-surface
    # gyrofrequency to the entire flight. Include all241 measurement instants.
    accepted_B = field(solution.y[:3].T, eq, axis)
    omega_max = elementary_charge/proton_mass*float(np.max(np.linalg.norm(accepted_B, axis=1))) if magnetic else 0.
    midpoint = (solution.t[:-1]+solution.t[1:])/2
    mid_B = field(solution.sol(midpoint)[:3].T, eq, axis)
    local_B = np.maximum.reduce((np.linalg.norm(accepted_B[:-1],axis=1),
                                 np.linalg.norm(accepted_B[1:],axis=1),np.linalg.norm(mid_B,axis=1)))
    local_omega = elementary_charge/proton_mass*local_B*magnetic
    subdivisions = np.maximum(1,np.ceil(np.diff(solution.t)*scale_t*local_omega*1.05*20/(2*math.pi))).astype(int)
    if int(np.sum(subdivisions))+241 > MAX_TRACE:
        raise ValueError('A trajetória requer mais amostras para resolver o giro. Reduza duração ou campo, ou aumente o raio inicial.')
    intervals = [np.linspace(a,b,int(n)+1)[1:]*scale_t for a,b,n in zip(solution.t[:-1],solution.t[1:],subdivisions)]
    trace_times = np.unique(np.concatenate(([0.],*intervals,times)))
    trace = solution.sol(trace_times/scale_t)[:3].T
    accepted = solution.y.T
    potential = -proton_mass*gm/(RADIUS_M*np.linalg.norm(accepted[:, :3], axis=1))*gravitational
    kinetic = .5*proton_mass*speed**2*np.sum(accepted[:, 3:]**2, axis=1)
    energy = kinetic+potential
    residual = float(np.max(np.abs(energy-energy[0]))/(kinetic[0]+abs(potential[0])))
    return {'times':times, 'states':states, 'trace_times':trace_times, 'trace':trace,
            'speed':speed, 'status':status, 'energy_residual':residual, 'evaluations':evaluations,
            'omega_max':omega_max, 'solver_nodes':len(solution.t)}


def readings(run, params, magnetic, gravitational):
    _, _, axis = basis(params['tilt_deg'])
    position = run['states'][:, :3]
    velocity = run['states'][:, 3:]*run['speed']
    b = field(position, params['B_equator_uT']*1e-6, axis)
    norm_b = np.linalg.norm(b, axis=1)
    parallel = np.sum(velocity*b, axis=1)/norm_b
    speed2 = np.sum(velocity**2, axis=1)
    perp2 = np.maximum(0., speed2-parallel**2)
    pitch = np.degrees(np.arctan2(np.sqrt(perp2), parallel))
    kinetic = .5*proton_mass*speed2
    gm = GM_EARTH*params['mass_earth']
    potential = -proton_mass*gm/(RADIUS_M*np.linalg.norm(position, axis=1))*gravitational
    fm = params['charge_sign']*elementary_charge*np.cross(velocity, b)*magnetic
    fg = proton_mass*gravity(position, gm)*gravitational
    moment = .5*proton_mass*perp2/norm_b
    return {'velocity_m_s':velocity.tolist(), 'magnetic_field_T':b.tolist(),
            'gravity_force_N':fg.tolist(), 'magnetic_force_N':fm.tolist(),
            'total_force_N':(fm+fg).tolist(), 'kinetic_energy_J':kinetic.tolist(),
            'potential_energy_J':potential.tolist(), 'total_energy_J':(kinetic+potential).tolist(),
            'magnetic_power_W':np.sum(fm*velocity, axis=1).tolist(),
            'parallel_velocity_m_s':parallel.tolist(), 'pitch_deg':pitch.tolist(),
            'magnetic_moment_J_T':moment.tolist()}


def field_lines(params):
    e1, e2, axis = basis(params['tilt_deg'])
    lines = []
    for shell in (2., 4., 6.):
        low = math.asin(math.sqrt(1/shell))
        theta = np.linspace(low, math.pi-low, 81)
        for longitude in np.linspace(0, 2*math.pi, 8, endpoint=False):
            equator = e1*math.cos(longitude)+e2*math.sin(longitude)
            line = shell*np.sin(theta)[:, None]**2*(np.sin(theta)[:, None]*equator+np.cos(theta)[:, None]*axis)
            lines.append(line.tolist())
    return lines


def experiment(params, controls):
    magnetic = controls['electromagnetic']['acting'] and controls['electromagnetic']['effects']['magnetic_deflection']
    gravitational = controls['gravity']['acting'] and controls['gravity']['effects']['orbital_acceleration']
    reference = integrate(params)
    actual = reference if magnetic and gravitational else integrate(params, magnetic, gravitational)
    read = readings(actual, params, magnetic, gravitational)
    _, _, axis = basis(params['tilt_deg'])
    eq = params['B_equator_uT']*1e-6
    gm = GM_EARTH*params['mass_earth']
    samples = []
    for radius in (1.5, 3., 6.):
        for i in range(32):
            z = 1-2*(i+.5)/32
            angle = i*math.pi*(3-math.sqrt(5))
            samples.append([radius*math.sqrt(1-z*z)*math.cos(angle), radius*math.sqrt(1-z*z)*math.sin(angle), radius*z])
    samples = np.array(samples)
    bs, gs = field(samples, eq, axis), gravity(samples, gm)
    fields = []
    for position, b, g in zip(samples, bs, gs):
        fields.append({'position':position.tolist(),'vector':b.tolist(),'applied_vector':(b*magnetic).tolist(), 'unit':'T','kind':'magnetic','force':'electromagnetic'})
        fields.append({'position':position.tolist(),'vector':g.tolist(),'applied_vector':(g*gravitational).tolist(), 'unit':'m/s²','kind':'gravity','force':'gravity',
                       'potential_m2_s2':-gm/(RADIUS_M*np.linalg.norm(position))})
    angle = math.radians(params['pitch_deg'])
    mirror_latitude = math.degrees(brentq(lambda latitude: math.cos(latitude)**6/math.sqrt(1+3*math.sin(latitude)**2)-math.sin(angle)**2,0.,math.pi/2-.001))
    mirror_r = params['initial_radius_R']*math.cos(math.radians(mirror_latitude))**2
    velocity_parallel = np.array(read['parallel_velocity_m_s'])
    reversals = np.flatnonzero(velocity_parallel[:-1]*velocity_parallel[1:] < 0)
    bnorm = np.linalg.norm(read['magnetic_field_T'], axis=1)
    kinetic = np.array(read['kinetic_energy_J'])
    total = np.array(read['total_energy_J'])
    moment = np.array(read['magnetic_moment_J_T'])
    gyro_radius = actual['speed']*math.sin(angle)*proton_mass/(elementary_charge*bnorm[0])
    return {
        'model':'Dipolo estático ideal + gravidade Newtoniana; posição e velocidade integradas por DOP853, sem força de espelho adicional.',
        'domain':'Próton/antipróton clássico, fonte esférica prescrita, exterior entre1 e10R; E=0, sem atmosfera, rotação, plasma coletivo ou campo IGRF. Limites encerram o modelo e não produzem colisões simuladas.',
        'parameter_note':'Energia≤30keV: v/c<0,008. As linhas são soluções analíticas do dipolo; momento magnético e latitude prevista são aproximações adiabáticas comparativas.',
        'influences':['gravity','electromagnetic'], 'time_s':actual['times'].tolist(),
        'positions':actual['states'][:, :3].tolist(), 'reference_positions':reference['states'][:, :3].tolist(),
        'position_unit_m':RADIUS_M, 'field':fields, 'field_unit':'per_item', 'particle_readings':read,
        'curve_axis':'razões adimensionais; pitch dividido por90°',
        'curves':[{'name':'B / B₀','values':(bnorm/bnorm[0]).tolist()},
                  {'name':'Pitch /90°','values':(np.array(read['pitch_deg'])/90).tolist()},
                  {'name':'K / K₀','values':(kinetic/kinetic[0]).tolist()},
                  {'name':'(K+U) / (K₀+U₀)','values':(total/total[0]).tolist()},
                  {'name':'μ / μ₀ · adiabático','values':(moment/moment[0]).tolist()}],
        'dipole':{'radius_m':RADIUS_M,'axis':axis.tolist(),'magnetic_applied':magnetic,'gravity_applied':gravitational,
                  'status':actual['status'],'reference_status':reference['status'],
                  'trace':actual['trace'].tolist(),'trace_time_s':actual['trace_times'].tolist(),
                  'reference_trace':reference['trace'].tolist(),'reference_time_s':reference['trace_times'].tolist(),
                  'field_lines':field_lines(params),'parallel_reversals':int(len(reversals)),
                  'solver_evaluations':actual['evaluations'],'solver_nodes':actual['solver_nodes'],
                  'trace_samples':len(actual['trace']),'maximum_gyrofrequency_rad_s':actual['omega_max'],
                  'energy_residual':actual['energy_residual'], 'reference_energy_residual':reference['energy_residual']},
        'reference':{'B_equator_T':eq,'GM_m3_s2':gm,'radius_m':RADIUS_M,'axis':axis.tolist(),
                     'charge_C':params['charge_sign']*elementary_charge,'mass_kg':proton_mass,
                     'initial_speed_m_s':actual['speed'],'initial_speed_fraction_c':actual['speed']/c,
                     'adiabatic_mirror_latitude_deg':mirror_latitude,'adiabatic_mirror_radius_R':mirror_r,
                     'mirror_inside_domain':mirror_r>1,'initial_gyroradius_m':gyro_radius,
                     'initial_gyroradius_over_radius':gyro_radius/(RADIUS_M*params['initial_radius_R']),
                     'channel_dependencies':'Gravidade e força magnética são operadores somados sobre uma única partícula de teste. Fonte/campo permanecem prescritos ao suprimi-los; forte/fraca não têm operador neste palco.'},
        'measurements':[{'label':'B inicial de referência','value':bnorm[0],'unit':'T'},
                        {'label':'Inversões de velocidade paralela','value':int(len(reversals)),'unit':'na amostragem'},
                        {'label':'Resíduo de K+U aplicado','value':actual['energy_residual'],'unit':'relativo'},
                        {'label':'Raio de Larmor inicial / raio orbital','value':gyro_radius/(RADIUS_M*params['initial_radius_R']),'unit':'razão'}],
        'sources':SOURCES,
    }
