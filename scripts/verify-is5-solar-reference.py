"""B23 import, independent unit checks, conservative ideal-EOS comparison and figure."""
from pathlib import Path
from decimal import Decimal,localcontext
import copy
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
import is5_core as legacy
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    folder=ROOT/'output/is5-solar-reference-20261027a';out=ROOT/'evidence/is5-solar-reference-20261027a.json'
    if folder.exists() or out.exists():raise FileExistsError('Preserve reference evidence')
    folder.mkdir()
    files=[Path(__file__),Path(source.__file__),Path(eos.__file__),source.ARCHIVE,
           ROOT/'output/is5-solar-reference-staging/record-10822316.json',ROOT/'output/is5-solar-reference-staging/README-original-0.txt',
           ROOT/'IS-5-REFERENCIAS-SOLARES-CONTRATO-PREVIO.md',ROOT/'IS-5-REFERENCIAS-SOLARES-IMPORTACAO.md',
           ROOT/'evidence/is5-solar-reference-acquisition-20261027a.json']+[ROOT/n for n in legacy.IMPORTED]
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(accepted=False,completed=False,source_sha256=hashes,models=[],conversion_checks=0,refusals=0,comparison=[],figures=[])
    def persist():out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    persist()
    try:
        models={name:source.load(name) for name in source.MODELS}
        for name,data in models.items():
            _,original=source.original(name);lines=original.decode('ascii').splitlines()
            errors=[]
            with localcontext() as ctx:
                ctx.prec=50
                for index in (0,3,100,500,2000):
                    tokens=lines[index+1].split()
                    for col,field,multiplier in [('logT','temperature_K','1'),('logRho','density_kg_m3','1000'),('logP','pressure_Pa','.1'),('log_ne','electron_density_m3','6.02214076e29')]:
                        expected=float(ctx.power(Decimal(10),Decimal(tokens[source.COLUMNS.index(col)]))*Decimal(multiplier))
                        measured=data['derived'][index][field];error=abs(measured-expected)/expected
                        assert error<1e-12;errors.append(error);r['conversion_checks']+=1
            path=folder/(name+'-imported.json');path.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
            r['models'].append(dict(model=name,path=path.relative_to(ROOT).as_posix(),sha256=sha(path),rows=2001,
                eligible=sum(d['eligible'] for d in data['derived']),maximum_conversion_relative=max(errors),
                quality_flag_counts={q:sum(q in flags for flags in data['flags']) for q in ['central_interpolation_residue','inconsistent_log_radius','signed_auxiliary_source_values']}))
        _,raw=source.original('GS98');base=raw.decode('ascii').splitlines()
        for kind in ('header','missing_row','missing_field','nonfinite','duplicate_radius','negative_fraction','excess_fraction','decreasing_mass','large_central_residue'):
            lines=base.copy();fields=lines[26].split()
            if kind=='header':lines[0]=lines[0].replace('logRho','log_density')
            elif kind=='missing_row':lines.pop()
            elif kind=='missing_field':fields.pop();lines[26]=' '.join(fields)
            else:
                if kind=='nonfinite':fields[4]='nan'
                elif kind=='duplicate_radius':fields[0]=lines[25].split()[0]
                elif kind=='negative_fraction':fields[18]='-0.1'
                elif kind=='excess_fraction':fields[18]='1.1'
                elif kind=='decreasing_mass':fields[1]='-0.01'
                elif kind=='large_central_residue':
                    first=lines[1].split();first[1]='-0.001';lines[1]=' '.join(first)
                lines[26]=' '.join(fields)
            try:source.parse(('\n'.join(lines)+'\n').encode('ascii'))
            except ValueError:r['refusals']+=1
            else:raise AssertionError('Invalid source accepted: '+kind)
        try:source.original('../GS98')
        except ValueError:r['refusals']+=1
        else:raise AssertionError('Unpinned source accepted')
        for name in ('GS98','AGSS09'):
            data=models[name];rows=[]
            for index,d in enumerate(data['derived']):
                if not d['eligible']:continue
                T,rho,ne=d['temperature_K'],d['density_kg_m3'],d['electron_density_m3']
                nb=rho/eos.MU;yi=d['covered_ions_per_baryon'];dy=d['uncovered_mass_fraction']/10;ye=ne/nb
                state=eos.mixture(T,rho,yi,ye)
                lo=state['pressure_Pa'];hi=lo+nb*dy*eos.K*T;ref=d['pressure_Pa']
                assert lo<=hi
                rows.append(dict(index=index,r_over_Rsun=data['raw_values'][index][0],temperature_K=T,density_kg_m3=rho,
                    covered_mass_fraction=d['covered_mass_fraction'],uncovered_mass_fraction=d['uncovered_mass_fraction'],
                    electrons_per_baryon_from_reference=ye,ions_per_baryon_lower=yi,ions_per_baryon_upper=yi+dy,
                    reference_pressure_Pa=ref,ideal_pressure_lower_Pa=lo,ideal_pressure_upper_Pa=hi,
                    pressure_relative_lower=lo/ref-1,pressure_relative_upper=hi/ref-1))
            for row in (rows[0],rows[len(rows)//2],rows[-1]):
                expected=eos.mixture(row['temperature_K'],row['density_kg_m3'],row['ions_per_baryon_upper'],row['electrons_per_baryon_from_reference'])['pressure_Pa']
                assert math.isclose(expected,row['ideal_pressure_upper_Pa'],rel_tol=1e-12)
            path=folder/(name+'-ideal-EOS.json');path.write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
            r['comparison'].append(dict(model=name,path=path.relative_to(ROOT).as_posix(),sha256=sha(path),points=len(rows),
                radial_range=[rows[0]['r_over_Rsun'],rows[-1]['r_over_Rsun']],
                relative_difference_range=[min(x['pressure_relative_lower'] for x in rows),max(x['pressure_relative_upper'] for x in rows)],
                excluded=2001-len(rows)))
            persist();print(json.dumps(r['comparison'][-1]),flush=True)
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        plt.rcParams.update({'font.size':10})
        fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
        for name,color in [('GS98','#146d86'),('AGSS09','#c56f32')]:
            data=models[name];x=[v[0] for v in data['raw_values']]
            axes[0,0].plot(x,[d['temperature_K']/1e6 for d in data['derived']],color=color,label=name)
            axes[0,1].semilogy(x,[d['density_kg_m3'] for d in data['derived']],color=color,label=name)
            axes[1,0].plot(x,[v[18] for v in data['raw_values']],color=color,label=name+' H-1')
            axes[1,0].plot(x,[v[19] for v in data['raw_values']],color=color,linestyle='--',label=name+' He-4')
            comparison=next(c for c in r['comparison'] if c['model']==name);rows=json.loads((ROOT/comparison['path']).read_text())
            axes[1,1].fill_between([v['r_over_Rsun'] for v in rows],[v['pressure_relative_lower']*100 for v in rows],[v['pressure_relative_upper']*100 for v in rows],color=color,alpha=.35,label=name)
        for ax in axes.flat:ax.set_xlabel('r / R☉');ax.grid(alpha=.25);ax.legend(fontsize=8);ax.set_xlim(0,1)
        axes[0,0].set_ylabel('Temperatura de referência (MK)');axes[0,1].set_ylabel('Densidade de referência (kg/m³, log)')
        axes[1,0].set_ylabel('Fração mássica de referência');axes[1,1].set_ylabel('100 × (P ideal / P referência − 1) (%)')
        axes[1,1].set_xlim(0,.19);axes[1,1].set_title('Recorte no domínio da zona; intervalo conservador de íons',fontsize=10)
        fig.suptitle('Perfis solares B23 v1.2 · referência GarStEC, sem evolução pelo Cosmos2',fontsize=13)
        for suffix in ('png','svg'):
            path=folder/('B23-reference-comparison.'+suffix);fig.savefig(path,dpi=170)
            r['figures'].append(dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path)))
        plt.close(fig)
        assert all(sha(ROOT/n)==v for n,v in hashes.items())
        r.update(accepted=True,completed=True,EOS_generation=eos.generation(),
            scope='Validated reference import and declared ideal-EOS pressure bracket only. No zone initialization, solar calibration, transport, hydrostatic evolution or luminosity prediction.')
    except Exception:r['failure']=traceback.format_exc()
    persist();print(json.dumps({k:v for k,v in r.items() if k not in ('source_sha256','EOS_generation')}),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
