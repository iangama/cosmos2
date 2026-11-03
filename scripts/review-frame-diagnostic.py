"""Summarize instrumented native captures, preserving their diagnostic scope."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];label=sys.argv[1]
if not label.isalnum():raise ValueError('Label must be alphanumeric')
p=ROOT/('evidence/frame-diagnostic-'+label+'.json');r=json.loads(p.read_text());assert r.get('completed')
def array(value):return value if isinstance(value,list) else [value[str(i)] for i in range(1,len(value)+1)]
values=array(r['frames']['samples_s']);offset=0.;slow=[]
for i,v in enumerate(values):
 if i and v>.1:slow.append({'frame':i,'offset_s':offset,'duration_ms':v*1000})
 offset+=v
report={'diagnostic':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'scope':r['scope'],'frames_after_initial_interval':len(values)-1,'duration_s':sum(values[1:]),'maximum_interval_ms':max(values[1:])*1000,'over100ms':slow,'renderer_RTT_max_ms':max(s['renderer_RTT_ms'] for s in r['samples']),'CEF_longtasks':r['CEF']['longtasks'],'CEF_async_function_slow_samples':sorted(r['CEF']['functions'],key=lambda s:-s['duration_ms'])[:10]}
if 'stages' in r:
 stats=r['stages']['stats'];stats={str(i):x for i,x in enumerate(stats)} if isinstance(stats,list) else stats
 report['stages_maximum_ms']=sorted([{'slot':int(i),'name':s['name'],'maximum_ms':s['maximum_s']*1000,'mean_ms':s['total_s']/s['count']*1000,'samples':s['count']} for i,s in stats.items()],key=lambda s:-s['maximum_ms'])
 report['slow_stage_intervals']=[{**s,'name':stats[str(int(s['slot']))]['name']} for s in array(r['stages']['slow_intervals'])]
 report['stage_buffer_truncated']=r['stages']['truncated'];assert not report['stage_buffer_truncated']
(ROOT/('evidence/frame-diagnostic-'+label+'-review.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='CEF_async_function_slow_samples'},indent=2))
