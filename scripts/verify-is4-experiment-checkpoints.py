"""Exact two-part particle phase continuation, transactional refusals and real Windows locks."""
from pathlib import Path
from dataclasses import asdict
import argparse
import copy
import ctypes
import hashlib
import json
import math
import os
import struct
import subprocess
import sys
import threading
import traceback
import zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1];APP=ROOT/'output/is3-body-points-product/app';STAGE=ROOT/'output/is4-body-particle-staging'
sys.path[:0]=[str(STAGE),str(APP)]
from is4_experiment import Experiment
from is4_body_snapshot import digest
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def advance(experiment,count):
    while count:
        n=min(256,count);result=experiment.advance_steps(n);assert result['accepted_steps']==n,result;count-=n


def phase_bytes(payload):
    p=payload['phase']
    return struct.pack('<13d',p['time_s'],*p['position_m'],*p['velocity_m_s'],*p['position_origin_m'],*p['position_offset_m'])


def physics(payload):
    result=copy.deepcopy(payload);result.pop('edit_token');return json.loads(json.dumps(result))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--resume');parser.add_argument('--steps',type=int);parser.add_argument('--result');parser.add_argument('--label');args=parser.parse_args()
    if args.resume:
        experiment=Experiment.load(args.resume);advance(experiment,args.steps);experiment.save()
        Path(args.result).write_text(json.dumps({'pid':os.getpid(),'payload':experiment.payload()})+'\n',encoding='utf-8');return 0
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Explicit safe label required.')
    folder=ROOT/('output/is4-experiment-checkpoints-'+args.label);receipt=ROOT/('evidence/is4-experiment-checkpoints-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve checkpoint evidence.')
    folder.mkdir();fixture_path=ROOT/'output/is4-body-snapshot-20261025b/JRM33-13.json'
    fixture=json.loads(fixture_path.read_text(encoding='utf-8'));constants=json.loads((STAGE/'constants.json').read_text(encoding='utf-8'))
    owner=sha(ROOT/'user/sessions/latest.json');paths=[*STAGE.glob('*.py'),STAGE/'constants.json',Path(__file__),fixture_path,ROOT/'IS-4-EXPERIMENTO-CHECKPOINT-CONTRATO.md']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    with zipfile.ZipFile(folder/'executed-sources-and-fixtures.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in paths:z.write(p,p.relative_to(ROOT).as_posix())
    report={'schema':1,'accepted':False,'completed':False,'source_sha256':hashes,'checks':[]}
    try:
        p,r=fixture['phase'],fixture['reading'];seed=r['point_SystemIII_m'];b=np.array(r['field_SystemIII_T']);direction=b/np.linalg.norm(b)
        axis=np.eye(3)[int(np.argmin(abs(direction)))];v=np.cross(direction,axis);v=v/np.linalg.norm(v)*1e6
        parameters={'charge_C':-constants['elementary_charge_C']['value'],'mass_kg':constants['electron_mass_kg']['value'],
            'dt_s':float(2*math.pi/(constants['elementary_charge_C']['value']/constants['electron_mass_kg']['value']*np.linalg.norm(b))/800),
            'initial_position_m':seed,'initial_velocity_m_s':v.tolist()}
        flags={'electric':True,'magnetic':True,'gravity':True}
        first=Experiment(folder/'saved',p,r,parameters,flags);baseline=Experiment(folder/'baseline',p,r,parameters,flags)
        p0,r0=copy.deepcopy(p),copy.deepcopy(r);advance(first,123);saved=first.save();old_token=first.edit_token
        restored=Experiment.load(first.storage);assert restored.id==first.id and restored.edit_token!=old_token
        assert phase_bytes(restored.payload())==phase_bytes(first.payload())
        advance(first,777);advance(restored,777);advance(baseline,900)
        assert physics(first.payload())==physics(restored.payload())
        assert phase_bytes(first.payload())==phase_bytes(baseline.payload())
        output=folder/'new-process-result.json'
        subprocess.run([sys.executable,'-Xutf8',str(Path(__file__)),'--resume',str(first.storage),'--steps','777','--result',str(output)],check=True,capture_output=True,timeout=60)
        child=json.loads(output.read_text(encoding='utf-8'));assert child['pid']!=os.getpid()
        assert physics(child['payload'])==physics(first.payload()) and phase_bytes(child['payload'])==phase_bytes(first.payload())
        report['checks'].append({'exact_JSON_and_new_process_continuation':True,'split_steps':[123,777],'position_components_and_work_included':True,'child_pid':child['pid']})
        before_phase=phase_bytes(first.payload());field=first.sample()['field'];new_flags={**flags,'gravity':False}
        assert first.set_controls(new_flags) and not first.set_controls(new_flags)
        assert first.revision==1 and phase_bytes(first.payload())==before_phase and first.sample()['field']==field
        assert first.reference==first.phase and all(value==(0.,0.) for value in first.work.values())
        advance(first,25);first.save();control_restore=Experiment.load(first.storage)
        assert physics(control_restore.payload())==physics(first.payload())
        assert p==p0 and r==r0
        report['checks'].append({'physical_controls_preserve_fields_and_phase':True,'reference_reset_and_restore':True})
        stable=physics(first.payload());refusals=0
        for invalid in [True,0,257,-1]:
            try:first.advance_steps(invalid)
            except ValueError:refusals+=1
            else:raise AssertionError('Invalid quantum accepted.')
            assert physics(first.payload())==stable
        for invalid in [{'electric':True,'magnetic':True,'gravity':1},{'gravity':False}]:
            try:first.set_controls(invalid)
            except ValueError:refusals+=1
            else:raise AssertionError('Invalid control accepted.')
            assert physics(first.payload())==stable
        manifest=json.loads((first.storage/'latest.json').read_text(encoding='utf-8'))
        edits=['seal','origin_missing','offset_mismatch','velocity_limit','clock','step_bool','generation','field_epoch','snapshot_hash','work_nan','work_inconsistent','electric_work','trail_endpoint','control_bool','event_count','reference_future']
        for index,edit in enumerate(edits):
            bad=copy.deepcopy(manifest)
            if edit=='seal':bad['manifest_sha256']='bad'
            if edit=='origin_missing':bad['phase']['position_origin_m']=None
            if edit=='offset_mismatch':bad['phase']['position_offset_m'][0]+=1.
            if edit=='velocity_limit':bad['phase']['velocity_m_s'][0]=1e8
            if edit=='clock':bad['phase']['time_s']+=parameters['dt_s']
            if edit=='step_bool':bad['step_index']=True
            if edit=='generation':bad['scientific_generation']['version']='unknown'
            if edit=='field_epoch':bad['source_reading']['epoch']['et_tdb_s']+=1.
            if edit=='snapshot_hash':bad['configuration_sha256']='bad'
            if edit=='work_nan':bad['work']['gravity'][0]=float('nan')
            if edit=='work_inconsistent':bad['work']['gravity'][0]=1.
            if edit=='electric_work':bad['work']['electric'][0]=1.
            if edit=='trail_endpoint':bad['trail'][-1]['velocity_m_s'][0]+=1.
            if edit=='control_bool':bad['controls']['magnetic']=1
            if edit=='event_count':bad['revision']+=1
            if edit=='reference_future':bad['reference']['time_s']=bad['phase']['time_s']+1.
            if edit!='seal' and edit!='work_nan':bad['manifest_sha256']=digest({k:v for k,v in bad.items() if k!='manifest_sha256'})
            storage=folder/('corrupt-'+str(index));storage.mkdir();(storage/'latest.json').write_text(json.dumps(bad)+'\n',encoding='utf-8')
            try:Experiment.load(storage)
            except ValueError:refusals+=1
            else:raise AssertionError('Invalid checkpoint accepted: '+edit)
            assert physics(first.payload())==stable
        report['transactional_refusals']=refusals
        # Actual OS file handles: share read/write but deny delete/rename.
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p];kernel.CreateFileW.restype=ctypes.c_void_p
        kernel.CloseHandle.argtypes=[ctypes.c_void_p]
        checkpoint=first.storage/'latest.json'
        def lock():
            handle=kernel.CreateFileW(str(checkpoint),0x80000000,3,None,3,128,None)
            if handle==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
            return handle
        handle=lock();timer=threading.Timer(.1,lambda:kernel.CloseHandle(handle));timer.start();first.save();timer.join()
        handle=lock();previous=sha(checkpoint)
        try:
            try:first.save()
            except PermissionError:pass
            else:raise AssertionError('Permanent Windows lock unexpectedly replaced checkpoint.')
            assert sha(checkpoint)==previous and not list(first.storage.glob('*.tmp'))
        finally:kernel.CloseHandle(handle)
        report['checks'].append({'real_Windows_short_lock_recovered':True,'persistent_lock_previous_manifest_and_phase_retained':True})
        # A valid initial point moving outside the adopted outer domain must
        # stop before publishing an invalid phase, then save/load that stop.
        edge=copy.deepcopy(parameters);edge.update(charge_C=0.,dt_s=1.,initial_position_m=[19.999*71492000.,0.,0.],initial_velocity_m_s=[1e6,0.,0.])
        boundary=Experiment(folder/'boundary',p,r,edge,flags);initial_boundary=phase_bytes(boundary.payload())
        result=boundary.advance_steps(1);assert result['accepted_steps']==0 and result['termination'] and phase_bytes(boundary.payload())==initial_boundary
        boundary.save();stopped=Experiment.load(boundary.storage);assert stopped.termination==boundary.termination and phase_bytes(stopped.payload())==initial_boundary
        report['checks'].append({'boundary_last_phase_retained_and_stopped_checkpoint_restored':True})
        assert all(sha(ROOT/name)==value for name,value in hashes.items()) and sha(ROOT/'user/sessions/latest.json')==owner
        report.update(accepted=True,completed=True,owner_pointer_unchanged=True,
            scope='Bounded one-particle static experiment, exact synchronized origin/offset phase and compensated-work JSON/new-process continuation, physical controls, transactional invalid requests/checkpoints, real Windows lock behavior and last-valid boundary stop. Worker/native/performance still pending.')
    except Exception:report['failure']=traceback.format_exc()
    receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({'accepted':report['accepted'],'checks':len(report['checks']),'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
