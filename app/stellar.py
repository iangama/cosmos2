"""Fixed-zone forward pp-I network. No stellar structure or surface prediction."""
from pathlib import Path
import json
import math

import numpy as np
from scipy.integrate import solve_ivp
from scipy.constants import Avogadro, atomic_mass, elementary_charge

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'data/science/pp1.json').read_text(encoding='utf-8'))
YEAR_S = 31557600.0  # Julian year; model duration, not NUBASE's table conversion.
SPECIES = ('p', 'd', 'he3', 'he4')
STOICHIOMETRY = np.array([[-2, -1, 2], [1, -1, 0], [0, 1, -2], [0, 0, 1]], dtype=float)


def rate_value(temperature, entry):
    t = temperature/1e9
    basis = (1, 1/t, t**(-1/3), t**(1/3), t, t**(5/3), math.log(t))
    return sum(math.exp(sum(a*b for a, b in zip(coef, basis))) for coef in entry['sets'])


def integrate_zone(temperature, density, hydrogen, duration_s, channels=None, tolerance=1e-9):
    """n_i/n_b and reaction extents/n_b; baryon density prescribed in m^-3.

    REACLIB molar coefficients become <sigma v> in m^3/s. The identical-
    reactant factor 1/2 is included once, in each event rate, not in dY/dt.
    Atomic mass unit defines the conventional baryon-density normalization;
    mass defects are in the separate energy accounting.
    """
    if not 1e7 <= temperature <= 3e7 or not 1e4 <= density <= 3e5:
        raise ValueError('Zona pp-I fora do domínio de temperatura/densidade.')
    if not .05 <= hydrogen <= .75 or not YEAR_S <= duration_s <= 5e9*YEAR_S:
        raise ValueError('Composição/duração fora do domínio da zona pp-I.')
    active = {'pp': True, 'dp': True, 'he3he3': True} if channels is None else channels
    if set(active) != set(DATA['rates']) or any(type(value) is not bool for value in active.values()):
        raise ValueError('Canais pp-I inválidos.')
    baryons = density/atomic_mass
    names = ('pp', 'dp', 'he3he3')
    k = np.array([rate_value(temperature, DATA['rates'][name])*1e-6/Avogadro*baryons
                  *DATA['rates'][name]['prefactor']*int(active[name]) for name in names])
    initial = np.array([hydrogen, 0, 0, (1-hydrogen)/4, 0, 0, 0])

    def flux(y):
        return k*np.array([y[0]**2, y[0]*y[1], y[2]**2])

    def rhs(_, y):
        event = flux(y)
        return np.r_[STOICHIOMETRY @ event, event]

    def jacobian(_, y):
        event_jac = np.zeros((3, 7))
        event_jac[0, 0] = 2*k[0]*y[0]
        event_jac[1, 0] = k[1]*y[1]
        event_jac[1, 1] = k[1]*y[0]
        event_jac[2, 2] = 2*k[2]*y[2]
        return np.vstack((STOICHIOMETRY @ event_jac, event_jac))

    times = np.linspace(0, duration_s, 241)
    solution = solve_ivp(rhs, (0, duration_s), initial, t_eval=times, method='Radau',
                         jac=jacobian, rtol=tolerance,
                         atol=[1e-13, 1e-25, 1e-16, 1e-13, 1e-16, 1e-16, 1e-16])
    if not solution.success:
        raise RuntimeError('A rede pp-I não convergiu: ' + solution.message)
    values = solution.y.T
    if np.min(values[:, :4]) < -1e-20:
        raise RuntimeError('A rede pp-I produziu abundância negativa fora da tolerância.')
    mass_fractions = values[:, :4]*[1, 2, 3, 4]
    baryon_error = float(np.max(np.abs(np.sum(mass_fractions, axis=1)-1)))
    if baryon_error > 1e-8:
        raise RuntimeError('Conservação bariônica da rede fora da tolerância.')
    # Atomic Q for pp includes annihilation rest energy. Q is not all local heat.
    # The fixed solar mean below is an approximation, not a computed spectrum.
    q = np.array([DATA['rates'][name]['Q_MeV'] for name in names])
    joules = 1e6*elementary_charge*baryons
    available = values[:, 4:] @ q * joules
    neutrino_energy = values[:, 4]*DATA['pp_neutrino_mean_MeV']*joules
    deposited = available-neutrino_energy
    events_final = flux(values[-1])*baryons
    all_events = np.array([flux(y) for y in values])*baryons
    return {'name': 'pp-I', 'time_s': times.tolist(), 'species': list(SPECIES),
            'baryon_density_m3': baryons,
            'number_per_baryon': values[:, :4].tolist(), 'mass_fractions': mass_fractions.tolist(),
            'reaction_extents_m3': (values[:, 4:]*baryons).tolist(),
            'event_rates_m3_s': all_events.tolist(),
            'energy_available_J_m3': available.tolist(),
            'energy_neutrinos_J_m3': neutrino_energy.tolist(),
            'energy_deposited_J_m3': deposited.tolist(),
            'neutrino_count_m3': (values[:, 4]*baryons).tolist(),
            'final_event_rates_m3_s': dict(zip(names, events_final.tolist())),
            'final_deposition_power_W_m3': float(events_final @ q*1e6*elementary_charge
                                               -events_final[0]*DATA['pp_neutrino_mean_MeV']*1e6*elementary_charge),
            'baryon_error': baryon_error, 'minimum_abundance': float(np.min(values[:, :4])),
            'solver': {'method': 'Radau', 'rtol': tolerance, 'nfev': solution.nfev,
                       'njev': solution.njev, 'nlu': solution.nlu}, 'channels': active,
            'domain': DATA['domain'],
            'energy_assumption': 'Positrons annihilate locally; all non-neutrino Q deposits locally. T/rho remain prescribed; no thermal or hydrostatic feedback, photon transport, luminosity or neutrino oscillations.'}
