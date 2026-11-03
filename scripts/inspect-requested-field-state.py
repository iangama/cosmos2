from pathlib import Path
import json
import urllib.request
from cef_page import Page
from importlib.util import spec_from_file_location,module_from_spec
ROOT=Path(__file__).resolve().parents[1]
spec=spec_from_file_location('engine_command',ROOT/'scripts/engine-command.py')
module=module_from_spec(spec);spec.loader.exec_module(module)
s=json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/state',timeout=10))
report={k:s.get(k) for k in ('mode','error','fields_visible','last_error')}
p=s.get('physics');report['physics']={k:p.get(k) for k in ('time','paused','revision','count')} if p else None
meshes=(s.get('fields_preview') or {}).get('render',{}).get('meshes',[])
report['meshes']=meshes
if meshes:
    report['native']=module.execute('return {enabled={'+','.join('openspace.propertyValue('+json.dumps('Scene.'+m['node']+'.Renderable.Enabled')+')' for m in meshes)+'}}')
(ROOT/'evidence/requested-field-toggle-first-attempt-diagnostic.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
