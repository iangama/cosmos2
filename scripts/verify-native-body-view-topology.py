"""Check saved magnetic selections after removing selected and other bodies in CEF."""
from pathlib import Path
import hashlib
import json
import traceback
import zipfile
from importlib.machinery import SourceFileLoader
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is3-body-view-topology-product/app'
h=SourceFileLoader('view_topology_native_helpers',str(ROOT/'scripts/verify-native-solar-tide.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    folder=ROOT/'output/is3-native-view-topology-20261024a'
    receipt=ROOT/'evidence/is3-native-view-topology-20261024a.json'
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve topology evidence.')
    launch=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'));assert launch.get('bodyViewTopologyCandidate')
    folder.mkdir()
    files=[p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [Path(__file__).resolve(),ROOT/'scripts/cef_page.py']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for p in files:archive.write(p,p.relative_to(ROOT).as_posix())
    owner=sha(ROOT/'user/sessions/latest.json')
    report={'schema':1,'accepted':False,'completed':False,'session':launch,'source_sha256':hashes,'cases':[]}
    try:
        with Page() as page:
            page.goto('http://127.0.0.1:4700/');page.wait_for_function('appState?.mode==="atlas"&&!pending')
            atlas=h.get('/api/atlas/state')
            for target in ['599','399']:
                h.click(page,'#copy-solar');page.wait_for_function('appState?.physics?.bodies.length===4&&!pending',timeout=70000)
                first=h.get('/api/state')['physics']
                earth=next(b for b in first['bodies'] if b['reference_id']=='sol:naif:399')
                removed=next(b for b in first['bodies'] if b['reference_id']=='sol:naif:'+target)
                for name in ['solar-panel','body-field-vector-panel']:
                    if not page.evaluate('document.getElementById('+json.dumps(name)+').open'):h.click(page,'#'+name+' > summary')
                page.locator('#solar-body').select_option(earth['id'])
                page.locator('#body-field-representation').select_option('lines')
                h.click(page,'#body-field-show');h.click(page,'#save')
                if not page.evaluate('document.getElementById("body-editor").open'):h.click(page,'#body-editor > summary')
                page.locator('#edit-operation').select_option('edit');page.locator('#edit-body').select_option(removed['id'])
                h.click(page,'#remove-edit-body')
                after=h.get('/api/state');physical=h.physical(after['physics'])
                assert len(after['physics']['bodies'])==3 and after['body_field_preview'] is None
                assert (after['physics']['body_field_view'] is None)==(target=='399')
                page.goto('http://127.0.0.1:4700/');page.wait_for_function('appState?.physics?.bodies.length===3&&!pending')
                selected=page.evaluate('document.getElementById("solar-body").value')
                assert selected in [b['id'] for b in after['physics']['bodies']] and selected!=removed['id']
                assert h.physical(h.get('/api/state')['physics'])==physical
                h.click(page,'#save');h.click(page,'#load')
                loaded=h.get('/api/state')
                assert loaded['physics']['bodies']==after['physics']['bodies'] and loaded['physics']['time']==after['physics']['time']
                assert loaded['body_field_preview'] is None
                assert page.evaluate('bodyFieldConfiguration().selected_body_id')==selected
                report['cases'].append({'removed_reference':'sol:naif:'+target,'removed_selected':target=='399',
                                        'reload_selected_active':True,'save_load_modified_phase_exact':True})
                h.click(page,'#atlas')
            last=h.get('/api/atlas/state');assert last['epoch']==atlas['epoch'] and last['bodies']==atlas['bodies']
        assert all(sha(ROOT/name)==digest for name,digest in hashes.items()) and sha(ROOT/'user/sessions/latest.json')==owner
        report.update(accepted=True,completed=True,scope='Focused0.6.1 topology/configuration fix through actual CEF and worker; no inherited sustained-performance acceptance.')
    except Exception:report['failure']=traceback.format_exc()
    receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'accepted':report['accepted'],'cases':len(report['cases']),'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
