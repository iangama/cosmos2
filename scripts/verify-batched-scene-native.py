"""All256 positions, stale packets, topology rebinding and clear of cached URIs."""
from pathlib import Path
import hashlib,json,time,urllib.request
from websockets.sync.client import connect
import numpy as np
ROOT=Path(__file__).resolve().parents[1];serial=0;pointer=ROOT/'user/sessions/latest.json';saved=pointer.read_bytes()
def command(action,**kw):return json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:4700/api/command',data=json.dumps({'command':action,**kw}).encode(),headers={'Content-Type':'application/json'}),timeout=65))
def physics():return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/state'))['physics']
def guard(p):return {k:p[k] for k in ('system_id','edit_token','revision')}|{'expected_time':p['time'],'frame':p['contract']['frame']}
ws=connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=1,ping_interval=None);ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
def lua(code):
 global serial
 serial+=1;ws.send(json.dumps({'topic':serial,'type':'luascript','payload':{'script':code,'return':True}}));r=json.loads(ws.recv(timeout=20));assert r.get('topic')==serial,r;assert '1' in r.get('payload',{}),r;return r['payload']['1']
def poses(p):
 uris='{'+','.join(json.dumps('Scene.'+b['scene_node']+'.Translation.Position') for b in p['bodies'])+'}'
 rows=lua('local r={};for i,u in ipairs('+uris+') do r[i]=openspace.propertyValue(u) end;return r')
 rows=[rows[str(i)] for i in range(1,len(rows)+1)] if isinstance(rows,dict) else rows
 return np.array([[row[str(i)] for i in (1,2,3)] if isinstance(row,dict) else row for row in rows])
def verify(p):
 expected=np.array([b['position'] for b in p['bodies']])*p['physical_scale']['length_unit_m'];deadline=time.perf_counter()+10
 while True:
  actual=poses(p);difference=float(np.max(np.abs(actual-expected)))
  if difference<=.001:return difference,actual
  if time.perf_counter()>deadline:raise AssertionError(difference)
  time.sleep(.05)
def stale(p,topology):
 before=poses(p);row='{'+','.join('{0,0,0}' for b in p['bodies'])+'}'
 result=lua('local ok=pcall(__c2LabPositions,'+','.join([json.dumps(p['system_id']),json.dumps(p['edit_token']),str(topology),row,'{0,0,0}','{0,0,0}','nil'])+');return {ok=ok}')
 assert not result['ok'] and np.array_equal(poses(p),before),result
try:
 command('enter');command('reset',count=256);p=physics();error,actual=verify(p);frozen=p['bodies'];stale(p,-1);assert physics()['bodies']==frozen
 stats=lua('local counts={markers=0,shapes=0,axes=0};local nodes={'+','.join('{'+','.join(json.dumps(b[k]) for k in ('scene_node','shape_node','spin_node'))+'}' for b in p['bodies'])+'};for _,n in ipairs(nodes) do if openspace.propertyValue("Scene."..n[1]..".Renderable.Enabled") then counts.markers=counts.markers+1 end;if openspace.hasSceneGraphNode(n[2]) then counts.shapes=counts.shapes+1 end;if openspace.hasSceneGraphNode(n[3]) then counts.axes=counts.axes+1 end end;return counts');assert stats=={'markers':256,'shapes':0,'axes':0},stats
 removed=p['bodies'][-1]['id'];command('remove_body',**guard(p),body=removed);p=physics();assert len(p['bodies'])==255;verify(p)
 command('create_body',**guard(p),name='Reposição de identidade',mass_kg=1e-8*p['physical_scale']['mass_unit_kg'],position_m=[1e11,1e11,0],velocity_m_s=[0,0,0]);p=physics();assert len(p['bodies'])==256 and removed not in [b['id'] for b in p['bodies']]
 rebound_error,_=verify(p);stale(p,0)
 before=physics();command('atlas');assert lua('return {clear=__c2LabPositions==nil}')['clear'];assert pointer.read_bytes()==saved
 report={'status':'batched_native_positions_verified','all256_native_position_max_error_m':error,'native_default_components':stats,'remove_recreate_identity_native_max_error_m':rebound_error,'stale_topology_packets_rejected_before_mutation':True,'new_identity_not_reassigned_to_old_body':True,'clear_releases_binding':True,'owner_pointer_preserved':True,'scope':'Bridge/native semantics; formal frame profile separate'}
 (ROOT/'evidence/batched-scene-native-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
finally:ws.close()
assert pointer.read_bytes()==saved
