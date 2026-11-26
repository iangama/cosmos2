"""Independent raw-data audit and A>=1 upper ion bound; preserve the conditional A>=10 result."""
from pathlib import Path
from decimal import Decimal,localcontext
import hashlib
import json
import math
import sys
import traceback
import zipfile
import is5_solar_reference as source
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'output/is5-thermal-staging'))
import is5_eos as eos
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    prior=ROOT/'evidence/is5-solar-reference-20261027a.json';previous=json.loads(prior.read_text())
    folder=ROOT/'output/is5-solar-reference-audit-20261027b';out=ROOT/'evidence/is5-solar-reference-audit-20261027b.json'
    if folder.exists() or out.exists():raise FileExistsError('Preserve reference audit')
    folder.mkdir();files=[Path(__file__),prior,ROOT/'IS-5-REFERENCIAS-SOLARES-EOS-LIMITES.md']+[ROOT/n for n in previous['source_sha256']]
    files += [ROOT/m['path'] for m in previous['models']]+[ROOT/c['path'] for c in previous['comparison']]
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    with zipfile.ZipFile(folder/'executed-sources-and-inputs.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(accepted=False,source_sha256=hashes,original_receipt_sha256=sha(prior),models_checked=0,points_checked=0,comparison=[],figures=[])
    try:
        assert previous['accepted'] and previous['refusals']==10 and previous['conversion_checks']==120
        assert all(sha(ROOT/n)==h for n,h in previous['source_sha256'].items())
        imported={}
        for row in previous['models']:
            path=ROOT/row['path'];assert sha(path)==row['sha256'];data=json.loads(path.read_text());imported[row['model']]=data
            _,raw=source.original(row['model']);tokens=[line.split() for line in raw.decode('ascii').splitlines()[1:]]
            assert [[float(v) for v in line] for line in tokens]==data['raw_values']
            assert data['flags'][0][0]=='central_interpolation_residue' and all('inconsistent_log_radius' in data['flags'][i] for i in (1,2))
            r['models_checked']+=1
        for old in previous['comparison']:
            model=old['model'];path=ROOT/old['path'];assert sha(path)==old['sha256']
            oldrows=json.loads(path.read_text());data=imported[model];_,raw=source.original(model)
            tokens=[line.split() for line in raw.decode('ascii').splitlines()[1:]];eligible=[]
            with localcontext() as ctx:
                ctx.prec=50
                for i,line in enumerate(tokens):
                    T=float(ctx.power(Decimal(10),Decimal(line[4])));rho=float(ctx.power(Decimal(10),Decimal(line[6]))*1000)
                    if i>=3 and 1e7<T<1.6e7 and 1e4<=rho<=3e5:eligible.append(i)
            assert eligible==[v['index'] for v in oldrows]
            rows=[]
            for oldrow in oldrows:
                i=oldrow['index'];line=tokens[i]
                with localcontext() as ctx:
                    ctx.prec=50
                    T=float(ctx.power(Decimal(10),Decimal(line[4])));rho=float(ctx.power(Decimal(10),Decimal(line[6]))*1000)
                    P=float(ctx.power(Decimal(10),Decimal(line[5]))/10);ne=float(ctx.power(Decimal(10),Decimal(line[17]))*Decimal('6.02214076e29'))
                    pairs=[(Decimal(line[data['columns'].index(n)]),Decimal(a)) for n,a in source.COVERED.items()]
                    mass=float(sum(v for v,a in pairs));ions=float(sum(v/a for v,a in pairs))
                for actual,expected in [(oldrow['temperature_K'],T),(oldrow['density_kg_m3'],rho),(oldrow['reference_pressure_Pa'],P),(oldrow['covered_mass_fraction'],mass),(oldrow['ions_per_baryon_lower'],ions)]:
                    assert math.isclose(actual,expected,rel_tol=1e-12)
                missing=1-mass;hi=oldrow['ideal_pressure_lower_Pa']+(rho/eos.MU)*missing*eos.K*T
                row={**oldrow,'ions_per_baryon_upper':ions+missing,'ideal_pressure_upper_Pa':hi,'pressure_relative_upper':hi/P-1,'upper_mass_number_bound':1}
                rows.append(row);r['points_checked']+=1
            for row in (rows[0],rows[len(rows)//2],rows[-1]):
                for bound in ('lower','upper'):
                    pressure=eos.mixture(row['temperature_K'],row['density_kg_m3'],row['ions_per_baryon_'+bound],row['electrons_per_baryon_from_reference'])['pressure_Pa']
                    assert math.isclose(pressure,row['ideal_pressure_'+bound+'_Pa'],rel_tol=1e-12)
            path=folder/(model+'-ideal-EOS-Age1.json');path.write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
            r['comparison'].append(dict(model=model,path=path.relative_to(ROOT).as_posix(),sha256=sha(path),points=len(rows),
                radial_range=[rows[0]['r_over_Rsun'],rows[-1]['r_over_Rsun']],
                relative_difference_range=[min(x['pressure_relative_lower'] for x in rows),max(x['pressure_relative_upper'] for x in rows)]))
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        plt.rcParams.update({'font.size':10})
        fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
        for model,color in [('GS98','#146d86'),('AGSS09','#c56f32')]:
            data=imported[model];x=[v[0] for v in data['raw_values']]
            axes[0,0].plot(x,[d['temperature_K']/1e6 for d in data['derived']],color=color,label=model)
            axes[0,1].semilogy(x,[d['density_kg_m3'] for d in data['derived']],color=color,label=model)
            axes[1,0].plot(x,[v[18] for v in data['raw_values']],color=color,label=model+' H-1')
            axes[1,0].plot(x,[v[19] for v in data['raw_values']],color=color,linestyle='--',label=model+' He-4')
            c=next(v for v in r['comparison'] if v['model']==model);rows=json.loads((ROOT/c['path']).read_text())
            axes[1,1].fill_between([v['r_over_Rsun'] for v in rows],[v['pressure_relative_lower']*100 for v in rows],[v['pressure_relative_upper']*100 for v in rows],color=color,alpha=.35,label=model)
        for ax in axes.flat:ax.set_xlabel('r / R☉');ax.grid(alpha=.25);ax.legend(fontsize=8);ax.set_xlim(0,1)
        axes[0,0].set_ylabel('Temperatura de referência (MK)');axes[0,1].set_ylabel('Densidade de referência (kg/m³, log)')
        axes[1,0].set_ylabel('Fração mássica de referência');axes[1,1].set_ylabel('100 × (P ideal / P referência − 1) (%)')
        axes[1,1].set_xlim(0,.19);axes[1,1].set_title('Recorte válido; limite geral para massa não coberta (A ≥ 1)',fontsize=10)
        fig.suptitle('B23 v1.2 · perfis de referência GarStEC e comparação com EOS ideal',fontsize=13)
        for suffix in ('png','svg'):
            path=folder/('B23-reference-comparison-Age1.'+suffix);fig.savefig(path,dpi=170)
            r['figures'].append(dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path)))
        plt.close(fig)
        assert all(sha(ROOT/n)==h for n,h in hashes.items())
        r.update(accepted=True,scope='ImportA remains valid. This audit replaces its conditional A>=10 upper ion bound with the declared general A>=1 bound; no solar evolution/calibration or statistical physical uncertainty claimed.')
    except Exception:r['failure']=traceback.format_exc()
    out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in r.items() if k!='source_sha256'}),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
