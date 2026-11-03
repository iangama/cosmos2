"""Supplement the frozen frame auditor with every scalar, species and channel probe."""
from pathlib import Path
import argparse
import hashlib
import json
import traceback

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    source=ROOT/('evidence/is5-pp2-zone-profile-'+args.label+'.json')
    frame=ROOT/('evidence/is5-pp2-zone-profile-audit-'+args.label+'.json')
    out=ROOT/('evidence/is5-pp2-zone-profile-probes-'+args.label+'.json')
    if out.exists():raise FileExistsError('Preserve complete probe audit')
    r=dict(accepted=False,profile=source.relative_to(ROOT).as_posix(),profile_sha256=sha(source),
           frame_audit=frame.relative_to(ROOT).as_posix(),frame_audit_sha256=sha(frame),auditor_sha256=sha(Path(__file__)),states=0,values_compared=0)
    try:
        frames=json.loads(frame.read_text());assert frames['accepted'] and frames['profile_sha256']==sha(source)
        profile=json.loads(source.read_text())
        scalars=['time_s','temperature_K','pressure_Pa','internal_energy_J_m3','heat_capacity_J_m3_K',
                 'energy_available_J_m3','energy_neutrinos_J_m3','non_neutrino_energy_available_J_m3',
                 'nuclear_power_W_m3','neutrino_power_W_m3','neutrino_count_m3','produced_positrons_m3',
                 'annihilated_electrons_m3','captured_electrons_m3']
        for row in profile['runs']:
            path=ROOT/row['thermal_result'];assert sha(path)==row['thermal_result_sha256']
            payload=json.loads(path.read_text())
            for state in [row['initial'],row['final'],*[s['zone'] for s in row['samples']]]:
                w=state['worker'];i=w['view']['selected_index'];assert w['sample']['index']==i
                for network in ('actual','reference'):
                    sample=w['sample'][network];result=payload[network]
                    assert len(result['species'])==len(result['channels'])==12
                    for field in scalars:
                        assert sample[field]==result[field][i],(row['run'],network,i,field)
                        r['values_compared']+=1
                    for field,keys in [('mass_fractions',result['species']),('number_per_baryon',result['species']),
                                       ('event_rates_m3_s',result['channels']),('reaction_extents_m3',result['channels'])]:
                        assert set(sample[field])==set(keys)
                        assert sample[field]==dict(zip(keys,result[field][i])),(row['run'],network,i,field)
                        r['values_compared']+=len(keys)
                    assert sample['annihilated_electrons_m3']==sample['produced_positrons_m3']
                r['states']+=1
        assert r['states']==24 and r['values_compared']==2976
        r.update(accepted=True,scope='All recorded probes exactly match sealed calculated knots. Together with the frame audit this covers the pp-II profile contract; not solver/pp-III acceptance.')
    except Exception:r['failure']=traceback.format_exc()
    out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(r,ensure_ascii=False),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
