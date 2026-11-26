"""Independent circular Kepler oracle for all10k positions after a native profile."""
from pathlib import Path
import hashlib
import json
import math
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'output/c211-cloud-product/app'))
import cloud_transport as wire
from physics import PHYSICAL_SCALE as U

label=sys.argv[1]
if not all(c.isalnum() or c in '_-' for c in label):raise ValueError('Invalid label')
benchmark=ROOT/f'evidence/native-benchmark-{label}.json'
r=json.loads(benchmark.read_text());assert r['completed'] and len(r['runs'])==3
p=r['fixture_initial_state'];c=p['test_particle_cloud'];body=p['bodies'][0]
binding=(p['system_id'],p['edit_token'],c['cloud_id'],c['source_id'],p['contract']['frame'],10000)
last=r['runs'][-1]['memory'][-1]['cloud_view']['native']['metadata']
matched=[]
for path in (ROOT/'output').glob('cloud-native-*.bin'):
    try:
        packet=path.read_bytes();m,xyz=wire.decode(packet,*binding,last['sequence'])
    except (ValueError,OSError):continue
    matched.append((m['sequence'],path,packet,m,xyz))
assert matched,'No retained packet matching the profiled population'
_,path,packet,m,xyz=max(matched,key=lambda x:x[0])
elapsed=m['time_model']-c['epoch'];assert elapsed>0
center=np.array(body['position'])+np.array(body['velocity'])*elapsed
radius=np.array([1.+3.*i/9999 for i in range(10000)])
angle=np.array([(i*math.pi*(3.-math.sqrt(5.)))%(2*math.pi) for i in range(10000)])
angle+=np.sqrt(body['mass']/radius**3)*elapsed
expected=np.column_stack((radius*np.cos(angle),radius*np.sin(angle),np.zeros(10000)))+center
relative=np.linalg.norm(xyz/U['length_unit_m']-expected,axis=1)/radius
worst=float(np.max(relative));assert worst<1e-8,worst
frozen=ROOT/f'evidence/native-benchmark-{label}-final-packet.bin'
if frozen.exists():assert frozen.read_bytes()==packet
else:frozen.write_bytes(packet)
report={'status':'all_10000_profile_packet_positions_match_independent_Kepler_oracle',
    'benchmark':str(benchmark.relative_to(ROOT)),'benchmark_sha256':hashlib.sha256(benchmark.read_bytes()).hexdigest(),
    'count':10000,'maximum_relative_position_error':worst,'elapsed_model_time':elapsed,
    'inner_orbital_periods':elapsed*math.sqrt(body['mass'])/(2*math.pi),
    'metadata':m,'packet':str(frozen.relative_to(ROOT)),'packet_sha256':hashlib.sha256(packet).hexdigest(),
    'scope':'The final retained SI float64 packet from this profiled population, independently checked against circular Kepler trajectories. Formal frame acceptance is separate; this is not an additional integration or a GPU float32 accuracy claim.'}
(ROOT/f'evidence/cloud-profile-phase-{label}-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='metadata'},indent=2),flush=True)
