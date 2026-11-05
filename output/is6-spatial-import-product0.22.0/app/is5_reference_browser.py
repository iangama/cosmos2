"""Read-only access to pinned, previously audited B23 data; no EOS integration."""
from pathlib import Path
import copy
import hashlib
import json
import re
from urllib.parse import parse_qsl
from is5_reference_manifest import FILES, MODELS, PROVENANCE


class Library:
    def __init__(self, data_root=None):
        self.root=Path(data_root) if data_root is not None else Path(__file__).parent/'references'
        self.models={}
        self.comparisons={}
        for name,expected in FILES.items():
            if Path(name).name!=name:
                raise ValueError('Nome inválido no arquivo de referências solares.')
            raw=(self.root/name).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=expected:
                raise ValueError('Dados da referência solar alterados: '+name)
            data=json.loads(raw)
            if name.endswith('-ideal-EOS-Age1.json'):
                model=name.removesuffix('-ideal-EOS-Age1.json')
                self.comparisons[model]={row['index']:row for row in data}
            else:
                model=name.removesuffix('.json')
                if model not in MODELS or data['model']!=model:
                    raise ValueError('Modelo solar diferente do pacote de referências.')
                if not (len(data['raw_values'])==len(data['derived'])==len(data['flags'])==2001):
                    raise ValueError('Modelo solar incompleto no pacote de referências.')
                self.models[model]=data
        if set(self.models)!=set(MODELS) or set(self.comparisons)!={'GS98','AGSS09'}:
            raise ValueError('Biblioteca de referências solares incompleta.')

    def _model(self, model):
        if type(model) is not str or model not in MODELS:
            raise ValueError('Escolha um modelo solar disponível.')
        return self.models[model]

    def catalog(self):
        return dict(models=list(MODELS),points_per_model=2001,
                    provenance=copy.deepcopy(PROVENANCE),interpolation=False,
                    scope='Perfis de referência GarStEC; não são evolução pelo Cosmos2 nem dados observados.')

    def series(self, model):
        data=self._model(model)
        return dict(model=model,r_over_Rsun=[row[0] for row in data['raw_values']],
                    **{field:[row[field] for row in data['derived']] for field in
                       ('temperature_K','density_kg_m3','pressure_Pa','electron_density_m3')},
                    provenance=copy.deepcopy(PROVENANCE))

    def sample(self, model, index):
        data=self._model(model)
        if type(index) is not int or not 0<=index<=2000:
            raise ValueError('O índice radial deve ser inteiro de 0 a 2000.')
        values=data['raw_values'][index]
        return dict(model=model,index=index,r_over_Rsun=values[0],
                    structure=copy.deepcopy(data['derived'][index]),
                    abundances=dict(zip(data['columns'][18:],values[18:])),
                    quality_flags=list(data['flags'][index]),
                    ideal_comparison=copy.deepcopy(self.comparisons.get(model,{}).get(index)),
                    provenance=copy.deepcopy(PROVENANCE),interpolation=False)

    def query(self, operation, query):
        try:pairs=parse_qsl(query,keep_blank_values=True,strict_parsing=True)
        except ValueError as error:raise ValueError('Consulta de referência solar inválida.') from error
        fields=dict(pairs)
        if len(fields)!=len(pairs):raise ValueError('Parâmetro repetido na consulta solar.')
        if operation=='catalog' and not fields:return self.catalog()
        if operation=='series' and set(fields)=={'model'}:return self.series(fields['model'])
        if operation=='sample' and set(fields)=={'model','index'}:
            if not re.fullmatch(r'0|[1-9][0-9]{0,3}',fields['index']):
                raise ValueError('Índice radial inválido.')
            return self.sample(fields['model'],int(fields['index']))
        raise ValueError('Operação ou parâmetros de referência solar inválidos.')
