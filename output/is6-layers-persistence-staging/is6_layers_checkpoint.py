"""CPU checkpoint envelope; no file replacement, native scene or service commands."""
from pathlib import Path
import copy
import hashlib
import json
import is6_layer_contract as contract

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
FILES = [Path(__file__), Path(contract.__file__)]
IMPORTED = {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES}


def generation():
    if any(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() != seal for p,seal in IMPORTED.items()):
        raise ValueError('Restart checkpoint validation after source changes')
    return dict(id='cosmos2:independent-layer-checkpoint', version='0.1.0', source_sha256=dict(IMPORTED),
                spatial=contract.artifact.generation())


def visibility(value):
    if not isinstance(value,dict) or set(value) != {'spatial','magnetic'} or any(type(v) is not bool for v in value.values()):
        raise ValueError('Two explicit boolean visibilities required')
    return dict(value)


def scientific(value):
    if not isinstance(value,dict) or set(value) != {'schema','kind','spatial','magnetic','admission'}:
        raise ValueError('Complete scientific pair required')
    if type(value['schema']) is not int or value['schema'] != 1 or value['kind'] != 'independent_frozen_layer_pair':
        raise ValueError('Unsupported scientific pair format')
    # Finitude also applies to unknown numeric subfields before reconstruction.
    try:
        json.dumps(value,allow_nan=False)
        run = contract.artifact.Run.restore(copy.deepcopy(value['spatial']))
        reading = contract.magnetic(run.payload['phase'],copy.deepcopy(value['magnetic']))
        admission = contract.compose(run.payload['phase'],run.payload,reading,dict(spatial=True,magnetic=True))
        if contract.encoded(admission) != contract.encoded(value['admission']):
            raise ValueError('Scientific pair admission differs')
    except (KeyError,TypeError,OverflowError) as error:
        raise ValueError('Incomplete scientific pair') from error
    return copy.deepcopy(value)


def create(value, visible):
    value = scientific(value)
    body = dict(schema=1, kind='independent_frozen_layer_checkpoint', generation=generation(),
                scientific=value, scientific_sha256=contract.digest(value), visible=visibility(visible))
    return {**body,'checkpoint_sha256':contract.digest(body)}


def restore(value):
    fields = {'schema','kind','generation','scientific','scientific_sha256','visible','checkpoint_sha256'}
    if not isinstance(value,dict) or set(value) != fields:
        raise ValueError('Complete composite checkpoint required; legacy spatial saves are not composite')
    if type(value['schema']) is not int or value['schema'] != 1 or value['kind'] != 'independent_frozen_layer_checkpoint':
        raise ValueError('Unsupported composite checkpoint format')
    if value['generation'] != generation():
        raise ValueError('Composite checkpoint generation differs; no implicit migration')
    body = {k:copy.deepcopy(v) for k,v in value.items() if k != 'checkpoint_sha256'}
    try:
        if contract.digest(body) != value['checkpoint_sha256']:
            raise ValueError('Composite checkpoint checksum differs')
        visible = visibility(value['visible'])
        data = scientific(value['scientific'])
        if contract.digest(data) != value['scientific_sha256']:
            raise ValueError('Scientific pair checksum differs')
    except (TypeError,OverflowError) as error:
        raise ValueError('Invalid composite checkpoint') from error
    return data,visible
