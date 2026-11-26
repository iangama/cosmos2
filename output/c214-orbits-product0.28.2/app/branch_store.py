"""Candidate immutable forks; independent archive pointers, same physical origin."""
from pathlib import Path
import copy
import datetime
import hashlib
import json
import re
import shutil
import uuid

import instrument_history
import gravity_harmonics
from body_registry import digest
from physics import PHYSICAL_SCALE as U

MAX_BRANCHES=32
IDENTITY=re.compile(r'branch:[0-9a-f]{32}')

def label(value):
    if not isinstance(value,str) or not 1<=len(value)<=80 or value!=value.strip() or any(ord(c)<32 or ord(c)==127 for c in value):
        raise ValueError('Nome do ramo:1–80 caracteres sem controles.')
    return value

class Store:
    def __init__(self,directory):
        self.directory=Path(directory)
        self.active_id=None
        self.records={}
        if self.directory.exists():
            for folder in sorted(self.directory.iterdir()):
                if re.fullmatch('[0-9a-f]{32}',folder.name) and folder.is_dir():
                    record=json.loads((folder/'branch.json').read_text(encoding='utf8'))
                    self._validate_record(record,folder.name)
                    self.records[record['id']]=record
            if len(self.records)>MAX_BRANCHES:raise ValueError('Catálogo de ramos excede32arquivos.')
            for record in self.records.values():self._lineage(record)

    @staticmethod
    def _validate_record(record,identifier):
        keys={'schema','id','name','parent_id','parent_sha256','created_utc','checkpoint_manifest_sha256','system_id','time','revision','fixture_sha256','frame','record_sha256'}
        if not isinstance(record,dict) or set(record)!=keys or type(record['schema']) is not int or record['schema']!=1 or record['id']!='branch:'+identifier:
            raise ValueError('Recibo de ramo incompatível.')
        if record['record_sha256']!=digest({k:v for k,v in record.items() if k!='record_sha256'}):raise ValueError('Selo do ramo inválido.')
        label(record['name'])
        for key in ('checkpoint_manifest_sha256','record_sha256','fixture_sha256'):
            if not isinstance(record[key],str) or not re.fullmatch('[0-9a-f]{64}',record[key]):raise ValueError('Hash do ramo inválido.')
        if record['parent_id'] is None:
            if record['parent_sha256'] is not None:raise ValueError('Pai ausente com hash informado.')
        elif not isinstance(record['parent_id'],str) or not IDENTITY.fullmatch(record['parent_id']):raise ValueError('Pai de ramo inválido.')
        if type(record['revision']) is not int or record['revision']<0 or type(record['time']) not in (int,float) or not 0<=record['time']<float('inf'):
            raise ValueError('Instante/revisão do ramo inválidos.')
        if not isinstance(record['system_id'],str) or not re.fullmatch('[0-9a-f]{32}',record['system_id']) or not isinstance(record['frame'],str):raise ValueError('Origem do ramo inválida.')
        stamp=datetime.datetime.fromisoformat(record['created_utc'])
        if stamp.utcoffset()!=datetime.timedelta(0):raise ValueError('Época do recibo deve declarar UTC.')

    def _lineage(self,record):
        visited={record['id']}
        while record['parent_id'] is not None:
            parent=self.records.get(record['parent_id'])
            if parent is None or parent['id'] in visited or parent['record_sha256']!=record['parent_sha256']:
                raise ValueError('Genealogia de ramos incoerente.')
            if any(parent[k]!=record[k] for k in ('system_id','fixture_sha256','frame')) or parent['time']>record['time']:
                raise ValueError('Pai de ramo com origem/instante incompatível.')
            visited.add(parent['id']);record=parent

    def public(self):
        return {'maximum_branches':MAX_BRANCHES,'active_id':self.active_id,'branches':[
            {k:copy.deepcopy(r[k]) for k in ('id','name','parent_id','created_utc','system_id','time','revision','frame','record_sha256')}
            for r in self.records.values()]}

    def create(self,session,request):
        session._expect(request)
        name=label(request.get('name'))
        if len(self.records)>=MAX_BRANCHES:raise ValueError('Limite de32ramos; preserve ou exporte os arquivos antes de ampliar.')
        parent=self.records.get(self.active_id)
        if parent and (parent['system_id']!=session.system_id or parent['fixture_sha256']!=session.fixture_sha256):parent=None
        identifier=uuid.uuid4().hex
        self.directory.mkdir(parents=True,exist_ok=True)
        temporary=self.directory/('.pending-'+identifier)
        try:
            session.save(temporary,renderer_view=request.get("renderer_view"))
            manifest=json.loads((temporary/'latest.json').read_text())
            record={'schema':1,'id':'branch:'+identifier,'name':name,'parent_id':parent['id'] if parent else None,
                'parent_sha256':parent['record_sha256'] if parent else None,
                'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'checkpoint_manifest_sha256':manifest['manifest_sha256'],'system_id':session.system_id,
                'time':session.sim.t,'revision':session.revision,'fixture_sha256':session.fixture_sha256,'frame':session.contract()['frame']}
            record['record_sha256']=digest(record)
            self._validate_record(record,identifier)
            (temporary/'branch.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
            temporary.rename(self.directory/identifier)
        except BaseException:
            if temporary.exists():shutil.rmtree(temporary)
            raise
        self.records[record['id']]=record;self.active_id=record['id']
        return copy.deepcopy(record)

    def _archive(self,identifier):
        if not isinstance(identifier,str) or not IDENTITY.fullmatch(identifier) or identifier not in self.records:
            raise ValueError('Selecione um ramo arquivado deste catálogo.')
        folder=self.directory/identifier.split(':')[1]
        record=json.loads((folder/'branch.json').read_text(encoding='utf8'))
        self._validate_record(record,folder.name)
        if record!=self.records[identifier]:raise ValueError('Ramo mudou desde a seleção; catálogo deve ser reaberto.')
        manifest=json.loads((folder/'latest.json').read_text(encoding='utf8'))
        if manifest.get('manifest_sha256')!=record['checkpoint_manifest_sha256'] or manifest.get('manifest_sha256')!=digest({k:v for k,v in manifest.items() if k!='manifest_sha256'}):
            raise ValueError('Checkpoint não corresponde ao recibo do ramo.')
        if any(manifest.get(k)!=record[k] for k in ('system_id','revision','fixture_sha256')) or manifest.get('contract',{}).get('frame')!=record['frame']:
            raise ValueError('Origem do checkpoint divergiu do ramo.')
        # Binary/phase/history/registry checks happen through Session.load before
        # replacing any active simulation. No archive file is modified on reads.
        return folder,record

    def load(self,session,request):
        session._expect(request)
        self.inspect(session,request.get('branch_id'))
        folder,record=self._archive(request.get('branch_id'))
        result=session.load(folder)
        self.active_id=record['id']
        return {**result,'branch':copy.deepcopy(record)}

    def inspect(self,session,identifier):
        folder,record=self._archive(identifier)
        clone=type(session)(folder)
        clone.load(folder)
        if clone.sim.t!=record['time']:raise ValueError('Instante do recibo não corresponde à fase.')
        return clone,record

    def compare(self,session,request):
        session._expect(request)
        first,second=request.get('first_id'),request.get('second_id')
        if first==second:raise ValueError('Selecione dois ramos distintos.')
        a,ra=self.inspect(session,first);b,rb=self.inspect(session,second)
        import material_tides
        import orbital_instruments
        import test_cloud
        compatible=all(ra[k]==rb[k] for k in ('system_id','fixture_sha256','frame')) and gravity_harmonics.monopole_contract(material_tides.base_contract(test_cloud.base_contract(a.contract())))==gravity_harmonics.monopole_contract(material_tides.base_contract(test_cloud.base_contract(b.contract())))
        if not compatible:raise ValueError('Ramos têm origens ou referenciais diferentes; não sobreponha as séries.')
        if a.restoration['saved_generation']!=b.restoration['saved_generation']:
            raise ValueError('Ramos foram gravados com gerações científicas diferentes; comparação requer política explícita de migração.')
        same_instant=a.sim.t==b.sim.t
        definitions={}
        for archive in (a,b):
            for record in archive.instrument_history['samples']:
                for probe in record['reading']['readings']:
                    physical_definition={k:v for k,v in probe['definition'].items() if k not in ('id','name')}
                    definitions.setdefault(probe['id'],set()).add(digest(physical_definition))
        rows=[];pa={x['id']:x for x in a.state()['bodies']};pb={x['id']:x for x in b.state()['bodies']}
        for identifier in dict.fromkeys([*pa,*pb]):
            row={'id':identifier,'available_in_first':identifier in pa,'available_in_second':identifier in pb}
            if identifier in pa and identifier in pb and same_instant:
                row.update(delta_position_m=[(pb[identifier]['position'][k]-pa[identifier]['position'][k])*U['length_unit_m'] for k in range(3)],
                    delta_velocity_m_s=[(pb[identifier]['velocity'][k]-pa[identifier]['velocity'][k])*U['velocity_unit_m_s'] for k in range(3)],
                    delta_mass_kg=(pb[identifier]['mass']-pa[identifier]['mass'])*U['mass_unit_kg'])
            rows.append(row)
        return {'schema':1,'first':copy.deepcopy(ra),'second':copy.deepcopy(rb),'frame':ra['frame'],
            'first_gravity_effects':copy.deepcopy(a.gravity_effects),'second_gravity_effects':copy.deepcopy(b.gravity_effects),
            'gravity_definition_changed':a.gravity_effects!=b.gravity_effects,
            'first_material_tides':material_tides.public(a._tides),'second_material_tides':material_tides.public(b._tides),
            'first_test_cloud':test_cloud.public(a._cloud),'second_test_cloud':test_cloud.public(b._cloud),
            'test_cloud_definition_changed':(None if a._cloud is None else a._cloud.origin())!=(None if b._cloud is None else b._cloud.origin()),
            'first_orbital_curves':orbital_instruments.curves(a.orbital_instruments),
            'second_orbital_curves':orbital_instruments.curves(b.orbital_instruments),
            'orbital_definition_changed':a.orbital_instruments['definition']!=b.orbital_instruments['definition'],
            'material_definition_changed':(None if a._tides is None else (a._tides.source_id,a._tides.configuration))!=(None if b._tides is None else (b._tides.source_id,b._tides.configuration)),
            'saved_scientific_generation':copy.deepcopy(a.restoration['saved_generation']),
            'definition_variation_probe_ids':[identifier for identifier,values in definitions.items() if len(values)>1],
            'same_physical_instant':same_instant,'body_differences':rows,
            'first_curves':instrument_history.curves(a.instrument_history),'second_curves':instrument_history.curves(b.instrument_history),
            'policy':'independent archived trajectories from one origin; exact original timestamps, no interpolation; endpoint differences only at equal physical time; unavailable identities remain gaps; active evolution unchanged'}
