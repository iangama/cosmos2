# SPDX-License-Identifier: LGPL-3.0-or-later
"""Closed baryon-count zone with prescribed density and explicit pressure work.

No hydrostatic/dynamic gravity solver, photon transport or surface luminosity.
All rates, Q values, screening and EOS terms are imported from accepted models.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
import numpy as np
from scipy.integrate import solve_ivp
import is5_eos_cross as cross

ROOT=cross.ROOT
sys.path.insert(0,str(ROOT/'output/is5-coulomb-network-staging'))
import is5_coulomb_network as network

base=network.base
NSPEC,NVAR,NCHAN=network.NSPEC,network.NVAR,network.NCHAN
PT=cross.PT
PARENT=ROOT/'evidence/is5-eos-cross-20261029a.json'
FILES=[Path(__file__),ROOT/'IS-5-COMPRESSAO-EVOLUCAO-CONTRATO.md',PARENT]
IMPORTED=None


def generation():
    global IMPORTED
    current={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES}
    if IMPORTED is None:IMPORTED=current
    if current!=IMPORTED:raise ValueError('Restart after prescribed-density model source changes')
    accepted=json.loads(PARENT.read_text(encoding='utf-8'))
    cross_gen=cross.generation()
    if not accepted['accepted'] or accepted['generation']!=cross_gen:
        raise ValueError('Prescribed-density evolution requires accepted cross derivatives')
    return dict(schema=1,id='is5:closed-baryon-prescribed-density-CNOII-PC-zone',version='0.1.0',
                source_sha256=dict(IMPORTED),cross_EOS=cross_gen,network=network.generation(),
                scope='Prescribed density/volume, thermal/composition response and external pressure work; no hydrodynamics, transport or stellar calibration.')


def density_program(value,parameters):
    if not isinstance(value,dict) or value.get('kind') not in ('constant','exponential','cycle'):
        raise ValueError('Explicit constant, exponential or cycle density program required')
    expected={'kind'} if value['kind']=='constant' else {'kind','ratio'}
    if set(value)!=expected:raise ValueError('Density program fields differ')
    ratio=1. if value['kind']=='constant' else base.legacy.number(value['ratio'])
    if not .8<=ratio<=1.2:raise ValueError('Density ratio must lie from0.8to1.2')
    rho0=parameters['density_kg_m3']
    if not 1e4<=min(rho0,rho0*ratio)<=max(rho0,rho0*ratio)<=3e5:
        raise ValueError('Prescribed density extrema outside the accepted EOS domain')
    return dict(kind=value['kind']) if value['kind']=='constant' else dict(kind=value['kind'],ratio=ratio)


def _density(seconds,parameters,program):
    phase=seconds/parameters['duration_s']
    amplitude=math.log(program.get('ratio',1.))
    if program['kind']=='cycle':
        logratio=amplitude*math.sin(math.pi*phase)**2
        rate=amplitude*math.pi/parameters['duration_s']*math.sin(2*math.pi*phase)
    else:
        logratio=amplitude*phase
        rate=amplitude/parameters['duration_s']
    rho=parameters['density_kg_m3']*math.exp(logratio)
    volume=parameters['volume_m3']*parameters['density_kg_m3']/rho
    return rho,rate,volume


def _thermo(temp,rho,pop,include_coulomb):
    y=[float(v) for v in pop]
    if include_coulomb:
        result=cross.evaluate(float(temp),float(rho),y,network.AI,network.ZI)
        state=result['state'];s=state['total']
        return dict(total={**s,'gradient':np.array(s['du_dnumber_per_baryon_J_m3'])},
                    components=state['components'],pressure_T=result['derivatives']['total'][PT])
    state=base.eos.mixture(float(temp),float(rho),float(np.sum(pop)),float(network.Z@pop))
    gradient=state['du_dions_per_baryon_J_m3']+network.Z*state['du_delectrons_per_baryon_J_m3']
    return dict(total={**state,'gradient':gradient},components=None,
                pressure_T=state['ion_density_m3']*network.eos.K+(2/3)*state['electron_heat_capacity_J_m3_K']+
                           4*state['radiation_internal_energy_J_m3']/(3*temp))


def integrate_zone(value,history,acting=None,channel_switches=None,*,include_coulomb=True,include_screening=True,tolerance=1e-9):
    if not isinstance(value,dict) or set(value)!=set(base.DEFAULT_PARAMETERS):
        raise ValueError('Exact initial-zone parameter fields required')
    p=base.parameters(value);program=density_program(history,p)
    tol=base.legacy.number(tolerance)
    if not 1e-12<=tol<=1e-6:raise ValueError('Explicit integration tolerance outside declared range')
    if type(include_coulomb) is not bool or type(include_screening) is not bool:
        raise ValueError('Explicit boolean EOS and screening options required')
    if include_screening and not include_coulomb:raise ValueError('Screening requires Coulomb EOS')
    acting,switches,enabled=base.active_channels(acting,channel_switches)
    gen=generation()
    initial=base.initial_state(p)
    state0=_thermo(p['temperature_K'],p['density_kg_m3'],initial[:NSPEC],include_coulomb)
    nb0=p['density_kg_m3']/network.eos.MU
    baryon_count=nb0*p['volume_m3']
    energy0=state0['total']['internal_energy_J_m3']*p['volume_m3']
    values0=np.r_[initial,p['temperature_K']/1e7,0.]
    calls=0
    def rhs(seconds,values):
        nonlocal calls
        calls+=1
        if calls>base.legacy.MAX_RHS_EVALUATIONS:raise RuntimeError('Prescribed-density RHS budget exceeded')
        temp=float(values[NVAR]*1e7);pop=values[:NSPEC]
        rho,lograte,volume=_density(seconds,p,program);nb=rho/network.eos.MU
        bare=base.rate_constants(temp,rho,enabled)
        state=_thermo(temp,rho,pop,include_coulomb)
        factors=network._screening_from_state(temp,rho,pop,state)[0] if include_screening else np.ones(NCHAN)
        flux=base.flux(values,bare*factors);dy=base.S@flux;s=state['total']
        thermal=(nb*float((base.Q-base.QNU)@flux)-float(s['gradient']@dy)+temp*state['pressure_T']*lograte)/s['heat_capacity_J_m3_K']
        work=s['pressure_Pa']*volume*lograte
        return np.r_[dy,flux,thermal/1e7,work/energy0]
    times=np.linspace(0,p['duration_s'],241)
    sol=solve_ivp(rhs,[0,p['duration_s']],values0,method='Radau',t_eval=times,rtol=tol,
                  atol=np.r_[base.ATOL,1e-12,1e-13])
    if not sol.success:raise RuntimeError('Prescribed-density integration did not converge: '+sol.message)
    values=sol.y.T;pop=values[:,:NSPEC];xi=values[:,NSPEC:NVAR]
    if not np.isfinite(values).all() or min(float(np.min(pop)),float(np.min(xi))) < -1e-20:
        raise RuntimeError('Invalid prescribed-density populations/extents; no clamp')
    temps=values[:,NVAR]*1e7
    rho_rates=[_density(float(t),p,program) for t in times]
    densities=np.array([v[0] for v in rho_rates]);volumes=np.array([v[2] for v in rho_rates])
    states=[_thermo(float(t),float(rho),y,include_coulomb) for t,rho,y in zip(temps,densities,pop)]
    factors=np.array([network._screening_from_state(float(t),float(rho),y,state)[0] if include_screening else np.ones(NCHAN)
                      for t,rho,y,state in zip(temps,densities,pop,states)])
    fluxes=np.array([base.flux(y,base.rate_constants(float(t),float(rho),enabled)*f) for t,rho,y,f in zip(temps,densities,pop,factors)])
    extents=xi*baryon_count
    available=extents@base.Q;neutrinos=extents@base.QNU;retained=available-neutrinos
    u=np.array([s['total']['internal_energy_J_m3'] for s in states]);energy=u*volumes
    work=values[:,NVAR+1]*energy0
    pressure=np.array([s['total']['pressure_Pa'] for s in states])
    scale=np.maximum.reduce([np.full(241,energy0),abs(energy),abs(available),abs(work)])
    balance=float(np.max(abs(energy-energy0-retained-work)/scale))
    baryon=float(np.max(abs(pop@network.A-1)))
    cat0=float(np.sum(initial[base.CATALYST_INDICES]));cat=float(np.max(abs(np.sum(pop[:,base.CATALYST_INDICES],axis=1)-cat0)))
    if cat0:cat/=cat0
    charge=float(np.max(abs(pop@network.Z-initial[:NSPEC]@network.Z+xi@base.NU)))
    if balance>1e-8 or baryon>1e-8 or cat>1e-8 or charge>1e-10:
        raise RuntimeError('Prescribed-density conservation budget exceeded')
    if generation()!=gen:raise ValueError('Scientific source changed during prescribed-density integration')
    return dict(schema=1,kind='is5_prescribed_density_CNOII_PC_classical_zone',mode='prescribed_density',
        scientific_generation=gen,parameters=p,density_history=program,acting=acting,channel_switches=switches,active_channels=enabled,
        include_coulomb=include_coulomb,include_screening=include_screening,species=list(network.SPECIES),channels=list(network.CHANNELS),
        baryon_count=baryon_count,initial_internal_energy_J=energy0,initial_number_per_baryon=initial[:NSPEC].tolist(),
        time_s=times.tolist(),temperature_K=temps.tolist(),density_kg_m3=densities.tolist(),volume_m3=volumes.tolist(),
        number_per_baryon=pop.tolist(),mass_fractions=(pop*network.A).tolist(),reaction_extents_per_baryon=xi.tolist(),
        reaction_extents_count=extents.tolist(),event_rates_per_s=(fluxes*baryon_count).tolist(),
        event_rates_m3_s=(fluxes*(densities/network.eos.MU)[:,None]).tolist(),screening_factors=factors.tolist(),
        internal_energy_J_m3=u.tolist(),internal_energy_J=energy.tolist(),external_pressure_work_J=work.tolist(),
        energy_available_J=available.tolist(),energy_neutrinos_J=neutrinos.tolist(),non_neutrino_energy_available_J=retained.tolist(),
        nuclear_power_W=(fluxes@base.Q*baryon_count).tolist(),neutrino_power_W=(fluxes@base.QNU*baryon_count).tolist(),
        external_pressure_power_W=(pressure*volumes*np.array([v[1] for v in rho_rates])).tolist(),
        neutrino_count=(extents@base.NU).tolist(),produced_positrons=(extents@base.BETA).tolist(),
        annihilated_electrons=(extents@base.BETA).tolist(),captured_electrons=(extents@base.EC).tolist(),
        pressure_Pa=pressure.tolist(),heat_capacity_J_m3_K=[s['total']['heat_capacity_J_m3_K'] for s in states],
        Coulomb_internal_energy_J_m3=[0. if s['components'] is None else s['components']['sum']['internal_energy_J_m3'] for s in states],
        conservation=dict(baryon_absolute_error=baryon,catalyst_number_relative_error=cat,
            nuclear_charge_plus_leptons_per_baryon_error=charge,energy_normalized_error=balance,
            minimum_abundance=float(np.min(pop)),minimum_extent_per_baryon=float(np.min(xi))),
        solver=dict(method='Radau',rtol=tol,RHS_calls=calls,nfev=sol.nfev,njev=sol.njev,nlu=sol.nlu),
        scope='Externally prescribed density/volume of a closed baryon-count zone; nuclear/thermal response and external pressure work only. No hydrodynamics, gravitational evolution, transport or surface luminosity.')


generation()
