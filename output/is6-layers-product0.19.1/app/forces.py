"""Small, bounded scientific force experiments with independent view controls.

Disabling an operator is a counterfactual experiment with the material model
held fixed. It never changes the evaluated reference field or nuclear data.
No quantum field calculation or self-consistent stellar evolution is implied.
"""
from pathlib import Path
import hashlib
import json
import math
import os
import tempfile

import numpy as np
from scipy.integrate import solve_ivp
from scipy.constants import elementary_charge, proton_mass, Avogadro, c
from science_contracts import contract, physics_fingerprint, scientific_generation, generation_difference
from fusion import MIXTURES, CHANNEL_LABELS, effect_keys as fusion_effect_keys
from decays import CASES as DECAY_CASES, EFFECT_LABELS as DECAY_EFFECT_LABELS, channel_keys as decay_channel_keys

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'data/science/nuclear.json').read_text(encoding='utf-8'))
FORCES = ('gravity', 'electromagnetic', 'strong', 'weak')
EFFECTS = {
    'gravity': {'orbital_acceleration': 'Aceleração orbital', 'ray_bending': 'Desvio e captura da luz',
                'static_clock_rate': 'Diferença de ritmo dos relógios',
                'primary_attraction':'Atração da fonte primária','secondary_attraction':'Atração da fonte secundária'},
    'electromagnetic': {'electric_acceleration': 'Aceleração pelo campo elétrico',
                       'magnetic_deflection': 'Desvio pelo campo magnético',
                       'stellar_radiative_capture': 'Captura radiativa D + p',
                       'cno_radiative_capture': 'Emissão radiativa nas capturas CNO',
                       'fusion_radiative_capture': 'Emissão radiativa na captura'},
    'strong': {'dt_fusion': 'Canal de fusão D + T',
               'dp_capture': 'Ligação nuclear D + p', 'he3_fusion': 'Fusão ³He + ³He',
               'cno_c12_capture':'Captura de p por ¹²C','cno_c13_capture':'Captura de p por ¹³C',
               'cno_n14_capture':'Captura de p por ¹⁴N','cno_n15_alpha':'Saída ¹⁵N + p → ¹²C + ⁴He'},
    'weak': {'beta_decay': 'Canal de decaimento beta', 'pp_fusion': 'Conversão fraca p + p',
             'electron_capture': 'Canal de captura eletrônica',
             'cno_n13_beta':'Beta+ de ¹³N','cno_o15_beta':'Beta+ de ¹⁵O'},
}
EFFECTS['strong'].update({'fusion_' + k: label for k, label in CHANNEL_LABELS.items()})
EFFECTS['weak'].update(DECAY_EFFECT_LABELS)
DECAYS = {
    'n': {'name': 'Nêutrons livres', 'daughter': 'p', 'reaction': 'n → p + e⁻ + antineutrino eletrônico'},
    't': {'name': 'Trítio (³H)', 'daughter': 'he3', 'reaction': '³H → ³He + e⁻ + antineutrino eletrônico'},
    'c14': {'name': 'Carbono-14', 'daughter': 'n14', 'reaction': '¹⁴C → ¹⁴N + e⁻ + antineutrino eletrônico'},
    'be7': {'name': 'Berílio-7 · captura eletrônica', 'daughter': 'li7',
            'reaction': '⁷Be + e⁻ → ⁷Li + neutrino eletrônico', 'capture': True},
}
GM_SUN = 1.3271244e20  # IAU 2015 nominal solar mass parameter, m^3 s^-2
AU = 149597870700.0
SCENARIOS = {
    'decays': {'name': 'Decaimentos · ramos e cadeias', 'force': 'weak',
               'parameters': {'parent_case': ('f18', None, None, 'Núcleo inicial e cadeia'),
                              'initial_population': (1e6, 1, 1e12, 'População nuclear inicial total'),
                              'duration_half_lives': (4, .001, 20, 'Duração / meias-vidas ENSDF do pai inicial'),
                              'initial_daughter_fraction': (0, 0, 1, 'Fração inicial de Y-90 na cadeia Sr/Y')},
               'choices': {'parent_case': DECAY_CASES},
               'effect_keys': {'weak': list(DECAY_EFFECT_LABELS)},
               'effect_by_case': {k: {'weak': ['decay_' + c for c in decay_channel_keys(k)]} for k in DECAY_CASES}},
    'fusion': {'name': 'Fusão · canais e composição', 'force': 'strong',
               'parameters': {'mixture': ('dt', None, None, 'Mistura e canais'),
                              'temperature_K': (1e8, 1e7, 1e9, 'Temperatura prescrita / K'),
                              'density_m3': (1e20, 1e16, 1e24, 'Densidade inicial do primeiro combustível / m⁻³'),
                              'partner_ratio': (1, 1e-3, 1e3, 'Razão segundo / primeiro combustível'),
                              'duration_s': (1000, 1e-6, 1e20, 'Duração física / s')},
               'choices': {'mixture': {k: v['label'] for k, v in MIXTURES.items()}},
               'effect_keys': {'strong': ['fusion_' + k for k in CHANNEL_LABELS],
                               'electromagnetic': ['fusion_radiative_capture']},
               'effect_by_mixture': {k: fusion_effect_keys(k) for k in MIXTURES},
               'comparison_conditions': {k: {'temperature_K': 3e8, 'density_m3': 1e22,
                                              'partner_ratio': 1, 'duration_s': duration}
                                         for k, duration in {'dt': .7, 'dd': 50, 'dp': 5e6,
                                                             'he3he3': 2e5, 'li7p': 4e4, 'c12alpha': 6e19}.items()},
               'identical_fuels': [k for k, v in MIXTURES.items() if v['fuels'][0] == v['fuels'][1]]},
    'geomagnetic':{'name':'Campo terrestre · IGRF14 e sonda','force':'electromagnetic',
                   'parameters':{'year':(2026,1900,2030,'Época / ano decimal'),
                                 'latitude_deg':(-23.55,-90,90,'Latitude geodética / graus'),
                                 'longitude_deg':(-46.63,-180,180,'Longitude leste / graus'),
                                 'altitude_km':(0,0,1000,'Altitude WGS84 / km'),
                                 'velocity_north_km_s':(100, -2000,2000,'Velocidade norte / km·s⁻¹'),
                                 'velocity_east_km_s':(0,-2000,2000,'Velocidade leste / km·s⁻¹'),
                                 'velocity_down_km_s':(0,-2000,2000,'Velocidade para baixo / km·s⁻¹'),
                                 'charge_sign':(1,-1,1,'Sinal da carga')},
                   'effect_keys':{'electromagnetic':['magnetic_deflection']}},
    'dipole':{'name':'Dipolo planetário · partículas e espelhamento','force':'electromagnetic',
              'parameters':{'initial_radius_R':(4,2.5,6,'Raio equatorial inicial / R'),
                            'B_equator_uT':(30,5,40,'B equatorial superficial / µT'),
                            'energy_keV':(30,1,30,'Energia cinética inicial / keV'),
                            'pitch_deg':(60,5,85,'Ângulo inicial com B / graus'),
                            'tilt_deg':(0,0,60,'Inclinação do eixo / graus'),
                            'charge_sign':(1,-1,1,'Sinal da carga'),
                            'duration_s':(40,5,50,'Duração solicitada / s'),
                            'mass_earth':(1,.1,3,'GM / terrestre nominal')},
              'effect_keys':{'gravity':['orbital_acceleration'],'electromagnetic':['magnetic_deflection']}},
    'binary':{'name':'Gravidade · fontes binárias e sondas','force':'gravity',
              'parameters':{'primary_solar':(1,.2,3,'Massa primária nominal / Sol'),
                            'mass_ratio':(.01,.001,1,'Razão secundária / primária'),
                            'separation_au':(1,.1,10,'Separação das fontes / au'),
                            'periods':(2,.05,5,'Duração / períodos binários'),
                            'initial_mode':('custom',None,None,'Condições iniciais'),
                            'x':(2,-4,4,'Posição x / separação'), 'y':(0,-4,4,'Posição y / separação'),
                            'z':(.15,-4,4,'Posição z / separação'),
                            'vx':(0,-3,3,'Velocidade x girante / n·a'),
                            'vy':(-1.2928932188134525,-3,3,'Velocidade y girante / n·a'),
                            'vz':(0,-3,3,'Velocidade z girante / n·a'),
                            'probe_x':(0,-3,3,'Sonda girante x / separação'),
                            'probe_y':(1,-3,3,'Sonda girante y / separação'),
                            'probe_z':(.2,-3,3,'Sonda girante z / separação')},
              'choices':{'initial_mode':{'custom':'Posição e velocidade informadas','l4':'Equilíbrio L4 de referência','l5':'Equilíbrio L5 de referência'}},
              'effect_keys':{'gravity':['primary_attraction','secondary_attraction']}},
    'cno': {'name':'Região estelar · ciclo CNO-I','force':'strong',
            'parameters':{'temperature_K':(1.5e7,1e7,3e7,'Temperatura prescrita / K'),
                          'density_kg_m3':(1.5e5,1e4,3e5,'Densidade prescrita / kg·m⁻³'),
                          'hydrogen_fraction':(.35,.05,.75,'Fração mássica inicial de H'),
                          'catalyst_fraction':(.01,1e-8,.05,'Fração mássica inicial do catalisador'),
                          'initial_catalyst':('n14',None,None,'Catalisador inicial'),
                          'duration_years':(1e8,1,5e9,'Duração / anos julianos'),
                          'decay_evaluation':('nubase2020',None,None,'Avaliação dos decaimentos beta+')},
            'choices':{'initial_catalyst':{'c12':'Carbono-12','n14':'Nitrogênio-14'},
                       'decay_evaluation':{'nubase2020':'NUBASE2020','reaclib_wc12':'REACLIB · Wallet Cards2012'}},
            'effect_keys':{'strong':['cno_c12_capture','cno_c13_capture','cno_n14_capture','cno_n15_alpha'],
                           'weak':['cno_n13_beta','cno_o15_beta'],'electromagnetic':['cno_radiative_capture']}},
    'relativity': {'name': 'Luz e relógios · Schwarzschild', 'force': 'gravity',
                   'parameters': {'mass_solar': (10, .5, 1e7, 'Massa central / Sol'),
                                  'impact_rs': (3.2, 1.2, 1e6, 'Parâmetro de impacto no infinito / rₛ'),
                                  'probe_rs': (3, 1.01, 1e6, 'Raio do relógio estático / rₛ')},
                   'effect_keys': {'gravity': ['ray_bending', 'static_clock_rate']}},
    'gravity': {'name': 'Gravidade em todas as direções', 'force': 'gravity',
                'parameters': {'mass_solar': (1, .2, 3, 'Massa central / Sol'),
                               'radius_au': (1, .1, 10, 'Distância inicial / au')}},
    'electromagnetic': {'name': 'Carga em campos E e B', 'force': 'electromagnetic',
                       'parameters': {'B_T': (.001, .0001, .01, 'Campo B / T'),
                                      'E_Vm': (0, -1, 1, 'Campo E / V·m⁻¹'),
                                      'charge_sign': (1, -1, 1, 'Sinal da carga')}} ,
    'strong': {'name': 'Fusão D + T → ⁴He + n', 'force': 'strong',
               'parameters': {'temperature_K': (1e8, 1e7, 1e9, 'Temperatura / K'),
                              'density_m3': (1e20, 1e16, 1e24, 'Densidade inicial de cada espécie / m⁻³')}},
    'weak': {'name': 'Decaimento beta e transformação de espécies', 'force': 'weak',
             'parameters': {'initial_population': (1e6, 1, 1e12, 'População inicial'),
                            'species': ('n', None, None, 'Espécie em decaimento')},
             'choices': {'species': {key: decay['name'] for key, decay in DECAYS.items()}}},
    'stellar': {'name': 'Região estelar · rede próton–próton I', 'force': 'strong',
                'parameters': {'temperature_K': (1.5e7, 1e7, 3e7, 'Temperatura prescrita / K'),
                               'density_kg_m3': (1.5e5, 1e4, 3e5, 'Densidade prescrita / kg·m⁻³'),
                               'hydrogen_fraction': (.35, .05, .75, 'Fração mássica inicial de H'),
                               'duration_years': (1e8, 1, 5e9, 'Duração / anos julianos')},
                'effect_keys': {'weak': ['pp_fusion'], 'strong': ['dp_capture', 'he3_fusion'],
                                'electromagnetic': ['stellar_radiative_capture']}},
}
for _name, _effect_keys in {
    'gravity': ['orbital_acceleration'], 'electromagnetic': ['electric_acceleration', 'magnetic_deflection'],
    'strong': ['dt_fusion'], 'weak': ['beta_decay'],
}.items():
    SCENARIOS[_name]['effect_keys'] = {_name: _effect_keys}
SCENARIOS['weak']['effect_by_species'] = {name: 'electron_capture' if decay.get('capture') else 'beta_decay'
                                        for name, decay in DECAYS.items()}


def normalize(request):
    if not isinstance(request, dict) or set(request) - {'scenario', 'controls', 'parameters'}:
        raise ValueError('Configuração de forças inválida.')
    scenario = request.get('scenario', 'gravity')
    if not isinstance(scenario, str) or scenario not in SCENARIOS:
        raise ValueError('Cenário desconhecido.')
    given = request.get('controls', {})
    if not isinstance(given, dict) or set(given) - set(FORCES):
        raise ValueError('Interação desconhecida.')
    controls = {}
    for force in FORCES:
        item = given.get(force, {})
        if not isinstance(item, dict) or set(item) - {'acting', 'visible', 'effects'}:
            raise ValueError('Controle desconhecido.')
        controls[force] = {'acting': item.get('acting', True), 'visible': item.get('visible', True)}
        if any(type(v) is not bool for v in controls[force].values()):
            raise ValueError('Os controles precisam ser booleanos.')
        effects = item.get('effects', {})
        if not isinstance(effects, dict) or set(effects) - set(EFFECTS[force]):
            raise ValueError('Efeito não disponível nesta interação.')
        controls[force]['effects'] = {key: effects.get(key, True) for key in EFFECTS[force]}
        if any(type(value) is not bool for value in controls[force]['effects'].values()):
            raise ValueError('Os controles de efeitos precisam ser booleanos.')
    supplied = request.get('parameters', {})
    spec = SCENARIOS[scenario]['parameters']
    if not isinstance(supplied, dict) or set(supplied) - set(spec):
        raise ValueError('Parâmetro não disponível neste cenário.')
    parameters = {}
    for key, (default, minimum, maximum, _) in spec.items():
        value = supplied.get(key, default)
        choices = SCENARIOS[scenario].get('choices', {}).get(key)
        if choices is not None:
            if not isinstance(value, str) or value not in choices:
                raise ValueError(f'{key}: escolha uma opção disponível.')
            parameters[key] = value
            continue
        if type(value) not in (int, float) or not math.isfinite(value) or not minimum <= value <= maximum:
            raise ValueError(f'{key}: valor fora do domínio [{minimum}, {maximum}].')
        if key == 'charge_sign' and value not in (-1, 1):
            raise ValueError('Escolha carga positiva ou negativa.')
        parameters[key] = value
    return {'scenario': scenario, 'controls': controls, 'parameters': parameters}


def point_gravity(position, mu):
    r = math.sqrt(sum(v*v for v in position))
    if r == 0:
        raise ValueError('A fonte pontual não admite avaliação na origem.')
    return [-mu*v/r**3 for v in position]


def reaclib_rate(temperature):
    t = temperature / 1e9
    basis = (1, 1/t, t**(-1/3), t**(1/3), t, t**(5/3), math.log(t))
    return sum(math.exp(sum(a*b for a, b in zip(coef, basis))) for coef in DATA['rate']['sets'])


def _gravity(params, enabled):
    radius = params['radius_au'] * AU
    mu = GM_SUN * params['mass_solar']
    time_unit = math.sqrt(radius**3 / mu)
    tau = np.linspace(0, 2*math.pi, 241)
    v = np.array([0, math.sqrt(.5), math.sqrt(.5)])
    reference = np.column_stack((np.cos(tau), v[1]*np.sin(tau), v[2]*np.sin(tau)))
    if enabled:
        def rhs(_, y):
            return np.concatenate((y[3:], -y[:3]/np.linalg.norm(y[:3])**3))
        solution = solve_ivp(rhs, (0, float(tau[-1])), [1, 0, 0, *v],
                             t_eval=tau, method='DOP853', rtol=1e-11, atol=1e-13)
        if not solution.success:
            raise RuntimeError('A integração gravitacional não convergiu.')
        positions = solution.y[:3].T
        speeds = np.linalg.norm(solution.y[3:].T, axis=1)
        energy = .5*speeds**2 - 1/np.linalg.norm(positions, axis=1)
        error = float(np.max(np.abs((energy - energy[0])/energy[0])))
    else:
        positions = np.array([1, 0, 0]) + tau[:, None] * v
        error = 0.0
    arrows = []
    for shell in (.65, 1.25, 2):
        for i in range(48):
            z = 1 - 2*(i+.5)/48
            angle = i*math.pi*(3-math.sqrt(5))
            p = [shell*math.sqrt(1-z*z)*math.cos(angle), shell*math.sqrt(1-z*z)*math.sin(angle), shell*z]
            g = point_gravity([a*radius for a in p], mu)
            arrows.append({'position': p, 'vector': g})
    rs = 2*mu/c**2
    return {'model': 'Fonte esférica isolada; órbita newtoniana de partícula de teste.',
            'domain': 'Exterior da fonte. Referências relativísticas: Schwarzschild estático; a órbita usa Newton.',
            'influences': ['gravity'], 'time_s': (tau*time_unit).tolist(),
            'positions': positions.tolist(), 'reference_positions': reference.tolist(),
            'position_unit_m': radius, 'position_label': 'distância inicial',
            'field': arrows, 'field_unit': 'm/s²',
            'reference': {'g_m_s2': mu/radius**2, 'potential_m2_s2': -mu/radius,
                          'schwarzschild_radius_m': rs, 'static_clock_ratio': math.sqrt(1-rs/radius),
                          'radial_tidal_s2': 2*mu/radius**3,
                          'kretschmann_m_minus4': 12*rs**2/radius**6},
            'measurements': [{'label': 'Campo de referência na sonda inicial', 'value': mu/radius**2, 'unit': 'm/s²'},
                             {'label': 'Aceleração aplicada inicial', 'value': mu/radius**2 if enabled else 0, 'unit': 'm/s²'},
                             {'label': 'Deriva numérica de energia', 'value': error, 'unit': 'relativa'},
                             {'label': 'Diferença de ritmo do relógio estático', 'value': (rs/radius)/(1+math.sqrt(1-rs/radius)), 'unit': 's/s'}],
            'sources': ['https://iauarchive.eso.org/static/resolutions/IAU2015_English.pdf']}


def _electromagnetic(params, enabled, effects=None):
    # A proton/antiproton test particle, uniform B along z and E along x.
    b, electric = params['B_T'], params['E_Vm']
    q = elementary_charge * params['charge_sign']
    omega = q*b/proton_mass
    times = np.linspace(0, 4*math.pi/abs(omega), 241)
    # 10 km/s transverse and 3 km/s along B. Far inside the classical regime.
    vx, vz = 1e4, 3e3
    def trajectory(applied_e, applied_b):
        if applied_b == 0:
            acceleration = q*applied_e/proton_mass
            position = np.column_stack((vx*times+.5*acceleration*times**2, times*0, vz*times))
            velocity = np.column_stack((vx+acceleration*times, times*0, times*0+vz))
        else:
            frequency = q*applied_b/proton_mass
            phase = frequency*times
            drift_speed = applied_e/applied_b
            x = (vx*np.sin(phase)+drift_speed*(1-np.cos(phase)))/frequency
            y = (vx*(np.cos(phase)-1)+drift_speed*np.sin(phase))/frequency-drift_speed*times
            position = np.column_stack((x, y, vz*times))
            velocity = np.column_stack((vx*np.cos(phase)+drift_speed*np.sin(phase),
                                        -vx*np.sin(phase)+drift_speed*np.cos(phase)-drift_speed,
                                        times*0+vz))
        return position, velocity
    effects = effects or {key: True for key in EFFECTS['electromagnetic']}
    applied_e = electric if enabled and effects['electric_acceleration'] else 0
    applied_b = b if enabled and effects['magnetic_deflection'] else 0
    reference, _ = trajectory(electric, b)
    actual, velocities = trajectory(applied_e, applied_b)
    scale = vx/abs(omega)
    kinetic = .5*proton_mass*np.sum(velocities**2, axis=1)
    initial = .5*proton_mass*(vx**2+vz**2)
    balance = float(np.max(np.abs(kinetic-initial-q*applied_e*actual[:, 0]))/initial)
    electric_force=np.tile([q*applied_e,0,0],(len(times),1))
    magnetic_force=q*np.cross(velocities,[0,0,applied_b])
    arrows = [{'position': [x, y, z], 'vector': [0, 0, b]}
              for x in (-1, 0, 1) for y in (-2, -1, 0) for z in (0, 1, 2, 3)]
    return {'model': 'Solução analítica da força de Lorentz em campos E/B uniformes.',
            'domain': 'Partícula de teste não relativística; campos externos sem retroação.',
            'influences': ['electromagnetic'], 'time_s': times.tolist(),
            'positions': (actual/scale).tolist(), 'reference_positions': (reference/scale).tolist(),
            'position_unit_m': scale, 'position_label': 'raio de Larmor para E = 0',
            'field': arrows, 'field_unit': 'T', 'electric_field_Vm': [electric, 0, 0],
            'applied_fields': {'B_T': applied_b, 'E_Vm': applied_e},
            'particle_readings':{'velocity_m_s':velocities.tolist(),
                                 'electric_force_N':electric_force.tolist(),
                                 'magnetic_force_N':magnetic_force.tolist(),
                                 'total_force_N':(electric_force+magnetic_force).tolist(),
                                 'kinetic_energy_J':kinetic.tolist(),
                                 'electric_work_J':(q*applied_e*actual[:,0]).tolist(),
                                 'electric_power_W':np.sum(electric_force*velocities,axis=1).tolist(),
                                 'magnetic_power_W':np.sum(magnetic_force*velocities,axis=1).tolist()},
            'reference': {'B_T': b, 'E_Vm': electric, 'charge_C': q, 'omega_rad_s': omega,
                          'larmor_radius_m': scale},
            'measurements': [{'label': 'Campo magnético de referência', 'value': b, 'unit': 'T'},
                             {'label': 'Força inicial aplicada', 'value': abs(q)*math.hypot(applied_e, vx*applied_b), 'unit': 'N'},
                             {'label': 'Raio de Larmor (E = 0)', 'value': scale, 'unit': 'm'},
                             {'label': 'Resíduo K − K₀ − trabalho elétrico', 'value': balance, 'unit': 'relativo'}],
            'sources': ['https://docs.plasmapy.org/en/stable/api/plasmapy.simulation.particle_integrators.BorisIntegrator.html']}


def _strong(params, enabled):
    # nD(0)=nT(0)=n0. dn/dt=-<sigma v> n² has the exact solution n=n0/(1+k n0 t).
    rate = reaclib_rate(params['temperature_K'])
    sigma_v = rate * 1e-6 / Avogadro  # cm³ mol⁻¹ s⁻¹ -> m³ s⁻¹
    density = params['density_m3']
    t0 = 1/(sigma_v*density)
    times = np.linspace(0, 4*t0, 241)
    reference = 1/(1+sigma_v*density*times)
    fraction = reference if enabled else np.ones_like(times)
    reactions = density*(1-fraction)
    q_joule = DATA['rate']['Q_MeV']*1e6*elementary_charge
    return {'model': 'Taxa D+T → ⁴He+n REACLIB; mistura homogênea equimolar, solução exata do consumo.',
            'domain': 'T e volume prescritos; sem blindagem de plasma, reações inversas, transporte ou aquecimento realimentado. Suprimir o canal mantém núcleos/taxa de referência fixos.',
            'influences': ['strong'], 'time_s': times.tolist(),
            'curves': [{'name': 'D e T restantes / inicial', 'values': fraction.tolist()},
                       {'name': '⁴He produzido / D inicial', 'values': (1-fraction).tolist()}],
            'reference_curve': reference.tolist(),
            'reference': {'rate_cm3_mol_s': rate, 'sigma_v_m3_s': sigma_v, 'Q_MeV': DATA['rate']['Q_MeV'],
                          'initial_rate_m3_s': sigma_v*density*density,
                          'binding_MeV_per_nucleon': {n: DATA['nuclides'][n]['binding_MeV_per_nucleon'] for n in ('d', 't', 'he4')},
                          'binding_nuclei': [{'name': name, 'A': DATA['nuclides'][name]['A'],
                                              'Z': DATA['nuclides'][name]['Z'],
                                              'binding_MeV_per_nucleon': DATA['nuclides'][name]['binding_MeV_per_nucleon'],
                                              'binding_total_MeV': DATA['nuclides'][name]['A']*DATA['nuclides'][name]['binding_MeV_per_nucleon']}
                                             for name in ('d', 't', 'he4')],
                          'Q_atomic_AME_MeV': DATA['nuclides']['d']['atomic_mass_MeV']+DATA['nuclides']['t']['atomic_mass_MeV']
                                              -DATA['nuclides']['he4']['atomic_mass_MeV']-DATA['nuclides']['n']['atomic_mass_MeV'],
                          'channel_dependencies': 'Interação forte; barreira EM incorporada na taxa avaliada e mantida fixa.'},
            'measurements': [{'label': 'Taxa de referência Nₐ⟨σv⟩', 'value': rate, 'unit': 'cm³/(mol·s)'},
                             {'label': 'Reações aplicadas no instante inicial', 'value': sigma_v*density*density if enabled else 0, 'unit': 'm⁻³·s⁻¹'},
                             {'label': 'Energia disponível por reação (Q)', 'value': DATA['rate']['Q_MeV'], 'unit': 'MeV'},
                             {'label': 'Energia liberada por volume ao final', 'value': float(reactions[-1]*q_joule), 'unit': 'J/m³'},
                             {'label': 'Ligação total do hélio-4, AME2020', 'value': 4*DATA['nuclides']['he4']['binding_MeV_per_nucleon'], 'unit': 'MeV'}],
            'sources': [DATA['rate']['url'], DATA['evaluations']['url']]}


def _weak(params, enabled):
    species = params['species']
    channel = DECAYS[species]
    half_life = DATA['nuclides'][species]['half_life_s']
    times = np.linspace(0, 4*half_life, 241)
    reference = np.exp(-math.log(2)*times/half_life)
    fraction = reference if enabled else np.ones_like(times)
    number = params['initial_population']
    decays = number*(1-fraction)
    capture = channel.get('capture', False)
    products = [channel['daughter'], 'nu_e'] if capture else [channel['daughter'], 'e-', 'anti_nu_e']
    return {'model': channel['reaction'] + '; evolução média por lei exponencial.',
            'domain': 'Meia-vida NUBASE2020 no estado de referência da avaliação. Núcleos em estado fundamental; população esperada. Captura usa os elétrons/estado atômico da referência e não prevê a taxa de plasma ionizado. Espectro/energia de neutrinos ainda não calculados.',
            'influences': ['weak'], 'time_s': times.tolist(),
            'curves': [{'name': channel['name'] + ' restantes / inicial', 'values': fraction.tolist()},
                       {'name': ('Capturas' if capture else 'Decaimentos')+' / inicial', 'values': (1-fraction).tolist()}],
            'reference_curve': reference.tolist(),
            'reference': {'half_life_s': half_life, 'lambda_s': math.log(2)/half_life,
                          'parent': species, 'daughter': channel['daughter'],
                          'products': products, 'captured_electrons_per_event': int(capture),
                          'parent_A': DATA['nuclides'][species]['A'],
                          'parent_Z': DATA['nuclides'][species]['Z'],
                          'daughter_A': DATA['nuclides'][channel['daughter']]['A'],
                          'daughter_Z': DATA['nuclides'][channel['daughter']]['Z'],
                          'uncertainty': 'Não disponível no recorte; não é zero.'},
            'measurements': [{'label': 'Meia-vida de referência', 'value': half_life, 'unit': 's'},
                             {'label': 'Atividade inicial aplicada', 'value': number*math.log(2)/half_life if enabled else 0, 'unit': 's⁻¹'},
                             {'label': 'Espécie inicial esperada ao final', 'value': float(number*fraction[-1]), 'unit': 'partículas'},
                             {'label': ('Neutrinos' if capture else 'Antineutrinos')+' produzidos, valor esperado', 'value': float(decays[-1]), 'unit': 'partículas'}],
            'sources': [DATA['evaluations']['url']]}


def _stellar(params, controls):
    from stellar import integrate_zone, rate_value, DATA as stellar_data, YEAR_S
    strong, weak, em = (controls[force] for force in ('strong', 'weak', 'electromagnetic'))
    channels = {'pp': strong['acting'] and weak['acting'] and weak['effects']['pp_fusion'],
                'dp': strong['acting'] and em['acting'] and strong['effects']['dp_capture']
                      and em['effects']['stellar_radiative_capture'],
                'he3he3': strong['acting'] and strong['effects']['he3_fusion']}
    args = (params['temperature_K'], params['density_kg_m3'], params['hydrogen_fraction'],
            params['duration_years']*YEAR_S)
    baseline = integrate_zone(*args)
    actual = baseline if all(channels.values()) else integrate_zone(*args, channels=channels)
    names = ('H', 'D', '³He', '⁴He')
    curves = [{'name': f'Fração mássica de {name}', 'values': [row[i] for row in actual['mass_fractions']]}
              for i, name in enumerate(names)]
    return {'model': 'Rede pp-I: p+p → D+e⁺+ν; D+p → ³He+γ; ³He+³He → ⁴He+2p. Integração rígida Radau.',
            'domain': 'Zona homogênea com T/densidade prescritas, H/⁴He iniciais e D/³He inicialmente nulos; taxas sem blindagem. Sem estrutura, realimentação térmica, CNO, pp-II/III, pep, transporte ou luminosidade solar prevista. Energia dos neutrinos usa média solar fixa.',
            'influences': ['strong', 'weak', 'electromagnetic'], 'time_s': actual['time_s'],
            'time_display': {'unit': 'anos', 'seconds_per_unit': YEAR_S},
            'curves': curves, 'reference_curve': [row[0] for row in baseline['mass_fractions']],
            'curve_axis': 'Fração mássica', 'probe_kind': 'composition',
            'reference': {'channels': {name: {'rate_cm3_mol_s': rate_value(params['temperature_K'], entry),
                                              'Q_MeV': entry['Q_MeV'], 'source': entry['source']}
                                       for name, entry in stellar_data['rates'].items()},
                          'pp_neutrino_mean_MeV': stellar_data['pp_neutrino_mean_MeV'],
                          'energy_assumption': actual['energy_assumption'],
                          'channel_dependencies': 'Atuação forte suprime canais de ligação/fusão; fraca suprime pp; EM suprime a captura radiativa D+p. A barreira Coulomb já incorporada nas taxas permanece fixa. Gravidade/estrutura externas não evoluem neste palco.'},
            'network': actual,
            'reactions': [{'key': key, 'reaction': text, 'force': force, 'from': parent,
                           'to': daughter, 'products': products}
                          for key,text,force,parent,daughter,products in [
                              ('pp','p + p → D + e⁺ + ν','weak','p','d','+ p → e⁺ + ν'),
                              ('dp','D + p → ³He + γ','electromagnetic','d','he3','+ p → γ'),
                              ('he3he3','³He + ³He → ⁴He + 2p','strong','he3','he4','+ ³He → 2p')]],
            'measurements': [{'label': 'Energia nuclear disponível ao final', 'value': actual['energy_available_J_m3'][-1], 'unit': 'J/m³'},
                             {'label': 'Potência depositada ao final', 'value': actual['final_deposition_power_W_m3'], 'unit': 'W/m³'},
                             {'label': 'Energia levada pelos neutrinos', 'value': actual['energy_neutrinos_J_m3'][-1], 'unit': 'J/m³'},
                             {'label': 'Energia depositada localmente, hipótese', 'value': actual['energy_deposited_J_m3'][-1], 'unit': 'J/m³'},
                             {'label': 'Neutrinos pp produzidos por volume', 'value': actual['neutrino_count_m3'][-1], 'unit': 'm⁻³'},
                             {'label': 'Resíduo de conservação bariônica', 'value': actual['baryon_error'], 'unit': 'absoluto'}],
            'sources': ['https://reaclib.jinaweb.org/index.php', stellar_data['neutrino_source']['url']]}


def evaluate(request):
    config = normalize(request)
    key = config['scenario']
    control = config['controls'][SCENARIOS[key]['force']]
    effect_keys = SCENARIOS[key]['effect_keys']
    if key == 'weak':
        effect_keys = {'weak': [SCENARIOS['weak']['effect_by_species'][config['parameters']['species']]]}
    if key == 'fusion':
        effect_keys = fusion_effect_keys(config['parameters']['mixture'])
    if key == 'decays':
        effect_keys = SCENARIOS['decays']['effect_by_case'][config['parameters']['parent_case']]
    applied = {effect: config['controls'][force]['acting'] and config['controls'][force]['effects'][effect]
               for force, effects in effect_keys.items() for effect in effects}
    enabled = any(applied.values())
    if key == 'decays':
        from decays import experiment
        result = experiment(config['parameters'], config['controls'])
        applied = result['decays']['channels']
    elif key == 'fusion':
        from fusion import experiment
        result = experiment(config['parameters'], config['controls'])
        applied = result['fusion']['channels']
    elif key == 'stellar':
        result = _stellar(config['parameters'], config['controls'])
        applied = result['network']['channels']
    elif key == 'relativity':
        from relativity import experiment
        result = experiment(config['parameters'], config['controls'])
    elif key == 'cno':
        from cno import experiment
        result = experiment(config['parameters'],config['controls'])
        applied = result['network']['channels']
    elif key == 'binary':
        from binary_gravity import experiment
        result = experiment(config['parameters'],config['controls'])
    elif key == 'dipole':
        from dipole import experiment
        result = experiment(config['parameters'],config['controls'])
    elif key == 'geomagnetic':
        from geomagnetism import experiment
        result = experiment(config['parameters'],config['controls'])
    else:
        function = {'gravity': _gravity, 'electromagnetic': _electromagnetic, 'strong': _strong, 'weak': _weak}[key]
        result = function(config['parameters'], control['acting'], control['effects']) if key == 'electromagnetic' else function(config['parameters'], enabled)
    result['applied_effects'] = applied
    fingerprint = hashlib.sha256(json.dumps(config, sort_keys=True, allow_nan=False).encode()).hexdigest()
    model_contract = contract(key,result)
    return {'schema': 2, 'ok': True, 'configuration': config, 'configuration_sha256': fingerprint,
            'physics_sha256':physics_fingerprint(config,result,model_contract),'scientific_contract':model_contract,
            'counterfactual': not all(applied.values()), 'result': result}


def save_configuration(request, directory=None):
    config = normalize(request)
    folder = Path(directory) if directory else ROOT / 'user' / 'forces'
    folder.mkdir(parents=True, exist_ok=True)
    generation=scientific_generation(config['scenario'])
    manifest = {'schema': 3, 'configuration': config, 'sha256': _record_hash(config),
                'scientific_generation':generation,'generation_sha256':_record_hash(generation)}
    manifest['manifest_sha256']=_record_hash(manifest)
    fd, name = tempfile.mkstemp(prefix='force-', suffix='.tmp', dir=folder)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, allow_nan=False)
        Path(name).replace(folder/'latest.json')
    finally:
        Path(name).unlink(missing_ok=True)
    return manifest


def _record_hash(record):
    return hashlib.sha256(json.dumps(record,sort_keys=True,separators=(',', ':'),allow_nan=False).encode()).hexdigest()


def load_configuration_record(directory=None):
    folder = Path(directory) if directory else ROOT / 'user' / 'forces'
    manifest = json.loads((folder/'latest.json').read_text(encoding='utf-8'))
    schema=manifest.get('schema')
    if schema not in (1, 2, 3):
        raise ValueError('Versão de configuração desconhecida.')
    if schema==3 and _record_hash({k:v for k,v in manifest.items() if k!='manifest_sha256'})!=manifest.get('manifest_sha256'):
        raise ValueError('O registro salvo está corrompido (condições ou geração científica).')
    if _record_hash(manifest['configuration']) != manifest.get('sha256'):
        raise ValueError('A configuração salva está corrompida.')
    config=normalize(manifest['configuration'])
    current=scientific_generation(config['scenario'])
    saved=manifest.get('scientific_generation') if schema==3 else None
    if schema==3:
        if not isinstance(saved,dict) or _record_hash(saved)!=manifest.get('generation_sha256'):
            raise ValueError('Registro de geração científica inválido.')
        differences=generation_difference(saved,current)
    else:
        differences=[]
    return {'configuration':config,'restoration':{'saved_schema':schema,
            'status':'unknown_generation' if saved is None else 'changed_generation' if differences else 'same_generation',
            'saved_generation':saved,'current_generation':current,'differences':differences,
            'scope':'Conditions restored; calculation uses current code/data. Matching declared versions is not a bit-exact checkpoint.'}}


def load_configuration(directory=None):
    """Compatibility API for callers that only need normalized conditions."""
    return load_configuration_record(directory)['configuration']
