"""Export accepted prescribed-density trajectories; never rerun a simulation."""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True)
    parser.add_argument('--receipt',default='evidence/is5-compression-20261029b.json');args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    anchor=(ROOT/args.receipt).resolve();assert anchor.is_relative_to(ROOT)
    accepted=json.loads(anchor.read_text());assert accepted['accepted'] and accepted['completed']
    hashes=dict(accepted['source_sha256']);hashes[anchor.relative_to(ROOT).as_posix()]=sha(anchor)
    hashes[Path(__file__).relative_to(ROOT).as_posix()]=sha(Path(__file__))
    runs=[]
    for case in accepted['cases']:
        name=next(n for n in case['artifact_sha256'] if n.endswith('-Radau.json'))
        p=ROOT/name;assert sha(p)==case['artifact_sha256'][name]
        hashes[name]=sha(p);runs.append(json.loads(p.read_text()))
    assert len(runs)==3 and all(len(run['time_s'])==241 for run in runs)
    assert all(sha(ROOT/n)==value for n,value in hashes.items())
    folder=ROOT/f'output/is5-compression-figure-{args.label}'
    receipt=ROOT/f'evidence/is5-compression-figure-{args.label}.json'
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve compression figures')
    folder.mkdir();archive=folder/'executed-sources-and-data.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for name in hashes:z.write(ROOT/name,name)
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10})
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    colors=['#146d86','#c56f32','#7851a9']
    labels=['N14 · compressão 1000 anos','O16 · expansão 1000 anos','N14 · ciclo 1 ano, canais desligados']
    endpoints=[]
    for run,color,label in zip(runs,colors,labels):
        x=np.array(run['time_s'])/run['parameters']['duration_s']
        rho=np.array(run['density_kg_m3']);temp=np.array(run['temperature_K'])
        energy=np.array(run['internal_energy_J']);work=np.array(run['external_pressure_work_J'])
        q=np.array(run['non_neutrino_energy_available_J']);e0=run['initial_internal_energy_J']
        axes[0,0].plot(x,rho/rho[0],color=color,label=label)
        axes[0,1].plot(x,temp/temp[0],color=color,label=label)
        axes[1,0].plot(x,work/e0,color=color,label=label+' · W')
        axes[1,0].plot(x,(energy-energy[0])/e0,color=color,linestyle='--',linewidth=1.1)
        axes[1,1].plot(x,q/e0,color=color,label=label)
        endpoints.append(dict(label=label,T_initial_K=float(temp[0]),T_final_K=float(temp[-1]),
                              rho_ratio_final=float(rho[-1]/rho[0]),W_final_J=float(work[-1]),Q_retained_final_J=float(q[-1])))
    axes[0,0].set_ylabel('ρ / ρ inicial · intervenção prescrita')
    axes[0,1].set_ylabel('T / T inicial · resposta térmica')
    axes[1,0].set_ylabel('W / E₀ e ΔE / E₀')
    axes[1,1].set_ylabel('Q nuclear retido / E₀')
    axes[1,0].set_title('Contínuo: trabalho externo W; tracejado: Δ(VU)',fontsize=10)
    axes[1,1].ticklabel_format(axis='y',style='sci',scilimits=(-3,3))
    for ax in axes.flat:
        ax.set_xlabel('t / duração do programa');ax.set_xlim(0,1);ax.grid(alpha=.25)
        ax.legend(fontsize=8)
    fig.suptitle('Zona com densidade imposta · número bariônico fixo\nSem hidrodinâmica, evolução gravitacional ou calibração solar',fontsize=13)
    figures=[]
    for suffix in ['png','svg']:
        p=folder/('prescribed-density-work.'+suffix);fig.savefig(p,dpi=200)
        figures.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)))
    plt.close(fig)
    assert all(sha(ROOT/n)==value for n,value in hashes.items())
    result=dict(accepted=True,visual_review_pending=True,source_sha256=hashes,archive_sha256=sha(archive),
                figures=figures,states_per_case=241,endpoint_values=endpoints,
                libraries=dict(matplotlib=matplotlib.__version__,numpy=np.__version__),
                scope='Plot of accepted trajectory data only. Every case has its own initial T/rho/E0; no new integration or observational uncertainty claim.')
    receipt.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(figures=figures,visual_review_pending=True)),flush=True)


if __name__=='__main__':main()
