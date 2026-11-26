# SPDX-License-Identifier: LGPL-3.0-or-later
"""Same accepted Coulomb free energy, using only its required thermal Hessian row."""
from pathlib import Path
import hashlib
import json
import math
import sys
import numpy as np

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'output/is5-compression-staging'))
import is5_eos_cross as reference
parent=reference.model
import is5_thermal_jet as ad

PARENT=ROOT/'evidence/is5-eos-cross-20261029a.json'
FILES=[Path(__file__),HERE/'is5_thermal_jet.py',HERE/'THIRD-PARTY.md',HERE/'LICENSE-LGPL-3.0.txt',HERE/'LICENSE-GPL-3.0.txt',
       ROOT/'IS-5-COMPRESSAO-OTIMIZACAO-CONTRATO.md',PARENT]
IMPORTED=None
PT,UR=reference.PT,reference.UR


def generation():
    global IMPORTED
    hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES}
    if IMPORTED is None:IMPORTED=hashes
    if hashes!=IMPORTED:raise ValueError('Restart after thermal-row EOS source changes')
    accepted=json.loads(PARENT.read_text());ref=reference.generation()
    if not accepted['accepted'] or accepted['generation']!=ref:raise ValueError('Accepted full EOS cross reference differs')
    return dict(schema=1,id='is5:same-PC-EOS-thermal-Hessian-row',version='0.1.0',source_sha256=dict(IMPORTED),
                reference_generation=ref,scope='Same free energy/domain; scalar, full composition gradient and thermal Hessian row only.')


def _numeric(temperature_K,density_kg_m3,number_per_baryon,mass_numbers,charges):
    """Internal evaluation inside a caller's before/after generation guard.

    Physical validation runs on every call. Public callers use evaluate().
    """
    t,rho,y,base,diagnostics=parent._validated(temperature_K,density_kg_m3,number_per_baryon,mass_numbers,charges)
    dimension=len(y)+2;nb=rho/parent.MU
    tj=ad.exp(ad.Jet.variable(math.log(t),0,dimension))
    nbj=ad.exp(ad.Jet.variable(math.log(nb),1,dimension))
    yj=[ad.Jet.variable(float(v),i+2,dimension) for i,v in enumerate(y)]
    free=parent.free_energy_components(tj,nbj,yj,charges,ad);free['sum']=sum(free.values())
    components={};derivatives={}
    for name,jet in free.items():
        if not all(math.isfinite(float(v)) for v in [jet.v,*jet.g,*jet.ht]):raise RuntimeError('Nonfinite thermal-row free energy')
        components[name]=dict(free_energy_J_m3=jet.v,internal_energy_J_m3=jet.v-jet.g[0],
            pressure_Pa=jet.g[1]-jet.v,heat_capacity_J_m3_K=(jet.g[0]-jet.ht[0])/t,
            du_dnumber_per_baryon_J_m3=(jet.g[2:]-jet.ht[2:]).tolist(),neutral_chemical_potential_J=(jet.g[2:]/nb).tolist())
        derivatives['Coulomb_sum' if name=='sum' else name]={PT:float((jet.ht[1]-jet.g[0])/t),UR:float(jet.g[1]-jet.ht[1])}
    ye=base['electron_density_m3']/base['baryon_density_m3']
    derivatives['ideal']={PT:base['ion_density_m3']*parent.K+(2/3)*base['electron_heat_capacity_J_m3_K']+
                             4*base['radiation_internal_energy_J_m3']/(3*t),
                          UR:base['ion_internal_energy_J_m3']+ye*base['du_delectrons_per_baryon_J_m3']}
    derivatives['total']={field:derivatives['ideal'][field]+derivatives['Coulomb_sum'][field] for field in [PT,UR]}
    total={field:base[field]+components['sum'][field] for field in ['pressure_Pa','internal_energy_J_m3','heat_capacity_J_m3_K']}
    total['du_dnumber_per_baryon_J_m3']=(base['du_dions_per_baryon_J_m3']+np.array(charges)*base['du_delectrons_per_baryon_J_m3']+
                                      np.array(components['sum']['du_dnumber_per_baryon_J_m3'])).tolist()
    if any(not math.isfinite(total[field]) or total[field]<=0 for field in ['pressure_Pa','internal_energy_J_m3','heat_capacity_J_m3_K']):
        raise RuntimeError('Invalid total thermal-row thermodynamics')
    return dict(state=dict(temperature_K=t,density_kg_m3=rho,components=components,ideal=base,total=total,diagnostics=diagnostics),
                derivatives=derivatives)


def evaluate(temperature_K,density_kg_m3,number_per_baryon,mass_numbers,charges):
    gen=generation()
    result=_numeric(temperature_K,density_kg_m3,number_per_baryon,mass_numbers,charges)
    if generation()!=gen:raise ValueError('Source changed during thermal-row evaluation')
    return {**result,'scientific_generation':gen}


generation()
