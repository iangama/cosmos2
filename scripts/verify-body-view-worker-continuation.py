"""Finish the pending worker branch/restart checks without repeating16 accepted roundtrips."""
from pathlib import Path
import copy
import hashlib
import json
import shutil
import traceback
import zipfile
from importlib.machinery import SourceFileLoader

ROOT=Path(__file__).resolve().parents[1]
h=SourceFileLoader('view_checkpoint_helpers',str(ROOT/'scripts/verify-body-view-checkpoints.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    folder=ROOT/'output/is3-view-worker-20261024c';receipt=ROOT/'evidence/is3-view-worker-20261024c.json'
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve continuation evidence.')
    previous=ROOT/'evidence/is3-view-checkpoints-20261024b.json';prior=json.loads(previous.read_text())
    assert len(prior['roundtrips'])==16 and all(prior['checks'].values())
    assert 'multiple values' in prior['failure']
    for name,digest in prior['source_sha256'].items():
        if name.startswith('output/is3-body-view-product/app/'):assert sha(ROOT/name)==digest
    folder.mkdir();storage=folder/'sessions'
    shutil.copytree(ROOT/'output/is3-view-checkpoints-20261024b/worker',storage)
    paths=[p for p in h.APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    paths += [Path(__file__).resolve(),ROOT/'scripts/verify-body-view-checkpoints.py',previous]
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for p in paths:archive.write(p,p.relative_to(ROOT).as_posix())
    report={'schema':1,'accepted':False,'completed':False,'source_sha256':hashes,'checks':{}}
    worker=None
    try:
        worker=h.Worker(storage);worker.call('load');saved=copy.deepcopy(worker.latest)
        metadata=saved['body_field_view'];assert metadata['layer']['visible'] is False
        phase=lambda p:(p['time'],p['bodies'],p['interventions'],p['atlas_initial'])
        branch=worker.call('create_branch',**{**h.helpers.guard(saved),'name':'worker-view','renderer_view':metadata})['result']
        worker.call('load_branch',**{**h.helpers.guard(worker.latest),'branch_id':branch['id']})
        assert phase(worker.latest)==phase(saved) and worker.latest['body_field_view']==metadata
        report['checks']['actual_worker_branch_phase_and_view_exact']=True
        worker.close();worker=h.Worker(storage);worker.call('load')
        assert phase(worker.latest)==phase(saved) and worker.latest['body_field_view']==metadata
        report['checks']['new_worker_process_restores_saved_phase_and_view']=True
        worker.close();worker=None
        assert all(sha(ROOT/name)==digest for name,digest in hashes.items())
        report.update(accepted=True,completed=True)
    except Exception:report['failure']=traceback.format_exc()
    finally:
        if worker is not None:worker.close()
        receipt.write_text(json.dumps(report,indent=2)+'\n')
    if report['accepted']:
        summary=ROOT/'evidence/is3-view-checkpoints-summary-20261024.json';assert not summary.exists()
        summary.write_text(json.dumps({'schema':1,'accepted':True,'completed':True,
            'parts':[{'path':previous.relative_to(ROOT).as_posix(),'sha256':sha(previous),'accepted_checks_only':prior['checks']},
                     {'path':receipt.relative_to(ROOT).as_posix(),'sha256':sha(receipt),'checks':report['checks']}],
            'roundtrips':16,'save_load_refusals':8,'unchanged_candidate_source_sha256':{k:v for k,v in hashes.items() if k.startswith('output/is3-body-view-product/app/')},
            'scope':'B passed16 checkpoint/branch combinations,8 transactional refusals and old-copy migration; B remained incomplete from a harness argument-name collision. C completed worker branch/new-process checks with identical product sources. No native renderer restart or performance acceptance.'},indent=2)+'\n')
    print(json.dumps({'accepted':report['accepted'],'checks':report['checks'],'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
