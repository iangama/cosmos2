"""Independent scalar SI formulas audit the new read-only G instruments."""
from copy import deepcopy
from pathlib import Path
import argparse
import hashlib
import itertools
import json
import math
import sys

ROOT=Path(__file__).resolve().parents[1];G=ROOT/'output/c212-em-integration-product'
sys.path[:0]=[str(G/'app'),str(G/'em')]
from em_measurements import measure
from em_presets import create, NAMES
from em_editor import default_editor, diagnostics
from em_experiment import generation
from em_timing import execution_generation

parser=argparse.ArgumentParser();parser.add_argument('--label',default='initial');args=parser.parse_args()
assert args.label.isalnum() and len(args.label)<=16
suffix='' if args.label=='initial' else '-'+args.label
destination=ROOT/f'evidence/em-integration-measurements{suffix}-check.json';assert not destination.exists()
constants=json.loads((G/'em/constants.json').read_bytes())
ke=1/(4*math.pi*constants['vacuum_electric_permittivity_F_m']['value'])
mu=constants['vacuum_magnetic_permeability_N_A2']['value']/(4*math.pi)
def cross(a,b):return [a[(k+1)%3]*b[(k+2)%3]-a[(k+2)%3]*b[(k+1)%3] for k in range(3)]
def dot(a,b):return math.fsum(x*y for x,y in zip(a,b))
def scalar_fields(p,index=0):
    mutual=p['mode']=='mutual_electrostatic'
    x=p['phase']['position_m'][index] if mutual else p['phase']['position_m']
    if mutual:
        sources=[{'position_m':position,'charge_C':q,'magnetic_moment_A_m2':[0,0,0]}
                 for j,(position,q) in enumerate(zip(p['phase']['position_m'],p['system']['charge_C'])) if j!=index]
        es=[0.,0.,0.];bs=[0.,0.,0.]
    else:sources=p['model']['sources'];es=list(p['model']['uniform_E_V_m']);bs=list(p['model']['uniform_B_T'])
    for source in sources:
        d=[a-b for a,b in zip(x,source['position_m'])];r=math.hypot(*d);moment=source['magnetic_moment_A_m2']
        for k in range(3):
            es[k]+=ke*source['charge_C']*d[k]/r**3
            bs[k]+=mu*(3*d[k]*dot(moment,d)/r**5-moment[k]/r**3)
    return es,bs
def energies(p):
    if p['mode']=='test_particle':
        m=p['particle']['mass_kg'];q=p['particle']['charge_C'];v=p['phase']['velocity_m_s'];x=p['phase']['position_m']
        potential=q*(math.fsum(ke*s['charge_C']/math.dist(x,s['position_m']) for s in p['model']['sources'])-dot(p['model']['uniform_E_V_m'],x)) if p['controls']['electric_acting'] else 0.
        return .5*m*dot(v,v),potential
    masses=p['system']['mass_kg'];qs=p['system']['charge_C'];xs=p['phase']['position_m'];vs=p['phase']['velocity_m_s']
    kinetic=math.fsum(.5*m*dot(v,v) for m,v in zip(masses,vs))
    potential=math.fsum(ke*qs[i]*qs[j]/math.dist(xs[i],xs[j]) for i,j in itertools.combinations(range(len(qs)),2)) if p['controls']['acting'] else 0.
    return kinetic,potential
def close(a,b,scale=0.):
    scale=max(abs(a),abs(b),scale,1e-100)
    assert abs(a-b)<=3e-12*scale+1e-100,(a,b)

checks=[]
for name in NAMES:
    combos=itertools.product((False,True),repeat=2) if name!='coulomb' else ((False,),(True,))
    for flags in combos:
        ex=create(name)
        ex.controls=dict(zip(('electric_acting','magnetic_acting') if name!='coulomb' else ('acting',),flags))
        ex.editor=default_editor(ex);initial=deepcopy(ex.payload());ex.advance(128)
        for index in (range(2) if name=='coulomb' else range(1)):
            if name=='coulomb':ex.editor['visual']['selected_id']=ex.model.ids[index]
            s={'system_id':'fixture','edit_token':'token','revision':0,'time_s':ex.phase.time_s,'frame':'EM_SI_FIXED_INERTIAL',
               'scientific_generation':generation(),'execution_generation':execution_generation(),
               'experiment':ex.payload(),'editor':deepcopy(ex.editor),'diagnostics':diagnostics(ex)}
            before=json.dumps(s,sort_keys=True);r=measure(s);assert json.dumps(s,sort_keys=True)==before
            p=s['experiment'];electric,magnetic=scalar_fields(p,index);q=r['particle']['charge_C'];v=r['particle']['velocity_m_s']
            expected_e=[q*e*(flags[0]) for e in electric]
            expected_b=[q*b*(flags[1]) for b in cross(v,magnetic)] if name!='coulomb' else [0.,0.,0.]
            for actual,expected in zip(r['force']['electric_force_N'],expected_e):close(actual,expected)
            for actual,expected in zip(r['force']['magnetic_force_N'],expected_b):close(actual,expected)
            for actual,e,b in zip(r['force']['force_N'],expected_e,expected_b):close(actual,e+b)
            k0,u0=energies(initial);k,u=energies(p)
            close(r['energy']['kinetic_energy_J'],k);close(r['energy']['potential_energy_J'],u)
            close(r['balance']['electric_work_from_static_potential_J'],u0-u,abs(k0)+abs(u0))
            close(r['balance']['kinetic_change_J'],k-k0,abs(k0)+abs(u0))
            close(r['electric_power_W'],dot(expected_e,v))
            assert r['source_snapshot']==s['experiment'] and r['time_s']==ex.phase.time_s
            if name=='helix' and flags[1]:
                close(r['gyro_reference']['period_s'],2*math.pi);close(r['gyro_reference']['radius_m'],math.hypot(v[0],v[1]))
            checks.append({'preset':name,'controls':ex.controls,'particle':r['particle']['id'],'independent_force_energy_work_and_power':True})
report={'status':'read_only_SI_instruments_verified_against_independent_scalar_formulas','checks':checks,
        'snapshot_preserved':True,'scientific_generation':generation(),
        'source_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),G/'app/em_measurements.py')},
        'scope':'New force, energy and potential-difference work readouts only. Does not replace core convergence, native UI, or performance proofs.'}
destination.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'cases':len(checks)}),flush=True)
