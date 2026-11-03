"""Confirmed binary transport: all10k SI positions, strict binding, corruption and atomic replace."""
from pathlib import Path
import copy
import hashlib
import json
import math
import sys
import tempfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'output/c211-cloud-product/app'))
from session import Session
from physics import PHYSICAL_SCALE as U
import cloud_transport as wire

with tempfile.TemporaryDirectory(prefix='cosmos2-cloud-wire-') as folder:
    s=Session(folder,2)
    s.load_cloud_experiment({'system_id':s.system_id,'edit_token':s.edit_token,'revision':s.revision,
        'expected_time':s.sim.t,'frame':s.contract()['frame'],'parameters':{'count':10000}})
    s.integrate(.1);cloud=s._cloud
    before=cloud.driver.sim.__reduce__()[1][0]
    packet,meta=wire.encode(cloud,s.system_id,s.edit_token,7,s.contract()['frame'])
    binding=dict(system_id=s.system_id,edit_token=s.edit_token,cloud_id=cloud.id,source_id=s.registry[0]['id'],
        frame=s.contract()['frame'],count=10000,minimum_sequence=7)
    decoded,xyz=wire.decode(packet,**binding)
    assert decoded==meta and np.array_equal(xyz,cloud.driver.positions()*U['length_unit_m'])
    assert cloud.driver.sim.__reduce__()[1][0]==before
    _,n=wire.HEADER.unpack_from(packet);payload=packet[wire.HEADER.size+n:]
    def replace_header(m,payload=payload):
        h=json.dumps(m,separators=(',',':'),allow_nan=True).encode('ascii')
        return wire.HEADER.pack(wire.MAGIC,len(h))+h+payload
    refused=[]
    for key,bad in [('schema',True),('model','other'),('system_id','0'*32),('edit_token','0'*32),
        ('cloud_id','0'*32),('source_id','other'),('frame','other'),('count',True),('count',9999),
        ('sequence',True),('sequence',6),('sequence',2**63),('time_model',True),('time_model',-1.),
        ('time_model',float('nan')),('time_s',0.),('time_unit_s',1.),('length_unit_m',1.),
        ('positions','float32'),('payload_sha256','0'*64),('payload_crc32',True),('payload_crc32',0)]:
        m=copy.deepcopy(meta);m[key]=bad
        try:wire.decode(replace_header(m),**binding)
        except ValueError:refused.append(key+':'+str(bad))
        else:raise AssertionError('Invalid wire metadata accepted: '+key)
    for name,bad in [('truncated',packet[:-1]),('extra',packet+b'x'),('magic',b'BADMAGIC'+packet[8:]),
        ('payload-bitflip',packet[:-1]+bytes([packet[-1]^1])),('empty',b''),
        ('oversized',wire.MAGIC+b'\xff\xff\xff\x7f'+b'x'*100)]:
        try:wire.decode(bad,**binding)
        except ValueError:refused.append(name)
        else:raise AssertionError('Invalid wire bytes accepted: '+name)
    # Checksums cannot turn a nonfinite or physically unbounded coordinate into valid data.
    for bad in (float('nan'),1e18):
        points=xyz.copy();points[9999,2]=bad;raw=points.astype('<f8').tobytes();m=copy.deepcopy(meta)
        import zlib
        m['payload_sha256']=hashlib.sha256(raw).hexdigest();m['payload_crc32']=zlib.crc32(raw)
        try:wire.decode(replace_header(m,raw),**binding)
        except ValueError:refused.append('resealed position '+str(bad))
        else:raise AssertionError('Invalid SI position accepted')
    path=Path(folder)/'packet.bin';wire.publish(path,packet);assert path.read_bytes()==packet
    saved=path.read_bytes()
    try:wire.publish(path,b'')
    except ValueError:pass
    else:raise AssertionError('Empty publication accepted')
    assert path.read_bytes()==saved and not list(Path(folder).glob('*.tmp'))
    target=ROOT/'output/c211-cloud-native';target.mkdir(exist_ok=True)
    wire.publish(target/'packet.bin',packet)
    (target/'binding.json').write_text(json.dumps({'binding':binding,'metadata':meta},indent=2)+'\n')
    report={'status':'confirmed_v2_cloud_binary_transport_verified_not_installed','count':10000,
        'packet_bytes':len(packet),'all_float64_SI_positions_exact':True,'joint_IAS15_binary_unchanged':True,
        'invalid_packets_refused':refused,'atomic_publication_and_previous_preserved':True,
        'payload_crc32':meta['payload_crc32'],'scope':'Python producer/decoder; native live buffer and performance acceptance pending.'}
    (ROOT/'evidence/cloud-transport-prototype-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
