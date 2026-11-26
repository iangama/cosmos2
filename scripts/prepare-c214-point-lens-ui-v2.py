"""Curate labels and view restoration in a new staging; keep the measured backend intact."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'output/c214-point-lens-ui-staging'
TARGET=ROOT/'output/c214-point-lens-ui-staging-v2'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert not TARGET.exists()
    tested=json.loads((ROOT/'evidence/c214-point-lens-ui-20261121a.json').read_text())
    assert tested['accepted'] and tested['completed'] and len(tested['checks'])==11
    previous=json.loads((SOURCE/'preparation.json').read_text())
    assert all(sha(SOURCE/n)==s for n,s in previous['files_sha256'].items())
    for folder in ['app','data']:shutil.copytree(SOURCE/folder,TARGET/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copy2(ROOT/'scripts/point-lens-view-v2.js',TARGET/'app/ui/point-lens-view.js')
    html=TARGET/'app/ui/forces.html';text=html.read_text()
    before='<div class="point-lens-probes">'
    assert text.count(before)==1
    text=text.replace(before,'<button id="point-lens-restore-view" type="button" title="Enquadra a cena e limpa a medição, mantendo as condições.">Restaurar vista</button>'+before)
    html.write_text(text,encoding='utf8')
    js=TARGET/'app/ui/forces.js';text=js.read_text()
    before="for(const key of keys){const title=catalog.effects[force][key];"
    assert text.count(before)==1
    text=text.replace(before,"for(const key of keys){const title=draftConfig.scenario==='point-lens'&&key==='ray_bending'?'Desvio gravitacional da luz':catalog.effects[force][key];")
    before="byId('framing').onchange=draw;";assert text.count(before)==1
    text=text.replace(before,"byId('framing').onchange=()=>{if(config.scenario==='point-lens')zoom=1;draw();};")
    js.write_text(text,encoding='utf8')
    files={p.relative_to(TARGET).as_posix():sha(p) for folder in ['app','data'] for p in (TARGET/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    changed=[n for n in files if files[n]!=previous['files_sha256'][n]]
    assert sorted(changed)==['app/ui/forces.html','app/ui/forces.js','app/ui/point-lens-view.js']
    proof=dict(accepted=True,completed=True,installed=False,native_user_flow_accepted=False,files_sha256=files,changed_app_files=changed,
      parent_preparation_sha256=sha(SOURCE/'preparation.json'),backend_preparation_sha256=previous['backend_preparation_sha256'],
      script_sha256=sha(Path(__file__)),view_source_sha256=sha(ROOT/'scripts/point-lens-view-v2.js'),
      scope='Visual curation only after isolated UI acceptance: aligned labels, truthful deflection caption, framing limited to sky view, restore-view clears measurement and resets framing/zoom. Backend unchanged; native path pending.')
    (TARGET/'preparation.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(prepared=True,backend_unchanged=True,installed=False,changed=changed)))


if __name__=='__main__':main()
