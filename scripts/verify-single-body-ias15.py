"""Pinned REBOUND zero-force criteria against analytic inertial motion.

Standalone diagnosis/proposal, no changes to installed Session or library.
"""
from pathlib import Path
import hashlib
import json
import math
import tempfile
import warnings

import rebound

ROOT=Path(__file__).resolve().parents[1]
cases=[]
for moving in (False,True):
    initial=[3.,-2.,7.]
    velocity=[.17,-.31,.09] if moving else [0.,0.,0.]
    models=[]
    for mode in ('PRS23','INDIVIDUAL'):
        sim=rebound.Simulation();sim.G=1.;sim.integrator='ias15';sim.integrator.epsilon=1e-9;sim.integrator.adaptive_mode=mode
        sim.add(m=.01,x=initial[0],y=initial[1],z=initial[2],vx=velocity[0],vy=velocity[1],vz=velocity[2])
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            for index in range(1,101):sim.integrate(index*.01)
        body=sim.particles[0];expected=[initial[k]+velocity[k]*sim.t for k in range(3)]
        difference=max(abs(a-b) for a,b in zip([body.x,body.y,body.z],expected))
        assert difference<4e-14 and [body.vx,body.vy,body.vz]==velocity
        assert body.ax==body.ay==body.az==0. and sim.integrator.epsilon==1e-9
        record={'moving':moving,'adaptive_mode':mode,'zero_acceleration':True,'max_position_difference_model_units':difference,
                'velocity_exact':True,'nonconverged_iteration_steps':sim.integrator.iterations_max_exceeded,
                'warnings':[str(w.message) for w in caught]}
        if mode=='INDIVIDUAL':
            assert not caught and sim.integrator.iterations_max_exceeded==0
            with tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/'test.bin';sim.save_to_file(str(path));restored=rebound.Simulation(str(path))
                assert restored.integrator.adaptive_mode==sim.integrator.adaptive_mode and restored==sim
                restored.integrate(2.)
                assert restored.integrator.iterations_max_exceeded==0
        else:
            assert sim.integrator.iterations_max_exceeded>0 and caught
        cases.append(record)
        models.append(sim)
    a,b=models[0].particles[0],models[1].particles[0]
    assert [a.x,a.y,a.z,a.vx,a.vy,a.vz]==[b.x,b.y,b.z,b.vx,b.vy,b.vz]
report={'rebound':rebound.__version__,'cases':cases,'criteria_phase_and_velocity_equal':True,
        'proposal':'INDIVIDUAL for one active point mass with basic gravity and no extra forces; PRS23 unchanged for multiple masses',
        'source':'https://github.com/hannorein/rebound/blob/5.2.2/src/integrator_ias15.c',
        'source_sha256':hashlib.sha256((ROOT/'output/rebound-5.2.2-integrator_ias15.c').read_bytes()).hexdigest(),
        'status':'isolated_proposal_verified_not_installed'}
(ROOT/'evidence/single-body-ias15-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
