"""Scientific and process-protocol checks, run with native Windows Python."""
from pathlib import Path
import json
import math
import queue
import subprocess
import sys
import threading
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from physics import fixture
import rebound

sim = fixture(2)
start = [(p.x, p.y, p.vx, p.vy) for p in sim.particles]
energy = sim.energy()
sim.integrate(2*math.pi/math.sqrt(1+1e-8))
orbit_error = max(abs(a-b) for p, old in zip(sim.particles, start)
                  for a,b in zip((p.x,p.y,p.vx,p.vy), old))
assert orbit_error < 1e-9, orbit_error
results = {"platform": sys.platform, "rebound": rebound.__version__, "two_body_period_error": orbit_error, "fixtures": []}
for count in (32,128):
    sim = fixture(count)
    energy = sim.energy()
    began = time.perf_counter()
    sim.integrate(1.0)
    elapsed = time.perf_counter()-began
    drift = abs((sim.energy()-energy)/energy)
    assert drift < 1e-9, drift
    results["fixtures"].append({"bodies":count,"physical_time":sim.t,"wall_seconds":elapsed,"energy_relative_error":drift})

process = subprocess.Popen([sys.executable, '-u', str(ROOT/'app'/'worker.py')], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
messages = queue.Queue()
def read():
    for line in process.stdout:
        messages.put(json.loads(line))
threading.Thread(target=read,daemon=True).start()
def command(name, identifier):
    began = time.perf_counter()
    process.stdin.write(json.dumps({"command":name,"id":identifier})+'\n');process.stdin.flush()
    while True:
        response=messages.get(timeout=10)
        if response.get('type')=='ack' and response.get('id')==identifier:
            return (time.perf_counter()-began)*1000,response
try:
    assert messages.get(timeout=10)['type']=='ready'
    command('resume',1)
    time.sleep(1)
    latency,ack=command('pause',2)
    assert latency <= 250,latency
    paused_time=ack['time']
    time.sleep(.1)
    _,ack=command('snapshot',3)
    assert ack['time']==paused_time
    results['worker']={"pause_ack_ms":latency,"paused_time":paused_time,"pause_stable":True}
    command('quit',4)
    process.wait(timeout=5)
    assert process.returncode==0,process.stderr.read()
finally:
    if process.poll() is None:
        process.kill();process.wait()
(ROOT/'evidence'/'physics-check.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
