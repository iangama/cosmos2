"""Repair only the scale fixture that exceeded the predeclared coordinate budget."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import sys
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/c214-point-lens-offline-20261121b.json'
FOLDER=ROOT/'output/c214-point-lens-scaling-20261121b'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert not OUT.exists() and not FOLDER.exists();FOLDER.mkdir()
    prior_path=ROOT/'evidence/c214-point-lens-offline-20261121a.json';prior=json.loads(prior_path.read_text())
    assert prior['completed'] and not prior['accepted']
    failed=[c for c in prior['checks'] if not c['passed']]
    assert len(failed)==1 and failed[0]['name']=='joint-length-GM-scaling-and-translated-input-resolution'
    assert 'Coordenada fora do orçamento' in failed[0]['failure']
    assert all(sha(ROOT/n)==seal for n,seal in prior['source_sha256'].items())
    sources=prior['source_sha256']|{prior_path.relative_to(ROOT).as_posix():sha(prior_path),Path(__file__).relative_to(ROOT).as_posix():sha(Path(__file__))}
    recipe=dict(source_sha256=sources,joint_scales=[2.**-10,2.**10],translation_m=[2.**40,-2.**45,2.**50],
      reason='Original upper scale2**20 put source beyond1e25m and was correctly refused. The corrected fixture uses in-domain scales; numerical/physical acceptance bounds are unchanged. Six successful original groups remain referenced, not rerun.')
    (FOLDER/'recipe-before-execution.json').write_text(json.dumps(recipe,indent=2)+'\n')
    with zipfile.ZipFile(FOLDER/'executed-sources.zip','x',zipfile.ZIP_DEFLATED) as archive:
        for name in sources:archive.write(ROOT/name,name)
    spec=importlib.util.spec_from_file_location('point_lens_scaling_candidate',ROOT/'output/c214-point-lens-staging/point_lens.py')
    core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
    sys.path.insert(0,str(ROOT/'scripts'))
    from importlib.machinery import SourceFileLoader
    old=SourceFileLoader('point_lens_original_test_helpers',str(ROOT/'scripts/verify-c214-point-lens.py')).load_module()
    proof=dict(accepted=False,completed=False,source_sha256=sources,prior_receipt_sha256=sha(prior_path),
      source_archive_sha256=sha(FOLDER/'executed-sources.zip'),inherited_checks=[c for c in prior['checks'] if c['passed']],
      checks=[],refusals=prior['refusals'],scope='CPU composition only: six original successful groups plus corrected in-domain scaling/translation fixture. Original refused receipt untouched. No change to kernel/contract/tolerances or service/UI/performance/C2-14 promotion.')
    try:
        cfg=old.inputs();base=core.experiment(cfg)
        for factor in recipe['joint_scales']:
            candidate=copy.deepcopy(cfg);candidate['GM_m3_s2']*=factor
            for name in ['observer_m','lens_m','source_m']:candidate[name]=[x*factor for x in candidate[name]]
            assert all(abs(x)<=1e25 for name in ['observer_m','lens_m','source_m'] for x in candidate[name])
            value=core.experiment(candidate)
            old.relative(value['reference']['magnification_total'],base['reference']['magnification_total'])
            old.relative(value['geometry']['einstein_angle_rad'],base['geometry']['einstein_angle_rad'])
            for a,b in zip(value['actual']['images'],base['actual']['images']):old.relative(a['impact_m'],b['impact_m']*factor)
            proof['checks'].append(dict(name='joint-length-GM-scale',factor=factor,passed=True))
        candidate=copy.deepcopy(cfg)
        for name in ['observer_m','lens_m','source_m']:candidate[name]=[x+y for x,y in zip(candidate[name],recipe['translation_m'])]
        value=core.experiment(candidate);reference=old.oracle(candidate)
        old.relative(value['reference']['magnification_total'],reference['total'])
        old.relative(value['geometry']['einstein_angle_rad'],reference['thetaE'])
        proof['checks'].append(dict(name='translated-geometry-matches-independent-oracle',passed=True,input_resolution=value['input_resolution']))
        assert all(sha(ROOT/n)==seal for n,seal in sources.items())
        proof.update(accepted=True,completed=True)
    except Exception:proof['failure']=traceback.format_exc()
    OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:proof.get(k) for k in ['accepted','completed','checks','failure']},ensure_ascii=False))
    return 0 if proof['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
