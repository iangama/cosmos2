"""UI-only0.26.2: concise model summary and visible selected-body labels."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/is6-dynamics16-product0.26.1'
TARGET=ROOT/'output/is6-dynamics16-product0.26.2'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def replace(text,old,new):
    assert text.count(old)==1,(old[:70],text.count(old));return text.replace(old,new)


def main():
    assert not TARGET.exists()
    parent=json.loads((BASE/'build-manifest.json').read_text(encoding='utf8'))
    actual={p.relative_to(BASE/'app').as_posix():sha(p) for p in (BASE/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    assert actual==parent['files_sha256']
    native=ROOT/'evidence/is6-dynamics16-native-20261112b.json';assert json.loads(native.read_text())['functional_accepted']
    html=(BASE/'app/ui/index.html').read_text(encoding='utf8')
    html=replace(html,'<p id="dynamics16-model" class="field-help" hidden></p>',
        '<p id="dynamics16-summary" class="field-help" style="white-space:pre-line" hidden></p><details id="dynamics16-model-panel" hidden><summary>Época, fontes e limites do modelo</summary><p id="dynamics16-model" class="field-help" style="white-space:pre-line" hidden></p></details>')
    solar=(BASE/'app/ui/solar.js').read_text(encoding='utf8')
    solar=replace(solar,"  $('dynamics16-model').hidden = !sixteen;", "  $('dynamics16-model').hidden = !sixteen;\n  $('dynamics16-summary').hidden = !sixteen;")
    solar=replace(solar,"panel.hidden=sixteen;", "panel.hidden=panel.id==='dynamics16-model-panel' ? !sixteen : sixteen;")
    solar=replace(solar,'    const model=p.dynamics16;', "    const model=p.dynamics16;\n    $('dynamics16-summary').textContent=`16 centros físicos · Newton / IAS15\\n${p.bodies.length} fontes ativas · t = ${(model.elapsed_s/3600).toPrecision(7)} h · revisão ${p.revision}\\nMarcadores ampliados; sem acoplamento EM ou nuclear.`;")
    solar=solar.replace('16fontes iniciais','16 fontes iniciais')
    editor=(BASE/'app/ui/body-editor.js').read_text(encoding='utf8')
    old="  const distance=appState.display?.physical_radii&&b.attributes.radius_m>0?Math.max(4*b.attributes.radius_m,1):b.display_marker_radius_m?b.display_marker_radius_m*10:b.reference_id==='sol:naif:10'?4e9:p.atlas_initial?8e8:1.2e9;"
    new="  const markerRadius=p.dynamics16?(b.display_marker_radius_m||(b.reference_id==='sol:naif:10'?4e8:b.reference_id==='sol:naif:599'?2e8:b.reference_id==='sol:naif:399'?8e7:4e7)):0;\n  const distance=appState.display?.physical_radii&&b.attributes.radius_m>0?Math.max(4*b.attributes.radius_m,1):p.dynamics16?Math.max(8e8,markerRadius*10):b.display_marker_radius_m?b.display_marker_radius_m*10:b.reference_id==='sol:naif:10'?4e9:p.atlas_initial?8e8:1.2e9;\n  const offset=p.dynamics16?Math.max(1.8*markerRadius,distance*.09):distance*.03+1.5*(appState.display?.physical_radii?b.attributes.radius_m||0:b.display_marker_radius_m||0);\n  const labelPosition=p.dynamics16?[0,.3*offset/Math.sqrt(1.09),offset/Math.sqrt(1.09)]:[0,0,offset];"
    editor=replace(editor,old,new)
    old="{0,0,'+(distance*.03+1.5*(appState.display?.physical_radii?b.attributes.radius_m||0:b.display_marker_radius_m||0))+'}"
    editor=replace(editor,old,"{'+labelPosition.join(',')+'}")
    shutil.copytree(BASE/'app',TARGET/'app',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name,value in [('ui/index.html',html),('ui/solar.js',solar),('ui/body-editor.js',editor)]:
        (TARGET/'app'/name).write_text(value,encoding='utf8')
    files={p.relative_to(TARGET/'app').as_posix():sha(p) for p in (TARGET/'app').rglob('*') if p.is_file()}
    changed=sorted(n for n,s in files.items() if actual.get(n)!=s)
    assert changed==['ui/body-editor.js','ui/index.html','ui/solar.js']
    assert {n:s for n,s in files.items() if n.endswith('.py')}=={n:s for n,s in actual.items() if n.endswith('.py')}
    inputs=[Path(__file__),BASE/'build-manifest.json',native,ROOT/'evidence/is6-dynamics16-service-20261112c.json',ROOT/'evidence/is6-dynamics16-http-20261112c.json']
    sources={**parent['source_sha256'],**{p.relative_to(ROOT).as_posix():sha(p) for p in inputs}}
    assert all(sha(ROOT/n)==s for n,s in sources.items())
    manifest=dict(candidate='0.26.2',accepted=False,promoted=False,source_sha256=sources,files_sha256=files,changed=changed,
        base_manifest=(BASE/'build-manifest.json').relative_to(ROOT).as_posix(),scene_profile=parent['scene_profile'],
        inherited_service=dict(receipt='evidence/is6-dynamics16-service-20261112c.json',python_files_byte_identical=True,scientific_extension_version='0.26.1'),
        scope='UI-only refinement after direct visual review; science, worker and HTTP Python files byte-identical to accepted serviceC. New native and visual journey and own profile required.')
    (TARGET/'build-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    # Launch gates keep the accepted service receipts and pin the exact UI-only delta.
    launch=ROOT/'scripts/launch-is6-dynamics16-candidate-v5.py';assert not launch.exists()
    text=(ROOT/'scripts/launch-is6-dynamics16-candidate-v4.py').read_text(encoding='utf8').replace('0.26.1','0.26.2')
    anchor="    assert manifest['promoted'] is False and manifest['candidate']=='0.26.2'"
    text=replace(text,anchor,anchor+"\n    assert manifest['inherited_service']['python_files_byte_identical'] and manifest['changed']==['ui/body-editor.js','ui/index.html','ui/solar.js']")
    compile(text,str(launch),'exec');launch.write_text(text,encoding='utf8')
    switch=ROOT/'scripts/switch-is6-dynamics16-candidate-v5.py';assert not switch.exists()
    text=(ROOT/'scripts/switch-is6-dynamics16-candidate-v4.py').read_text(encoding='utf8')
    text=text.replace('0.26.1','0.26.2').replace('launch-is6-dynamics16-candidate-v4.py','launch-is6-dynamics16-candidate-v5.py')
    text=replace(text,"ROOT/'output/is6-dynamics16-product0.26.0/app/server.py',TARGET/'app/server.py'","ROOT/'output/is6-dynamics16-product0.26.0/app/server.py',ROOT/'output/is6-dynamics16-product0.26.1/app/server.py',TARGET/'app/server.py'")
    compile(text,str(switch),'exec');switch.write_text(text,encoding='utf8')
    admission=ROOT/'scripts/verify-native-is6-dynamics16-admission-v2.py';assert not admission.exists()
    text=(ROOT/'scripts/verify-native-is6-dynamics16-admission.py').read_text(encoding='utf8').replace("('0.26.0','0.26.1')","('0.26.0','0.26.1','0.26.2')")
    compile(text,str(admission),'exec');admission.write_text(text,encoding='utf8')
    verifier=ROOT/'scripts/verify-native-is6-dynamics16-v3.py';assert not verifier.exists()
    text=(ROOT/'scripts/verify-native-is6-dynamics16.py').read_text(encoding='utf8')
    text=text.replace('is6-dynamics16-product0.26.1','is6-dynamics16-product0.26.2').replace('native-admission-20261112c.json','native-admission-20261112d.json')
    text=text.replace('if(!document.body.classList.contains("details-open"))$("panel-toggle").click()','if(document.body.classList.contains("details-open"))$("panel-toggle").click()')
    text=text.replace('.every(e=>e.hidden)', '.every(e=>e.id==="dynamics16-model-panel"?!e.hidden:e.hidden)')
    compile(text,str(verifier),'exec');verifier.write_text(text,encoding='utf8')
    print(json.dumps(dict(prepared=True,candidate='0.26.2',changed=changed,python_byte_identical=True)),flush=True)


if __name__=='__main__':main()
