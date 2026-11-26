"""Attribute EM128 CPU cost without changing the frozen numerical kernel."""
from pathlib import Path
import cProfile
import hashlib
import itertools
import json
import pstats
import sys
import time

ROOT=Path(__file__).resolve().parents[1];variant='-v03' if '--v03' in sys.argv else '';EM=ROOT/('output/c212-em-v03-staging' if variant else 'output/c212-em-product/em');sys.path.insert(0,str(EM))
from em_experiment import Experiment,generation
from em_mutual import System,Phase

target=ROOT/('evidence/em128-kernel-cost'+variant+'.json');assert not target.exists()
fixture=json.loads((ROOT/'evidence/em128-native-preprofile.json').read_text())['fixture'];q=fixture['abs_charge_C']
xs=tuple(itertools.islice(itertools.product((-4,-2,0,2,4),repeat=3),125))+((-6,0,0),(6,0,0),(0,6,0))
ex=Experiment('mutual_electrostatic',System(tuple(map(str,range(128))),tuple(q*(-1)**i for i in range(128)),(1.,)*128,(.01,)*128),Phase(xs,((0.,0.,0.),)*128),.001,{'acting':True})
profile=cProfile.Profile();began=time.perf_counter();profile.enable();ex.advance(1000);profile.disable();elapsed=time.perf_counter()-began
raw=ROOT/('evidence/em128-kernel-cost'+variant+'.pstats');profile.dump_stats(str(raw));stats=pstats.Stats(profile)
rows=[]
for (file,line,name),(primitive,calls,own,cumulative,callers) in stats.stats.items():
    rows.append({'file':file,'line':line,'name':name,'calls':calls,'primitive_calls':primitive,'self_s':own,'cumulative_s':cumulative})
report={'status':'EM128_kernel_cost_attributed_without_scientific_source_changes','steps':1000,'elapsed_wall_s_with_profiler':elapsed,
        'model_time_s':ex.phase.time_s,'top_self_time':sorted(rows,key=lambda r:r['self_s'],reverse=True)[:20],
        'top_cumulative_time':sorted(rows,key=lambda r:r['cumulative_s'],reverse=True)[:20],
        'scientific_generation':generation(),'pstats_file':str(raw.relative_to(ROOT)),'pstats_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),
        'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'scope':'Isolated instrumented CPU attribution only; profiler overhead prevents comparison with the native requested-rate profile. No solver optimization, new generation, migration or performance approval.'}
target.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'elapsed_s':elapsed,'top_self_time':report['top_self_time'][:8],'top_cumulative_time':report['top_cumulative_time'][:5]},indent=2))
