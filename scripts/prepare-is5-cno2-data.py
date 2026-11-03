"""Acquire four cold-CNO-II channels without changing the accepted pp-III dataset."""
from pathlib import Path
from decimal import Decimal,localcontext
import copy
import hashlib
import json
import math
import sys
import urllib.request
import zipfile
import pynucastro as pyna

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'output/is5-cno2-staging'
RECEIPT=ROOT/'evidence/is5-cno2-data-20261027a.json'
sys.path.append(str(ROOT/'app'))
import nuclei
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    if DEST.exists() or RECEIPT.exists():raise FileExistsError('Preserve CNO-II acquisition')
    assert pyna.__version__=='3.1.0'
    oldpath=ROOT/'output/is5-pp3-staging/pp3-data.json'
    old=json.loads(oldpath.read_text(encoding='utf-8'));data=copy.deepcopy(old)
    files=[oldpath,ROOT/'output/is5-pp3-staging/is5_pp3.py',ROOT/'data/science/ame2020-mass-original.txt',
           ROOT/'data/science/decays-nubase-original.txt',ROOT/'app/nuclei.py',ROOT/'IS-5-CNO-II-CONTRATO-PREVIO.md',Path(__file__)]
    files += [ROOT/e['raw_file'] for e in old['rates'].values() if 'raw_file' in e]
    files += [ROOT/p['path'] for p in old['primary_papers']]
    before={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    DEST.mkdir();refs=DEST/'references';refs.mkdir()
    with zipfile.ZipFile(DEST/'before-acquisition.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n in before:z.write(ROOT/n,n)
    url='https://arxiv.org/pdf/hep-ph/9710491v1'
    request=urllib.request.Request(url,headers={'User-Agent':'Cosmos2 local scientific research'})
    with urllib.request.urlopen(request,timeout=30) as response:raw=response.read(16*1024*1024+1)
    assert raw.startswith(b'%PDF-') and len(raw)<=16*1024*1024
    paper=refs/'Bahcall1997-v1.pdf';paper.write_bytes(raw)
    data['primary_papers'].append(dict(url=url,path=paper.relative_to(ROOT).as_posix(),sha256=sha(paper),bytes=len(raw)))
    library=pyna.ReacLibLibrary()
    added={'n15pg':'n15(p,g)o16','o16pg':'o16(p,g)f17','f17beta':'f17(,)o17','o17pa':'o17(p,a)n14'}
    for channel,query in added.items():
        rate=library.get_rate_by_name(query)
        if isinstance(rate,list):
            candidates=[r for r in rate if r.weak_type=='beta_pos'];assert len(candidates)==1;rate=candidates[0]
        assert rate is not None
        if channel=='f17beta':assert rate.weak_type=='beta_pos'
        file=DEST/('cno2-'+channel+'-reaclib.txt');file.write_bytes(rate.original_data.encode('ascii'))
        data['rates'][channel]=dict(fname=rate.fname,reactants=[n.raw for n in rate.reactants],products=[n.raw for n in rate.products],
            Q_fit_MeV=rate.Q,source=rate.source,sets=[s.a for s in rate.sets],prefactor=rate.prefactor,weak_type=rate.weak_type,
            raw_file=file.relative_to(ROOT).as_posix(),sha256=sha(file),units='s^-1' if channel=='f17beta' else 'cm^3 mol^-1 s^-1',
            reference_rates={str(t):float(rate.eval(t)) for t in (10.1e6,12e6,15e6,15.9e6)})
    table=nuclei.parse_table((ROOT/'data/science/ame2020-mass-original.txt').read_bytes())
    for name in ('o16','f17','o17'):
        n=pyna.Nucleus(name);record=next(v for v in table if v['Z']==n.Z and v['A']==n.A)
        assert record['quantities']['mass_excess']['status']=='evaluated'
        data['species'].append(name);data['nuclides'][name]=dict(A=n.A,Z=n.Z,AME2020=record,pynucastro_mass_excess_MeV=n.dm)
    lines=(ROOT/'data/science/decays-nubase-original.txt').read_text(encoding='ascii').splitlines()
    found=[(i,line) for i,line in enumerate(lines,1) if line.startswith('017 0090')];assert len(found)==1
    line_number,line=found[0];assert line[78:80].strip()=='s'
    half=Decimal(line[69:78].strip());unc=Decimal(line[81:88].strip())
    assert math.isclose(float(half),float(pyna.Nucleus('f17').tau),rel_tol=1e-14)
    data['nuclides']['f17']['NUBASE2020']=dict(source_line=line_number,raw_line=line,half_life_s=float(half),uncertainty_s=float(unc),
        half_life_raw=line[69:78].strip(),unit_raw=line[78:80].strip(),uncertainty_raw=line[81:88].strip(),
        raw_file='data/science/decays-nubase-original.txt',sha256=sha(ROOT/'data/science/decays-nubase-original.txt'))
    beta=data['rates']['f17beta'];beta['nubase2020_decay_constant_s']=math.log(2)/float(half)
    beta['decay_source']='Original terrestrial NUBASE2020 F17 ground-state half-life used as an approximate beta+ coefficient; minor CNO electron-capture branches are not resolved. Pinned REACLIB retained as comparison.'
    with localcontext() as ctx:
        ctx.prec=50
        for c in added:
            entry=data['rates'][c]
            masses=lambda names:sum((Decimal(data['nuclides'][n]['AME2020']['quantities']['mass_excess']['raw_value']) for n in names),Decimal(0))
            assert sum(data['nuclides'][n]['A'] for n in entry['reactants'])==sum(data['nuclides'][n]['A'] for n in entry['products'])
            q=(masses(entry['reactants'])-masses(entry['products']))/1000
            entry['Q_MeV']=float(q);entry['Q_AME2020_decimal_MeV']=str(q)
    assert all(data['rates'][c]==entry for c,entry in old['rates'].items())
    data['neutrino_mean_MeV']['f17beta']=.9977
    data['neutrino_mean_source_by_channel']={'f17beta':dict(url=url,equation=36,page_one_based=24,MeV=.9977,
        scope='Fixed mean solar F17 neutrino energy from the primary spectrum calculation; not a locally recomputed spectrum.')}
    data.update(kind='is5_ppI_ppII_ppIII_effective_CNOI_CNOII_added_data',domain='10<T_MK<16; fixed rho/V; solar Be7 EC approximation, ideal EOS, cold-CNO-II and effective B8. No CNOIII/hot-CNO/pep/hep/screening/transport/stellar structure.')
    path=DEST/'cno2-data.json';path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert all(sha(ROOT/n)==v for n,v in before.items())
    package=Path(pyna.__file__).parent
    receipt=dict(accepted_for_candidate_data=True,scientific_model_accepted=False,dataset=path.relative_to(ROOT).as_posix(),dataset_sha256=sha(path),
        source_sha256=before,new_files_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in DEST.rglob('*') if p.is_file()},
        library_sha256=sha(package/'data/reaclib_default2_20250330'),scope='Four added fits, original masses/half-life and primary F17 neutrino source only; no solver acceptance.')
    RECEIPT.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(species=len(data['species']),channels=len(data['rates']),F17_half_life_s=float(half),new_Q={c:data['rates'][c]['Q_MeV'] for c in added})),flush=True)


if __name__=='__main__':main()
