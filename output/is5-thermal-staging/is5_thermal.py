"""Isochoric burning with a composition-aware ideal-mixture thermal reservoir."""
from pathlib import Path
import copy
import hashlib
import numpy as np
from scipy.integrate import solve_ivp
from scipy.constants import elementary_charge,atomic_mass
import is5_core as core
import is5_eos as eos

T_SCALE=1e7
MEV_J=1e6*elementary_charge
ATOL=[1e-13,1e-25,1e-16,1e-13,1e-16,1e-28,1e-16,1e-16,1e-28,1e-16]+[1e-17]*9+[1e-12]
CODE_SHA=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def generation():
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest()!=CODE_SHA:
        raise ValueError('Restart after thermal evolution source changes')
    return dict(schema=1,id='is5:isochoric-ideal-mixture-burning',version='0.1.0',
                core=core.generation(),EOS=eos.generation(),code_sha256=CODE_SHA)


def integrate_zone(value,acting=None,channel_switches=None,*,decay_basis='nubase2020',tolerance=1e-9):
    p=core.parameters(value);a,c,active=core.active_channels(acting,channel_switches)
    tol=core.number(tolerance)
    if not 1e-12<=tol<=1e-6:
        raise ValueError('Thermal integration tolerance outside declared range')
    gen=generation();initial=np.r_[core.initial_state(p),p['temperature_K']/T_SCALE]
    nb=p['density_kg_m3']/atomic_mass
    qnet=(core.Q_MEV-core.NEUTRINO_MEV)*MEV_J
    calls=0
    def rhs(t,y):
        nonlocal calls
        calls+=1
        if calls>core.MAX_RHS_EVALUATIONS:
            raise RuntimeError('Thermal RHS budget exceeded')
        temperature=float(y[-1]*T_SCALE)
        state=eos.mixture(temperature,p['density_kg_m3'],float(np.sum(y[:10])),float(core.Z@y[:10]))
        k=core.coefficients(temperature,p['density_kg_m3'],active,decay_basis)
        f=core.flux(y,k);dy=core.S@f
        gradient=state['du_dions_per_baryon_J_m3']+core.Z*state['du_delectrons_per_baryon_J_m3']
        dT=(nb*float(qnet@f)-float(gradient@dy))/state['heat_capacity_J_m3_K']
        return np.r_[dy,f,dT/T_SCALE]
    times=np.linspace(0,p['duration_s'],241)
    solution=solve_ivp(rhs,[0,p['duration_s']],initial,method='Radau',rtol=tol,atol=ATOL,t_eval=times)
    if not solution.success:
        raise RuntimeError('Isochoric thermal integration did not converge: '+solution.message)
    values=solution.y.T;pop=values[:,:10];xi=values[:,10:19];temperatures=values[:,-1]*T_SCALE
    if not np.isfinite(values).all() or np.min(pop)<-1e-20 or np.min(xi)<-1e-20:
        raise RuntimeError('Thermal populations/extents outside conservation tolerance')
    if np.min(temperatures)<1e7 or np.max(temperatures)>3e7:
        raise ValueError('Thermal solution left the prescribed rate/EOS temperature domain')
    states=[eos.mixture(float(t),p['density_kg_m3'],float(np.sum(y)),float(core.Z@y)) for t,y in zip(temperatures,pop)]
    u=np.array([s['internal_energy_J_m3'] for s in states]);pressure=np.array([s['pressure_Pa'] for s in states])
    events=np.array([core.flux(y,core.coefficients(float(t),p['density_kg_m3'],active,decay_basis)) for t,y in zip(temperatures,pop)])*nb
    extents=xi*nb;available=extents@core.Q_MEV*MEV_J;neutrinos=extents@core.NEUTRINO_MEV*MEV_J
    deposited=available-neutrinos
    baryon=float(np.max(abs(pop@core.A-1)))
    catalyst0=float(np.sum(initial[4:10]));catalyst_drift=float(np.max(abs(np.sum(pop[:,4:],axis=1)-catalyst0)))
    catalyst_error=catalyst_drift/catalyst0 if catalyst0 else catalyst_drift
    charge=float(np.max(abs(pop@core.Z-initial[:10]@core.Z+xi@core.WEAK)))
    energy_error=float(np.max(abs(u-u[0]-deposited)/np.maximum(u[0],available)))
    if baryon>1e-8 or catalyst_error>1e-8 or charge>1e-10 or energy_error>1e-8:
        raise RuntimeError('Thermal baryon/catalyst/charge/energy conservation budget exceeded')
    if generation()!=gen:
        raise ValueError('Scientific generation changed during thermal integration')
    return dict(schema=1,kind='is5_isochoric_thermal_zone',scientific_generation=gen,parameters=p,acting=a,
        channel_switches=c,active_channels=active,decay_basis=decay_basis,species=list(core.SPECIES),channels=list(core.CHANNELS),
        time_s=times.tolist(),temperature_K=temperatures.tolist(),pressure_Pa=pressure.tolist(),
        number_per_baryon=pop.tolist(),mass_fractions=(pop*core.A).tolist(),reaction_extents_m3=extents.tolist(),event_rates_m3_s=events.tolist(),
        energy_available_J_m3=available.tolist(),energy_neutrinos_J_m3=neutrinos.tolist(),retained_nuclear_energy_J_m3=deposited.tolist(),
        internal_energy_J_m3=u.tolist(),total_internal_energy_J=(u*p['volume_m3']).tolist(),
        ion_internal_energy_J_m3=[s['ion_internal_energy_J_m3'] for s in states],
        electron_internal_energy_J_m3=[s['electron_internal_energy_J_m3'] for s in states],
        radiation_internal_energy_J_m3=[s['radiation_internal_energy_J_m3'] for s in states],
        heat_capacity_J_m3_K=[s['heat_capacity_J_m3_K'] for s in states],electron_eta=[s['electron_eta'] for s in states],
        neutrino_count_m3=(xi@core.WEAK*nb).tolist(),nuclear_power_W_m3=(events@core.Q_MEV*MEV_J).tolist(),
        neutrino_power_W_m3=(events@core.NEUTRINO_MEV*MEV_J).tolist(),
        conservation=dict(baryon_absolute_error=baryon,catalyst_number_relative_error=catalyst_error,
            nuclear_charge_plus_beta_per_baryon_error=charge,energy_normalized_error=energy_error,minimum_abundance=float(np.min(pop))),
        solver=dict(method='Radau',rtol=tol,atol=ATOL,RHS_calls=calls,nfev=solution.nfev,njev=solution.njev,nlu=solution.nlu),
        closure=dict(density='fixed',volume='fixed',external_work_W=0.,photon_escape_W=0.,neutrinos='local free escape',
            positrons='instant local annihilation already included in adopted atomic Q',radiation='confined LTE energy reservoir'),
        surface_luminosity_W=None,spatial_neutrino_flux_m2_s=None,stellar_structure=None,
        scope='Ideal isochoric thermal zone only. No Coulomb/screening, relativity, thermal pairs, partial ionization, spatial transport, hydrostatic adjustment or observed stellar profile.')
