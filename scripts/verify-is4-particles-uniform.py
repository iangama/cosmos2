"""Analytic sign, second-order refinement, work and transaction checks for IS4 staging."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys
import traceback
import zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/is4-body-particle-staging';sys.path.insert(0,str(STAGE))
from is4_particles import Phase,DomainExit,boris_step
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

class Uniform:
    def __init__(self,E=(0.,0.,0.),B=(0.,0.,1.),g=(0.,0.,0.),domain=True):self.E,self.B,self.g,self.domain=E,B,g,domain
    def segment_in_domain(self,start,end):return self.domain
    def evaluate(self,x):return {'valid':True,'electric_field_V_m':self.E,'magnetic_field_T':self.B,'gravity_m_s2':self.g}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label.')
    folder=ROOT/('output/is4-particles-uniform-'+args.label);receipt=ROOT/('evidence/is4-particles-uniform-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve IS4 evidence.')
    folder.mkdir();files=[*STAGE.glob('*.py'),Path(__file__),ROOT/'IS-4-PARTICULAS-CONTRATO-PREVIO.md',ROOT/'output/c212-em-integration-product/em/em_particles.py']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(ROOT).as_posix())
    report={'schema':1,'accepted':False,'completed':False,'source_sha256':hashes,'cases':[]}
    try:
        for charge in [-1.,1.]:
            errors=[];energy_error=0.
            for count in [2000,4000,8000]:
                phase=Phase((0.,0.,0.),(1.,0.,0.));h=20*math.pi/count
                for i in range(count):
                    phase,diagnostic=boris_step(Uniform(),phase,charge,1.,h)
                    energy_error=max(energy_error,abs(math.hypot(*phase.velocity_m_s)-1.))
                # Analytic v=(cos(qt),-sin(qt),0), x=(sin(qt)/q,(cos(qt)-1)/q,0).
                t=phase.time_s
                exact=np.array([math.sin(charge*t)/charge,(math.cos(charge*t)-1)/charge,0.])
                errors.append(float(np.linalg.norm(np.array(phase.position_m)-exact)))
            ratios=[errors[i]/errors[i+1] for i in range(2)]
            assert all(3.4<=r<=4.6 for r in ratios),ratios
            assert errors[-1]<=5e-4+1e-5 and energy_error<=1e-12,(errors,energy_error)
            first,_=boris_step(Uniform(),Phase((0.,0.,0.),(1.,0.,0.)),charge,1.,.01)
            assert first.velocity_m_s[1]*charge<0
            report['cases'].append({'charge':charge,'position_errors_m':errors,'refinement_ratios':ratios,'speed_relative_error_max':energy_error,'handedness_correct':True})
        for electric,gravity in [(True,False),(False,True),(True,True),(False,False)]:
            initial=Phase((2.,3.,4.),(1.,2.,3.));phase=initial
            model=Uniform(E=(2.,-1.,.5),B=(0.,0.,0.),g=(.25,-2.,1.))
            acceleration=(np.array(model.E)*.5 if electric else np.zeros(3))+(np.array(model.g) if gravity else np.zeros(3))
            maximum=0.
            for i in range(100):
                phase,d=boris_step(model,phase,1.,2.,.01,electric_acting=electric,gravity_acting=gravity)
                residual=abs(d['kinetic_change_J']-d['electric_work_J']-d['gravity_work_J'])
                maximum=max(maximum,residual)
            t=phase.time_s;expected=np.array(initial.position_m)+t*np.array(initial.velocity_m_s)+.5*t*t*acceleration
            assert np.max(np.abs(expected-phase.position_m))<=1e-10
            assert np.max(np.abs(np.array(initial.velocity_m_s)+t*acceleration-phase.velocity_m_s))<=1e-10
            assert maximum<=1e-12
            report['cases'].append({'electric':electric,'gravity':gravity,'analytic_position_velocity':True,'work_residual_max_J':maximum})
        # Nonzero B with E+g verifies the combined kick/rotation work identity.
        phase=Phase((0.,0.,0.),(1.,2.,3.));maximum=0.
        for _ in range(100):
            phase,d=boris_step(Uniform(E=(2.,-1.,.5),g=(.25,-2.,1.)),phase,-1.,2.,.01)
            maximum=max(maximum,abs(d['kinetic_change_J']-d['electric_work_J']-d['gravity_work_J']))
        assert maximum<=1e-12
        report['combined_B_E_gravity_work_residual_max_J']=maximum
        initial=Phase((0.,0.,0.),(1.,0.,0.));refusals=0
        for model,changes in [(Uniform(),{'dt_s':0.}),(Uniform(),{'mass_kg':-1.}),(Uniform(),{'charge_C':True}),
            (Uniform(),{'gravity_acting':1}),(Uniform(),{'dt_s':.11}),(Uniform(domain=False),{}),
            (Uniform(g=(float('nan'),0.,0.)),{}),(Uniform(E=(1e20,0.,0.)),{})]:
            args={'charge_C':1.,'mass_kg':1.,'dt_s':.01,**changes};before=repr(initial)
            try:boris_step(model,initial,**args)
            except (ValueError,DomainExit):refusals+=1
            else:raise AssertionError('Invalid trial accepted.')
            assert repr(initial)==before
        assert all(sha(ROOT/name)==value for name,value in hashes.items())
        report.update(accepted=True,completed=True,transactional_refusals=refusals,
            scope='Uniform analytic sign/order2, separate E/gravity controls, E+B+g discrete work and input refusals only. Frozen IGRF/JRM/gravity snapshot adapter, real domain-segment checks, independent DOP853 body tests, persistence/worker/native/profile remain pending.')
    except Exception:report['failure']=traceback.format_exc()
    receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'accepted':report['accepted'],'cases':len(report['cases']),'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
