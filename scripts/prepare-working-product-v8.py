"""Bring the accepted timelike backend into the curated local product, preserving its UI fixes."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT/'output/original-flow-hotfix-product0.27.7'
BENCH=ROOT/'output/c214-orbits-product0.28.2'
TARGET=ROOT/'output/original-flow-hotfix-product0.28.3'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def replace(text,before,after):
    assert text.count(before)==1,'Unique patch required: '+before[:100]
    return text.replace(before,after)


def main():
    assert not TARGET.exists(),'Preserve revisions'
    for name in ['c214-orbits-profile-host-20261121b.json','c214-orbits-profile-audit-20261121b.json','spatial-roundtrip-delivery-20261121a.json']:
        gate=json.loads((ROOT/'evidence'/name).read_text());assert gate['accepted'] and gate['completed']
    parent=json.loads((PARENT/'build-manifest.json').read_text())
    bench=json.loads((BENCH/'build-manifest.json').read_text())
    assert all(sha(PARENT/n)==seal for n,seal in parent['files_sha256'].items())
    assert all(sha(BENCH/'app'/n)==seal for n,seal in bench['files_sha256'].items())
    for folder in ['app','data']:shutil.copytree(PARENT/folder,TARGET/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    # Exact accepted scientific implementation; no old executed revision is changed.
    for name in ['forces.py','science_contracts.py','timelike_orbits.py','timelike_force_adapter.py','timelike_service.py']:
        shutil.copy2(BENCH/'app'/name,TARGET/'app'/name)
    server=TARGET/'app/server.py';text=server.read_text()
    text=replace(text,'FORCE_JOBS = threading.BoundedSemaphore(2)','FORCE_JOBS = threading.BoundedSemaphore(2)\nfrom timelike_service import Laboratory as TimelikeLaboratory\nTIMELIKE = TimelikeLaboratory()')
    text=replace(text,'    def do_GET(self):','    def do_GET(self):\n        if self.path == \'/api/timelike/state\':\n            return self.json_response(TIMELIKE.status())')
    text=replace(text,"            elif self.path.startswith('/api/forces/'):","            elif self.path == '/api/timelike/command':\n                self.json_response(TIMELIKE.command(request))\n            elif self.path.startswith('/api/forces/'):")
    text=replace(text,"[('layers',LAYERS)","[('timelike',TIMELIKE),('layers',LAYERS)")
    server.write_text(text,encoding='utf8')
    html=TARGET/'app/ui/forces.html';text=html.read_text()
    bench_html=(BENCH/'app/ui/forces.html').read_text()
    controls=next(line for line in bench_html.splitlines() if 'id="timelike-controls"' in line)
    readings=next(line for line in bench_html.splitlines() if 'id="timelike-readings"' in line)
    text=replace(text,'    <div id="geomagnetic-controls"',controls+'\n    <div id="geomagnetic-controls"')
    text=replace(text,'    <div id="probe-panel"',readings+'\n    <div id="probe-panel"')
    text=replace(text,'<script src="forces.js">','<script src="timelike-view.js"></script><script src="forces.js">')
    html.write_text(text,encoding='utf8')
    css=TARGET/'app/ui/forces.css'
    css.write_text(css.read_text()+'\n'+next(line for line in (BENCH/'app/ui/forces.css').read_text().splitlines() if line.startswith('#timelike-controls')),encoding='utf8')
    # Form-only helpers edit the draft; graphics and exports continue using confirmed config.
    extension=(BENCH/'app/ui/timelike-view.js').read_text()
    extension=replace(extension,"if(config.scenario!=='timelike-orbits')return;","if(draftConfig.scenario!=='timelike-orbits')return;")
    extension=replace(extension,'else{config=structuredClone(state.configuration);','else{draftConfig=structuredClone(state.configuration);')
    (TARGET/'app/ui/timelike-view.js').write_text(extension,encoding='utf8')
    js=TARGET/'app/ui/forces.js';text=js.read_text()
    text=replace(text,'const visibleCurves=new Map();',"sceneLabels['timelike-orbits']=['Órbitas e relógios','◉','Newton, precessão e tempo próprio'];\nconst lastTimeIndex=()=>Math.max(0,(response?.result.time_s.length||241)-1);\nconst visibleCurves=new Map();")
    text=replace(text,'draftConfig.parameters={};buildControls();',"draftConfig.parameters={};if(key==='timelike-orbits'){azimuth=0;elevation=1.15;zoom=1;}buildControls();")
    text=replace(text,"    if(key==='initial_mode')input.onchange=updateInitialMode;","    if(key==='initial_mode')input.onchange=updateInitialMode;\n    if(draftConfig.scenario==='timelike-orbits'&&key==='orbit_kind')input.onchange=updateTimelikeParameters;")
    text=replace(text,'  updateDecayParameters();','  updateDecayParameters();\n  updateTimelikeParameters();')
    text=replace(text,"value=await post('evaluate',structuredClone(draftConfig));","value=draftConfig.scenario==='timelike-orbits'?await calculateTimelike(structuredClone(draftConfig)):await post('evaluate',structuredClone(draftConfig));")
    text=replace(text,"byId('time-index').value=240;","byId('time-index').max=lastTimeIndex();byId('time-index').value=lastTimeIndex();")
    text=replace(text,"    if(!response){startupState('error');", "    if(error.cancelled&&response){draftNotice('Cálculo cancelado. O último resultado completo permanece disponível.');status(error.message);}\n    else if(!response){startupState('error');")
    text=replace(text,"finally{lock(!response&&document.querySelector('article').dataset.startup==='error');}","finally{lock(!response&&document.querySelector('article').dataset.startup==='error');updateTimelikeParameters();}")
    text=replace(text,'  const r=response.result;','  const r=response.result;\n  byId(\'timelike-controls\').hidden=byId(\'timelike-readings\').hidden=!r.timelike;')
    text=replace(text,"r.ray?'RELATIVIDADE GERAL", "r.timelike?'ÓRBITAS LIGADAS · TEMPO COORDENADO E PRÓPRIO':r.ray?'RELATIVIDADE GERAL")
    text=replace(text,"byId('framing-control').hidden=!r.ray&&!r.binary;","byId('framing-control').hidden=!r.ray&&!r.binary&&!r.timelike;\n  byId('framing').options[0].textContent=r.timelike?'Região orbital':'Região do desvio';")
    text=replace(text,'  if(r.geomagnetic){drawGeomagnetic(r,w,h);return;}','  if(r.timelike){drawTimelike(r,index,w,h);return;}\n  if(r.geomagnetic){drawGeomagnetic(r,w,h);return;}')
    text=replace(text,"byId('animate').onclick=", "byId('timelike-view').onchange=()=>{byId('probe').textContent='';draw();};\nbyId('cancel-timelike').onclick=cancelTimelike;\nbyId('animate').onclick=")
    text=replace(text,"Number(byId('time-index').value)===240","Number(byId('time-index').value)===lastTimeIndex()")
    text=replace(text,"let index=Number(byId('time-index').value)+1;","let index=Math.min(lastTimeIndex(),Number(byId('time-index').value)+Math.max(1,Math.round(lastTimeIndex()/240)));")
    text=replace(text,'if(index>=240)','if(index>=lastTimeIndex())')
    js.write_text(text,encoding='utf8')
    files={p.relative_to(TARGET).as_posix():sha(p) for folder in ['app','data'] for p in (TARGET/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    old_science={n:seal for n,seal in parent['files_sha256'].items() if n.endswith('.py') and n not in ['app/server.py','app/artifacts.py']}
    changed_science=[n for n,seal in old_science.items() if files[n]!=seal]
    assert len(old_science)==140 and sorted(changed_science)==['app/forces.py','app/science_contracts.py']
    changed=[n for n in parent['files_sha256'] if files[n]!=parent['files_sha256'][n]]
    added=[n for n in files if n not in parent['files_sha256']]
    manifest=dict(schema=2,candidate='0.28.3',promoted=False,native_user_flow_accepted=False,files_sha256=files,
      parent_product=PARENT.relative_to(ROOT).as_posix(),parent_manifest_sha256=sha(PARENT/'build-manifest.json'),
      inherited_scientific_python=140,scientific_python_unchanged=138,changed_scientific_python=changed_science,
      changed_app_files=changed,added_app_files=added,
      accepted_backend_sha256={name:sha(BENCH/'app'/name) for name in ['forces.py','science_contracts.py','timelike_orbits.py','timelike_force_adapter.py','timelike_service.py']},
      preparation_script_sha256=sha(Path(__file__)),
      scope='Static local delivery candidate: accepted0.28.2 scientific backend copied exactly into0.27.7 curation; preserve separate draft/confirmed config, manual option controls, spatial versioned imports, scale and recovery. Two inherited scientific modules extended,138 unchanged,three scientific modules added. Native owner-path and new combined HTTP acceptance pending. Isolated profile remains scoped to0.28.2.')
    (TARGET/'build-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(prepared=True,changed=changed,added=added,scientific_unchanged=138,selected=False)))


if __name__=='__main__':main()
