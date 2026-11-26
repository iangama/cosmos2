"""Frozen10k aggregated native draw only; not the dynamic particle product."""
from pathlib import Path
import hashlib,json,runpy,subprocess,time,urllib.request
from cef_page import Page
ROOT=Path(__file__).resolve().parents[1];execute=runpy.run_path(str(ROOT/'scripts/engine-command.py'))['execute']
pointer=ROOT/'user/sessions/latest.json';before=pointer.read_bytes();source=ROOT/'output/c211-test-particles-staging/confirmed-static.speck'
def lua(code):
 response=execute(code);value=response.get('payload',{}).get('1')
 if value is None:raise RuntimeError(response)
 return value
def value(x):
 if isinstance(x,bool):return str(x).lower()
 if isinstance(x,str):return json.dumps(x,ensure_ascii=False)
 if isinstance(x,(int,float)):return repr(x)
 if isinstance(x,list):return '{'+','.join(value(a) for a in x)+'}'
 if isinstance(x,dict):return '{'+','.join(k+'='+value(v) for k,v in x.items())+'}'
 raise ValueError(x)
node={'Identifier':'C2CloudPrototype','Transform':{'Translation':{'Type':'StaticTranslation','Position':[1e14,0,0]}},'Renderable':{'Type':'RenderablePointCloud','File':source.as_posix(),'UseCaching':False,'Unit':'m','Texture':{'Enabled':False},'SizeSettings':{'ScaleExponent':7.1,'ScaleFactor':1.,'EnableMaxSizeControl':True,'MaxSize':.15},'Coloring':{'FixedColor':[.35,.8,.88]},'UseAdditiveBlending':False},'GUI':{'Name':'Protótipo10mil posições congeladas'}}
try:
 request=urllib.request.Request('http://127.0.0.1:4700/api/command',data=b'{"command":"atlas"}',headers={'Content-Type':'application/json'})
 json.load(urllib.request.urlopen(request,timeout=65))
 lua('openspace.addSceneGraphNode('+value(node)+');return {queued=true}')
 end=time.perf_counter()+20
 while time.perf_counter()<end:
  count=lua('return {count=openspace.propertyValue("Scene.C2CloudPrototype.Renderable.NumberOfDataPoints")}')['count']
  if count==10000:break
  time.sleep(.1)
 assert count==10000,count
 lua('openspace.navigation.setNavigationState({Anchor="C2CloudPrototype",Position={0,-8e9,6e9},Up={0,0,1}});return {ready=true}')
 with Page() as page:
  page.evaluate('(() => {const e=document.createElement("div");e.id="cloud-prototype-note";e.style="position:fixed;top:120px;right:35px;max-width:420px;padding:18px;background:#0b1925;color:#b4d5df;z-index:9999;border:1px solid #456174;font:16px sans-serif";e.textContent="Protótipo de renderização: 10.000 posições sem massa, congeladas em t=0,05 unidades do modelo. Um desenho agregado; sem evolução ou seleção individual nesta prova.";document.body.append(e)})()')
 time.sleep(2)
 subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name','cosmos2-cloud-static-prototype.png'],check=True,capture_output=True)
 report={'status':'isolated_frozen_10k_native_aggregate_draw_verified_not_installed','native_loaded_points':count,'single_point_cloud_draw':True,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'owner_pointer_preserved':pointer.read_bytes()==before,'scope':'Static render feasibility only. No live10k dynamics, selection, Session integration or formal performance acceptance.'}
 (ROOT/'evidence/cloud-native-prototype-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
finally:
 with Page() as page:page.evaluate('document.getElementById("cloud-prototype-note")?.remove()')
 lua('openspace.navigation.setNavigationState({Anchor="Earth",Position={-16000000,-17000000,10000000},Up={0,0,1}});if openspace.hasSceneGraphNode("C2CloudPrototype") then openspace.removeSceneGraphNode("C2CloudPrototype") end;return {clean=true}')
assert pointer.read_bytes()==before
