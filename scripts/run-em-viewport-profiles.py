"""Sequential J profiles and independent audits; stop on any unfinished/refused job."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'evidence/em-viewport-profile-sequence.json'
assert not DEST.exists()
session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
assert session['emViewportCandidate']
report={'completed':False,'session':session,'jobs':[],'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
flags=['--topic-cleanup','--time-controls','--integration','--cloud-editor','--framing','--viewport']
jobs=[('128','benchmark-em128-new-runtime-native.py','review-em128-new-runtime-benchmark.py','native-em128-c212j128a','c212j128a'),
      ('potential','benchmark-em128-potential-native.py','review-em128-new-runtime-benchmark.py','native-em128-c212jpota','c212jpota'),
      ('cloud','benchmark-em-cloud-source128-native.py','review-em-cloud-source128-benchmark.py','native-emcloud-c212jsrca','c212jsrca')]


def persist():
    DEST.write_text(json.dumps(report,indent=2)+'\n')


try:
    for kind,runner,auditor,prefix,label in jobs:
        job={'kind':kind,'started':datetime.now(timezone.utc).isoformat(),'completed':False,'runner':runner,'auditor':auditor,'label':label}
        report['jobs'].append(job);persist()
        for phase,arguments in (('capture',[str(ROOT/'scripts'/runner),'--label',label,*flags]),('audit',[str(ROOT/'scripts'/auditor),label])):
            log=ROOT/'output'/f'em-viewport-{kind}-{phase}.log'
            assert not log.exists()
            print(json.dumps({'kind':kind,'phase':phase,'started':True,'log':str(log.relative_to(ROOT))}),flush=True)
            with log.open('w',encoding='utf-8') as out:
                child=subprocess.run([sys.executable,'-Xutf8',*arguments],cwd=ROOT,stdout=out,stderr=subprocess.STDOUT)
            job[phase+'_exit_code']=child.returncode;job[phase+'_log']=str(log.relative_to(ROOT));persist()
            if child.returncode:
                raise RuntimeError(kind+' '+phase+' failed; preserve attempt and inspect '+str(log))
        raw=json.loads((ROOT/'evidence'/(prefix+'.json')).read_bytes())
        review=json.loads((ROOT/'evidence'/(prefix+'-review.json')).read_bytes())
        assert raw['completed'] and raw['viewport_profile'] and review['accepted']
        job.update(completed=True,accepted=True,finished=datetime.now(timezone.utc).isoformat(),review=prefix+'-review.json')
        persist();print(json.dumps(job),flush=True)
    report['completed']=True
finally:
    persist()
