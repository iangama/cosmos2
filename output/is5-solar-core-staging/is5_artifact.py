"""Immutable calculated scenario and one atomic sealed scenario+view checkpoint."""
from pathlib import Path
import copy
import hashlib
import json
import os
import time
import uuid
from is5_core import integrate_zone,generation as core_generation,parameters,active_channels
from is5_solar_source import bind,validate,digest

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
HERE=Path(__file__).resolve().parent
MAX_BYTES=16*1024*1024
IMPORTED={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ['is5_artifact.py','is5_solar_source.py']}

def identity(value):
    if not isinstance(value,str) or len(value)!=32 or any(c not in '0123456789abcdef' for c in value):raise ValueError('Artifact identity invalid')
    return value

def generation():
    if any(hashlib.sha256((HERE/n).read_bytes()).hexdigest()!=v for n,v in IMPORTED.items()):raise ValueError('Restart after artifact/source changes')
    return dict(core=core_generation(),artifact_code_sha256=dict(IMPORTED),schema=1)

def index(value):
    if type(value) is not int or not 0<=value<=240:raise ValueError('Calculated sample index must be0..240')
    return value

def view(value):
    if not isinstance(value,dict) or set(value)!={'selected_index','visible'}:raise ValueError('Complete calculated-sample view required')
    i=index(value['selected_index']);v=value['visible']
    if not isinstance(v,dict) or set(v)!={'composition','energy','neutrinos','reference'} or any(type(x) is not bool for x in v.values()):raise ValueError('Explicit view flags required')
    return dict(selected_index=i,visible=dict(v))

DEFAULT_VIEW=dict(selected_index=0,visible=dict(composition=True,energy=True,neutrinos=True,reference=True))

class Run:
    @classmethod
    def create(cls,source_phase,configuration):
        if not isinstance(configuration,dict) or set(configuration)!={'parameters','acting','channel_switches','decay_basis'}:raise ValueError('Complete nuclear scenario configuration required')
        p=parameters(configuration['parameters']);a,c,enabled=active_channels(configuration['acting'],configuration['channel_switches']);basis=configuration['decay_basis']
        source=bind(source_phase);gen=generation()
        actual=integrate_zone(p,a,c,decay_basis=basis)
        reference=actual if all(enabled.values()) else integrate_zone(p,decay_basis=basis)
        if generation()!=gen:raise ValueError('Scientific generation changed during scenario calculation')
        self=cls();self._payload=dict(schema=1,kind='is5_calculated_solar_scenario',id=uuid.uuid4().hex,scientific_generation=gen,source_phase=copy.deepcopy(source_phase),source=source,
            configuration=dict(parameters=p,acting=a,channel_switches=c,decay_basis=basis),actual=actual,reference=reference)
        return self

    @property
    def id(self):return self._payload['id']

    @property
    def payload(self):return copy.deepcopy(self._payload)

    @classmethod
    def restore(cls,payload):
        if not isinstance(payload,dict) or set(payload)!={'schema','kind','id','scientific_generation','source_phase','source','configuration','actual','reference'} or type(payload['schema']) is not int or payload['schema']!=1 or payload['kind']!='is5_calculated_solar_scenario':raise ValueError('Nuclear artifact schema differs')
        identity(payload['id'])
        if payload['scientific_generation']!=generation():raise ValueError('Nuclear artifact generation differs; migration required')
        validate(payload['source_phase'],payload['source'])
        candidate=cls.create(payload['source_phase'],payload['configuration'])
        for key in ['scientific_generation','source','configuration','actual','reference']:
            if digest(candidate._payload[key])!=digest(payload[key]):raise ValueError('Recomputed nuclear artifact differs: '+key)
        candidate._payload['id']=payload['id'];return candidate

    def sample(self,selected_index):
        i=index(selected_index)
        def at(network):
            names=network['species'];channels=network['channels']
            return dict(time_s=network['time_s'][i],mass_fractions=dict(zip(names,network['mass_fractions'][i])),number_per_baryon=dict(zip(names,network['number_per_baryon'][i])),
                event_rates_m3_s=dict(zip(channels,network['event_rates_m3_s'][i])),reaction_extents_m3=dict(zip(channels,network['reaction_extents_m3'][i])),
                energy_available_J_m3=network['energy_available_J_m3'][i],energy_neutrinos_J_m3=network['energy_neutrinos_J_m3'][i],non_neutrino_energy_available_J_m3=network['non_neutrino_energy_available_J_m3'][i],
                nuclear_power_W_m3=network['nuclear_power_W_m3'][i],neutrino_power_W_m3=network['neutrino_power_W_m3'][i],neutrino_count_m3=network['neutrino_count_m3'][i],
                produced_positrons_m3=network['produced_positrons_m3'][i],annihilated_electrons_m3=network['annihilated_electrons_m3'][i],electron_fraction=network['electron_fraction'][i])
        return dict(index=i,sampling='Exact calculated knot among241; no interpolated or realtime-integration claim.',actual=at(self._payload['actual']),reference=at(self._payload['reference']))

class Store:
    def __init__(self,folder):
        self.folder=Path(folder).resolve()
        if not self.folder.is_relative_to((ROOT/'output').resolve()):raise ValueError('Nuclear checkpoints must remain under output')
        self.folder.mkdir(parents=True,exist_ok=True);self.branches=self.folder/'branches';self.branches.mkdir(exist_ok=True)

    @property
    def path(self):return self.folder/'saved.json'

    @staticmethod
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate nuclear JSON key')
            result[key]=value
        return result

    @staticmethod
    def atomic(path,value):
        text=json.dumps(value,sort_keys=True,ensure_ascii=True,allow_nan=False,indent=2)+'\n'
        if len(text.encode())>MAX_BYTES:raise ValueError('Nuclear record byte budget exceeded')
        path=Path(path);tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
        try:
            with tmp.open('x',encoding='utf-8',newline='\n') as f:f.write(text);f.flush();os.fsync(f.fileno())
            until=time.monotonic()+2.
            while True:
                try:os.replace(tmp,path);break
                except PermissionError:
                    if time.monotonic()>=until:raise
                    time.sleep(.01)
        finally:tmp.unlink(missing_ok=True)

    def save(self,run,preferences,*,name=None,parent=None):
        if not isinstance(run,Run):raise ValueError('Accepted calculated artifact required')
        branch=None;path=self.path
        if name is not None:
            if len(list(self.branches.glob('*.json')))>=32:raise ValueError('Nuclear branch limit32 reached')
            if not isinstance(name,str) or not 1<=len(name.strip())<=80:raise ValueError('Branch name must have1..80 characters')
            if parent is not None:
                identity(parent)
                if not (self.branches/(parent+'.json')).is_file():raise ValueError('Nuclear parent branch unavailable')
            branch=dict(id=uuid.uuid4().hex,parent=parent,name=name.strip());path=self.branches/(branch['id']+'.json')
        payload=dict(schema=1,kind='is5_solar_checkpoint',run=run.payload,view=view(preferences),branch=branch)
        record={**payload,'record_sha256':digest(payload)};self.atomic(path,record)
        return dict(path=str(path),record_sha256=record['record_sha256'],branch=branch)

    def _read(self,branch_id=None):
        if branch_id is not None:identity(branch_id)
        path=self.path if branch_id is None else self.branches/(branch_id+'.json')
        if path.stat().st_size>MAX_BYTES:raise ValueError('Saved nuclear record exceeds byte budget')
        record=json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=self.unique)
        if not isinstance(record,dict) or set(record)!={'schema','kind','run','view','branch','record_sha256'} or type(record['schema']) is not int or record['schema']!=1 or record['kind']!='is5_solar_checkpoint':raise ValueError('Nuclear checkpoint schema differs')
        if digest({k:v for k,v in record.items() if k!='record_sha256'})!=record['record_sha256']:raise ValueError('Nuclear checkpoint seal differs')
        branch=record['branch']
        if branch_id is None:
            if branch is not None:raise ValueError('Main checkpoint cannot masquerade as branch')
        else:
            if not isinstance(branch,dict) or set(branch)!={'id','parent','name'} or branch['id']!=branch_id:raise ValueError('Nuclear branch identity differs')
            if branch['parent'] is not None:identity(branch['parent'])
            if branch['parent']==branch_id or not isinstance(branch['name'],str) or not 1<=len(branch['name'])<=80 or branch['name'].strip()!=branch['name']:raise ValueError('Nuclear branch label/parent invalid')
        view(record['view']);identity(record['run']['id'])
        if record['run']['scientific_generation']!=generation():raise ValueError('Saved nuclear generation differs')
        return record

    def load(self,branch_id=None):
        record=self._read(branch_id);candidate=Run.restore(record['run'])
        return candidate,view(record['view']),copy.deepcopy(record['branch'])

    def catalog(self):
        result=[]
        for file in sorted(self.branches.glob('*.json'))[:32]:
            try:
                record=self._read(file.stem);result.append({**record['branch'],'artifact_id':record['run']['id'],'selected_index':record['view']['selected_index'],'valid':True,'validation':'Seal and generation checked; full physics recomputed on load.'})
            except Exception as error:result.append(dict(id=file.stem,name='Arquivo inválido',valid=False,error=str(error)))
        return result
