"""Prepare the actual HTTP/worker gate in0.27.0, preserving existing native app."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
target=ROOT/'scripts/verify-is6-expanded-journey-http.py';assert not target.exists()
text=(ROOT/'scripts/verify-is6-dynamics16-http-v3.py').read_text(encoding='utf8')
text=text.replace('output/is6-dynamics16-product0.26.1/app','output/is6-expanded-journey-product0.27.0/app')
text=text.replace('is6-dynamics16-http-','is6-expanded-journey-http-')
text=text.replace("f'evidence/is6-dynamics16-service-{label}.json'","f'evidence/is6-expanded-journey-service-{label}.json'")
anchor="        worker=helpers.Worker(folder/'sessions')"
assert text.count(anchor)==1;text=text.replace(anchor,"        helpers.APP=APP\n"+anchor)
anchor="        initial=copy.deepcopy(worker.latest)"
assert text.count(anchor)==1;text=text.replace(anchor,anchor+"\n        status,saved=call('/api/command',dict(command='save'))\n        assert status==200 and saved['ok']")
anchor="        assert all(sha(ROOT/n)==s for n,s in protected.items())"
extra="        status,restored=call('/api/command',dict(command='load'))\n        assert status==200 and restored['ok'] and len(worker.latest['bodies'])==16\n        assert worker.latest['bodies']==initial['bodies'] and worker.latest['dynamics16']==initial['dynamics16']\n        assert worker.latest['edit_token']!=initial['edit_token'] and worker.latest['paused']\n        report['successes'].append(dict(name='HTTP exact sixteen restore after legacy copies',bodies=16,new_token=True))\n"
assert text.count(anchor)==1;text=text.replace(anchor,extra+anchor)
compile(text,str(target),'exec');target.write_text(text,encoding='utf8')
print(json.dumps(dict(prepared=True,product_changed=False,actual_worker='0.27.0',renderer_substituted=True)))
