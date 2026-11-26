"""Standalone scientific figure of the isolated synthetic finite trajectories."""
from pathlib import Path
import json,math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
figure,axes=plt.subplots(2,1,figsize=(11,7),sharex=True,layout='constrained')
for axis,ratio,color in zip(axes,(2.,1.8),('#087f8c','#bd5d18')):
    document=json.loads((ROOT/f'output/c211-resonances-staging/dynamics-{ratio}.json').read_text())
    data=np.asarray(document['samples']);period=data[-1,0]/document['summary']['periods']
    phase=np.unwrap(data[:,1]);axis.plot(data[:,0]/period,phase/(2*math.pi),color=color,linewidth=.8)
    axis.set_ylabel('Ângulo crítico / 2π\n(desempacotado)')
    axis.set_title(f'Razão inicial {ratio:g}:1 · variação {np.ptp(phase)/(2*math.pi):.4g} voltas',loc='left',fontsize=11)
    axis.grid(alpha=.25)
axes[-1].set_xlabel('Tempo / período osculante externo inicial')
figure.suptitle('Três massas ativas · trajetórias sintéticas de 500 períodos',fontsize=14)
figure.text(.5,-.035,'Amostragem densa verificada para estes casos. Ângulos finitos não provam captura permanente.\nMassas canônicas: 1, 10⁻⁵ e 10⁻³; IAS15 ε=10⁻⁹. Sem operador de ressonância instalado.',ha='center',fontsize=9)
for extension in ('svg','png'):
    figure.savefig(ROOT/f'evidence/resonant-validation-prototype.{extension}',dpi=160,bbox_inches='tight')
print('Wrote evidence/resonant-validation-prototype.svg and .png')
