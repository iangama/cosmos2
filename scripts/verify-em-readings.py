"""Independent Lorentz force/work ledger for all E/B contribution switches."""
from pathlib import Path
import itertools
import json
import sys
import numpy as np
from scipy.constants import elementary_charge
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from forces import evaluate
errors=[]
for sign,electric,magnetic in itertools.product((-1,1),(False,True),(False,True)):
    r=evaluate({'scenario':'electromagnetic','parameters':{'E_Vm':.8,'charge_sign':sign},
                'controls':{'electromagnetic':{'effects':{'electric_acceleration':electric,'magnetic_deflection':magnetic}}}})['result']
    p=r['particle_readings'];q=sign*elementary_charge;v=np.array(p['velocity_m_s'])
    fe=np.array(p['electric_force_N']);fm=np.array(p['magnetic_force_N'])
    assert np.allclose(fe,[q*.8*electric,0,0],rtol=1e-14,atol=0)
    assert np.allclose(fm,q*np.cross(v,[0,0,.001*magnetic]),rtol=1e-14,atol=0)
    assert np.allclose(fe+fm,p['total_force_N'],rtol=1e-14,atol=0)
    energy=np.array(p['kinetic_energy_J']);work=np.array(p['electric_work_J'])
    error=float(np.max(np.abs(energy-energy[0]-work))/energy[0]);assert error<1e-12
    assert max(abs(x) for x in p['magnetic_power_W'])<1e-28
    assert np.allclose(np.sum(fe*v,axis=1),p['electric_power_W'],rtol=1e-14,atol=0)
    errors.append(error)
report={'charge_and_effect_combinations':8,'force_components':True,'electric_work_balance_max_relative':max(errors),
        'magnetic_force_does_no_work':True,'units':'SI','scope':'uniform prescribed E/B, classical test particle'}
(ROOT/'evidence/em-readings-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
