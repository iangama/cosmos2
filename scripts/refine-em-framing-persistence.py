"""Guard and save the new canvas preferences in view3; legacy1/2 stay explicit."""
from pathlib import Path
import ast
import hashlib
import json
ROOT=Path(__file__).resolve().parents[1];I=ROOT/'output/c212-em-framing-product'
dest=ROOT/'evidence/em-framing-persistence-prepared.json';assert not dest.exists()
outputs={}
def change(s,a,b):assert s.count(a)==1,a;return s.replace(a,b)
outputs[I/'app/em_canvas_view.py']="""\"\"\"Graphic canvas preferences only; no scientific state or integration settings.\"\"\"
from copy import deepcopy
DEFAULT={'scope':'layers','zoom':1.}
def validate(value):
    if not isinstance(value,dict) or set(value)!=set(DEFAULT):raise ValueError('Preferências do mapa inválidas.')
    if value['scope'] not in ('matter','layers') or type(value['scope']) is not str:raise ValueError('Enquadramento do mapa inválido.')
    if type(value['zoom']) not in (int,float) or value['zoom'] not in (1.,1.5,2.,4.):raise ValueError('Ampliação do mapa inválida.')
    return deepcopy(value)
"""
s=(I/'app/em_native.py').read_text();s=change(s,'from itertools import product','from itertools import product\nfrom em_canvas_view import DEFAULT as CANVAS_DEFAULT, validate as validate_canvas_view')
s=change(s,'        self.nodes={};self.confirmation=None;self.map=None;self.lines=None;self.error=None;self.previous=None','        self.nodes={};self.confirmation=None;self.map=None;self.lines=None;self.error=None;self.previous=None\n        self.canvas_view=deepcopy(CANVAS_DEFAULT)')
s=change(s,"value['schema'] not in (1,2)","value['schema'] not in (1,2,3)")
s=change(s,"({'potential'} if value['schema']==2 else set())","({'potential'} if value['schema']>=2 else set())|({'canvas_view'} if value['schema']==3 else set())")
s=change(s,"        if value['schema']==2:\n            from em_potential_native import validate_config\n            validate_config(value['potential'])","        if value['schema']>=2:\n            from em_potential_native import validate_config\n            validate_config(value['potential'])\n        if value['schema']==3:validate_canvas_view(value['canvas_view'])")
s=change(s,"self.validate_view({'schema':2,'frame':'EM_SI_FIXED_INERTIAL'","self.validate_view({'schema':3,'canvas_view':deepcopy(self.canvas_view),'frame':'EM_SI_FIXED_INERTIAL'")
s=change(s,"            self.potential.configure(value.get('potential',DEFAULT))","            self.potential.configure(value.get('potential',DEFAULT))\n            self.canvas_view=validate_canvas_view(value.get('canvas_view',CANVAS_DEFAULT))")
s=change(s,"'potential':self.potential.status(),'error':self.error}","'potential':self.potential.status(),'canvas_view':deepcopy(self.canvas_view),'error':self.error}")
ast.parse(s);outputs[I/'app/em_native.py']=s
s=(I/'app/em_laboratory.py').read_text()
key="            if name=='measure_particle':"
s=change(s,key,"""            if name=='configure_canvas_view':
                required={'command','system_id','edit_token','revision','frame','expected_time_s','changes'}
                if set(value)!=required:raise ValueError('Guardas exatas do mapa requeridas.')
                self._worker({'command':'snapshot'});state=self._current();t=value['expected_time_s']
                valid_time=type(t) in (int,float) and math.isfinite(t) and (t==state['time_s'] if state['paused'] else 0<=t<=state['time_s'])
                if not valid_time or type(value['revision']) is not int or any(value[k]!=state[k] for k in ('system_id','edit_token','revision','frame')):raise ValueError('Preferência do mapa obsoleta; consulte o estado confirmado.')
                from em_canvas_view import validate
                changes=value['changes']
                if not isinstance(changes,dict) or not changes or not set(changes)<={'scope','zoom'}:raise ValueError('Alterações do mapa inválidas.')
                with self.native.lock:self.native.canvas_view=validate({**self.native.canvas_view,**changes})
                return {'type':'ack','command':name,'time_s':state['time_s'],'canvas_view':deepcopy(self.native.canvas_view)}
"""+key)
s=change(s,"                    if name=='load' and view is not None:","                    if name=='load' and view is None:\n                        from em_canvas_view import DEFAULT\n                        self.native.canvas_view=deepcopy(DEFAULT)\n                    if name=='load' and view is not None:")
ast.parse(s);outputs[I/'app/em_laboratory.py']=s
s=(I/'app/ui/em/app.js').read_text();s=change(s,"value.native_view_source_schema===1?'Vista anterior retomada; preferências do potencial iniciadas no padrão.':","value.native_view_source_schema===1?'Vista anterior retomada; potencial e mapa iniciados no padrão.':value.native_view_source_schema===2?'Vista anterior retomada; mapa com enquadramento e ampliação no padrão.':")
outputs[I/'app/ui/em/app.js']=s
s=(ROOT/'scripts/em-framing-ui/frame.js').read_text()
s=change(s,"function makeCanvasProjection(width,height){","function syncCanvasPreferences(){\n  const view=nativeState?.canvas_view;if(!view)return;canvasFrameScope=view.scope;canvasZoom=view.zoom;$('canvas-zoom').value=String(canvasZoom);\n}\nfunction makeCanvasProjection(width,height){\n  syncCanvasPreferences();")
s=change(s,"  canvasFrameScope=layers?'layers':'matter';canvasZoom=1;$('canvas-zoom').value='1';draw();","  await command('configure_canvas_view',{...guard(),changes:{scope:layers?'layers':'matter',zoom:1}});draw();")
s=change(s,"$('canvas-zoom').onchange=()=>{canvasZoom=Number($('canvas-zoom').value);draw();};","$('canvas-zoom').onchange=()=>{const zoom=Number($('canvas-zoom').value);run(()=>command('configure_canvas_view',{...guard(),changes:{zoom}}));};")
s=change(s,"  previousNativeRender();","  syncCanvasPreferences();previousNativeRender();")
outputs[ROOT/'scripts/em-framing-ui/frame.js']=s;outputs[I/'app/ui/em/frame.js']=s
for p,s in outputs.items():p.write_text(s)
report={'status':'I_canvas_preferences_guarded_and_view3_persistence_prepared','source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in outputs},
        'scope':'Native view3 adds graphic canvas scope/zoom. Legacy1/2 validated without rewriting and restored with explicit defaults. No scientific/worker change; runtime tests required.'}
dest.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'files':len(outputs)}),flush=True)
