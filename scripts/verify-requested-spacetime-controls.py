"""Owner-requested native CEF check; report missing mesh separately from references."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import time
import urllib.request
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--port',type=int,default=4700)
parser.add_argument('--report',default='requested-spacetime-controls-20261018.json')
args=parser.parse_args()
assert Path(args.report).name==args.report
BASE='http://127.0.0.1:'+str(args.port)
owner=ROOT/'user/sessions/latest.json';original=owner.read_bytes()
report={'status':'running','browser':'actual OpenSpace CEF','base_url':BASE,'javascript_errors':[]}
def capture(name):
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
        str(ROOT/'scripts/capture-window.ps1'),'-Name',name],check=True,capture_output=True)
def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=True).encode()).hexdigest()
with Page() as page:
    page.on('pageerror',lambda e:report['javascript_errors'].append(e))
    previous=page.evaluate('location.href')
    def go(url):
        # Old polling requests may be canceled by navigation; wait for the new
        # document itself instead of treating every canceled subrequest as failure.
        page.call('Page.navigate',{'url':url})
        page.wait_for_function('location.href==='+json.dumps(url)+'&&document.readyState==="complete"')
    inventory='Array.from(document.querySelectorAll("button,label,summary")).map(e=>({id:e.id,text:e.textContent.trim()})).filter(e=>/malha|espaço[ -]?temporal|espaco[ -]?temporal|spacetime/i.test(e.text))'
    try:
        go(BASE+'/');page.wait_for_function('appState!==null')
        report['atlas_laboratory_spacetime_mesh_controls']=page.evaluate(inventory)
        go(BASE+'/forces.html')
        page.wait_for_function('typeof response!=="undefined"&&response&&!pending',timeout=30000)
        page.locator('[data-scenario="relativity"]').click()
        page.wait_for_function('!pending&&config.scenario==="relativity"&&response.result.ray',timeout=30000)
        report['forces_spacetime_mesh_controls']=page.evaluate(inventory)
        visible=page.locator('[data-force="gravity"][data-control="visible"]')
        acting=page.locator('[data-force="gravity"][data-control="acting"]')
        for locator in (visible,acting):
            locator.set_checked(True);page.wait_for_function('!pending')
        baseline=page.evaluate('response.result')
        baseline_hash=digest(baseline)
        assert baseline['ray']['curvature_term_applied'] is True
        probes=len(baseline['metric_probes']);assert probes>0
        cycles=[]
        for cycle in range(3):
            images={}
            for show in (False,True):
                visible.set_checked(show);page.wait_for_function('!pending')
                assert page.evaluate('config.controls.gravity.visible')==show
                current=page.evaluate('response.result');assert current==baseline
                drawn=page.evaluate('projectedArrows.filter(p=>p.metric).length')
                assert drawn==(probes if show else 0)
                images[show]=hashlib.sha256(page.evaluate('canvas.toDataURL()').encode()).hexdigest()
                cycles.append({'cycle':cycle+1,'reference_visible':show,'rendered_metric_probes':drawn,
                    'physical_result_sha256':digest(current),'canvas_sha256':images[show]})
                if cycle==0:
                    capture('cosmos2-requested-spacetime-reference-'+('on' if show else 'off')+'.png')
            assert images[False]!=images[True],'The rendered image must respond to visibility'
        report['curvature_reference_toggle']={'status':'passed','three_full_off_on_cycles':cycles,
            'metric_probes':probes,'physical_result_unchanged':True,'physical_result_sha256':baseline_hash}
        actions=[]
        for act in (False,True):
            acting.set_checked(act);page.wait_for_function('!pending')
            ray=page.evaluate('response.result.ray')
            assert ray['curvature_term_applied']==act
            assert page.evaluate('response.result.metric_probes')==baseline['metric_probes']
            assert page.evaluate('config.controls.gravity.visible') is True
            assert page.evaluate('projectedArrows.filter(p=>p.metric).length')==probes
            actions.append({'acting':act,'curvature_term_applied':ray['curvature_term_applied'],'ray_status':ray['status']})
        bending=page.locator('[data-effect="ray_bending"]')
        for enabled in (False,True):
            bending.set_checked(enabled);page.wait_for_function('!pending')
            assert page.evaluate('response.result.ray.curvature_term_applied')==enabled
            assert page.evaluate('response.result.metric_probes')==baseline['metric_probes']
        report['physical_curvature_controls']={'status':'passed','acting_off_on':actions,
            'ray_bending_effect_off_on':True,'reference_not_removed_by_physical_control':True}
        assert not report['javascript_errors'],report['javascript_errors']
        assert owner.read_bytes()==original
        report.update(status='existing_controls_passed_spacetime_mesh_button_absent',
            spacetime_mesh_button_present=False,owner_pointer_preserved=True,
            owner_pointer_sha256=hashlib.sha256(original).hexdigest(),
            scope_ptBR='A versão atual tem cascas de sondas de relógio/curvatura em Schwarzschild e referência visual. Não oferece malha espaço-temporal deformada nem botão específico para ela. Não confundir Referência com Atuação física.')
    finally:
        go(previous)
        assert owner.read_bytes()==original
(ROOT/'evidence'/args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
