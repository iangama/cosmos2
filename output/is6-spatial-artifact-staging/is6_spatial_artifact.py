"""Immutable spatial body artifact, exact probes and sealed atomic persistence."""
from pathlib import Path
from contextlib import contextmanager
import copy
import hashlib
import json
import os
import sys
import time
import uuid

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
sys.path.insert(0,str(ROOT/'output/is6-body-binding-staging'))
import is6_body_source as body
spatial=body.spatial
MAX_BYTES=16*1024*1024
FILES=[Path(__file__),ROOT/'IS-6-ARTEFATO-CONTRATO-PREVIO.md',ROOT/'evidence/is6-body-source-20261101a.json']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
IMPORTED={p.relative_to(ROOT).as_posix():sha(p) for p in FILES}
DEFAULT_CONFIGURATION=dict(inner_radius_boundary_units=1.,outer_radius_boundary_units=8.,radial_count=65,
                           azimuth_sectors=96,orientation=copy.deepcopy(spatial.IDENTITY),vertical_amplification=200.)


def encoded(value):return json.dumps(value,sort_keys=True,ensure_ascii=True,allow_nan=False).encode()
def digest(value):return hashlib.sha256(encoded(value)).hexdigest()


def generation():
    if any(sha(ROOT/n)!=v for n,v in IMPORTED.items()):raise ValueError('Restart after spatial-artifact source changes')
    acceptance=json.loads((ROOT/'evidence/is6-body-source-20261101a.json').read_text())
    current=body.generation()
    if not acceptance['accepted'] or acceptance['generation']!=current:raise ValueError('Accepted body-reference generation required')
    return dict(schema=1,id='cosmos2:is6-immutable-spatial-body-mesh',version='0.1.0',source_sha256=dict(IMPORTED),body_reference=current)


def identity(value):
    if not isinstance(value,str) or len(value)!=32 or any(c not in '0123456789abcdef' for c in value):raise ValueError('Spatial artifact identity differs')
    return value


def configuration(value):
    if not isinstance(value,dict) or set(value)!=set(DEFAULT_CONFIGURATION):raise ValueError('Complete spatial configuration required')
    a=spatial.number(value['inner_radius_boundary_units']);b=spatial.number(value['outer_radius_boundary_units'])
    amp=spatial.number(value['vertical_amplification']);nr,na=value['radial_count'],value['azimuth_sectors']
    basis=spatial.orientation(value['orientation'])
    if not 1<=a<b<=100 or not 0<=amp<=1000:raise ValueError('Spatial display/domain options outside adopted limits')
    if type(nr) is not int or nr not in [33,65,129,257] or type(na) is not int or na!=96:raise ValueError('Spatial resolution outside adopted budget')
    return dict(inner_radius_boundary_units=a,outer_radius_boundary_units=b,radial_count=nr,
                azimuth_sectors=na,orientation=basis,vertical_amplification=amp)


def view(value,config):
    keys={'visible','selected_radial_index','selected_azimuth_index','reference_radial_index'}
    if not isinstance(value,dict) or set(value)!=keys or type(value['visible']) is not bool:raise ValueError('Complete explicit spatial view required')
    for key,maximum in [('selected_radial_index',config['radial_count']),('reference_radial_index',config['radial_count']),('selected_azimuth_index',config['azimuth_sectors'])]:
        if type(value[key]) is not int or not 0<=value[key]<maximum:raise ValueError('Spatial probe index outside mesh')
    return dict(value)


class Run:
    @classmethod
    def create(cls,phase,selection,options):
        gen=generation();config=configuration(options);binding=body.bind(phase,selection)
        boundary=binding['source_configuration']['material_radius_m']
        mesh=spatial.mesh(binding['source_configuration'],dict(inner_radius_m=config['inner_radius_boundary_units']*boundary,
            outer_radius_m=config['outer_radius_boundary_units']*boundary,radial_count=config['radial_count'],
            azimuth_sectors=config['azimuth_sectors'],orientation=config['orientation'],center_m=binding['center_render_m'],
            vertical_amplification=config['vertical_amplification']))
        if generation()!=gen:raise ValueError('Spatial generation changed during construction')
        self=cls();self._payload=dict(schema=1,kind='is6_spatial_body_mesh_artifact',id=uuid.uuid4().hex,
            generation=gen,phase=copy.deepcopy(phase),selection=copy.deepcopy(selection),configuration=config,binding=binding,mesh=mesh)
        return self

    @property
    def payload(self):return copy.deepcopy(self._payload)

    @property
    def id(self):return self._payload['id']

    def default_view(self):
        return dict(visible=True,selected_radial_index=0,selected_azimuth_index=0,reference_radial_index=self._payload['configuration']['radial_count']-1)

    def sample(self,preferences):
        p=self._payload
        if generation()!=p['generation']:raise ValueError('Spatial artifact generation differs')
        v=view(preferences,p['configuration']);geometry=p['mesh'];i=v['selected_radial_index'];j=v['selected_azimuth_index']
        radius=geometry['meridian_radius_m'][i];reference=geometry['meridian_radius_m'][v['reference_radial_index']]
        index=i*geometry['vertices_per_ring']+j;source=p['binding']['source_configuration']
        return dict(view=v,radius_m=radius,azimuth_rad=2*spatial.math.pi*j/p['configuration']['azimuth_sectors'],
            metric=spatial.sample(source,radius),radial_distance=spatial.radial_distance(source,geometry['meridian_radius_m'][0],radius),
            static_clock_comparison=spatial.compare_clocks(source,radius,reference),
            physical_position_relative_m=list(geometry['physical_vertices_relative_m'][index]),
            displayed_position_relative_m=list(geometry['display_vertices_relative_m'][index]),
            source_center_render_m=list(p['binding']['center_render_m']),sampling='Exact mesh ring/azimuth; intrinsic metric independent of display amplification.')

    @classmethod
    def restore(cls,payload):
        keys={'schema','kind','id','generation','phase','selection','configuration','binding','mesh'}
        if not isinstance(payload,dict) or set(payload)!=keys or type(payload['schema']) is not int or payload['schema']!=1 or payload['kind']!='is6_spatial_body_mesh_artifact':raise ValueError('Spatial artifact schema differs')
        identity(payload['id'])
        if payload['generation']!=generation():raise ValueError('Spatial artifact generation differs')
        candidate=cls.create(payload['phase'],payload['selection'],payload['configuration'])
        for key in keys-{'id'}:
            if digest(candidate._payload[key])!=digest(payload[key]):raise ValueError('Recomputed spatial artifact differs:'+key)
        candidate._payload['id']=payload['id'];return candidate


class Store:
    def __init__(self,folder):
        self.folder=Path(folder).resolve()
        if not self.folder.is_relative_to((ROOT/'output').resolve()):raise ValueError('Spatial records must remain under output')
        self.folder.mkdir(parents=True,exist_ok=True);self.branches=self.folder/'branches';self.branches.mkdir(exist_ok=True)
        self.path=self.folder/'saved.json'

    def checked_path(self,path):
        p=Path(path).resolve()
        if not p.is_relative_to(self.folder):raise ValueError('Spatial record escaped its store')
        return p

    @staticmethod
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate spatial JSON key')
            result[key]=value
        return result

    @contextmanager
    def writer(self):
        lock=self.checked_path(self.folder/'writer.lock')
        with lock.open('a+b') as handle:
            if handle.tell()==0:handle.write(b'0');handle.flush()
            until=time.monotonic()+2
            while True:
                try:
                    handle.seek(0)
                    if os.name=='nt':
                        import msvcrt
                        msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
                    else:
                        import fcntl
                        fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.monotonic()>=until:raise
                    time.sleep(.01)
            try:yield
            finally:
                handle.seek(0)
                if os.name=='nt':msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
                else:fcntl.flock(handle.fileno(),fcntl.LOCK_UN)

    def atomic(self,path,value):
        path=self.checked_path(path);text=json.dumps(value,sort_keys=True,ensure_ascii=True,allow_nan=False,indent=2)+'\n'
        if len(text.encode())>MAX_BYTES:raise ValueError('Spatial record byte budget exceeded')
        temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
        try:
            with temporary.open('x',encoding='utf-8',newline='\n') as f:f.write(text);f.flush();os.fsync(f.fileno())
            until=time.monotonic()+2
            while True:
                try:os.replace(temporary,path);break
                except PermissionError:
                    if time.monotonic()>=until:raise
                    time.sleep(.01)
        finally:temporary.unlink(missing_ok=True)

    def save(self,run,preferences,*,name=None,parent=None):
        if not isinstance(run,Run):raise ValueError('Accepted spatial Run required')
        if run._payload['generation']!=generation():raise ValueError('Spatial generation differs')
        preferences=view(preferences,run._payload['configuration'])
        with self.writer():
            if parent is not None:
                identity(parent);self._read(parent)
            branch=None;path=self.path;lineage=parent
            if name is not None:
                if not isinstance(name,str) or not 1<=len(name.strip())<=80:raise ValueError('Spatial branch name must have1..80characters')
                if len(list(self.branches.glob('*.json')))>=32:raise ValueError('Spatial branch limit32 reached')
                branch=dict(id=uuid.uuid4().hex,parent=parent,name=name.strip());lineage=branch['id'];path=self.branches/(branch['id']+'.json')
            payload=dict(schema=1,kind='is6_spatial_body_mesh_checkpoint',artifact=run.payload,view=preferences,branch=branch,lineage_parent=lineage)
            record={**payload,'record_sha256':digest(payload)};self.atomic(path,record)
        return dict(path=str(path),record_sha256=record['record_sha256'],branch=copy.deepcopy(branch),lineage_parent=lineage)

    def _read(self,branch_id=None):
        if branch_id is not None:identity(branch_id)
        path=self.checked_path(self.path if branch_id is None else self.branches/(branch_id+'.json'))
        if path.stat().st_size>MAX_BYTES:raise ValueError('Spatial record byte budget exceeded')
        record=json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=self.unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite spatial JSON')))
        keys={'schema','kind','artifact','view','branch','lineage_parent','record_sha256'}
        if not isinstance(record,dict) or set(record)!=keys or type(record['schema']) is not int or record['schema']!=1 or record['kind']!='is6_spatial_body_mesh_checkpoint':raise ValueError('Spatial checkpoint schema differs')
        if digest({k:v for k,v in record.items() if k!='record_sha256'})!=record['record_sha256']:raise ValueError('Spatial checkpoint seal differs')
        lineage=record['lineage_parent'];branch=record['branch']
        if lineage is not None:
            identity(lineage)
            if not (self.branches/(lineage+'.json')).is_file():raise ValueError('Spatial lineage parent unavailable')
        if branch_id is None:
            if branch is not None:raise ValueError('Main spatial checkpoint cannot masquerade as branch')
        else:
            if not isinstance(branch,dict) or set(branch)!={'id','parent','name'} or branch['id']!=branch_id or lineage!=branch_id:raise ValueError('Spatial branch identity differs')
            if not isinstance(branch['name'],str) or not 1<=len(branch['name'])<=80 or branch['name']!=branch['name'].strip():raise ValueError('Spatial branch name differs')
            parent=branch['parent']
            if parent is not None:
                identity(parent)
                if parent==branch_id or not (self.branches/(parent+'.json')).is_file():raise ValueError('Spatial branch parent unavailable')
        artifact=record['artifact']
        if not isinstance(artifact,dict) or artifact.get('generation')!=generation():raise ValueError('Spatial saved generation differs')
        identity(artifact.get('id'));view(record['view'],configuration(artifact.get('configuration')))
        return record

    def load(self,branch_id=None):
        record=self._read(branch_id);candidate=Run.restore(record['artifact'])
        return candidate,view(record['view'],candidate._payload['configuration']),record['lineage_parent']

    def catalog(self):
        result=[]
        for path in sorted(self.branches.glob('*.json'))[:32]:
            try:
                record=self._read(path.stem);result.append({**record['branch'],'artifact_id':record['artifact']['id'],'view':record['view'],'valid':True,'validation':'Seal/generation only; mesh is recomputed on restore.'})
            except Exception as error:result.append(dict(id=path.stem,name='Arquivo inválido',valid=False,error=str(error)))
        return result

    def export(self,run,preferences,parent=None):
        folder=self.folder/'exports';folder.mkdir(exist_ok=True)
        with self.writer():
            if parent is not None:identity(parent);self._read(parent)
            payload=dict(schema=1,kind='is6_spatial_body_mesh_checkpoint',artifact=run.payload,
                         view=view(preferences,run._payload['configuration']),branch=None,lineage_parent=parent)
            record={**payload,'record_sha256':digest(payload)};path=folder/(uuid.uuid4().hex+'.json');self.atomic(path,record)
        return dict(path=str(path),record_sha256=record['record_sha256'])
