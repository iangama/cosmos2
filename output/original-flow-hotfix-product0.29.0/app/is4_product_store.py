"""One sealed atomic record for scientific checkpoint and view; immutable bounded branches."""
from pathlib import Path
import copy
import json
import os
import tempfile
import time
import uuid
from is4_body_snapshot import digest
from is4_experiment import Experiment
from is4_particle_scene import identity
from is4_values import scalar
from is4_trajectory_transport import unique_pairs

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
MAX_BYTES=4*1024*1024


class Store:
    def __init__(self,folder):
        self.folder=Path(folder).resolve()
        if not self.folder.is_relative_to((ROOT/'output').resolve()):raise ValueError('Product checkpoint must remain under output')
        self.folder.mkdir(parents=True,exist_ok=True);self.branches=self.folder/'branches';self.branches.mkdir(exist_ok=True)

    @property
    def path(self):return self.folder/'saved.json'

    @staticmethod
    def view(value):
        if not isinstance(value,dict) or set(value)!={'physical_unit_m','visible'} or type(value['visible']) is not bool:raise ValueError('Complete physical plot scale and visibility required')
        unit=scalar(value['physical_unit_m'])
        if not 1e-12<=unit<=1e12:raise ValueError('Saved plotting scale outside adopted bounds')
        return {'physical_unit_m':unit,'visible':value['visible']}

    def _science(self,value):
        # Reuse the full scientific validator, including paired positions/work/source seals.
        with tempfile.TemporaryDirectory(prefix='.validate-',dir=self.folder) as folder:
            path=Path(folder)/'latest.json';path.write_text(json.dumps(value,allow_nan=False),encoding='utf-8')
            return Experiment.load(folder)

    def _validate(self,record,branch_id=None):
        if not isinstance(record,dict) or set(record)!={'schema','kind','particle','view','branch','record_sha256'} or type(record['schema']) is not int or record['schema']!=1 or record['kind']!='is4_product_checkpoint':raise ValueError('Product checkpoint schema differs')
        payload={k:v for k,v in record.items() if k!='record_sha256'}
        if digest(payload)!=record['record_sha256']:raise ValueError('Product checkpoint seal differs')
        self.view(record['view']);branch=record['branch']
        if branch_id is None:
            if branch is not None:raise ValueError('Main checkpoint cannot masquerade as branch')
        else:
            identity(branch_id)
            if not isinstance(branch,dict) or set(branch)!={'id','parent','name'} or branch['id']!=branch_id:raise ValueError('Branch identity differs')
            if branch['parent'] is not None:identity(branch['parent'])
            if branch['parent']==branch_id or not isinstance(branch['name'],str) or not 1<=len(branch['name'])<=80 or branch['name'].strip()!=branch['name']:raise ValueError('Branch label/parent invalid')
        return self._science(record['particle'])

    def _atomic(self,path,record):
        text=json.dumps(record,sort_keys=True,ensure_ascii=True,allow_nan=False,indent=2)+'\n'
        if len(text.encode('utf-8'))>MAX_BYTES:raise ValueError('Product checkpoint exceeds byte budget')
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
        try:
            with temporary.open('x',encoding='utf-8',newline='\n') as stream:stream.write(text);stream.flush();os.fsync(stream.fileno())
            deadline=time.monotonic()+2.
            while True:
                try:os.replace(temporary,path);break
                except PermissionError:
                    if time.monotonic()>=deadline:raise
                    time.sleep(.01)
        finally:temporary.unlink(missing_ok=True)

    def save(self,particle,view,*,name=None,parent=None):
        branch=None;path=self.path
        if name is not None:
            if len(list(self.branches.glob('*.json')))>=32:raise ValueError('Limite de32ramos atingido.')
            if not isinstance(name,str) or not 1<=len(name.strip())<=80:raise ValueError('Nome do ramo deve ter1a80caracteres.')
            if parent is not None:
                identity(parent)
                if not (self.branches/(parent+'.json')).is_file():raise ValueError('Ramo pai indisponível.')
            branch={'id':uuid.uuid4().hex,'parent':parent,'name':name.strip()};path=self.branches/(branch['id']+'.json')
        payload={'schema':1,'kind':'is4_product_checkpoint','particle':copy.deepcopy(particle),'view':self.view(view),'branch':branch}
        record={**payload,'record_sha256':digest(payload)}
        self._validate(record,None if branch is None else branch['id'])
        self._atomic(path,record)
        return {'path':str(path),'record_sha256':record['record_sha256'],'branch':branch}

    def load(self,branch_id=None):
        if branch_id is not None:identity(branch_id)
        path=self.path if branch_id is None else self.branches/(branch_id+'.json')
        if path.stat().st_size>MAX_BYTES:raise ValueError('Saved product record exceeds byte budget')
        record=json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=unique_pairs)
        candidate=self._validate(record,branch_id)
        return record,candidate

    def restore_to(self,storage,branch_id=None):
        record,candidate=self.load(branch_id)
        storage=Path(storage).resolve()
        if not storage.is_relative_to((ROOT/'output').resolve()):raise ValueError('Worker restore must remain under output')
        self._atomic(storage/'latest.json',record['particle'])
        return copy.deepcopy(record['view']),candidate

    def catalog(self):
        result=[]
        for path in sorted(self.branches.glob('*.json'))[:32]:
            try:
                record,_=self.load(path.stem);result.append({**record['branch'],'time_s':record['particle']['phase']['time_s'],'valid':True})
            except Exception as error:result.append({'id':path.stem,'name':'Arquivo inválido','valid':False,'error':str(error)})
        return result
