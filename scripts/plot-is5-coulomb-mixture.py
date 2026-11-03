"""Plot only frozen accepted EOS fixtures; no scientific recomputation."""
from pathlib import Path
import hashlib
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

ROOT = Path(__file__).resolve().parents[1]
receipt = ROOT/'evidence/is5-coulomb-mixture-20261028b.json'
source = json.loads(receipt.read_text(encoding='utf-8'))
assert source['accepted']
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert all(sha(ROOT/n) == h for n,h in source['source_sha256'].items())
folder = ROOT/'output/is5-coulomb-mixture-figure-20261028a'
if folder.exists():
    raise FileExistsError('Preserve EOS figures')
folder.mkdir()
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'axes.titlesize':13,
                     'axes.labelsize':12,'xtick.labelsize':11,'ytick.labelsize':11,
                     'savefig.facecolor':'white'})
fig, axes = plt.subplots(2,2,figsize=(16,10),sharex=True,sharey=True)
labels = {'ii':'Íon–íon','ie':'Íon–elétron','ee':'Elétron–elétron','mix':'Mistura não linear','sum':'Total'}
colors = {'ii':'#275d9c','ie':'#a35913','ee':'#8555a4','mix':'#2c7f62','sum':'#111b29'}
data = []
for row, seed in enumerate([7,13]):
    for col, density in enumerate([1.1e4,1.5e5]):
        ax = axes[row,col]
        cases = sorted([v for v in source['cases'] if v['fixture']['Y'][seed] > 0 and v['fixture']['rho'] == density],key=lambda v:v['fixture']['T'])
        assert len(cases) == 3
        t = [v['fixture']['T']/1e6 for v in cases]
        for component in ['ii','ie','ee','mix','sum']:
            values = [100*v['EOS']['components'][component]['pressure_Pa']/v['EOS']['ideal']['pressure_Pa'] for v in cases]
            ax.plot(t,values,label=labels[component],color=colors[component],
                    linewidth=2.6 if component == 'sum' else 1.7,
                    marker='o' if component == 'sum' else '.',markersize=6,
                    linestyle='-' if component == 'sum' else '--')
            data.append(dict(seed='N14' if seed == 7 else 'O16',density_kg_m3=density,
                             component=component,temperature_MK=t,pressure_over_ideal_percent=values))
        composition = 'H=0,34 · N14=0,01' if seed == 7 else 'H=0,70 · O16=0,02'
        ax.set_title(f'{composition} | ρ={density/1e3:g} × 10³ kg/m³',pad=12)
        ax.axhline(0,color='#6e7780',linewidth=.9)
        ax.grid(True,color='#dfe3e8',linewidth=.7,alpha=.8)
        ax.set_axisbelow(True)
        ax.spines[['top','right']].set_visible(False)
        ax.set_xticks([11,15,28])
        ax.yaxis.set_major_locator(MaxNLocator(6))
        if row == 1:
            ax.set_xlabel('Temperatura (MK)')
        if col == 0:
            ax.set_ylabel('Contribuição de pressão / P ideal (%)')
fig.suptitle('Coulomb: de onde vem a correção de pressão',fontsize=20,y=.975,fontweight='bold')
fig.text(.5,.925,'12 estados numéricos aceitos · H/He totalmente ionizado com sementes N14/O16',ha='center',fontsize=13)
fig.text(.5,.895,'Íons clássicos + resposta eletrônica dos ajustes PC/EXCOR7; ideal FD + radiação confinada como referência.',ha='center',fontsize=12,color='#334155')
handles, names = axes[0,0].get_legend_handles_labels()
fig.legend(handles,names,loc='lower center',bbox_to_anchor=(.5,.065),ncol=5,frameon=False,fontsize=12)
fig.text(.5,.045,'As linhas ligam amostras; não representam ajuste nem intervalo de incerteza. Estes fixtures não são um perfil observado do Sol.',ha='center',fontsize=11,color='#334155')
fig.text(.5,.02,'Fonte: is5-coulomb-mixture-20261028b · modelo PC clássico, geração 0.1.0 · sem evolução, transporte ou calibração solar.',ha='center',fontsize=10,color='#536171')
fig.subplots_adjust(left=.08,right=.98,top=.835,bottom=.165,hspace=.30,wspace=.13)
png, svg = folder/'pressure-components.png', folder/'pressure-components.svg'
fig.savefig(png,dpi=150)
fig.savefig(svg)
plt.close(fig)
manifest = dict(accepted=False,numerical_source_accepted=True,visual_review_pending=True,
                source_receipt=receipt.relative_to(ROOT).as_posix(),source_receipt_sha256=sha(receipt),
                script_sha256=sha(Path(__file__)),data=data,
                outputs_sha256={p.name:sha(p) for p in [png,svg]},
                scope='Frozen fixture visualization; no new model evaluation, fit or observational comparison.')
(folder/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(png=str(png),svg=str(svg),series=len(data)),ensure_ascii=False))
