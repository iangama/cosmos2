"""One focusable selection anchor bound to the exact native-confirmed cloud instant."""
from pathlib import Path
import math
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())

def selected_nodes(confirmation,point,parent):
    if not isinstance(confirmation,dict) or confirmation.get('state')!='accepted' or not confirmation.get('gpu_buffer_uploaded'):
        raise ValueError('Aguarde a confirmação do pacote pela cena nativa.')
    m=confirmation['metadata']
    for key in ('system_id','edit_token','cloud_id','source_id','frame','time_model'):
        if point.get(key)!=m.get(key):raise ValueError('Leitura individual e cena têm identidades ou instantes diferentes.')
    index=point.get('index')
    if type(index) is not int or not 0<=index<m['count'] or point.get('id')!='tp:'+m['cloud_id']+':'+str(index):
        raise ValueError('Identidade individual fora da população confirmada.')
    r=point.get('position_m')
    if not isinstance(r,list) or len(r)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in r) or math.hypot(*r)>1e17:
        raise ValueError('Posição individual SI inválida.')
    anchor={'Identifier':'C2CloudSelection','Parent':parent,
        'Transform':{'Translation':{'Type':'StaticTranslation','Position':r}},
        'Renderable':{'Type':'RenderableSphereImageLocal','Size':2e7,'Segments':12,
            'Texture':(ROOT/'data/markers/orbiter.ppm').as_posix()},
        'GUI':{'Name':'Partícula de teste '+str(index)}}
    label={'Identifier':'C2CloudSelectionLabel','Parent':'C2CloudSelection',
        'Transform':{'Translation':{'Type':'StaticTranslation','Position':[0.,0.,3e7]}},
        'Renderable':{'Type':'RenderableLabel','Text':'tp '+str(index),'FontSize':40,'Size':6,
            'MinMaxSize':[12,18],'OrientationOption':'Camera View Direction','EnableFading':False},
        'GUI':{'Name':'Seleção individual','Focusable':False}}
    return [anchor,label]
