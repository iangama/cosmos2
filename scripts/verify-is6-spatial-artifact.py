"""Windows exact spatial checkpoint, mesh/view separation, lineage and atomicity."""
from pathlib import Path
import argparse
import copy
import ctypes
import hashlib
import json
import subprocess
import sys
import time
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/is6-spatial-artifact-staging'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/f'output/is6-spatial-artifact-{args.label}';path=ROOT/f'evidence/is6-spatial-artifact-{args.label}.json'
    if folder.exists() or path.exists():raise FileExistsError('Preserve artifact evidence')
    binding_path=ROOT/'evidence/is6-body-source-20261101a.json';binding=json.loads(binding_path.read_text());assert binding['accepted']
    fixture_path=ROOT/'output/is6-body-fixtures-20261101a/fixtures-before-execution.json'
    fixture=json.loads(fixture_path.read_text());phase=fixture['phases'][0];phase_before=copy.deepcopy(phase)
    files=[Path(__file__),STAGE/'is6_spatial_artifact.py',ROOT/'IS-6-ARTEFATO-CONTRATO-PREVIO.md',
           ROOT/'scripts/is6-spatial-artifact-roundtrip.py',binding_path,fixture_path]
    hashes=dict(binding['source_sha256']);hashes.update({p.relative_to(ROOT).as_posix():sha(p) for p in files})
    assert all(sha(ROOT/n)==v for n,v in hashes.items());folder.mkdir();archive=folder/'executed-sources.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    owner=ROOT/'user/sessions/latest.json'
    r=dict(accepted=False,completed=False,source_sha256=hashes,archive_sha256=sha(archive),owner_sha256=sha(owner),
           limits_before_execution=dict(create_s=2.,restore_s=2.,maximum_bytes=16*1024*1024,branches=32),
           groups=[],refusals=[],timings=[],scope='Headless spatial artifact/probes/persistence/Windows locks only; no native, UI, visual or profile acceptance.')
    def persist():path.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def passed(name):r['groups'].append(name);persist();print(json.dumps(dict(group=name,passed=True)),flush=True)
    persist()
    try:
        sys.path.insert(0,str(STAGE));import is6_spatial_artifact as artifact
        generation=artifact.generation();r['generation']=generation
        configurations={};runs={}
        for body in phase['bodies']:
            selection=dict(body_id=body['id'],source_guard=artifact.body.guard(phase))
            config=copy.deepcopy(artifact.DEFAULT_CONFIGURATION);saved=copy.deepcopy(config)
            began=time.perf_counter();run=artifact.Run.create(phase,selection,config);elapsed=time.perf_counter()-began
            assert elapsed<=2.,elapsed;r['timings'].append(dict(body=body['reference_id'],operation='default_create',elapsed_s=elapsed))
            assert config==saved and phase==phase_before
            payload=run.payload;view=run.default_view();digest=artifact.digest(payload)
            for i in [0,32,64]:
                v={**view,'selected_radial_index':i,'selected_azimuth_index':95}
                sample=run.sample(v);p=payload['mesh'];radius=p['meridian_radius_m'][i]
                assert sample['metric']==artifact.spatial.sample(payload['binding']['source_configuration'],radius)
                assert sample['physical_position_relative_m']==p['physical_vertices_relative_m'][i*97+95]
                assert sample['static_clock_comparison']==artifact.spatial.compare_clocks(payload['binding']['source_configuration'],radius,p['meridian_radius_m'][-1])
                hidden=run.sample({**v,'visible':False});assert hidden['metric']==sample['metric']
                assert artifact.digest(run.payload)==digest
            outside=run.payload;outside['mesh']['physical_vertices_relative_m'][0][0]=123
            assert artifact.digest(run.payload)==digest
            configurations[body['reference_id']]=config;runs[body['reference_id']]=run
        run=runs['sol:naif:10'];base=run.payload;selected=base['selection'];maximum=copy.deepcopy(base['configuration']);maximum['radial_count']=257
        began=time.perf_counter();large=artifact.Run.create(phase,selected,maximum);elapsed=time.perf_counter()-began
        r['timings'].append(dict(operation='maximum_create',elapsed_s=elapsed));assert elapsed<=2.,elapsed
        for kind,candidate in [('default',run),('maximum',large)]:
            payload=candidate.payload;began=time.perf_counter();restored=artifact.Run.restore(payload);elapsed=time.perf_counter()-began
            assert restored.payload==payload and elapsed<=2.,(kind,elapsed)
            r['timings'].append(dict(operation=kind+'_restore',elapsed_s=elapsed))
        passed('Four_bodies_default_mesh_exact_probes_visibility_input_output_isolation_and_default_maximum_create_restore_under2s')
        store=artifact.Store(folder/'checkpoints');preferences={**run.default_view(),'selected_radial_index':32,'selected_azimuth_index':13,'visible':False}
        parent=store.save(run,preferences,name='Malha · ramo inicial')['branch']['id']
        store.save(run,preferences,parent=parent);original=store.path.read_bytes()
        loaded,v,lineage=store.load();assert loaded.payload==base and v==preferences and lineage==parent
        child=store.save(loaded,{**preferences,'selected_radial_index':64},name='Malha · instante externo',parent=parent)['branch']['id']
        loaded,v,lineage=store.load(child);assert v['selected_radial_index']==64 and lineage==child
        store.save(loaded,v,parent=lineage)
        process=subprocess.run([sys.executable,str(ROOT/'scripts/is6-spatial-artifact-roundtrip.py'),'--folder',str(store.folder)],check=True,capture_output=True,text=True,encoding='utf-8',timeout=30)
        record=json.loads(process.stdout);assert record==dict(artifact_sha256=artifact.digest(base),view=v,lineage_parent=child,sample=loaded.sample(v))
        export=store.export(loaded,v,parent=child);exported=json.loads(Path(export['path']).read_text())
        assert exported['artifact']==base and exported['view']==v and exported['lineage_parent']==child and exported['record_sha256']==export['record_sha256']
        passed('Save_load_branches_new_process_preserve_exact_artifact_probe_view_and_explicit_lineage_parent_export')
        original=store.path.read_bytes();held=artifact.digest(run.payload)
        def reseal(value):value['record_sha256']=artifact.digest({k:v for k,v in value.items() if k!='record_sha256'})
        for change in ['seal','old_type','old_artifact','generation','epoch','configuration','vertex','view_bool','duplicate','extra','budget']:
            bad=json.loads(original)
            if change=='seal':bad['record_sha256']='0'*64
            elif change=='old_type':bad['kind']='is5_compression_solar_checkpoint'
            elif change=='old_artifact':bad['artifact']['kind']='is5_compression_calculated_solar_scenario'
            elif change=='generation':bad['artifact']['generation']['version']='wrong'
            elif change=='epoch':bad['artifact']['binding']['epoch']['utc']='wrong'
            elif change=='configuration':bad['artifact']['configuration']['vertical_amplification']=999.
            elif change=='vertex':bad['artifact']['mesh']['display_vertices_relative_m'][0][0]+=1
            elif change=='view_bool':bad['view']['selected_radial_index']=True
            elif change=='extra':bad['extra']=1
            if change!='seal':reseal(bad)
            text=json.dumps(bad)
            if change=='duplicate':text=text.replace('"schema": 1','"schema": 1,"schema": 1',1)
            if change=='budget':text=' '*(artifact.MAX_BYTES+1)
            try:
                store.path.write_text(text,encoding='utf-8')
                try:store.load()
                except ValueError:r['refusals'].append(change)
                else:raise AssertionError('Accepted damaged record:'+change)
                assert artifact.digest(run.payload)==held
            finally:store.path.write_bytes(original)
            assert store.path.read_bytes()==original
        passed('Seals_old_types_generation_epoch_options_vertex_view_duplicates_budget_refused_preserve_previous_artifact')
        for name,parent_id in [('',None),('x'*81,None),('bad parent','f'*32)]:
            try:store.save(run,preferences,name=name,parent=parent_id)
            except (ValueError,FileNotFoundError):r['refusals'].append('invalid_branch:'+name[:8])
            else:raise AssertionError('Invalid branch accepted')
            assert store.path.read_bytes()==original
        for i in range(30):store.save(run,preferences,name='Ramo '+str(i),parent=parent)
        assert len(store.catalog())==32 and all(b['valid'] for b in store.catalog())
        try:store.save(run,preferences,name='Ramo33',parent=parent)
        except ValueError:r['refusals'].append('branch33')
        else:raise AssertionError('Branch33 accepted')
        assert len(list(store.branches.glob('*.json')))==32 and store.path.read_bytes()==original
        for bad in ['../escape','1'*31,True]:
            try:store.load(bad)
            except ValueError:r['refusals'].append('branch_identity:'+str(bad))
            else:raise AssertionError('Invalid path accepted')
        assert sys.platform=='win32','This verifier requires actual Windows locking evidence'
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p]
        kernel.CreateFileW.restype=ctypes.c_void_p;kernel.CloseHandle.argtypes=[ctypes.c_void_p]
        handle=kernel.CreateFileW(str(store.path),0x80000000,1,None,3,0,None)
        assert handle not in (None,ctypes.c_void_p(-1).value)
        try:
            try:store.save(run,preferences,parent=parent)
            except PermissionError:r['refusals'].append('Windows_destination_lock')
            else:raise AssertionError('Replace should fail while destination denies delete sharing')
            assert store.path.read_bytes()==original
        finally:kernel.CloseHandle(handle)
        assert not list(store.folder.glob('*.tmp'))
        store.save(run,preferences,parent=parent);restored,restored_view,restored_parent=store.load()
        assert restored.payload==base and restored_view==preferences and restored_parent==parent
        passed('32branches_refuse33_names_parents_paths_Windows_lock_atomicity_and_recovery')
        assert phase==phase_before and artifact.generation()==generation and sha(owner)==r['owner_sha256']
        assert all(sha(ROOT/n)==v for n,v in hashes.items())
        r.update(accepted=True,completed=True)
    except Exception:r['failure']=traceback.format_exc()
    finally:persist()
    print(json.dumps(dict(accepted=r['accepted'],completed=r['completed'],groups=len(r['groups']),refusals=len(r['refusals']),timings=r['timings'],failure=r.get('failure'))),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
