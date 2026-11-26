"""Reuse completed hashed five-case science; fix the EMoff test expectation only."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import traceback
import zipfile
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'output/is5-coulomb-network-staging'))
import is5_coulomb_network as model
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label',required=True)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label')
    path = ROOT/f'evidence/is5-coulomb-evolution-controls-{args.label}.json'
    archive = ROOT/f'output/is5-coulomb-evolution-controls-{args.label}.zip'
    folder = ROOT/f'output/is5-coulomb-evolution-controls-{args.label}'
    if any(p.exists() for p in [path,archive,folder]):
        raise FileExistsError('Preserve controls evidence')
    anchor = ROOT/'evidence/is5-coulomb-evolution-20261028a.json'
    if not anchor.exists():
        raise RuntimeError('A still running or incomplete; inspect before controls audit')
    prior = json.loads(anchor.read_text(encoding='utf-8'))
    if prior.get('accepted') or len(prior.get('cases',[])) != 5:
        raise ValueError('Require five completed A cases and documented test failure; inspect other failures')
    expected_controls = [('ideal_legacy_limit','prescribed'),('ideal_legacy_limit','isochoric'),('alloff',None)]
    if [(v['name'],v.get('mode')) for v in prior['controls']] != expected_controls or 'ValueError: Exact explicit physical switches required' not in prior.get('failure',''):
        raise ValueError('A failed somewhere other than the documented incomplete force-switch request')
    assert prior['generation'] == model.generation()
    hashes = {**prior['source_sha256'],anchor.relative_to(ROOT).as_posix():sha(anchor),
              Path(__file__).relative_to(ROOT).as_posix():sha(Path(__file__)),
              'IS-5-COULOMB-EVOLUCAO-CONTROLE-B.md':sha(ROOT/'IS-5-COULOMB-EVOLUCAO-CONTROLE-B.md')}
    for case in prior['cases']:
        assert max(case['BDF_composition_absolute_error'],case['refinement_composition_absolute_error']) <= 1e-8
        assert max(case['BDF_temperature_relative_error'],case['refinement_temperature_relative_error']) <= 1e-7
        if case['mode'] == 'isochoric':
            assert case['conservation']['energy_normalized_error'] <= 1e-8
        hashes.update(case['artifact_sha256'])
    assert all(sha(ROOT/n) == h for n,h in hashes.items())
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:
            z.write(ROOT/n,n)
    folder.mkdir()
    r = dict(accepted=False,completed=False,source_sha256=hashes,archive_sha256=sha(archive),
             generation=model.generation(),reused_cases=prior['cases'],reused_controls=prior['controls'],
             controls=[],refusals=[],A_status='REJECTED: incomplete weakoff force dictionary. EMoff invariant expectation also corrected before B')
    try:
        year = 31557600.
        short = {**model.base.DEFAULT_PARAMETERS,'duration_s':100*year}
        weakoff = model.integrate_zone(short,dict(strong=True,weak=False,electromagnetic=True),mode='isochoric')
        assert max(weakoff['neutrino_count_m3']) == 0
        assert weakoff['conservation']['energy_normalized_error'] <= 1e-8
        output = folder/'weakoff.json'
        output.write_text(json.dumps(weakoff,ensure_ascii=False)+'\n',encoding='utf-8')
        r['controls'].append(dict(name='weakoff_explicit',conservation=weakoff['conservation'],artifact_sha256=sha(output)))
        print(json.dumps(dict(control='weakoff_explicit',passed=True)),flush=True)
        actual = model.integrate_zone(short,dict(strong=True,weak=True,electromagnetic=False),mode='isochoric')
        pop, events = np.array(actual['number_per_baryon']), np.array(actual['event_rates_m3_s'])
        pp = model.CHANNELS.index('pp')
        assert actual['active_channels']['pp'] and not actual['active_channels']['dp'] and not actual['active_channels']['n14pg']
        assert pop[-1,0] < pop[0,0] and pop[-1,1] > pop[0,1]
        assert np.min(events[:,pp]) > 0
        other = [j for j in range(model.NCHAN) if j != pp]
        assert np.max(abs(events[:,other])) <= 1e-12*np.max(events[:,pp])
        assert actual['neutrino_count_m3'][-1] > 0 and actual['captured_electrons_m3'][-1] == 0
        assert actual['conservation']['energy_normalized_error'] <= 1e-8
        output = folder/'EMoff.json'
        output.write_text(json.dumps(actual,ensure_ascii=False)+'\n',encoding='utf-8')
        r['controls'].append(dict(name='EMoff_pp_allowed',conservation=actual['conservation'],artifact_sha256=sha(output)))
        print(json.dumps(dict(control='EMoff_pp_allowed',passed=True)),flush=True)
        unscreened = model.integrate_zone(short,mode='isochoric',include_screening=False)
        assert np.array(unscreened['screening_factors']).min() == np.array(unscreened['screening_factors']).max() == 1.
        assert unscreened['conservation']['energy_normalized_error'] <= 1e-8
        output = folder/'Coulomb-no-screening.json'
        output.write_text(json.dumps(unscreened,ensure_ascii=False)+'\n',encoding='utf-8')
        r['controls'].append(dict(name='Coulomb_reservoir_without_screening',conservation=unscreened['conservation'],artifact_sha256=sha(output)))
        print(json.dumps(dict(control='Coulomb_reservoir_without_screening',passed=True)),flush=True)
        for opts in [dict(include_coulomb=False),dict(include_coulomb=1),dict(include_screening=1),
                     dict(mode='unknown'),dict(tolerance=True),dict(tolerance=1e-14)]:
            try:
                model.integrate_zone(short,**opts)
            except ValueError as e:
                r['refusals'].append(str(e))
            else:
                raise AssertionError('Invalid integration options accepted')
        hot = {**short,'temperature_K':1.5999999e7,'duration_s':1e6*year}
        try:
            model.integrate_zone(hot)
        except ValueError as e:
            r['refusals'].append('whole-run hot trajectory: '+str(e))
        else:
            raise AssertionError('Out-of-domain trajectory accepted')
        assert all(sha(ROOT/n) == h for n,h in hashes.items())
        r.update(accepted=True,completed=True,scope='Five reused hashed Radau/BDF/refined cases plus corrected controls; A remains rejected. No worker/product acceptance.')
    except Exception:
        r['failure'] = traceback.format_exc()
    path.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(accepted=r['accepted'],reused_cases=len(r['reused_cases']),controls=len(r['controls']),refusals=len(r['refusals']),failure=r.get('failure'))),flush=True)
    return 0 if r['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
