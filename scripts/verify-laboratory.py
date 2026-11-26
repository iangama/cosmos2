"""Exercise the live HTTP->worker->OpenSpace integration and persistent session."""
from pathlib import Path
import json
import time
import urllib.request
ROOT=Path(__file__).resolve().parents[1]
def state():
    return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/state',timeout=5))
def command(name,**payload):
    request=urllib.request.Request('http://127.0.0.1:4700/api/command',
        data=json.dumps({'command':name,**payload}).encode(),headers={'Content-Type':'application/json'})
    result=json.load(urllib.request.urlopen(request,timeout=15))
    assert result['ok'],result
    return result['ack']
command('enter');command('reset',count=32);command('resume')
time.sleep(1)
command('pause')
first=state()['physics'];assert first['time']>0 and first['paused']
command('set_mass',body='p0',mass=2)
changed=state()['physics'];assert changed['revision']==1 and changed['bodies'][0]['mass']==2
command('save');command('resume');time.sleep(.5);command('pause')
assert state()['physics']['time']>changed['time']
command('load')
loaded=state()['physics'];assert loaded['bodies']==changed['bodies'] and loaded['time']==changed['time'] and loaded['paused']
command('reset',count=128);assert len(state()['physics']['bodies'])==128
command('resume');time.sleep(.5);command('pause')
assert state()['physics']['time']>0
command('atlas');assert state()['mode']=='atlas' and state()['physics']['paused']
command('enter');assert state()['mode']=='experiment'
command('reset',count=32)
result={'entered_lab':True,'pause_resume':True,'mass_intervention':True,
        'checkpoint_restored_exact_body_state':True,'p128_render_scene':True,
        'atlas_round_trip':True,'final_state':'P32 paused','scope':'functional smoke check'}
(ROOT/'evidence'/'laboratory-check.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
