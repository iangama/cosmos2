"""Confirmed10k binary position packet and atomic publication, outside product."""
from pathlib import Path
import copy,hashlib,json,struct,sys,tempfile,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'output/c211-test-particles-staging'))
from test_particle_cloud import make
from cloud_snapshot import encode,decode,publish,HEADER,MAGIC
import numpy as np
sim=make();sim.integrate(.05);system='1'*32;token='2'*32;original=sim.__reduce__()[1][0]
began=time.perf_counter();packet=encode(sim,system,token,4,1e9,2745.0101772765446);cost=(time.perf_counter()-began)*1000
m,xyz=decode(packet,system,token,4);assert xyz.shape==(10000,3) and not xyz.flags.writeable
expected=np.empty((10001,3));sim.serialize_particle_data(xyz=expected);assert np.array_equal(xyz,expected[1:]*1e9) and sim.__reduce__()[1][0]==original
rejected=0
for change in ({'system_id':'3'*32},{'edit_token':'3'*32},{'sequence':True},{'sequence':3},{'count':10001},{'count':9999},{'frame':'other'},{'active_source_count':2},{'length_unit_m':0},{'time_unit_s':0},{'time_s':0},{'positions':'float32'}):
 bad=copy.deepcopy(m);bad.update(change);h=json.dumps(bad,separators=(',',':')).encode();candidate=HEADER.pack(MAGIC,len(h))+h+xyz.astype('<f8').tobytes()
 try:decode(candidate,system,token,4)
 except ValueError:rejected+=1
 else:raise AssertionError(change)
for candidate in (packet[:-1],packet+b'x',packet[:4],b'x'+packet[1:],packet[:-1]+bytes([packet[-1]^1])):
 try:decode(candidate,system,token,4)
 except ValueError:rejected+=1
 else:raise AssertionError('Corruption accepted')
with tempfile.TemporaryDirectory(prefix='cosmos2-cloud-packet-') as temp:
 path=Path(temp)/'confirmed.cloud';publish(path,packet);assert path.read_bytes()==packet
 sim.integrate(.1);later=encode(sim,system,token,5,1e9,2745.0101772765446);publish(path,later);meta,positions=decode(path.read_bytes(),system,token,5);assert meta['time_model']==.1 and not list(Path(temp).glob('*.tmp'))
# Static point-cloud source for a separate native aggregation experiment.
static=ROOT/'output/c211-test-particles-staging/confirmed-static.speck'
static.write_text('# Synthetic massless positions SI_m; frozen t_model=0.05; not live physics\ndatavar 0 cloud_index\n'+''.join(' '.join(format(float(v),'.17g') for v in row)+' '+str(i)+'\n' for i,row in enumerate(xyz)))
report={'status':'isolated_cloud_packet_verified_not_installed','count':10000,'positions_SI_float64_exact':True,'bytes':len(packet),'same_solver_binary_preserved':True,'stale_identity_sequence_and_domain_or_payload_corruptions_rejected':rejected,'atomic_replace_and_new_sequence':True,'encode_ms_single_observation':cost,'static_native_input':str(static.relative_to(ROOT)),'scope':'Transport prototype only; no dynamic native renderer or full10k product/profile acceptance.'}
(ROOT/'evidence/cloud-snapshot-prototype-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
