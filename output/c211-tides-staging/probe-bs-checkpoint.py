from pathlib import Path
import json,math,warnings
import rebound
ROOT=Path(__file__).resolve().parent

def attach(sim,y):
    ode=sim.create_ode(length=2,needs_nbody=False)
    def derivatives(ode,dy,y,t):dy[0]=y[1];dy[1]=-y[0]
    ode.derivatives=derivatives
    for i,v in enumerate(y):ode.y[i]=v
    return ode

sim=rebound.Simulation();sim.integrator='bs';sim.integrator.eps_abs=1e-13;sim.integrator.eps_rel=1e-13;sim.dt=.01
ode=attach(sim,[1.,0.]);sim.integrate(4.25)
state=[ode.y[i] for i in range(2)]
path=ROOT/'bs-probe.bin';sim.save_to_file(str(path),delete_file=True)
with warnings.catch_warnings(record=True) as captured:
    restored=rebound.Simulation(str(path))
print(json.dumps({'warnings':[str(w.message) for w in captured],'odes_original':sim._N_odes,'odes_loaded':restored._N_odes,'original_integrator':repr(sim.integrator),'loaded_integrator':repr(restored.integrator),'dt':[sim.dt,restored.dt]}),flush=True)
copyode=attach(restored,state)
for target in [6.,8.75,12.5,40.]:
    sim.integrate(target);restored.integrate(target)
    original=[ode.y[i] for i in range(2)];loaded=[copyode.y[i] for i in range(2)]
    print(json.dumps({'t':target,'exact':original==loaded,'difference':[a-b for a,b in zip(original,loaded)],'original':original,'loaded':loaded,'dt':[sim.dt,restored.dt]}),flush=True)
