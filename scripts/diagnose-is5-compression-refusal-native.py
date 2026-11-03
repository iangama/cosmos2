"""Separate refusal latency from preservation for the native0.17.1 failure."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import copy
import hashlib
import json
import time
import traceback
import zipfile
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is5-compression-product0.17.1/app'
h=SourceFileLoader('compression_refusal_tools',str(ROOT/'scripts/verify-native-is5-compression-v2.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    path=ROOT/'evidence/is5-compression-refusal-native-20261101a.json'
    archive=ROOT/'output/is5-compression-refusal-native-20261101a.zip'
    if path.exists() or archive.exists():raise FileExistsError('Preserve diagnostic')
    files=[p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [Path(__file__),ROOT/'scripts/verify-native-is5-compression-v2.py',ROOT/'evidence/is5-native-compression-20261101b.json']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(accepted=False,completed=False,source_sha256=hashes,archive_sha256=sha(archive),cases=[])
    def zone():return h.request('/api/solar-zone/state')
    def guard(z):return {k:z['worker'][k] for k in ['worker_id','artifact_id','edit_token','revision']}
    def stable(z):return {k:z['worker'][k] for k in ['worker_id','artifact_id','artifact_sha256','edit_token','revision','sample','configuration','source','view','branch_parent']}|{'scene':z['scene']}
    def persist():path.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    try:
        with Page() as page:
            page.goto(h.h.BASE+'/');page.wait_for_function('solarZoneState!==null&&!pending')
            h.h.click(page,'#copy-solar')
            page.wait_for_function('!pending&&appState?.physics?.paused&&appState.physics.bodies.length===4',timeout=70000)
            page.evaluate('document.getElementById("zone-setup").open=true;document.getElementById("zone-duration").value=1')
            page.locator('#zone-history').select_option('constant');h.h.click(page,'#zone-create')
            page.wait_for_function('solarZoneState?.active&&!solarZonePending&&!solarZoneCurvePending&&solarZoneCurveId===solarZoneState.worker.artifact_id',timeout=750000)
            config=zone()['worker']['configuration']
            for kind in ['wrong_bool','invalid_ratio','trajectory_guard','EOS_mismatch','old_decay','extra_field']:
                bad=copy.deepcopy(config)
                if kind=='wrong_bool':bad['parameters']['temperature_K']=True
                elif kind=='invalid_ratio':bad['density_history']=dict(kind='exponential',ratio=1.3)
                elif kind=='trajectory_guard':bad['parameters']['density_kg_m3']=300000.;bad['density_history']=dict(kind='exponential',ratio=1.2)
                elif kind=='EOS_mismatch':bad['include_coulomb']=False
                elif kind=='old_decay':bad['decay_basis']='reaclib_wc12'
                else:bad['unknown']=1
                before=zone();began=time.perf_counter()
                reply=h.request('/api/solar-zone/command',dict(command='configure',configuration=bad,guard=guard(before)),expected=400)
                elapsed=time.perf_counter()-began;after=zone()
                differences=[k for k,v in stable(before).items() if stable(after)[k]!=v]
                row=dict(case=kind,elapsed_s=elapsed,preserved=not differences,differences=differences,error=reply.get('error'))
                r['cases'].append(row);persist();print(json.dumps(row,ensure_ascii=False),flush=True)
            r['completed']=True
    except Exception:r['failure']=traceback.format_exc()
    finally:
        try:
            if zone()['active']:h.request('/api/solar-zone/command',dict(command='leave',guard=guard(zone())))
            h.h.native('openspace.toggleShutdown();return {closing=true}')
        except Exception:r['cleanup_failure']=traceback.format_exc()
        persist()


if __name__=='__main__':main()
