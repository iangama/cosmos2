# SPDX-License-Identifier: LGPL-3.0-or-later
"""Density/temperature cross derivatives of the frozen, accepted Coulomb EOS.

No dynamics, new EOS terms, altered domain guards or numerical differentiation
in this production wrapper. See the preceding contract and derivation note.
"""
from pathlib import Path
import hashlib
import json
import math
import sys

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'output/is5-coulomb-mixture-staging'))
import is5_coulomb_mixture as model

PARENT=ROOT/'evidence/is5-coulomb-mixture-20261028b.json'
FILES=[Path(__file__),HERE/'THIRD-PARTY.md',HERE/'LICENSE-LGPL-3.0.txt',HERE/'LICENSE-GPL-3.0.txt',
       ROOT/'IS-5-COMPRESSAO-CONTRATO-PREVIO.md',ROOT/'IS-5-COMPRESSAO-DERIVADAS.md',PARENT,
       ROOT/'output/is5-compression-research-20261029/acquisition.json',
       ROOT/'output/is5-compression-research-20261029/mesa-controls-latest-20261029.html']
IMPORTED=None
PT='pressure_temperature_derivative_Pa_K'
UR='energy_log_density_derivative_J_m3'


def generation():
    global IMPORTED
    current={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES}
    if IMPORTED is None:IMPORTED=current
    if current!=IMPORTED:raise ValueError('Restart after cross-derivative source changes')
    accepted=json.loads(PARENT.read_text(encoding='utf-8'))
    parent=model.generation()
    if not accepted['accepted'] or parent!=accepted['generation']:
        raise ValueError('Cross derivatives require the accepted parent Coulomb EOS')
    return dict(schema=1,id='is5:accepted-EOS-density-temperature-cross-derivatives',version='0.1.0',
                source_sha256=dict(IMPORTED),parent_generation=parent,
                scope='Analytic cross derivatives only; no prescribed-density evolution, work integration, hydrostatics or new EOS.')


def evaluate(temperature_K,density_kg_m3,number_per_baryon,mass_numbers,charges):
    state=model.evaluate(temperature_K,density_kg_m3,number_per_baryon,mass_numbers,charges)
    t,rho=state['temperature_K'],state['density_kg_m3']
    base=state['ideal'];nb=base['baryon_density_m3'];ye=base['electron_density_m3']/nb
    y=[model.ideal.number(value) for value in number_per_baryon]
    derivatives={
        'ideal_ions':{PT:base['ion_density_m3']*model.K,UR:base['ion_internal_energy_J_m3']},
        'ideal_electrons':{PT:(2/3)*base['electron_heat_capacity_J_m3_K'],UR:ye*base['du_delectrons_per_baryon_J_m3']},
        'photons':{PT:4*base['radiation_internal_energy_J_m3']/(3*t),UR:0.}}
    def combine(names):return {field:math.fsum(derivatives[name][field] for name in names) for field in (PT,UR)}
    derivatives['ideal']=combine(['ideal_ions','ideal_electrons','photons'])
    tj=model.ad.exp(model.ad.Jet.variable(math.log(t),0,2))
    nbj=model.ad.exp(model.ad.Jet.variable(math.log(rho/model.MU),1,2))
    free=model.free_energy_components(tj,nbj,y,charges)
    for name,jet in free.items():
        derivatives[name]={PT:float((jet.h[0,1]-jet.g[0])/t),UR:float(jet.g[1]-jet.h[0,1])}
    derivatives['Coulomb_sum']=combine(['ii','ie','ee','mix'])
    derivatives['total']=combine(['ideal','Coulomb_sum'])
    thermodynamics={
        'ideal_ions':(base['ion_internal_energy_J_m3'],base['ion_pressure_Pa']),
        'ideal_electrons':(base['electron_internal_energy_J_m3'],base['electron_pressure_Pa']),
        'photons':(base['radiation_internal_energy_J_m3'],base['radiation_pressure_Pa']),
        'ideal':(base['internal_energy_J_m3'],base['pressure_Pa']),
        **{name:(values['internal_energy_J_m3'],values['pressure_Pa']) for name,values in state['components'].items() if name!='sum'},
        'Coulomb_sum':(state['components']['sum']['internal_energy_J_m3'],state['components']['sum']['pressure_Pa']),
        'total':(state['total']['internal_energy_J_m3'],state['total']['pressure_Pa'])}
    maxwell={}
    for name,values in derivatives.items():
        if not all(math.isfinite(value) for value in values.values()):raise RuntimeError('Nonfinite EOS cross derivative')
        u,p=thermodynamics[name];target=u+p-t*values[PT]
        scale=max(abs(u+p),abs(t*values[PT]),abs(values[UR]),1e-14*nb*model.K*t)
        maxwell[name]=dict(residual_J_m3=values[UR]-target,relative=abs(values[UR]-target)/scale)
    return dict(state=state,derivatives=derivatives,maxwell=maxwell,scientific_generation=generation())


generation()
