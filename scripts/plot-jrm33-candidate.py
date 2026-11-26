"""Standalone scientific maps in the validated model frame, without scene claims."""
from pathlib import Path
import hashlib
import json
import math
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'output/is3-jrm33-staging'))
import jrm33
folder=ROOT/'output/is3-jrm33-figures-20261023'
if folder.exists():raise FileExistsError('Preserve prior figures.')
folder.mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
acceptance=json.loads((ROOT/'evidence/is3-jrm33-check-20261023a.json').read_text(encoding='utf-8'))
assert acceptance['accepted'] and sha(ROOT/'output/is3-jrm33-staging/jrm33.py')==acceptance['source_sha256']['output/is3-jrm33-staging/jrm33.py']
longitude=np.linspace(-math.pi,math.pi,73);latitude=np.linspace(-math.pi/2,math.pi/2,37)
strength=[];difference=[];radial=[]
for lat in latitude:
    strength_row=[];difference_row=[];radial_row=[]
    for lon in longitude:
        theta=math.pi/2-lat;phi=lon%(2*math.pi)
        position=[jrm33.R*math.cos(lat)*math.cos(phi),jrm33.R*math.cos(lat)*math.sin(phi),jrm33.R*math.sin(lat)]
        a=jrm33.sample(position,13);b=jrm33.sample(position,18)
        strength_row.append(a['field_norm_T']*1e4)
        radial_row.append(a['field_spherical_T'][0]*1e4)
        difference_row.append(math.dist(a['field_SystemIII_T'],b['field_SystemIII_T'])/a['field_norm_T']*100)
    strength.append(strength_row);difference.append(difference_row);radial.append(radial_row)
strength,difference,radial=map(np.array,[strength,difference,radial])
fig,axes=plt.subplots(1,2,figsize=(12,5),subplot_kw={'projection':'mollweide'},constrained_layout=True)
for ax,values,title,label,cmap in [(axes[0],strength,'Componente interna: intensidade em grau13','|B| (Gauss)','viridis'),
    (axes[1],difference,'Diferença vetorial entre graus18 e13','|B18 − B13| / |B13| (%)','magma')]:
    surface=ax.pcolormesh(longitude,latitude,values,cmap=cmap,shading='auto')
    ax.grid(alpha=.3);ax.set_title(title,fontsize=11)
    ax.set_xlabel('Longitude leste, SistemaIII(1965)');ax.set_ylabel('Latitude geocêntrica')
    fig.colorbar(surface,ax=ax,orientation='horizontal',pad=.14,shrink=.9,label=label)
fig.suptitle('JRM33 · esfera de raio1Rj = 71.492 km · coeficientes da época2019',fontsize=13)
fig.supxlabel('Modelo estático interno; sem correntes externas ou achatamento. Diferença de truncamento não é incerteza observacional.\n'
              'Coeficientes: Connerney et al.(2022), PDS JRM33.MOD. Síntese própria verificada contraPSH; somente staging.',fontsize=9)
for extension in ['png','pdf','svg']:fig.savefig(folder/('jrm33-grau13-comparacao18.'+extension),dpi=180)
plt.close(fig)
data=folder/'sampled-model-grid.json'
data.write_text(json.dumps({'longitude_east_rad':longitude.tolist(),'geocentric_latitude_rad':latitude.tolist(),
    'radius_m':jrm33.R,'B13_magnitude_G':strength.tolist(),'B13_radial_G':radial.tolist(),
    'vector_difference_18_13_percent':difference.tolist()},allow_nan=False)+'\n',encoding='utf-8')
report={'schema':1,'script_sha256':sha(Path(__file__)),'model_sha256':sha(ROOT/'output/is3-jrm33-staging/jrm33.py'),
    'coefficients_sha256':jrm33.DATA_SHA,'grid_points':strength.size,
    'B13_magnitude_range_G':[float(strength.min()),float(strength.max())],
    'vector_difference_18_13_percent_max':float(difference.max()),
    'files':{p.relative_to(ROOT).as_posix():sha(p) for p in folder.iterdir()},
    'scope':'Model-frame numerical illustration; not Jupiter texture, observations, scene orientation or native rendering acceptance.'}
(folder/'provenance.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='files'}))
