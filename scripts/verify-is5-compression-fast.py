"""Optimized trajectories against all archived accepted compression oracles."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import time
import traceback
import zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'output/is5-compression-fast-staging'))
import is5_compression_fast as model
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--label',required=True);args=ap.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):ap.error('Invalid label')
    folder=ROOT/f'output/is5-compression-fast-{args.label}';path=ROOT/f'evidence/is5-compression-fast-{args.label}.json'
    if folder.exists() or path.exists():raise FileExistsError('Preserve optimized evolution evidence')
    science=json.loads(model.SCIENCE.read_text());eos=json.loads(model.PARENT.read_text());assert science['accepted'] and eos['accepted']
    hashes={**science['source_sha256'],**eos['source_sha256']}
    for p in [Path(__file__),*model.FILES]:hashes[p.relative_to(ROOT).as_posix()]=sha(p)
    for c in science['cases']+science['controls']:hashes.update(c['artifact_sha256'])
    assert all(sha(ROOT/n)==v for n,v in hashes.items())
    folder.mkdir();archive=folder/'executed-sources.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    gen=model.generation()
    r=dict(accepted=False,completed=False,generation=gen,source_sha256=hashes,archive_sha256=sha(archive),cases=[],controls=[],refusals=[],
           limits_before_execution=dict(T_relative=1e-9,Y_absolute=1e-10,W_over_E0_absolute=1e-9,energy_normalized=1e-8,case0_target_s=60))
    def persist():path.write_text(json.dumps(r,ensure_ascii=False,allow_nan=False,indent=2)+'\n',encoding='utf-8')
    def compare(run,ref):
        ey=float(np.max(abs(np.array(run['number_per_baryon'])-np.array(ref['number_per_baryon']))))
        et=float(np.max(abs(np.array(run['temperature_K'])-np.array(ref['temperature_K']))/np.array(ref['temperature_K'])))
        ew=None
        if 'external_pressure_work_J' in ref:
            ew=float(np.max(abs(np.array(run['external_pressure_work_J'])-np.array(ref['external_pressure_work_J']))/run['initial_internal_energy_J']))
            assert ew<=1e-9,ew
        assert ey<=1e-10 and et<=1e-9,(ey,et)
        return dict(Y_absolute=ey,T_relative=et,W_over_E0_absolute=ew)
    def execute(label,reference,oracles):
        began=time.perf_counter()
        run=model.integrate_zone(reference['parameters'],reference['density_history'],reference['acting'],reference['channel_switches'],
            include_coulomb=reference['include_coulomb'],include_screening=reference['include_screening'])
        elapsed=time.perf_counter()-began
        results={n:compare(run,ref) for n,ref in oracles.items()}
        energy=np.array(run['internal_energy_J']);work=np.array(run['external_pressure_work_J']);retained=np.array(run['non_neutrino_energy_available_J'])
        scale=np.maximum.reduce([np.full(241,energy[0]),abs(energy),abs(work),abs(np.array(run['energy_available_J']))])
        err=float(np.max(abs(energy-energy[0]-retained-work)/scale));assert err<=1e-8
        assert np.allclose(energy,np.array(run['volume_m3'])*np.array(run['internal_energy_J_m3']),rtol=1e-15,atol=0)
        assert np.max(abs(np.array(run['density_kg_m3'])*np.array(run['volume_m3'])/model.network.eos.MU/run['baryon_count']-1))<=1e-14
        assert np.allclose(run['neutrino_count'],np.array(run['produced_positrons'])+np.array(run['captured_electrons']),rtol=1e-12,atol=1e-99)
        assert run['produced_positrons']==run['annihilated_electrons']
        for field in ['parameters','density_history','acting','channel_switches','include_coulomb','include_screening','active_channels','time_s','density_kg_m3','volume_m3','baryon_count']:
            assert run[field]==reference[field],field
        out=folder/(label+'.json');out.write_text(json.dumps(run,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
        item=dict(name=label,elapsed_s=elapsed,comparisons=results,energy_normalized_error=err,conservation=run['conservation'],
                  solver=run['solver'],artifact_sha256={out.relative_to(ROOT).as_posix():sha(out)})
        print(json.dumps(item),flush=True)
        return item
    persist()
    try:
        for index,c in enumerate(science['cases']):
            oracles={n:json.loads((ROOT/n).read_text()) for n in c['artifact_sha256']}
            baseline=next(v for n,v in oracles.items() if n.endswith('-Radau.json'))
            r['cases'].append(execute('case'+str(index),baseline,oracles));persist()
        for index,c in enumerate(science['controls']):
            oracles={n:json.loads((ROOT/n).read_text()) for n in c['artifact_sha256']}
            baseline=next(v for v in oracles.values() if v.get('mode')=='prescribed_density')
            r['controls'].append(execute('control'+str(index),baseline,oracles));persist()
        p=model.base.DEFAULT_PARAMETERS
        try:model.base.rate_constants(1.6001e7,p['density_kg_m3'])
        except ValueError as error:reason=str(error)
        else:raise AssertionError('Missing upper temperature guard')
        hot={**p,'temperature_K':1.5999e7,'duration_s':1000*31557600.}
        try:model.integrate_zone(hot,dict(kind='exponential',ratio=1.05))
        except ValueError as error:
            assert str(error)==reason
            r['refusals'].append(dict(case='whole_hot_trajectory',reason=reason))
        else:raise AssertionError('Hot trajectory accepted')
        for label,history,opts in [('history_type',None,{}),('ratio_bool',dict(kind='cycle',ratio=True),{}),
                ('ratio_range',dict(kind='exponential',ratio=1.21),{}),('extra_field',dict(kind='constant',ratio=1),{}),
                ('screen_without_EOS',dict(kind='constant'),dict(include_coulomb=False)),
                ('EOS_type',dict(kind='constant'),dict(include_coulomb=1)),('tolerance_type',dict(kind='constant'),dict(tolerance=True))]:
            try:model.integrate_zone(p,history,**opts)
            except ValueError as error:r['refusals'].append(dict(case=label,reason=str(error)))
            else:raise AssertionError('Invalid setup accepted: '+label)
        assert len(r['cases'])==3 and len(r['controls'])==4 and len(r['refusals'])==8
        assert model.generation()==gen and all(sha(ROOT/n)==v for n,v in hashes.items())
        r.update(accepted=True,completed=True,performance_target_met=r['cases'][0]['elapsed_s']<=60,
                 scope='Same restricted physical model and accepted trajectories, thermal-row numerical representation only. Worker/product/native performance not accepted.')
    except Exception:r['failure']=traceback.format_exc()
    persist();print(json.dumps({k:r.get(k) for k in ['accepted','performance_target_met','failure']}),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
