"""One controlled potential-D/cloud-B sequence, after real diagnostic collector preflights."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib
import json
import subprocess
import sys
import traceback

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'evidence/em-j-diagnostic-profile-sequence-20261023b.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    if DEST.exists():raise FileExistsError('Preserve previous sequence.')
    a=json.loads((ROOT/'evidence/em-native-preflight-jpdiag20261023a.json').read_text())
    b=json.loads((ROOT/'evidence/em-native-preflight-jpdiag20261023b.json').read_text())
    assert a['checks']['potential_three_routes_and_real_refusal_snapshot']
    assert b['accepted'] and b['checks']['cloud_three_routes_and_real_refusal_snapshot']
    session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert session['emViewportCandidate'] and session==a['session']==b['session']
    for preflight in [a,b]:
        for run in preflight['runs']:
            if not run['expected_refusal']:
                assert run['returncode']==0 and sha(ROOT/run['GPU_receipt'])==run['GPU_receipt_sha256']
    forks=json.loads((ROOT/'evidence/em-diagnostic-profile-forks-v2-20261023.json').read_text())
    for name,record in forks['records'].items():
        assert sha(ROOT/'scripts'/name)==record['original_sha256'] and sha(ROOT/record['fork'])==record['fork_sha256']
        assert record['all_other_text_and_AST_equal']
    memory=json.loads((ROOT/'evidence/em-diagnostic-memory-call-20261023.json').read_text())
    assert memory['accepted'] and memory['session']==session
    assert all(sha(ROOT/p)==h for p,h in memory['source_sha256'].items())
    flags=['--topic-cleanup','--time-controls','--integration','--cloud-editor','--framing','--viewport']
    jobs=[('potential','benchmark-em128-potential-native-diagnostic-v2.py','review-em128-new-runtime-benchmark-diagnostic.py','native-em128-c212jpotd','c212jpotd'),
        ('cloud','benchmark-em-cloud-source128-native-diagnostic-v2.py','review-em-cloud-source128-benchmark-diagnostic.py','native-emcloud-c212jsrcb','c212jsrcb')]
    for _,_,_,prefix,_ in jobs:
        if (ROOT/'evidence'/(prefix+'.json')).exists() or (ROOT/'evidence'/(prefix+'-review.json')).exists():raise FileExistsError(prefix)
    report={'schema':1,'session':session,'preflight_potential_scope':'jpdiag20261023a potential passed; overall A incomplete on cloud harness pause fields',
        'preflight_cloud_scope':'jpdiag20261023b cloud accepted after harness-only fix',
        'completed':False,'accepted':False,'jobs':[],'script_sha256':sha(Path(__file__)),
        'scope':'V2 runner passes the explicit session to the existing Windows memory helper; C remains incomplete. One controlled repeat per remaining J profile with diagnostic collectors only; original criteria and immutable J source/runtime retained. Stop on any failed/incomplete capture or audit. No automatic promotion.'}
    def persist():DEST.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    persist()
    try:
        for family,runner,auditor,prefix,label in jobs:
            job={'kind':family,'started_utc':datetime.now(timezone.utc).isoformat(),'runner':runner,'auditor':auditor,
                'label':label,'completed':False,'accepted':False}
            report['jobs'].append(job);persist()
            for phase,arguments in [('capture',[runner,'--label',label,*flags]),('audit',[auditor,label])]:
                log=ROOT/'output'/('em-j-diagnostic-'+label+'-'+phase+'.log')
                if log.exists():raise FileExistsError(log)
                print(json.dumps({'kind':family,'phase':phase,'label':label,'log':log.relative_to(ROOT).as_posix()}),flush=True)
                with log.open('w',encoding='utf-8') as out:
                    process=subprocess.run([sys.executable,'-Xutf8',str(ROOT/'scripts'/arguments[0]),*arguments[1:]],cwd=ROOT,stdout=out,stderr=subprocess.STDOUT)
                job[phase+'_exit_code']=process.returncode;job[phase+'_log']=log.relative_to(ROOT).as_posix();persist()
                if process.returncode:raise RuntimeError(family+' '+phase+' failed; inspect preserved log.')
            raw=json.loads((ROOT/'evidence'/(prefix+'.json')).read_text())
            audit=json.loads((ROOT/'evidence'/(prefix+'-review.json')).read_text())
            assert raw['completed'] and raw['viewport_profile'] and audit['accepted']
            job.update(completed=True,accepted=True,finished_utc=datetime.now(timezone.utc).isoformat(),review=prefix+'-review.json');persist()
        report['completed']=report['accepted']=True
    except Exception:report['failure']=traceback.format_exc()
    finally:persist()
    print(json.dumps({'receipt':DEST.relative_to(ROOT).as_posix(),'accepted':report['accepted'],'failure':report.get('failure')}),flush=True)
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
