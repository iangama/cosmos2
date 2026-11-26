"""Freeze pp-III effective channels, preserving the accepted twelve pp-II entries."""
from pathlib import Path
from decimal import Decimal, localcontext
import copy
import hashlib
import json
import math
import sys
import zipfile
import pynucastro as pyna

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'output/is5-pp3-staging'
RECEIPT=ROOT/'evidence/is5-pp3-data-20261026a.json'
sys.path.append(str(ROOT/'app'))
import nuclei
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    if DEST.exists() or RECEIPT.exists():raise FileExistsError('Preserve pp-III acquisition')
    assert pyna.__version__=='3.1.0'
    previous=ROOT/'output/is5-pp2-staging/pp2-data.json'
    data=copy.deepcopy(json.loads(previous.read_text(encoding='utf-8')))
    files=[previous,ROOT/'output/is5-pp2-staging/is5_pp2.py',ROOT/'data/science/ame2020-mass-original.txt',
           ROOT/'data/science/decays-nubase-original.txt',ROOT/'app/nuclei.py',ROOT/'IS-5-PP-III-CONTRATO-PREVIO.md',Path(__file__)]
    files += [ROOT/e['raw_file'] for e in data['rates'].values() if 'raw_file' in e]
    files += [ROOT/p['path'] for p in data['primary_papers']]
    before={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    DEST.mkdir()
    with zipfile.ZipFile(DEST/'before-acquisition.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n in before:z.write(ROOT/n,n)
    library=pyna.ReacLibLibrary()
    capture=library.get_rate_by_name('be7(p,g)b8')
    betas=[r for r in library.get_rates() if [n.raw for n in r.reactants]==['b8']
           and sorted(n.raw for n in r.products)==['he4','he4'] and r.weak_type=='beta_pos']
    assert capture is not None and not isinstance(capture,list) and len(betas)==1
    for channel,rate in [('be7p',capture),('b8beta2a',betas[0])]:
        file=DEST/('pp3-'+channel+'-reaclib.txt');file.write_bytes(rate.original_data.encode('ascii'))
        data['rates'][channel]=dict(fname=rate.fname,reactants=[n.raw for n in rate.reactants],products=[n.raw for n in rate.products],
            Q_fit_MeV=rate.Q,source=rate.source,sets=[s.a for s in rate.sets],prefactor=rate.prefactor,weak_type=rate.weak_type,
            raw_file=file.relative_to(ROOT).as_posix(),sha256=sha(file),units='s^-1' if channel=='b8beta2a' else 'cm^3 mol^-1 s^-1',
            reference_rates={str(t):float(rate.eval(t)) for t in (10.1e6,12e6,15e6,15.9e6)})
    n=pyna.Nucleus('b8');table=nuclei.parse_table((ROOT/'data/science/ame2020-mass-original.txt').read_bytes())
    record=next(v for v in table if v['Z']==n.Z and v['A']==n.A)
    assert record['quantities']['mass_excess']['status']=='evaluated'
    data['species'].append('b8')
    data['nuclides']['b8']=dict(A=n.A,Z=n.Z,AME2020=record,pynucastro_mass_excess_MeV=n.dm)
    lines=(ROOT/'data/science/decays-nubase-original.txt').read_text(encoding='ascii').splitlines()
    found=[(i,line) for i,line in enumerate(lines,1) if line.startswith('008 0050')]
    assert len(found)==1
    line_number,line=found[0]
    assert line[78:80].strip()=='ms'
    half=Decimal(line[69:78].strip())/1000
    assert math.isclose(float(half),float(n.tau),rel_tol=1e-14)
    data['nuclides']['b8']['NUBASE2020']=dict(source_line=line_number,raw_line=line,half_life_s=float(half),
        half_life_raw=line[69:78].strip(),unit_raw=line[78:80].strip(),uncertainty_raw=line[81:88].strip(),
        raw_file='data/science/decays-nubase-original.txt',sha256=sha(ROOT/'data/science/decays-nubase-original.txt'))
    beta=data['rates']['b8beta2a']
    beta['nubase2020_decay_constant_s']=math.log(2)/float(half)
    beta['decay_source']='Original NUBASE2020 ground-state B8 half-life; pinned REACLIB beta-delayed two-alpha rate retained as comparison.'
    beta['effective_channel']='B8 beta+ and strong continuation via broad Be8 resonances, aggregated; no resolved Be8 population/spectrum. Gate strong+weak does not redefine intrinsic beta half-life.'
    with localcontext() as ctx:
        ctx.prec=50
        for channel in ('be7p','b8beta2a'):
            entry=data['rates'][channel]
            masses=lambda names:sum((Decimal(data['nuclides'][v]['AME2020']['quantities']['mass_excess']['raw_value']) for v in names),Decimal(0))
            q=(masses(entry['reactants'])-masses(entry['products']))/1000
            entry['Q_MeV']=float(q);entry['Q_AME2020_decimal_MeV']=str(q)
    old=json.loads(previous.read_text(encoding='utf-8'))
    assert all(data['rates'][c]==entry for c,entry in old['rates'].items())
    data.update(kind='is5_ppI_ppII_ppIII_effective_CNOI_added_data',domain='10<T_MK<16; fixed rho/V; solar EC approximation; effective beta-delayed two-alpha B8 channel. No pep/hep/CNOII/screening/transport/stellar structure.')
    data['neutrino_mean_MeV']['b8beta2a']=6.735
    path=DEST/'pp3-data.json';path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert all(sha(ROOT/n)==value for n,value in before.items())
    package=Path(pyna.__file__).parent
    receipt=dict(accepted_for_candidate_data=True,scientific_model_accepted=False,dataset=path.relative_to(ROOT).as_posix(),dataset_sha256=sha(path),
        source_sha256=before,new_files_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in DEST.iterdir() if p.is_file()},
        library_sha256=sha(package/'data/reaclib_default2_20250330'),scope='Two added rate fits, original B8 masses/half-life and inherited primary papers only; no solver acceptance.')
    RECEIPT.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(species=len(data['species']),channels=len(data['rates']),half_life_s=float(half),new_Q={c:data['rates'][c]['Q_MeV'] for c in ('be7p','b8beta2a')})),flush=True)


if __name__=='__main__':main()
