"""Prepare the lens view on the accepted full-server staging, without touching the owner app."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'output/c214-point-lens-service-staging'
TARGET=ROOT/'output/c214-point-lens-ui-staging'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def replace(text,before,after):
    assert text.count(before)==1,before[:90]
    return text.replace(before,after)


def main():
    assert not TARGET.exists()
    gate=json.loads((ROOT/'evidence/c214-point-lens-http-20261121a.json').read_text());assert gate['accepted'] and gate['completed']
    prepared=json.loads((SOURCE/'preparation.json').read_text());assert all(sha(SOURCE/n)==s for n,s in prepared['files_sha256'].items())
    for folder in ['app','data']:shutil.copytree(SOURCE/folder,TARGET/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copy2(ROOT/'scripts/point-lens-view.js',TARGET/'app/ui/point-lens-view.js')
    html=TARGET/'app/ui/forces.html';text=html.read_text()
    controls='''    <div id="point-lens-controls" hidden><label>Vista <select id="point-lens-view"><option value="sky">Céu do observador</option><option value="rays">Construção dos raios</option></select></label><button id="point-lens-align" type="button" title="Centraliza os três objetos no eixo Z e mantém suas posições ao longo dele.">Alinhar no eixo Z</button><div class="point-lens-probes"><button id="point-lens-measure-outer" type="button">Medir imagem externa</button><button id="point-lens-measure-inner" type="button">Medir imagem interna</button><button id="point-lens-measure-ring" type="button" hidden>Medir anel</button></div></div>
    <p id="point-lens-limit" class="point-lens-limit" role="status" hidden></p>
'''
    text=replace(text,'    <div id="timelike-controls"',controls+'    <div id="timelike-controls"')
    text=replace(text,'    <output id="timelike-readings"','    <output id="point-lens-geometry" class="point-lens-geometry" hidden></output>\n    <output id="timelike-readings"')
    text=replace(text,'<script src="timelike-view.js">','<script src="point-lens-view.js"></script><script src="timelike-view.js">')
    html.write_text(text,encoding='utf8')
    css=TARGET/'app/ui/forces.css';css.write_text(css.read_text()+'''
#point-lens-controls{display:flex;gap:12px 18px;align-items:end;flex-wrap:wrap;margin-bottom:14px}#point-lens-controls[hidden],#point-lens-geometry[hidden],#point-lens-limit[hidden]{display:none}.point-lens-probes{display:flex;gap:8px;flex-wrap:wrap}.point-lens-position{border-top:1px solid var(--line);padding-top:12px;margin-top:14px}.point-lens-position summary{cursor:pointer;color:#79d5d1;font-size:13px;margin-bottom:12px}.point-lens-position label{margin:12px 0}.point-lens-limit{border:1px solid #8a7149;border-radius:9px;padding:12px 16px;color:#f1d5a6;background:#32291b;font-size:13px;line-height:1.6}.point-lens-geometry{display:block;white-space:pre-wrap;font:12px/1.7 Consolas,monospace;color:#c5dde3;padding:12px 16px;background:#122832;border:1px solid var(--line);border-radius:9px;margin-top:12px}
''',encoding='utf8')
    js=TARGET/'app/ui/forces.js';text=js.read_text()
    text=replace(text,"sceneLabels['timelike-orbits']=", "sceneLabels['point-lens']=['Lente pontual','◉','Fonte, lente, observador e imagens'];\nsceneLabels['timelike-orbits']=")
    text=replace(text,"elevation=1.15;zoom=1;}buildControls();","elevation=1.15;zoom=1;}if(key==='point-lens'){zoom=1;byId('framing').value='whole';}buildControls();")
    text=replace(text,'  updateTimelikeParameters();','  updateTimelikeParameters();\n  updatePointLensParameters();')
    text=replace(text,'  const r=response.result;',"  const r=response.result;\n  byId('point-lens-controls').hidden=byId('point-lens-geometry').hidden=!r.point_lens;\n  byId('point-lens-limit').hidden=!r.point_lens_message;byId('point-lens-limit').textContent=r.point_lens_message||'';\n  canvas.style.cursor=r.point_lens?'crosshair':'';")
    text=replace(text,"r.timelike?'ÓRBITAS LIGADAS", "r.point_lens?'LENTE PONTUAL · GEOMETRIA ESTÁTICA':r.timelike?'ÓRBITAS LIGADAS")
    text=replace(text,"byId('framing-control').hidden=!r.ray&&!r.binary&&!r.timelike;","byId('framing-control').hidden=!r.ray&&!r.binary&&!r.timelike&&!r.point_lens;")
    text=replace(text,"r.timelike?'Região orbital':'Região do desvio';","r.point_lens?'Região de Einstein':r.timelike?'Região orbital':'Região do desvio';\n  byId('framing').options[1].textContent=r.point_lens?'Todas as imagens':'Trajetória completa';")
    text=replace(text,"document.querySelector('.timeline').hidden=Boolean(r.geomagnetic);","document.querySelector('.timeline').hidden=Boolean(r.geomagnetic||r.point_lens);")
    text=replace(text,'  if(r.timelike){drawTimelike(r,index,w,h);return;}','  if(r.point_lens){drawPointLens(r,w,h);return;}\n  if(r.timelike){drawTimelike(r,index,w,h);return;}')
    text=replace(text,"selectedEmParticle=false;if(closest.geomagnetic)","selectedEmParticle=false;if(closest.pointLens){readPointLensProbe(closest.pointLens);}else if(closest.geomagnetic)")
    js.write_text(text,encoding='utf8')
    files={p.relative_to(TARGET).as_posix():sha(p) for folder in ['app','data'] for p in (TARGET/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    changed=[n for n in prepared['files_sha256'] if files[n]!=prepared['files_sha256'][n]]
    assert sorted(changed)==['app/ui/forces.css','app/ui/forces.html','app/ui/forces.js']
    assert all(files[n]==s for n,s in prepared['files_sha256'].items() if not n.startswith('app/ui/'))
    proof=dict(accepted=True,completed=True,installed=False,native_user_flow_accepted=False,files_sha256=files,
      changed_app_files=changed,added_app_files=['app/ui/point-lens-view.js'],backend_preparation_sha256=sha(SOURCE/'preparation.json'),
      script_sha256=sha(Path(__file__)),view_source_sha256=sha(ROOT/'scripts/point-lens-view.js'),
      scope='Isolated static UI staging on the HTTP-accepted backend. Grouped source/lens/observer coordinates, sky/ray views, physical probes, alignment and explicit point-source limit; all curated result/option/scale behavior retained. No native promotion.')
    (TARGET/'preparation.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(prepared=True,backend_unchanged=True,installed=False)))


if __name__=='__main__':main()
