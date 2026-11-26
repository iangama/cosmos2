"""Atomic candidate-local compound records, branches and exports."""
from pathlib import Path
import copy
import datetime as dt
import hashlib
import json
import os
import re
import unicodedata
import uuid
import is6_layers_checkpoint_v2 as checkpoint

ROOT=checkpoint.ROOT
MAX_BYTES=32*2**20


def identifier(value):
    if not isinstance(value,str) or re.fullmatch('[0-9a-f]{32}',value) is None:
        raise ValueError('Identificador do ramo inválido.')
    return value


def name(value):
    if not isinstance(value,str):raise ValueError('Nome do ramo inválido.')
    value=unicodedata.normalize('NFC',value).strip()
    if not value or len(value)>80 or any(ord(c)<32 or ord(c)==127 for c in value):raise ValueError('Use um nome de 1–80 caracteres sem controles.')
    return value


def unique_object(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Campo JSON repetido: '+key)
        result[key]=value
    return result


def decode(record):
    fields={'schema','kind','id','name','parent','created_utc','checkpoint','record_sha256'}
    if not isinstance(record,dict) or set(record)!=fields:raise ValueError('Registro composto completo obrigatório; formatos antigos não são convertidos automaticamente.')
    if type(record['schema']) is not int or record['schema']!=1 or record['kind']!='independent_layer_store_record':raise ValueError('Formato do registro composto incompatível.')
    identifier(record['id'])
    if record['name']!=name(record['name']):raise ValueError('Nome do ramo não canônico.')
    if record['parent'] is not None:identifier(record['parent'])
    stamp=record['created_utc']
    if not isinstance(stamp,str) or len(stamp)>64:raise ValueError('Data de gravação inválida.')
    try:
        created=dt.datetime.fromisoformat(stamp)
        if created.utcoffset()!=dt.timedelta(0):raise ValueError('Data de gravação deve usar UTC.')
        body={k:copy.deepcopy(v) for k,v in record.items() if k!='record_sha256'}
        if checkpoint.contract.digest(body)!=record['record_sha256']:raise ValueError('Checksum do registro composto diverge.')
        scientific,visible=checkpoint.restore(record['checkpoint'])
    except (TypeError,KeyError,OverflowError,RecursionError) as error:raise ValueError('Registro composto inválido.') from error
    return scientific,visible


class Store:
    def __init__(self,folder):
        self.folder=Path(folder).resolve()
        if not self.folder.is_relative_to((ROOT/'output').resolve()):raise ValueError('Armazenamento composto deve permanecer na candidata.')
        self.path=self.folder/'latest.json';self.branches=self.folder/'branches';self.exports=self.folder/'exports'
        for path in [self.branches,self.exports]:
            if not path.resolve().is_relative_to(self.folder):raise ValueError('Diretório de armazenamento redirecionado.')

    def _read(self,path):
        path=Path(path)
        if path.is_symlink() or not path.resolve().is_relative_to(self.folder):raise ValueError('Caminho do registro inválido.')
        if not path.is_file():raise ValueError('Não há referência composta salva neste caminho.')
        if path.stat().st_size>MAX_BYTES:raise ValueError('Registro composto excede o limite de tamanho.')
        def reject(value):raise ValueError('Número JSON não finito: '+value)
        try:record=json.loads(path.read_text(encoding='utf8'),object_pairs_hook=unique_object,parse_constant=reject)
        except (UnicodeError,RecursionError) as error:raise ValueError('JSON do registro composto inválido.') from error
        scientific,visible=decode(record)
        return record,scientific,visible

    def _record(self,scientific,visible,record_name,parent):
        record_name=name(record_name)
        if parent is not None:identifier(parent)
        envelope=checkpoint.create(scientific,visible)
        body=dict(schema=1,kind='independent_layer_store_record',id=uuid.uuid4().hex,name=record_name,parent=parent,
                  created_utc=dt.datetime.now(dt.timezone.utc).isoformat(),checkpoint=envelope)
        return {**body,'record_sha256':checkpoint.contract.digest(body)}

    def _write(self,path,record,*,replace):
        decode(record)
        encoded=(json.dumps(record,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf8')
        if len(encoded)>MAX_BYTES:raise ValueError('Registro composto excede o limite de tamanho.')
        path=Path(path)
        if path.is_symlink() or not path.resolve().is_relative_to(self.folder):raise ValueError('Destino do registro inválido.')
        if not replace and path.exists():raise FileExistsError('Preserve o registro composto anterior.')
        path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_name('.'+path.name+'.'+uuid.uuid4().hex+'.tmp')
        try:
            with temporary.open('xb') as stream:stream.write(encoded);stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,path)
        finally:temporary.unlink(missing_ok=True)
        return dict(path=path.as_posix(),sha256=hashlib.sha256(encoded).hexdigest(),record=self.summary(record))

    @staticmethod
    def summary(record):
        return dict(id=record['id'],name=record['name'],parent=record['parent'],created_utc=record['created_utc'],
                    scientific_sha256=record['checkpoint']['scientific_sha256'],visible=copy.deepcopy(record['checkpoint']['visible']))

    def save(self,scientific,visible,*,record_name='Vista de camadas',parent=None):
        record=self._record(scientific,visible,record_name,parent)
        return self._write(self.path,record,replace=True)

    def branch(self,scientific,visible,*,record_name,parent=None):
        record=self._record(scientific,visible,record_name,parent)
        return self._write(self.branches/(record['id']+'.json'),record,replace=False)

    def export(self,scientific,visible,*,parent=None):
        record=self._record(scientific,visible,'Referências exportadas',parent)
        return self._write(self.exports/(record['id']+'.json'),record,replace=False)

    def load(self,branch_id=None):
        path=self.path if branch_id is None else self.branches/(identifier(branch_id)+'.json')
        record,scientific,visible=self._read(path)
        if branch_id is not None and record['id']!=branch_id:raise ValueError('Identidade do ramo não corresponde ao arquivo.')
        return scientific,visible,self.summary(record)

    def catalog(self):
        rows=[]
        for path in sorted(self.branches.glob('*.json')):
            try:
                identifier(path.stem);record,_,_=self._read(path)
                if record['id']!=path.stem:raise ValueError('Identidade do ramo não corresponde ao arquivo.')
                rows.append(dict(valid=True,**self.summary(record)))
            except (ValueError,OSError) as error:rows.append(dict(id=path.stem,name=path.stem,valid=False,error=str(error)))
        return rows
