"""Shared CNO-II network with thermodynamic screening and a nonideal reservoir."""
from pathlib import Path
import hashlib
import math
import sys
import numpy as np
from scipy import constants
from scipy.integrate import solve_ivp

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
sys.path.insert(0, str(ROOT/'output/is5-cno2-staging'))
sys.path.insert(0, str(ROOT/'output/is5-coulomb-mixture-staging'))
import is5_cno2 as base
import is5_coulomb_mixture as eos

SPECIES, CHANNELS = base.SPECIES, base.CHANNELS
NSPEC, NCHAN, NVAR = base.NSPEC, base.NCHAN, base.NVAR
A, Z = base.A, base.Z
AI, ZI = [int(v) for v in A], [int(v) for v in Z]
BINARY = {}
for j, reactants in enumerate(base.REACTANTS):
    names = [n for n, count in reactants.items() for _ in range(count)]
    if len(names) == 2:
        BINARY[j] = tuple(SPECIES.index(n) for n in names)
FILES = [Path(__file__), ROOT/'IS-5-COULOMB-REDE-CONTRATO-PREVIO.md']
IMPORTED = {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES}


def generation():
    if any(hashlib.sha256((ROOT/n).read_bytes()).hexdigest() != h for n,h in IMPORTED.items()):
        raise ValueError('Restart after screened network source changes')
    return dict(schema=1, id='is5:shared-CNOII-PC-classical-Coulomb-static-screening', version='0.1.0',
                source_sha256=dict(IMPORTED), bare_network=base.generation(), Coulomb_EOS=eos.generation(),
                scope='Classical-ion nonideal isochoric/prescribed zone and static thermodynamic fusion screening; Be7EC and terrestrial beta approximations retained.')


def _state(t, rho, y, include_coulomb):
    if include_coulomb:
        components, ideal, diag = eos.correction(t, rho, [float(v) for v in y], AI, ZI)
        total = {key:ideal[key]+components['sum'][key] for key in
                 ['internal_energy_J_m3', 'pressure_Pa', 'heat_capacity_J_m3_K']}
        gradient = ideal['du_dions_per_baryon_J_m3']+Z*ideal['du_delectrons_per_baryon_J_m3']
        total['gradient'] = gradient+np.array(components['sum']['du_dnumber_per_baryon_J_m3'])
        return dict(total=total, components=components, diagnostics=diag)
    ideal = base.eos.mixture(float(t), float(rho), float(np.sum(y)), float(Z@y))
    return dict(total={**{key:ideal[key] for key in ['internal_energy_J_m3', 'pressure_Pa', 'heat_capacity_J_m3_K']},
                      'gradient':ideal['du_dions_per_baryon_J_m3']+Z*ideal['du_delectrons_per_baryon_J_m3']},
                components=None, diagnostics=None)


def _screening_from_state(t, rho, y, state):
    ne = rho/eos.MU*float(Z@y)
    ae = (3/(4*math.pi*ne))**(1/3)
    factors = np.ones(NCHAN)
    diagnostics = {}
    for j, (i1, i2) in BINARY.items():
        z1, z2 = ZI[i1], ZI[i2]
        compound = z1+z2
        if compound not in ZI:
            raise ValueError('No compound-charge representative in this network')
        ic = ZI.index(compound)
        terms = {}
        for name in ['ii', 'ie', 'ee', 'mix']:
            mu = state['components'][name]['neutral_chemical_potential_J']
            terms[name] = (mu[i1]+mu[i2]-mu[ic])/(eos.K*t)
        h = float(sum(terms.values()))
        gcompound = eos.COULOMB/(ae*eos.K*t)*compound**(5/3)
        acompound = AI[i1]+AI[i2]
        tpt = constants.hbar/(eos.K*t)*math.sqrt(ne*compound*constants.elementary_charge**2/(constants.epsilon_0*acompound*eos.MU))
        a12 = .5*ae*(z1**(1/3)+z2**(1/3))
        g12 = z1*z2*eos.COULOMB/(a12*eos.K*t)
        reduced_mass = AI[i1]*AI[i2]/(AI[i1]+AI[i2])*eos.MU
        er = (z1*z2*eos.COULOMB)**2*reduced_mass/(2*constants.hbar**2)
        tau = 3*(math.pi**2*er/(eos.K*t))**(1/3)
        ratio = 3*g12/tau
        if not 0 <= h <= 2 or gcompound > 20 or tpt > .1 or ratio > .1:
            raise ValueError('Static fusion-screening pair outside declared classical domain')
        if abs(terms['ee']) > 1e-12:
            raise RuntimeError('Electron-charge contribution did not cancel in virtual fusion')
        factors[j] = math.exp(h)
        diagnostics[CHANNELS[j]] = dict(exponent=h, factor=float(factors[j]), exponent_components=terms,
                 entrance_indices=[i1, i2], entrance_charges=[z1,z2], compound_charge=compound,
                 compound_mass_number=acompound, compound_Gamma=gcompound,
                 compound_Tp_over_T=tpt, three_Gamma12_over_tau=ratio)
    return factors, diagnostics


def screening_factors(t, rho, number_per_baryon):
    if not isinstance(number_per_baryon, (list, tuple)) or len(number_per_baryon) != NSPEC:
        raise ValueError('Explicit16-species list required')
    y = np.array([base.legacy.number(v) for v in number_per_baryon])
    t, rho = base.legacy.number(t), base.legacy.number(rho)
    state = _state(t, rho, y, True)
    factors, details = _screening_from_state(t, rho, y, state)
    return dict(factors=factors.tolist(), channels=list(CHANNELS), pairs=details, scientific_generation=generation())


def integrate_zone(value, acting=None, channel_switches=None, *, mode='isochoric',
                   include_coulomb=True, include_screening=True, tolerance=1e-9):
    p = base.parameters(value)
    tol = base.legacy.number(tolerance)
    if type(include_coulomb) is not bool or type(include_screening) is not bool:
        raise ValueError('Explicit boolean Coulomb and screening options required')
    if include_screening and not include_coulomb:
        raise ValueError('Screening requires the declared Coulomb free energy')
    if mode not in ('prescribed', 'isochoric') or not 1e-12 <= tol <= 1e-6:
        raise ValueError('Explicit integration mode and tolerance required')
    acting, switches, enabled = base.active_channels(acting, channel_switches)
    gen = generation()
    thermal = mode == 'isochoric'
    y0 = base.initial_state(p)
    if thermal:
        y0 = np.r_[y0, p['temperature_K']/1e7]
    rho = p['density_kg_m3']
    nb = rho/eos.MU
    calls = 0
    def rhs(time, values):
        nonlocal calls
        calls += 1
        if calls > base.legacy.MAX_RHS_EVALUATIONS:
            raise RuntimeError('Screened network RHS budget exceeded')
        t = float(values[-1]*1e7) if thermal else p['temperature_K']
        # The inherited rate constants enforce strict10<T_MK<16 for Be7EC.
        k = base.rate_constants(t, rho, enabled)
        state = _state(t, rho, values[:NSPEC], include_coulomb) if thermal or include_screening else None
        if include_screening:
            k = k*_screening_from_state(t, rho, values[:NSPEC], state)[0]
        flux = base.flux(values, k)
        dy = base.S@flux
        if not thermal:
            return np.r_[dy, flux]
        s = state['total']
        dT = (nb*float((base.Q-base.QNU)@flux)-float(s['gradient']@dy))/s['heat_capacity_J_m3_K']
        return np.r_[dy, flux, dT/1e7]
    times = np.linspace(0, p['duration_s'], 241)
    sol = solve_ivp(rhs, [0, p['duration_s']], y0, method='Radau', t_eval=times, rtol=tol,
                    atol=base.ATOL+([1e-12] if thermal else []))
    if not sol.success:
        raise RuntimeError('Screened network did not converge: '+sol.message)
    values = sol.y.T
    pop, xi = values[:,:NSPEC], values[:,NSPEC:NVAR]
    if not np.isfinite(values).all() or min(float(np.min(pop)), float(np.min(xi))) < -1e-20:
        raise RuntimeError('Invalid screened abundance/extent; no clamp')
    temps = values[:,-1]*1e7 if thermal else np.full(len(times), p['temperature_K'])
    baryon = float(np.max(abs(pop@A-1)))
    cat0 = float(np.sum(y0[base.CATALYST_INDICES]))
    cat = float(np.max(abs(np.sum(pop[:,base.CATALYST_INDICES],axis=1)-cat0)))
    if cat0:
        cat /= cat0
    charge = float(np.max(abs(pop@Z-y0[:NSPEC]@Z+xi@base.NU)))
    extents = xi*nb
    available, neutrinos = extents@base.Q, extents@base.QNU
    states = [_state(float(t), rho, y, include_coulomb) for t,y in zip(temps,pop)]
    factors = [_screening_from_state(float(t), rho, y, state)[0] if include_screening else np.ones(NCHAN)
               for t,y,state in zip(temps,pop,states)]
    events = np.array([base.flux(y, base.rate_constants(float(t),rho,enabled)*f)*nb for t,y,f in zip(temps,pop,factors)])
    u = np.array([state['total']['internal_energy_J_m3'] for state in states])
    energy = float(np.max(abs(u-u[0]-(available-neutrinos))/np.maximum(u[0],available))) if thermal else None
    if baryon > 1e-8 or cat > 1e-8 or charge > 1e-10 or energy is not None and energy > 1e-8:
        raise RuntimeError('Screened conservation or energy budget exceeded')
    if generation() != gen:
        raise ValueError('Scientific source changed during screened integration')
    return dict(schema=1, kind='is5_CNOII_PC_classical_screened_zone', mode=mode,
        scientific_generation=gen, parameters=p, acting=acting, channel_switches=switches, active_channels=enabled,
        include_coulomb=include_coulomb, include_screening=include_screening,
        species=list(SPECIES), channels=list(CHANNELS), initial_number_per_baryon=y0[:NSPEC].tolist(),
        time_s=times.tolist(), temperature_K=temps.tolist(), number_per_baryon=pop.tolist(), mass_fractions=(pop*A).tolist(),
        reaction_extents_m3=extents.tolist(), event_rates_m3_s=events.tolist(), screening_factors=np.array(factors).tolist(),
        energy_available_J_m3=available.tolist(), energy_neutrinos_J_m3=neutrinos.tolist(),
        non_neutrino_energy_available_J_m3=(available-neutrinos).tolist(),
        nuclear_power_W_m3=(events@base.Q).tolist(), neutrino_power_W_m3=(events@base.QNU).tolist(),
        neutrino_count_m3=(extents@base.NU).tolist(), produced_positrons_m3=(extents@base.BETA).tolist(),
        annihilated_electrons_m3=(extents@base.BETA).tolist(), captured_electrons_m3=(extents@base.EC).tolist(),
        internal_energy_J_m3=u.tolist(), pressure_Pa=[s['total']['pressure_Pa'] for s in states],
        heat_capacity_J_m3_K=[s['total']['heat_capacity_J_m3_K'] for s in states],
        Coulomb_internal_energy_J_m3=[0. if s['components'] is None else s['components']['sum']['internal_energy_J_m3'] for s in states],
        conservation=dict(baryon_absolute_error=baryon, catalyst_number_relative_error=cat,
                          nuclear_charge_plus_leptons_per_baryon_error=charge, energy_normalized_error=energy,
                          minimum_abundance=float(np.min(pop))),
        solver=dict(method='Radau', rtol=tol, RHS_calls=calls, nfev=sol.nfev, njev=sol.njev, nlu=sol.nlu),
        scope='Static thermodynamic fusion screening and classical-ion nonideal fixed-volume reservoir. SFII Be7EC/atomic Q/neutrino approximations retained. No quantum-ion screening, partial ionization, magnetic corrections, dynamic screening, transport, stellar structure or surface luminosity.')
