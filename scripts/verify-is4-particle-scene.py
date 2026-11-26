"""Real worker packets mapped to magnified native geometry, before opening the engine."""
from pathlib import Path
import copy
import hashlib
import json
import math
import sys
import traceback
import zipfile
from importlib.machinery import SourceFileLoader
import numpy as np

ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/is4-body-particle-staging';APP=ROOT/'output/is3-body-points-product/app'
sys.path[:0]=[str(STAGE),str(APP)]
from is4_particle_scene import geometry,prepare
helpers=SourceFileLoader('is4_geometry_worker_helpers',str(ROOT/'scripts/verify-is4-worker.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    folder=ROOT/'output/is4-particle-scene-20261025a';receipt=ROOT/'evidence/is4-particle-scene-20261025a.json'
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve geometry evidence.')
    folder.mkdir();constants=json.loads((STAGE/'constants.json').read_text(encoding='utf-8'))
    paths=[*STAGE.glob('*.py'),STAGE/'constants.json',Path(__file__),ROOT/'scripts/verify-is4-worker.py',ROOT/'IS-4-VISTA-AMPLIADA-CONTRATO.md']
    fixtures=[ROOT/('output/is4-body-snapshot-20261025b/'+model+'-'+str(degree)+'.json') for model,degree in [('IGRF14',13),('JRM33',13),('JRM33',18)]]
    paths+=fixtures;hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in paths:z.write(p,p.relative_to(ROOT).as_posix())
    report={'schema':1,'accepted':False,'completed':False,'source_sha256':hashes,'cases':[]};clients=[]
    try:
        for index,(model,degree,kind) in enumerate([('IGRF14',13,'proton'),('JRM33',13,'electron'),('IGRF14',13,'neutral'),('JRM33',18,'proton')]):
            fixture=json.loads((ROOT/('output/is4-body-snapshot-20261025b/'+model+'-'+str(degree)+'.json')).read_text(encoding='utf-8'))
            p,r=fixture['phase'],fixture['reading'];point=r['point_ITRF93_m' if model=='IGRF14' else 'point_SystemIII_m'];field=np.array(r['field_ITRF93_T' if model=='IGRF14' else 'field_SystemIII_T'])
            direction=field/np.linalg.norm(field);axis=np.eye(3)[int(np.argmin(abs(direction)))];v=np.cross(direction,axis);v/=np.linalg.norm(v)
            mass=constants['electron_mass_kg' if kind=='electron' else 'proton_mass_kg']['value'];q=0. if kind=='neutral' else constants['elementary_charge_C']['value']*(-1 if kind=='electron' else 1)
            speed=1e6 if kind=='electron' else 1e3 if kind=='neutral' else 1e5
            dt=.001 if kind=='neutral' else 2*math.pi/(abs(q/mass)*np.linalg.norm(field))/800
            params={'charge_C':float(q),'mass_kg':mass,'dt_s':float(dt),'initial_position_m':point,'initial_velocity_m_s':(v*speed).tolist()}
            client=helpers.Client(folder/('storage-'+str(index)),folder,'worker-'+str(index));clients.append(client)
            client.call('create',{'source_phase':p,'source_reading':r,'parameters':params,'controls':{'electric':True,'magnetic':True,'gravity':True}})
            unit=speed/(abs(q/mass)*np.linalg.norm(field)) if q else max(1.,speed*dt*64)
            client.advance(500);state=copy.deepcopy(client.last);before=json.loads(json.dumps(state))
            code,result=prepare(state,float(unit),field.tolist());g=result['geometry'];render=result['render']
            assert json.loads(json.dumps(state))==before
            points=np.array(g['vertices_normalized']);actual_offsets=np.array([row['position_offset_m'] for row in state['experiment']['recent_trajectory']])
            assert np.allclose(points*unit,actual_offsets,atol=1e-15*max(1.,float(unit)),rtol=1e-15)
            assert g['float32_error_m']+g['global_frame_conservative_error_m']<=g['adopted_total_error_bound_m']
            assert np.array_equal(points[-1],np.array(g['marker_normalized'])) and len(points)<=129
            assert sha(Path(render['file']))==render['file_sha256'] and sha(Path(render['receipt']))==render['receipt_sha256']
            x,y,z=g['rotation_euler_rad'];cx,sx=math.cos(x),math.sin(x);cy,sy=math.cos(y),math.sin(y);cz,sz=math.cos(z),math.sin(z)
            rx=np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]]);ry=np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]]);rz=np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]])
            assert np.max(abs(rz@ry@rx-g['model_to_render']))<=2e-12
            assert code.count('RenderableConstellationLines')==1 and 'Parent="LabRoot"' in code
            report['cases'].append({'model':model,'degree':degree,'kind':kind,'physical_unit_m':float(unit),'vertices':len(points),
                'float32_error_m':g['float32_error_m'],'frame_roundoff_budget_m':g['global_frame_conservative_error_m'],'adopted_bound_m':g['adopted_total_error_bound_m'],
                'receipt':render['receipt'],'receipt_sha256':render['receipt_sha256']})
            client.close();clients.remove(client)
        refusals=0
        for edit in ['running','bad_frame','bad_worker','sequence_bool','origin','endpoint','time_order','rotation']:
            bad=copy.deepcopy(state)
            if edit=='running':bad['paused']=False
            if edit=='bad_frame':bad['frame']='other'
            if edit=='bad_worker':bad['worker_id']='bad'
            if edit=='sequence_bool':bad['sequence']=True
            if edit=='origin':bad['experiment']['phase']['position_origin_m'][0]+=1.
            if edit=='endpoint':bad['experiment']['recent_trajectory'][-1]['velocity_m_s'][0]+=1.
            if edit=='time_order':bad['experiment']['recent_trajectory'][0]['time_s']=bad['experiment']['recent_trajectory'][1]['time_s']
            if edit=='rotation':bad['experiment']['model_to_J2000'][0][0]+=1.
            try:geometry(bad,float(unit),field.tolist())
            except ValueError:refusals+=1
            else:raise AssertionError(edit)
        for bad in [True,0.,float('nan')]:
            try:geometry(state,bad,field.tolist())
            except ValueError:refusals+=1
            else:raise AssertionError('Invalid scale accepted.')
        assert all(sha(ROOT/name)==value for name,value in hashes.items())
        report.update(accepted=True,completed=True,transactional_refusals=refusals,
            scope='Real worker frozen snapshots mapped to magnified 3D normalized positions/times, marker endpoint, frame orientation and float32/roundoff budgets. Native readback/render/images and live GPU confirmation separate.')
    except Exception:report['failure']=traceback.format_exc()
    finally:
        for client in clients:
            try:client.close()
            except Exception:
                if client.process.poll() is None:client.process.terminate();client.process.wait(timeout=5)
    receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({'accepted':report['accepted'],'cases':len(report['cases']),'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
