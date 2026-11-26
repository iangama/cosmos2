"""Capture real cancellation controls and exercise branch lineage after recalculation."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import hashlib
import json
import subprocess
import time
import traceback
import zipfile
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
h=SourceFileLoader('compression_supplement_tools',str(ROOT/'scripts/verify-native-is5-compression-v3.py')).load_module()
APP=h.APP
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    path=ROOT/'evidence/is5-compression-visual-supplement-20261101c.json'
    archive=ROOT/'output/is5-compression-visual-supplement-20261101c.zip'
    if path.exists() or archive.exists():raise FileExistsError('Preserve supplement')
    native=ROOT/'evidence/is5-native-compression-20261101c.json'
    prior=json.loads(native.read_text());assert prior['accepted'] and prior['completed']
    hashes=dict(prior['source_sha256'])
    for p in [native,Path(__file__)]:hashes[p.relative_to(ROOT).as_posix()]=sha(p)
    assert all(sha(ROOT/n)==v for n,v in hashes.items())
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(accepted=False,completed=False,source_sha256=hashes,archive_sha256=sha(archive),checks=[],captures=[],page_errors=[],
           scope='Additional CEF cancellation captures and successful-recalculation branch lineage. Separate visual review required; no profile acceptance.')
    def persist():path.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def zone():return h.request('/api/solar-zone/state')
    def command(name,**extra):
        w=zone()['worker'];guard={k:w[k] for k in ['worker_id','artifact_id','edit_token','revision']}
        return h.request('/api/solar-zone/command',dict(command=name,guard=guard,**extra))
    def settled(page):page.wait_for_function('!solarZonePending&&!solarZoneState.busy&&solarZoneState.active&&!solarZoneCurvePending&&solarZoneCurveId===solarZoneState.worker.artifact_id',timeout=750000)
    def reveal(page,identifier):
        page.evaluate('(()=>{const e=document.getElementById('+json.dumps(identifier)+');for(let p=e.parentElement;p;p=p.parentElement)if(p.tagName==="DETAILS")p.open=true;e.scrollIntoView({block:"center"});})()')
    def capture(page,button,phase,scale):
        page.locator('#ui-scale').select_option(scale);reveal(page,button);time.sleep(.35)
        file=ROOT/f'evidence/cosmos2-is5-compression-20261101c-{phase}-{100 if scale=="1" else 150}.png'
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',file.name],check=True,capture_output=True)
        r['captures'].append(dict(path=file.relative_to(ROOT).as_posix(),sha256=sha(file)));persist()
    def stable(z):
        return dict(worker=None if not z['worker'] else {k:z['worker'][k] for k in ['worker_id','artifact_id','artifact_sha256','edit_token','revision','configuration','source','sample','view','branch_parent']},scene=z['scene'])
    def cancel(page,button,before):
        page.locator('#ui-scale').select_option('1');page.locator('#'+button).click()
        page.wait_for_function('!solarZonePending&&!zoneCancelPending&&!solarZoneState.busy&&!solarZoneState.calculation',timeout=6000)
        assert stable(zone())==stable(before)
    def branch(page,name):
        reveal(page,'zone-branch-name');page.evaluate('document.getElementById("zone-branch-name").value='+json.dumps(name))
        h.h.click(page,'#zone-branch-create');settled(page)
        return zone()['worker']['branch_parent']
    persist()
    try:
        with Page() as page:
            page.on('pageerror',lambda error:r['page_errors'].append(error));page.goto(h.h.BASE+'/')
            page.wait_for_function('solarZoneState!==null&&!pending')
            h.h.click(page,'#copy-solar');page.wait_for_function('!pending&&appState?.physics?.paused&&appState.physics.bodies.length===4',timeout=70000)
            orbital=h.h.phase(h.request('/api/state')['physics'])
            page.evaluate('document.getElementById("zone-setup").open=true');before=zone()
            h.h.click(page,'#zone-create');page.wait_for_function('solarZoneState.calculation?.cancellable',timeout=10000)
            for scale in ['1','1.5']:capture(page,'zone-cancel-setup','creation-cancel',scale)
            cancel(page,'zone-cancel-setup',before)
            h.h.click(page,'#zone-load-saved');settled(page)
            command('set_view',view=dict(selected_index=240,visible=dict(composition=True,energy=True,neutrinos=True,reference=True)))
            page.wait_for_function('solarZoneState.worker.view.selected_index===240&&solarZoneState.worker.view.visible.neutrinos&&!document.getElementById("zone-neutrinos-chart").hidden')
            w=zone()['worker']
            assert not w['configuration']['acting']['weak'] and w['sample']['actual']['neutrino_count']==0 and w['sample']['reference']['neutrino_count']>0
            for scale in ['1','1.5']:
                capture(page,'zone-neutrinos-chart','weak-off-neutrinos',scale)
                capture(page,'zone-acting','force-controls',scale)
                capture(page,'zone-channels','channel-controls',scale)
                capture(page,'zone-coulomb','plasma-controls',scale)
            r['checks'].append('Saved weak-off scenario restored; actual neutrinos0 versus positive full reference; visible neutrino/force/channel/plasma panels captured100/150%')
            command('leave');page.wait_for_function('!solarZoneState.active')
            page.locator('#ui-scale').select_option('1')
            page.evaluate('document.getElementById("zone-duration").value=1');page.locator('#zone-history').select_option('constant')
            page.locator('#zone-weak').set_checked(True)
            h.h.click(page,'#zone-create');settled(page)
            parent=branch(page,'Suplemento · condição inicial de1s')
            assert parent
            command('set_view',view=dict(selected_index=120,visible=dict(composition=False,energy=True,neutrinos=False,reference=True)))
            settled(page);page.wait_for_function('solarZoneState.worker.view.selected_index===120')
            before=zone();reveal(page,'zone-duration')
            page.evaluate('document.getElementById("zone-duration").value=31557600000');page.locator('#zone-history').select_option('exponential')
            page.evaluate('document.getElementById("zone-ratio").value=1.05')
            h.h.click(page,'#zone-recompute');page.wait_for_function('solarZoneState.calculation?.cancellable',timeout=10000)
            for scale in ['1','1.5']:capture(page,'zone-cancel','recalculation-cancel',scale)
            cancel(page,'zone-cancel',before)
            r['checks'].append('Real creation and recalculation cancellation controls captured100/150%; confirmed source/scene/view/probe/branch preserved')
            reveal(page,'zone-duration');page.evaluate('document.getElementById("zone-duration").value=2')
            page.locator('#zone-history').select_option('constant');h.h.click(page,'#zone-recompute');settled(page)
            current=zone()['worker']
            assert current['artifact_id']!=before['worker']['artifact_id'] and current['branch_parent']==parent
            assert current['source']==before['worker']['source'] and current['view']['visible']==before['worker']['view']['visible'] and current['view']['selected_index']==0
            child=branch(page,'Suplemento · recálculo confirmado de2s')
            assert next(b for b in zone()['worker']['branches'] if b['id']==child)['parent']==parent
            assert h.h.phase(h.request('/api/state')['physics'])==orbital
            r['checks'].append('Successful CEF recalculation preserves branch parent/source/visibility, resets knot0 and new branch points to its parent')
            assert not r['page_errors'] and all(sha(ROOT/n)==v for n,v in hashes.items())
            r.update(accepted=True,completed=True)
    except Exception:r['failure']=traceback.format_exc()
    finally:
        try:
            state=zone()
            if state['calculation']:h.request('/api/solar-zone/cancel',dict(transaction_id=state['calculation']['transaction_id']))
            if zone()['active']:command('leave')
            with Page() as page:page.locator('#ui-scale').select_option('1')
            if h.request('/api/state')['mode']=='experiment':h.request('/api/command',dict(command='atlas'))
        except Exception:r['cleanup_failure']=traceback.format_exc();r['accepted']=False
        persist()
    print(json.dumps({k:r.get(k) for k in ['accepted','completed','checks','failure','cleanup_failure']}),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
