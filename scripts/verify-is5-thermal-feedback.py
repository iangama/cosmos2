"""Longer temperature feedback against independently evolved internal energy."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import argparse
import hashlib
import json
import traceback
import zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
h=SourceFileLoader('is5_thermal_reference',str(ROOT/'scripts/verify-is5-thermal.py')).load_module()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/('output/is5-thermal-feedback-'+args.label);path=ROOT/('evidence/is5-thermal-feedback-'+args.label+'.json')
    if path.exists() or folder.exists():raise FileExistsError('Preserve feedback evidence')
    folder.mkdir();files=[*h.STAGE.glob('*.py'),h.STAGE/'reference-manifest.json',h.STAGE/'base-manifest.json',Path(__file__),ROOT/'scripts/verify-is5-thermal.py',ROOT/'IS-5-TERMICA-CONTRATO-PREVIO.md']
    hashes={p.relative_to(ROOT).as_posix():h.sha(p) for p in files}
    with zipfile.ZipFile(folder/'sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(accepted=False,completed=False,source_sha256=hashes,reference='Independent BDF internal energy + EOS inversion; all operators/channels on',checks=[])
    try:
        p=dict(h.core.DEFAULT_PARAMETERS);result=h.model.integrate_zone(p)
        (folder/'Radau.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(dict(stage='independent1Myr',final_temperature_K=result['temperature_K'][-1])),flush=True)
        ref=h.independent(p,None,None,result['time_s'])
        (folder/'BDF.json').write_text(json.dumps({k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in ref.items()},indent=2)+'\n')
        temp=float(np.max(abs(ref['temperature_K']-result['temperature_K'])/np.array(result['temperature_K'])))
        composition=float(np.max(abs(ref['number_per_baryon']-result['number_per_baryon'])))
        extents=float(np.max(abs(ref['extents_per_baryon']-np.array(result['reaction_extents_m3'])/(p['density_kg_m3']/h.eos.MU))))
        assert temp<=1e-7 and composition<=1e-8 and extents<=1e-8,(temp,composition,extents)
        assert result['temperature_K'][-1]>1.05*p['temperature_K']
        refined=h.model.integrate_zone(p,tolerance=1e-10)
        delta=float(np.max(abs(np.array(refined['temperature_K'])-result['temperature_K'])/np.array(result['temperature_K'])))
        assert delta<=1e-7
        assert all(h.sha(ROOT/n)==v for n,v in hashes.items())
        r.update(accepted=True,completed=True,temperature_relative_error=temp,composition_absolute_per_baryon=composition,
            extents_absolute_per_baryon=extents,refinement_temperature_relative=delta,initial_temperature_K=p['temperature_K'],
            final_temperature_K=result['temperature_K'][-1],conservation=result['conservation'],
            Radau_sha256=h.sha(folder/'Radau.json'),BDF_sha256=h.sha(folder/'BDF.json'))
    except Exception:r['failure']=traceback.format_exc()
    path.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(r,ensure_ascii=False),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
