"""Freeze two added fits, AME2020 Q values and the explicitly bounded solar Be7 EC law."""
from pathlib import Path
from decimal import Decimal,localcontext
import copy
import hashlib
import json
import sys
import urllib.request
import zipfile
import pynucastro as pyna

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'output/is5-pp2-staging'
RECEIPT=ROOT/'evidence/is5-pp2-data-20261026a.json'
sys.path.append(str(ROOT/'app'))
import nuclei


def main():
    if DEST.exists() or RECEIPT.exists():raise FileExistsError('Preserve pp-II acquisition')
    assert pyna.__version__=='3.1.0'
    DEST.mkdir();research=DEST/'references';research.mkdir()
    originals=[ROOT/'data/science'/n for n in ['pp1.json','cno1.json','fusion.json','ame2020-mass-original.txt']]
    originals += [ROOT/'data/science'/entry['raw_file'] for name in ('pp1.json','cno1.json') for entry in json.loads((ROOT/'data/science'/name).read_text())['rates'].values()]
    originals += [ROOT/'app/nuclei.py',ROOT/'scripts/prepare-stellar-data.py',ROOT/'scripts/prepare-cno-data.py',ROOT/'IS-5-PP-II-CONTRATO-PREVIO.md',Path(__file__)]
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in originals}
    with zipfile.ZipFile(DEST/'before-acquisition.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    papers=[]
    for filename,url in [('SolarFusionII-v3.pdf','https://arxiv.org/pdf/1004.2318v3'),('Bahcall2001-v3.pdf','https://arxiv.org/pdf/hep-ph/0108148v3')]:
        request=urllib.request.Request(url,headers={'User-Agent':'Cosmos2 local scientific research'})
        with urllib.request.urlopen(request,timeout=30) as response:raw=response.read(16*1024*1024+1)
        assert len(raw)<=16*1024*1024 and raw.startswith(b'%PDF-'),(filename,len(raw))
        path=research/filename;path.write_bytes(raw);papers.append(dict(url=url,path=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=len(raw)))
    pp=json.loads((ROOT/'data/science/pp1.json').read_text());cno=json.loads((ROOT/'data/science/cno1.json').read_text())
    entries=copy.deepcopy({**pp['rates'],**cno['rates']})
    for entry in entries.values():
        entry['raw_file']=(ROOT/'data/science'/entry['raw_file']).relative_to(ROOT).as_posix()
    library=pyna.ReacLibLibrary()
    for channel,query in [('he3alpha','he3(a,g)be7'),('li7pa','li7(p,a)he4')]:
        rate=library.get_rate_by_name(query)
        assert rate is not None and not isinstance(rate,list),query
        raw=rate.original_data.encode('ascii');file=DEST/('pp2-'+channel+'-reaclib.txt');file.write_bytes(raw)
        entries[channel]=dict(fname=rate.fname,reactants=[n.raw for n in rate.reactants],products=[n.raw for n in rate.products],
            Q_MeV=rate.Q,source=rate.source,sets=[s.a for s in rate.sets],prefactor=rate.prefactor,weak_type=rate.weak_type,
            raw_file=file.relative_to(ROOT).as_posix(),sha256=sha(file),units='cm^3 mol^-1 s^-1',
            reference_rates={str(t):float(rate.eval(t)) for t in (10.1e6,12e6,15e6,15.9e6)})
        if channel=='li7pa':assert raw==(ROOT/'data/science/fusion-li7p-reaclib.txt').read_bytes()
    ec=library.get_rate_by_name('be7(,)li7')
    candidates=ec if isinstance(ec,list) else [ec]
    ec=next(r for r in candidates if r is not None and r.weak_type=='electron_capture')
    file=DEST/'be7ec-reaclib-comparison-only.txt';file.write_bytes(ec.original_data.encode('ascii'))
    entries['be7ec']=dict(fname='Be7_electron_capture_SFII_eq40',reactants=['be7'],products=['li7'],Q_MeV=ec.Q,
        prefactor=1.,weak_type='electron_capture',rate_kind='SFII_eq40_solar_plasma',units='s^-1 per Be7 nucleus',
        source=dict(url=papers[0]['url'],equation=40,page_one_based=26),coefficient=5.60e-9,slope=0.004,
        T6_anchor=16.,temperature_domain_K=dict(min_exclusive=1e7,max_exclusive=1.6e7),reported_fractional_uncertainty=.02,
        comparison_only=dict(source=ec.source,raw_file=file.relative_to(ROOT).as_posix(),sha256=sha(file),adopted=False),
        scope='Solar bound+continuum EC approximation. rho_g_cm3*Ye density factor exactly once; not atomic half-life or general plasma EC.')
    species=['p','d','he3','he4','c12','n13','c13','n14','o15','n15','be7','li7']
    table=nuclei.parse_table((ROOT/'data/science/ame2020-mass-original.txt').read_bytes())
    nuclides={}
    for name in species:
        n=pyna.Nucleus(name);record=next(v for v in table if v['Z']==n.Z and v['A']==n.A)
        assert record['quantities']['mass_excess']['status']=='evaluated'
        nuclides[name]=dict(A=n.A,Z=n.Z,AME2020=record,pynucastro_mass_excess_MeV=n.dm)
    with localcontext() as ctx:
        ctx.prec=50
        for channel,entry in entries.items():
            entry['Q_fit_MeV']=entry['Q_MeV']
            masses=lambda names:sum((Decimal(nuclides[n]['AME2020']['quantities']['mass_excess']['raw_value']) for n in names),Decimal(0))
            assert sum(nuclides[n]['A'] for n in entry['reactants'])==sum(nuclides[n]['A'] for n in entry['products'])
            q=(masses(entry['reactants'])-masses(entry['products']))/Decimal(1000)
            entry['Q_MeV']=float(q);entry['Q_AME2020_decimal_MeV']=str(q)
        references=[]
        for t in ('10100000','12000000','15000000','15900000'):
            for rho in ('10000','150000','300000'):
                for ye in ('.525','.67','.875'):
                    T=Decimal(t)/Decimal(10)**6
                    value=Decimal('5.60e-9')*(Decimal(rho)/1000)*Decimal(ye)/ctx.sqrt(T)*(1+Decimal('.004')*(T-16))
                    references.append(dict(T_K=float(t),rho_kg_m3=float(rho),Ye=float(ye),rate_s_inverse_decimal=str(value)))
    data=dict(schema=1,kind='is5_ppI_ppII_CNOI_added_data',pynucastro=pyna.__version__,species=species,
        rates=entries,nuclides=nuclides,ec_decimal_references=references,primary_papers=papers,
        Q_basis='All channels use original AME2020 atomic mass-excess differences; fitQ retained separately; beta+ annihilation included.',
        Q_uncertainties='Original mass uncertainties preserved; covariance not available; no derived Q uncertainty claimed.',
        neutrino_mean_MeV={**{'pp':pp['pp_neutrino_mean_MeV']},**cno['neutrino_mean_MeV'],'be7ec':.814},
        neutrino_mean_source=dict(url=papers[1]['url'],table='I',scope='Fixed solar-profile means, including thermal/ionization effects; not recomputed per zone.'),
        domain='10<T_MK<16 only; density1e4..3e5kg/m3; adopted solar Be7 EC law; not ppIII/pep/hep/CNOII.')
    path=DEST/'pp2-data.json';path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    assert all(sha(ROOT/n)==v for n,v in hashes.items())
    package=Path(pyna.__file__).parent
    receipt=dict(accepted_for_candidate_data=True,scientific_model_accepted=False,dataset=path.relative_to(ROOT).as_posix(),dataset_sha256=sha(path),
        original_source_sha256=hashes,new_files_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in DEST.rglob('*') if p.is_file()},
        installed_library=dict(path=str(package/'data/reaclib_default2_20250330'),sha256=sha(package/'data/reaclib_default2_20250330')),
        scope='Data and original papers only; no pp-II solver/worker/UI acceptance.')
    RECEIPT.write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(dataset=str(path),rates=len(entries),species=len(species),Q_Be7EC=entries['be7ec']['Q_MeV'],papers=len(papers))),flush=True)


if __name__=='__main__':main()
