"""Independent frozen upstream derivatives, beta limits and conservation."""
from pathlib import Path
import copy
import itertools
import json
import math
import sys
import numpy as np
from scipy.constants import atomic_mass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
from cno import DATA,SPECIES,CHANNELS,A,Z,STOICHIOMETRY,coefficients,event_flux,integrate_zone
from stellar import rate_value,YEAR_S
from forces import evaluate

assert np.array_equal(A@STOICHIOMETRY,np.zeros(6))
assert np.array_equal(Z@STOICHIOMETRY,[0,-1,0,0,-1,0])
rate_error = max(abs(rate_value(float(t),entry)/value-1) for entry in DATA['rates'].values()
                 for t,value in entry['reference_rates'].items())
assert rate_error<1e-12
derivative_error = 0
for ref in DATA['upstream_derivative_references']:
    y = np.array([ref['mass_fractions'][n] for n in SPECIES])/A
    own = STOICHIOMETRY@event_flux(y,coefficients(ref['T_K'],ref['rho_g_cm3']*1000,decay_basis='reaclib_wc12'))
    upstream = np.array([ref['ydot_mol_g_s'][n] for n in SPECIES])
    error = np.max(np.abs(own-upstream)/np.maximum(np.abs(upstream),1e-40))
    derivative_error = max(derivative_error,float(error))
assert derivative_error<1e-8  # m_u*N_A vs historical 1g/mol differs about10^-9.

default = integrate_zone(1.5e7,1.5e5,.35,.01,1e8*YEAR_S)
refined = integrate_zone(1.5e7,1.5e5,.35,.01,1e8*YEAR_S,tolerance=1e-10)
composition_error = float(np.max(np.abs(np.array(default['mass_fractions'])-refined['mass_fractions'])))
energy_error = abs(default['energy_deposited_J_m3'][-1]/refined['energy_deposited_J_m3'][-1]-1)
assert composition_error<1e-9 and energy_error<1e-8

def check_ledger(zone,density):
    assert zone['baryon_error']<1e-10 and zone['catalyst_number_relative_error']<1e-10
    assert zone['minimum_abundance']>=-1e-20
    y=np.array(zone['number_per_baryon'])
    extents=np.array(zone['reaction_extents_m3'])/(density/atomic_mass)
    ledger=y@Z+extents[:,1]+extents[:,4]
    assert np.max(np.abs(ledger-ledger[0]))<1e-12
    assert np.allclose(np.array(zone['energy_available_J_m3'])-zone['energy_neutrinos_J_m3'],
                       zone['energy_deposited_J_m3'],rtol=1e-14,atol=1e-12)

check_ledger(default,1.5e5)
for channel in CHANNELS:
    active={n:n!=channel for n in CHANNELS}
    zone=integrate_zone(1.5e7,1.5e5,.35,.01,1e8*YEAR_S,channels=active)
    check_ledger(zone,1.5e5)
    assert zone['final_event_rates_m3_s'][channel]==0
    assert np.array(zone['reaction_extents_m3'])[:,CHANNELS.index(channel)].max()==0
baseline=evaluate({'scenario':'cno'})['result']
for strong,weak,em in itertools.product((False,True),repeat=3):
    request={'scenario':'cno','controls':{name:{'acting':active} for name,active in
             zip(('strong','weak','electromagnetic'),(strong,weak,em))}}
    response=evaluate(request)
    zone=response['result']['network']
    check_ledger(zone,1.5e5)
    assert response['result']['reference']==baseline['reference']
    hidden=copy.deepcopy(request)
    for name in ('strong','weak','electromagnetic'): hidden['controls'][name]['visible']=False
    assert response['result']==evaluate(hidden)['result']
    if not weak: assert zone['neutrino_count_m3'][-1]==0
    if not em or not strong: assert zone['energy_available_J_m3'][-1]==0

# Isolate each weak channel with a seeded parent. One half-life must leave
# one half of the parent; no p capture or other beta decay participates.
for parent in ('n13','o15'):
    half=DATA['nuclides'][parent]['half_life_NUBASE_s']
    initial={n:0 for n in SPECIES};initial.update({'p':.35,'he4':.64,parent:.01})
    active={n:n==parent+'beta' for n in CHANNELS}
    zone=integrate_zone(1.5e7,1.5e5,.35,.01,half,channels=active,initial_mass_fractions=initial)
    assert abs(zone['mass_fractions'][-1][SPECIES.index(parent)]/.01-.5)<1e-9
    check_ledger(zone,1.5e5)

for temperature,density,catalyst,duration in ((1e7,1e4,1e-8,1),(3e7,3e5,.05,5e9)):
    zone=integrate_zone(temperature,density,.35,catalyst,duration*YEAR_S)
    check_ledger(zone,density)
report={'rate_relative_error':rate_error,'upstream_derivative_relative_error':derivative_error,
        'derivative_normalization':'Model rho/m_u; upstream conventional molar abundance per gram. Difference~10^-9 is retained, not tuned away.',
        'individual_channels_suppressed':6,'global_force_combinations':8,
        'composition_refinement_error':composition_error,'energy_refinement_relative_error':energy_error,
        'baryon_error':default['baryon_error'],'catalyst_number_relative_error':default['catalyst_number_relative_error'],
        'nubase_half_lives_verified':True,'charge_and_positron_ledger':True,'domain_corners':True,
        'scope':'Fixed-zone CNO-I only; no full stellar evolution or hot-CNO certification'}
(ROOT/'evidence/cno-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
