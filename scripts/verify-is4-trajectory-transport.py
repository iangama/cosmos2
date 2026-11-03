"""Own trajectory protocol using a real worker; corruptions never reach publication."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import math
import struct
import sys
import traceback
import zipfile
import zlib
from importlib.machinery import SourceFileLoader
import numpy as np

ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/is4-body-particle-staging';APP=ROOT/'output/is3-body-points-product/app'
sys.path[:0]=[str(STAGE),str(APP)]
import is4_trajectory_transport as wire
helpers=SourceFileLoader('is4_wire_worker_helpers',str(ROOT/'scripts/verify-is4-worker.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/('output/is4-trajectory-transport-'+args.label);receipt=ROOT/('evidence/is4-trajectory-transport-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve protocol evidence')
    folder.mkdir();fixture=ROOT/'output/is4-body-snapshot-20261025b/JRM33-13.json'
    data=json.loads(fixture.read_text(encoding='utf-8'));constants=json.loads((STAGE/'constants.json').read_text(encoding='utf-8'))
    field=np.array(data['reading']['field_SystemIII_T']);side=np.cross(field,np.eye(3)[int(np.argmin(abs(field)))]);side/=np.linalg.norm(side)
    q=-constants['elementary_charge_C']['value'];mass=constants['electron_mass_kg']['value'];speed=1e6
    omega=abs(q/mass)*np.linalg.norm(field);unit=float(speed/omega)
    params={'charge_C':q,'mass_kg':mass,'dt_s':float(2*math.pi/omega/800),'initial_position_m':data['reading']['point_SystemIII_m'],'initial_velocity_m_s':(side*speed).tolist()}
    paths=[*STAGE.glob('*.py'),Path(__file__),fixture,STAGE/'constants.json',ROOT/'IS-4-TRANSPORTE-NATIVO-CONTRATO.md']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths};owner=sha(ROOT/'user/sessions/latest.json')
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in paths:z.write(p,p.relative_to(ROOT).as_posix())
    report={'schema':1,'accepted':False,'completed':False,'source_sha256':hashes,'checks':[]};client=None
    try:
        client=helpers.Client(folder/'storage',folder,'worker')
        client.call('create',{'source_phase':data['phase'],'source_reading':data['reading'],'parameters':params,'controls':{'electric':True,'magnetic':True,'gravity':True}})
        packet,record=wire.encode(client.last,unit,field.tolist());binding=record['metadata']['binding_sha256'];m,rows=wire.decode(packet,binding)
        assert len(rows)==1 and rows[0,0]==0. and np.array_equal(rows[0,1:],[0.,0.,0.])
        client.advance(512);state=copy.deepcopy(client.last);before=json.dumps(state,sort_keys=True)
        packet,record=wire.encode(state,unit,field.tolist());m,rows=wire.decode(packet,binding)
        assert len(rows)==129 and m==record['metadata'] and before==json.dumps(state,sort_keys=True)
        assert np.array_equal(rows[:,0],record['geometry']['sample_times_s'])
        assert np.array_equal(rows[-1,1:],np.array(state['experiment']['phase']['position_offset_m'])/unit)
        path=folder/'native.bin';wire.publish(path,packet,binding);initial=path.read_bytes()
        report['checks'].append({'single_and_129_real_samples':True,'binding_sha256':binding,'count':len(rows),'exact_endpoint_time_and_normalized_offset':True})
        header_size=wire.HEADER.unpack_from(packet)[1];payload=packet[wire.HEADER.size+header_size:]
        def packed(meta,payload=payload):
            header=json.dumps(meta,separators=(',',':'),allow_nan=True).encode('ascii');return wire.HEADER.pack(wire.MAGIC,len(header))+header+payload
        bad_packets=[b'X'+packet[1:],packet[:-1],packet+b'x',packet[:-1]+bytes([packet[-1]^1]),b'x'*(wire.MAX_PACKET+1)]
        for edit in [{'schema':True},{'model':'massless_central_ias15_v1'},{'binding_sha256':'0'*64},{'sequence':True},{'sequence':2**63},
            {'revision':True},{'count':130},{'count':True},{'positions':'SI_m_float64_little_endian_xyz'},{'time_s':float('nan')},{'time_s':-1.},{'payload_crc32':True}]:
            bad_packets.append(packed({**m,**edit}))
        for index,value in [(0,float('nan')),(0,rows[-1,0]+1.),(1,1e9),(4,rows[0,0])]:
            altered=bytearray(payload);struct.pack_into('<d',altered,index*8,value)
            bad_packets.append(packed({**m,'payload_sha256':hashlib.sha256(altered).hexdigest(),'payload_crc32':zlib.crc32(altered)},altered))
        duplicated=json.dumps(m,separators=(',',':')).replace('"schema":1','"schema":1,"schema":1').encode()
        bad_packets.append(wire.HEADER.pack(wire.MAGIC,len(duplicated))+duplicated+payload)
        refusals=0
        for bad in bad_packets:
            try:wire.publish(path,bad,binding)
            except ValueError:refusals+=1
            else:raise AssertionError('Malformed trajectory accepted')
            assert path.read_bytes()==initial
        for bounds in [{'minimum_sequence':m['sequence']+1},{'minimum_time_s':m['time_s']+1.},{'minimum_revision':m['revision']+1}]:
            try:wire.publish(path,packet,binding,**bounds)
            except ValueError:refusals+=1
            else:raise AssertionError('Stale trajectory accepted')
            assert path.read_bytes()==initial
        client.call('set_rate',{'value':params['dt_s']*200});client.call('resume')
        live=copy.deepcopy(client.last);wire.encode(live,unit,field.tolist());client.call('pause')
        report['checks'].append({'transactional_refusals':refusals,'live_packets_supported':True,'no_SI_relabel':True,'published_bytes_unchanged_on_refusal':True})
        assert all(sha(ROOT/n)==v for n,v in hashes.items()) and sha(ROOT/'user/sessions/latest.json')==owner
        client.close();client=None;report.update(accepted=True,completed=True,refusals=refusals)
    except Exception:report['failure']=traceback.format_exc()
    finally:
        if client is not None:client.close()
        receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'accepted':report['accepted'],'failure':report.get('failure'),'refusals':report.get('refusals')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
