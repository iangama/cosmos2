"""Live-registry property lookup semantics and pure-read microdiagnostic."""
from pathlib import Path
import argparse,hashlib,json,time,urllib.request
from websockets.sync.client import connect
ROOT=Path(__file__).resolve().parents[1];parser=argparse.ArgumentParser();parser.add_argument('--label',choices=['baseline','query'],required=True);args=parser.parse_args()
def command(name,**kw):return json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:4700/api/command',data=json.dumps({'command':name,**kw}).encode(),headers={'Content-Type':'application/json'}),timeout=65))
def physics():return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/state'))['physics']
pointer=ROOT/'user/sessions/latest.json';saved=pointer.read_bytes();created=[];serial=0
ws=connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=1,ping_interval=None);ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
def lua(script):
 global serial
 serial+=1;ws.send(json.dumps({'topic':serial,'type':'luascript','payload':{'script':script,'return':True}}));reply=json.loads(ws.recv(timeout=25));assert reply.get('topic')==serial,reply
 result=reply.get('payload',{}).get('1');assert result is not None,reply;return result
try:
 command('enter');p=physics()
 if len(p['bodies'])!=256:command('reset',count=256)
 command('pause');p=physics();frozen={k:p[k] for k in ('bodies','time','conservation','revision','system_id','edit_token')}
 fallback=lua('return {visible=openspace.propertyValue("Modules.CefWebGui.Visible"),log=openspace.propertyValue("RenderEngine.ShowLog")}')
 for i in range(8):
  identifier='C2QueryProbe'+str(i);created.append(identifier)
  assert lua('return {ok=openspace.hasProperty("Scene.'+identifier+'.Translation.Position")}')['ok'] is False
  lua('openspace.addSceneGraphNode({Identifier="'+identifier+'",Transform={Translation={Type="StaticTranslation",Position={1,2,3}}}});return {ok=true}')
  actual=lua('openspace.setPropertyValueSingle("Scene.'+identifier+'.Translation.Position",{'+str(i+4)+',-8,16});return {v=openspace.propertyValue("Scene.'+identifier+'.Translation.Position"),ok=openspace.hasProperty("Scene.'+identifier+'.Translation.Position")}')
  values=actual['v'];values=[values[str(k)] for k in (1,2,3)] if isinstance(values,dict) else values;assert actual['ok'] and values==[i+4,-8,16],actual
  lua('openspace.removeSceneGraphNode("'+identifier+'");return {ok=true}')
  missing=lua('local ok,v=pcall(openspace.propertyValue,"Scene.'+identifier+'.Translation.Position");return {ok=ok,is_nil=v==nil,exists=openspace.hasProperty("Scene.'+identifier+'.Translation.Position")}');assert missing['is_nil'] and not missing['exists'],missing
  lua('openspace.addSceneGraphNode({Identifier="'+identifier+'",Transform={Translation={Type="StaticTranslation",Position={32,64,128}}}});return {ok=true}')
  fresh=lua('return {v=openspace.propertyValue("Scene.'+identifier+'.Translation.Position")}')['v'];fresh=[fresh[str(k)] for k in (1,2,3)] if isinstance(fresh,dict) else fresh;assert fresh==[32,64,128]
 assert lua('local ok,v=pcall(openspace.propertyValue,"Scene.C2QueryProbe0.NoSuchProperty");return {is_nil=v==nil}')['is_nil']
 assert fallback==lua('return {visible=openspace.propertyValue("Modules.CefWebGui.Visible"),log=openspace.propertyValue("RenderEngine.ShowLog")}')
 uris=['Scene.'+b['scene_node']+'.Translation.Position' for b in p['bodies']]
 table='{'+','.join(json.dumps(u) for u in uris)+'}'
 timings=[]
 for repeat in range(5):
  lua('openspace.cosmos2BeginStageTrace();return {ok=true}')
  result=lua('local uris='+table+';local sum=0;for r=1,32 do for _,u in ipairs(uris) do local p=openspace.propertyValue(u);sum=sum+p[1] end end;return {sum=sum}')
  stages=lua('return openspace.cosmos2EndStageTrace()');stat=stages['stats']['22'];timings.append({'lua_total_ms':stat['total_s']*1000,'script_count':stat['count'],'reads':8192,'sum':result['sum']})
 after=physics();assert {k:after[k] for k in frozen}==frozen and pointer.read_bytes()==saved
 report={'status':'scene_property_semantics_verified','runtime_label':args.label,'create_set_get_remove_recreate_same_identity_cases':8,'fallback_modules_and_render_engine_unchanged':True,'missing_node_and_property_return_no_value':True,'scientific_phase_reference_owner_pointer_preserved':True,'pure_read_diagnostic':timings,'scope':'Native API semantics and instrumented microdiagnostic. Formal256 frame profile separate.'}
 (ROOT/f'evidence/scene-query-{args.label}-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
finally:
 for identifier in reversed(created):lua('if openspace.hasSceneGraphNode("'+identifier+'") then openspace.removeSceneGraphNode("'+identifier+'") end;return {ok=true}')
 ws.close()
assert pointer.read_bytes()==saved
