"""A stiff physical orbit must yield to pause; radial collapse stops at domain boundary."""
from pathlib import Path
import json,math,queue,subprocess,sys,tempfile,threading,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from physics import PHYSICAL_SCALE as U
with tempfile.TemporaryDirectory() as folder:
 process=subprocess.Popen([sys.executable,'-X','utf8','-u',str(ROOT/'app/worker.py'),'--storage',folder],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 messages=queue.Queue();latest=None;serial=0
 def reader():
  for line in process.stdout:messages.put(json.loads(line))
 threading.Thread(target=reader,daemon=True).start()
 def wait(predicate,timeout=5):
  global latest
  end=time.perf_counter()+timeout
  while time.perf_counter()<end:
   message=messages.get(timeout=max(.01,end-time.perf_counter()))
   if message['type']=='snapshot':latest=message
   if predicate(message):return message
  raise TimeoutError('Worker response')
 def command(action,**fields):
  global serial
  serial+=1;process.stdin.write(json.dumps({'command':action,'id':serial,**fields})+'\n');process.stdin.flush()
  result=wait(lambda m:m.get('id')==serial and m['type'] in ('ack','error'))
  assert result['type']=='ack',result
  return result
 def guard():return {'system_id':latest['system_id'],'edit_token':latest['edit_token'],'revision':latest['revision'],'expected_time':latest['time'],'frame':latest['contract']['frame']}
 try:
  wait(lambda m:m['type']=='snapshot')
  command('new_system',**guard(),name='Compact primary',mass_kg=2e-12*U['mass_unit_kg'],position_m=[0,0,0],velocity_m_s=[0,0,0])
  command('create_body',**guard(),name='Compact companion',mass_kg=2e-12*U['mass_unit_kg'],position_m=[10,0,0],velocity_m_s=[0,math.sqrt(4e-12/1e-8)*U['velocity_unit_m_s'],0])
  command('rate',value=10);command('resume');yielded=wait(lambda m:m['type']=='snapshot' and m['integration_yielded'],timeout=5)
  began=time.perf_counter();command('pause');latency=(time.perf_counter()-began)*1000
  assert latest['paused'] and latency<500 and all(math.isfinite(v) for b in latest['bodies'] for key in ('position','velocity') for v in b[key]),latency
  command('save');command('load');assert latest['paused']
  command('new_system',**guard(),name='Radial primary',mass_kg=U['mass_unit_kg'],position_m=[0,0,0],velocity_m_s=[0,0,0])
  command('create_body',**guard(),name='Radial probe',mass_kg=1e-8*U['mass_unit_kg'],position_m=[1e9,0,0],velocity_m_s=[0,0,0]);command('resume')
  stopped=wait(lambda m:m['type']=='snapshot' and m['paused'] and m['integration_notice'],timeout=10)
  assert all(math.isfinite(v) for b in stopped['bodies'] for key in ('position','velocity') for v in b[key])
  separation=math.dist(*[b['position'] for b in stopped['bodies']])*1e9;assert 0<separation<=.001
  command('save');command('reset',count=32);assert latest['integration_notice'] is None
  report={'compact_binary_yielded':True,'pause_latency_ms':latency,'yield_snapshot_compute_ms':yielded['compute_ms'],'yield_model_time_canonical':yielded['time'],'no_runtime_callback_in_checkpoint':True,'radial_collapse_paused_finite':True,'radial_stop_separation_m':separation,'domain_notice':stopped['integration_notice'],'reset_clears_notice':True}
 finally:
  if process.poll() is None:
   command('quit');process.wait(timeout=5)
  stderr=process.stderr.read();assert not stderr,stderr
(ROOT/'evidence/worker-preemption-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
