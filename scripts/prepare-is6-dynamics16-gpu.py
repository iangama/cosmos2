"""Derive a strict moving-clock PDH collector/auditor without editing sealed readers."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
script=ROOT/'scripts'
replacements={'collect_gpu_pdh_v3.py':'collect_gpu_pdh_dynamics16.py',
              'gpu_pdh_audit_v3.py':'gpu_pdh_audit_dynamics16.py',
              'gpu_pdh_audit_v2.py':'gpu_pdh_audit_dynamics16_base.py'}
for old,new in replacements.items():assert not (script/new).exists()
base=(script/'gpu_pdh_audit_v2.py').read_text(encoding='utf8')
helper='''

def same_scenario(actual, initial):
    if not isinstance(actual,dict) or not isinstance(initial,dict) or actual.keys()!=initial.keys():
        return False
    for row in [actual,initial]:
        t=row.get('physical_time')
        if type(t) not in (int,float) or not math.isfinite(t) or t<0:
            return False
    if {k:v for k,v in actual.items() if k!='physical_time'} != {k:v for k,v in initial.items() if k!='physical_time'}:
        return False
    return actual['physical_time']==initial['physical_time'] if initial['paused'] else actual['physical_time']>=initial['physical_time']
'''
base+=helper
for old,new in [("require(scenario == report['scenario_after'],'Final renderer/scenario changed')", "require(same_scenario(report['scenario_after'],scenario),'Final renderer/scenario changed')"),
                ("require(row['scenario'] == scenario,'Renderer/scenario changed during GPU sampling')", "require(same_scenario(row['scenario'],scenario),'Renderer/scenario changed during GPU sampling')")]:
    assert base.count(old)==1;base=base.replace(old,new)
anchor="    for index in range(1,len(rows)):\n"
assert base.count(anchor)==1
extra="    physical_times=[row['scenario']['physical_time'] for row in rows]\n    require(all(scenario['physical_time']<=t<=report['scenario_after']['physical_time'] for t in physical_times),'Physical times outside before/after bracket')\n    if scenario['paused']:\n        require(all(t==scenario['physical_time'] for t in physical_times),'Paused clock changed')\n    elif len(rows)>1:\n        require(all(b>a for a,b in zip(physical_times,physical_times[1:])),'Moving clock did not progress strictly between1Hz samples')\n"
base=base.replace(anchor,extra+anchor)
texts={'gpu_pdh_audit_dynamics16_base.py':base}
text=(script/'gpu_pdh_audit_v3.py').read_text(encoding='utf8').replace('import gpu_pdh_audit_v2 as base','import gpu_pdh_audit_dynamics16_base as base')
texts['gpu_pdh_audit_dynamics16.py']=text
text=(script/'collect_gpu_pdh_v3.py').read_text(encoding='utf8')
for old,new in replacements.items():text=text.replace(old,new).replace(old.removesuffix('.py')+' as ',new.removesuffix('.py')+' as ')
old="if row['scenario'] != report['scenario_before']:";assert text.count(old)==1
text=text.replace(old,"if not audit.base.same_scenario(row['scenario'], report['scenario_before']):")
texts['collect_gpu_pdh_dynamics16.py']=text
for name,text in texts.items():compile(text,name,'exec');(script/name).write_text(text,encoding='utf8')
print(json.dumps(dict(prepared=True,files=list(texts),measurement_executed=False)))
