"""Restricted classical DH limit and ideal-FD susceptibility; not a solar EOS."""
from pathlib import Path
import hashlib
import math
import sys
import numpy as np
from scipy import constants
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.special import expit

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
sys.path.insert(0, str(ROOT/'output/is5-thermal-staging'))
import is5_eos as ideal

K, H, ME, MU = ideal.K, ideal.H, ideal.ME, ideal.MU
E, EPS = constants.elementary_charge, constants.epsilon_0
COULOMB = E*E/(4*math.pi*EPS)
LIMITS = dict(maximum_ion_Gamma=0.1, electron_degeneracy=0.05,
              kappa_lambda_e=0.3, maximum_ion_degeneracy=0.01,
              thermal_relativity=0.01, Fermi_relativity=0.1,
              maximum_linearization=0.1, screening_exponent=0.1)
HERE = Path(__file__).resolve().parent
FILES = [Path(__file__), ROOT/'IS-5-COULOMB-CONTRATO-PREVIO.md',
         *[HERE/'references'/n for n in ('pc2012.html', 'cp1998.html', 'dlmf25-12.html')]]
IMPORTED = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES}


def generation():
    if any(hashlib.sha256((ROOT/n).read_bytes()).hexdigest() != h for n, h in IMPORTED.items()):
        raise ValueError('Restart after Coulomb source or contract changes')
    return dict(schema=1, id='is5:classical-DH-restricted-and-ideal-FD-response', version='0.1.0',
                source_sha256=dict(IMPORTED), ideal_generation=ideal.generation(), limits=dict(LIMITS),
                scope='Classical DH interaction only within explicit weak/classical guards; no general solar EOS, exchange, quantum Coulomb or coupled evolution.')


def response_eta(temperature_K, eta):
    """q=kT*chi and derivatives, T derivatives at fixed ne. SI, nonrelativistic FD."""
    t, eta = ideal.number(temperature_K), ideal.number(eta)
    if not 1e7 <= t <= 3e7 or not -40 <= eta <= 40:
        raise ValueError('FD response outside declared T or numerical eta domain')
    wavelength = H/math.sqrt(2*math.pi*ME*K*t)
    c = 2/wavelength**3
    f, g = ideal.fermi(.5, eta), ideal.fermi(-.5, eta)
    scale = math.exp(eta) if eta < 0 else 1.
    def integrand(u, order):
        occ = float(expit(eta-u*u))
        base = 2*math.exp(-u*u)/(1+math.exp(eta-u*u)) if eta < 0 else 2*occ
        return base*(1-occ)*(1 if order == 1 else 1-2*occ)
    derivatives = []
    for order in (1, 2):
        value, error = quad(integrand, 0, math.sqrt(max(eta, 0)+80), args=(order,),
                            epsabs=1e-13, epsrel=3e-13, limit=120)
        if error > 1e-10*max(abs(value), 1e-4):
            raise RuntimeError('FD response quadrature error budget exceeded')
        derivatives.append(value*scale/math.sqrt(math.pi))
    gp, gpp = derivatives
    a = -1.5*f/g
    aL = -1.5*(1-f*gp/(g*g))*a
    q = c*g
    qL = 1.5*q+c*gp*a
    qLL = 2.25*q+3*c*gp*a+c*gpp*a*a+c*gp*aL
    r = gp/g
    return dict(temperature_K=t, electron_eta=eta, electron_density_m3=c*f,
                q_effective_electron_density_m3=q, susceptibility_m3_J=q/(K*t),
                dq_dlnT_fixed_ne_m3=qL, d2q_dlnT2_fixed_ne_m3=qLL,
                dq_dne_fixed_T=r, d_dlnT_dq_dne_fixed_ne=(gpp/g-r*r)*a,
                q_over_ne=g/f, electron_thermal_wavelength_m=wavelength)


def electron_response(temperature_K, electron_density_m3):
    t, ne = ideal.number(temperature_K), ideal.number(electron_density_m3)
    if not 1e7 <= t <= 3e7 or ne <= 0:
        raise ValueError('Positive electron density and declared T required')
    wavelength = H/math.sqrt(2*math.pi*ME*K*t)
    phi = ne*wavelength**3/2
    eta = brentq(lambda x: ideal.fermi(.5, x)-phi, -40, 40, xtol=2e-12, rtol=2e-14)
    return response_eta(t, float(eta))


def _input(temperature_K, density_kg_m3, fractions, mass_numbers, charges):
    t, rho = ideal.number(temperature_K), ideal.number(density_kg_m3)
    if not 1e7 <= t <= 3e7 or not 1e4 <= rho <= 3e5:
        raise ValueError('Coulomb input outside10–30MK or density domain')
    if any(not isinstance(v, (list, tuple)) for v in (fractions, mass_numbers, charges)):
        raise ValueError('Explicit lists of fractions, mass numbers and charges required')
    if not 1 <= len(fractions) <= 64 or len(fractions) != len(mass_numbers) or len(fractions) != len(charges):
        raise ValueError('Matching1–64 species required')
    if any(type(a) is not int or type(z) is not int or not 1 <= z <= min(a, 26) or a > 300
           for a, z in zip(mass_numbers, charges)):
        raise ValueError('Integer1<=Z<=A<=300 with Z<=26 required')
    y = np.array([ideal.number(v) for v in fractions])
    aa, zz = np.array(mass_numbers, dtype=float), np.array(charges, dtype=float)
    if np.min(y) < 0 or abs(float(aa@y)-1) > 1e-10:
        raise ValueError('Nonnegative normalized baryon fractions required; no clamp')
    return t, rho, y, aa, zz


def _classical(t, nb, y, z):
    """Mathematical density closure; public evaluation enforces physical guards."""
    moment = nb*float((z*z+z)@y)
    kappa = math.sqrt(E*E*moment/(EPS*K*t))
    free = -K*t*kappa**3/(12*math.pi)
    chemical = 1.5*free*(z*z+z)/moment
    return dict(kappa_m_inverse=kappa, free_energy_J_m3=free,
                internal_energy_J_m3=1.5*free, pressure_Pa=0.5*free,
                heat_capacity_J_m3_K=-0.75*free/t, entropy_J_m3_K=0.5*free/t,
                neutral_chemical_potential_J=chemical.tolist(),
                du_dnumber_per_baryon_J_m3=(1.5*nb*chemical).tolist())


def assess(temperature_K, density_kg_m3, fractions, mass_numbers, charges):
    t, rho, y, aa, z = _input(temperature_K, density_kg_m3, fractions, mass_numbers, charges)
    nb = rho/MU
    state = ideal.mixture(t, rho, float(sum(y)), float(z@y))
    response = response_eta(t, state['electron_eta'])
    kappa = math.sqrt(E*E*nb*float((z*z+z)@y)/(EPS*K*t))
    present = y > 0
    gamma = state['electron_Coulomb_parameter']*z**(5/3)
    linear = COULOMB*kappa*z/(K*t)
    lambdai = H/np.sqrt(2*math.pi*aa*MU*K*t)
    measures = dict(maximum_ion_Gamma=float(max(gamma[present])),
                    electron_degeneracy=state['degeneracy_ne_lambda3_over2'],
                    kappa_lambda_e=kappa*response['electron_thermal_wavelength_m'],
                    maximum_ion_degeneracy=float(max((nb*y*lambdai**3)[present])),
                    thermal_relativity=state['thermal_relativity_kT_over_mec2'],
                    Fermi_relativity=state['fermi_relativity_pF_over_mec'],
                    maximum_linearization=float(max(linear[present])))
    violations = [key for key, value in measures.items() if value > LIMITS[key]]
    return dict(inside_domain=not violations, violations=violations, measures=measures,
                limits=dict(LIMITS), ion_Gamma=gamma.tolist(), ion_linearization=linear.tolist(),
                species_present=present.tolist(), ideal=state, electron_response=response,
                classical_kappa_m_inverse=kappa,
                FD_to_classical_kappa_ratio=math.sqrt((float((z*z)@y)+float(z@y)*response['q_over_ne'])/float((z*z+z)@y)))


def evaluate(temperature_K, density_kg_m3, fractions, mass_numbers, charges):
    report = assess(temperature_K, density_kg_m3, fractions, mass_numbers, charges)
    if not report['inside_domain']:
        raise ValueError('Classical DH domain refused: '+', '.join(report['violations']))
    t, rho, y, aa, z = _input(temperature_K, density_kg_m3, fractions, mass_numbers, charges)
    base = report['ideal']
    correction = _classical(t, rho/MU, y, z)
    totals = {k:base[k]+correction[k] for k in ('pressure_Pa', 'internal_energy_J_m3', 'heat_capacity_J_m3_K')}
    if any(not math.isfinite(v) or v <= 0 for v in totals.values()):
        raise RuntimeError('Nonpositive or invalid total thermodynamic quantity')
    gradient = base['du_dions_per_baryon_J_m3']+z*base['du_delectrons_per_baryon_J_m3']
    totals['du_dnumber_per_baryon_J_m3'] = (gradient+np.array(correction['du_dnumber_per_baryon_J_m3'])).tolist()
    return dict(assessment=report, correction=correction, total=totals, scientific_generation=generation())


def screening(temperature_K, density_kg_m3, fractions, mass_numbers, charges, charge1, charge2):
    if type(charge1) is not int or type(charge2) is not int or not 1 <= charge1 <= 26 or not 1 <= charge2 <= 26 or charge1+charge2 > 26:
        raise ValueError('Integer positive test charges and compound Z<=26 required')
    result = evaluate(temperature_K, density_kg_m3, fractions, mass_numbers, charges)
    state, corr = result['assessment']['ideal'], result['correction']
    compound = charge1+charge2
    test_gamma = state['electron_Coulomb_parameter']*compound**(5/3)
    test_linear = COULOMB*corr['kappa_m_inverse']*compound/(K*temperature_K)
    h = charge1*charge2*COULOMB*corr['kappa_m_inverse']/(K*temperature_K)
    if test_gamma > LIMITS['maximum_ion_Gamma'] or test_linear > LIMITS['maximum_linearization'] or h > LIMITS['screening_exponent']:
        raise ValueError('DH screening compound charge or exponent outside weak domain')
    return dict(exponent=h, factor=math.exp(h), entrance_charges=[charge1, charge2],
                compound_charge=compound, compound_Gamma=test_gamma,
                compound_linearization=test_linear, scientific_generation=result['scientific_generation'])
