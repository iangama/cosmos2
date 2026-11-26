"""Installed Session against an independent two-body J2 DOP853 oracle."""
from pathlib import Path
import json
import math
import sys
import tempfile
import warnings

import numpy as np
import rebound
from scipy.integrate import solve_ivp

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from session import Session
from physics import PHYSICAL_SCALE as U


def guard(s):return {k:getattr(s,k) for k in ('system_id','edit_token','revision')}|{'expected_time':s.sim.t,'frame':s.contract()['frame']}
def relative(sim):
    a,b=sim.particles
    return np.array([b.x-a.x,b.y-a.y,b.z-a.z,b.vx-a.vx,b.vy-a.vy,b.vz-a.vz])


mu=1.0001;j2=.002;radius=.12;a=.4;period=2*math.pi*math.sqrt(a**3/mu)
def rhs(t,phase):
    x,y,z,vx,vy,vz=phase;r2=x*x+y*y+z*z;r=math.sqrt(r2);c=1.5*mu*j2*radius**2/r**5
    return [vx,vy,vz,-mu*x/r**3+c*x*(5*z*z/r2-1),-mu*y/r**3+c*y*(5*z*z/r2-1),-mu*z/r**3+c*z*(5*z*z/r2-3)]

with warnings.catch_warnings(record=True) as caught,tempfile.TemporaryDirectory() as temp:
    warnings.simplefilter('always')
    reference=rebound.Simulation();reference.G=1.;reference.add(m=1.);reference.add(m=.0001,a=a,e=.13,inc=.7,Omega=.2,omega=.5,f=.3);reference.move_to_com()
    s=Session(temp,2);s._new_population([{'name':'Modelo '+str(i),**s._phase(p)} for i,p in enumerate(reference.particles)])
    source=s.registry[0]['id'];s.set_j2({**guard(s),'body':source,'parameters':{'j2':j2,'radius_eq_m':radius*U['length_unit_m'],'axis':[0.,0.,1.],'provenance':'Ensaio sintético independente; não planeta observado'}})
    start=relative(s.sim);target=4*period
    oracle=solve_ivp(rhs,(0.,target),start,method='DOP853',rtol=2.3e-14,atol=1e-15,max_step=period/160)
    assert oracle.success
    energy=s.initial_energy
    for t in np.linspace(0.,target,49)[1:]:s.integrate(float(t))
    difference=relative(s.sim)-oracle.y[:,-1]
    phase_error=float(np.linalg.norm(np.r_[difference[:3]/a,difference[3:]/math.sqrt(mu/a)]))
    assert phase_error<2e-9 and abs((s._energy()-energy)/energy)<1e-10
    # Valid definitions can intentionally land in the unsupported interior.
    # The reading must be unavailable and preserve its actual reason.
    s.configure_instruments({**guard(s),'instruments_revision':s.instruments['revision'],'operation':'create',
        'definition':{'name':'Interior inválido','mode':'follow','body_id':source,'offset_m':[radius*U['length_unit_m']*.5,0.,0.],'exclude_followed_source':False}})
    measured=s.sample_instruments({**guard(s),'instruments_revision':s.instruments['revision']})
    row=measured['readings'][0];assert not row['available'] and 'exterior' in row['reason'] and 'acceleration_m_s2' not in row
    s.configure_history({**guard(s),'instruments_revision':s.instruments['revision'],'history_revision':s.instrument_history['revision'],'recording':True,'cadence_wall_s':.25})
    s.collect_history(s.state(),10.);s.save();restored=Session(temp,2);restored.load()
    assert restored.instrument_history==s.instrument_history and restored.sim==s.sim
    # Distinct prescribed axes have no single conserved orbital-L component.
    s.set_j2({**guard(s),'body':s.registry[1]['id'],'parameters':{'j2':.001,'radius_eq_m':1e6,'axis':[1.,0.,0.],'provenance':'Segunda fonte sintética, eixo não paralelo'}})
    assert s.state()['conservation']['J2_axial_angular'] is None
    s.integrate(s.sim.t+.01);s.save()
    assert not caught,[str(w.message) for w in caught]
report={'status':'installed3_9_J2_Session_independent_orbit_verified','dop853_relative_phase_error':phase_error,
        'relative_mechanical_energy_error_4_periods':abs((restored._energy()-energy)/energy),
        'interior_probe_is_explicit_gap_without_zero_field':True,'interior_history_checkpoint_exact':True,
        'nonparallel_J2_axes_do_not_claim_conserved_axial_component':True,'unhandled_warnings':len(caught)}
(ROOT/'evidence/j2-installed-orbits-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
