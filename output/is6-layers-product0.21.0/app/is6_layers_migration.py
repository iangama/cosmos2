"""Explicit, read-only conversion of known compound checkpoints and records."""
from pathlib import Path
import copy
import hashlib
import json
import is6_layers_checkpoint_v2 as checkpoint
import is6_layers_store as store

ROOT = checkpoint.ROOT
MAX_BYTES = store.MAX_BYTES
contract = checkpoint.contract
LEGACY_SOURCES = {
    'output/is6-layers-persistence-staging/is6_layers_checkpoint.py':
        '386c4665810017782ee3c973ab997474e5675020e56e57661ecfd5c5e3244ada',
    'output/is6-layers-product0.19.1/app/is6_layer_contract.py':
        'f721b43a55a5e4dd2bfedce262bba85ce099573cc039736a62b677cb9b5f1ce2',
}
TARGET_SOURCES = {
    'is6_layers_checkpoint_v2.py': '8d05595b50b47971c7f953109baf0d8dc9a7016602d9140434c0966f26db25ab',
    'is6_layer_contract.py': 'f721b43a55a5e4dd2bfedce262bba85ce099573cc039736a62b677cb9b5f1ce2',
}
FILES = [Path(__file__), Path(checkpoint.__file__), Path(store.__file__)]
IMPORTED = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES}
FIELDS = {'schema', 'kind', 'generation', 'scientific', 'scientific_sha256',
          'visible', 'checkpoint_sha256'}


def generation():
    if any(hashlib.sha256(p.read_bytes()).hexdigest() != seal for p, seal in IMPORTED.items()):
        raise ValueError('Reinicie a validação após alterações do conversor.')
    target = checkpoint.generation()
    if target['source_sha256'] != TARGET_SOURCES:
        raise ValueError('Validadores do destino não pertencem à conversão conhecida.')
    return dict(id='cosmos2:explicit-compound-import', version='0.1.0',
                source_sha256={p.name: seal for p, seal in IMPORTED.items()},
                target=target, legacy_source_sha256=dict(LEGACY_SOURCES))


def legacy_generation():
    return dict(id='cosmos2:independent-layer-checkpoint', version='0.1.0',
                source_sha256=dict(LEGACY_SOURCES), spatial=checkpoint.generation()['spatial'])


def parse(raw):
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_BYTES:
        raise ValueError('Arquivo JSON vazio ou maior que o limite de importação.')
    def reject(value):
        raise ValueError('Número JSON não finito: ' + value)
    try:
        return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=store.unique_object,
                          parse_constant=reject)
    except (UnicodeError, RecursionError, json.JSONDecodeError) as error:
        raise ValueError('Arquivo de importação não é um JSON UTF-8 válido.') from error


def _legacy(value):
    if (not isinstance(value, dict) or set(value) != FIELDS or
            type(value['schema']) is not int or value['schema'] != 1 or
            value['kind'] != 'independent_frozen_layer_checkpoint'):
        raise ValueError('Envelope composto legado incompleto.')
    if contract.encoded(value['generation']) != contract.encoded(legacy_generation()):
        raise ValueError('Geração legada desconhecida; conversão indisponível.')
    body = {k: v for k, v in value.items() if k != 'checkpoint_sha256'}
    if contract.digest(body) != value['checkpoint_sha256']:
        raise ValueError('Checksum do envelope legado diverge.')
    visible = checkpoint.visibility(value['visible'])
    scientific = checkpoint.scientific(value['scientific'])
    if contract.digest(scientific) != value['scientific_sha256']:
        raise ValueError('Checksum científico legado diverge.')
    return scientific, visible


def _source(value):
    if not isinstance(value, dict):
        raise ValueError('Documento composto obrigatório.')
    kind = value.get('kind')
    if kind == 'independent_layer_store_record':
        envelope = value.get('checkpoint')
        if (not isinstance(envelope, dict) or
                contract.encoded(envelope.get('generation')) != contract.encoded(checkpoint.generation())):
            raise ValueError('Geração do registro de origem desconhecida.')
        scientific, visible = store.decode(value)
        return scientific, visible, 'store-record-1/checkpoint-0.2.0', [
            'Registro de origem conservado integralmente; destino sem parentesco local implícito.']
    if kind == 'independent_frozen_layer_checkpoint':
        version = value.get('generation', {}).get('version') if isinstance(value.get('generation'), dict) else None
        if version == '0.1.0':
            scientific, visible = _legacy(value)
            return scientific, visible, 'checkpoint-0.1.0', [
                'Envelope 0.1.0 convertido explicitamente para 0.2.0; ciência e visibilidades idênticas.']
        if contract.encoded(value.get('generation')) != contract.encoded(checkpoint.generation()):
            raise ValueError('Geração do envelope de origem desconhecida.')
        scientific, visible = checkpoint.restore(value)
        return scientific, visible, 'checkpoint-0.2.0', [
            'Envelope 0.2.0 validado; ciência e visibilidades idênticas.']
    raise ValueError('Formato de importação indisponível; saves apenas espaciais exigem outra conversão.')


def preview(raw):
    """Return a new deterministic package; do not read a user-supplied path or write."""
    value = parse(raw)
    scientific, visible, source_format, changes = _source(value)
    body = dict(schema=1, kind='explicit_compound_import', generation=generation(),
                source_text=raw.decode('utf8'), source_sha256=hashlib.sha256(raw).hexdigest(),
                source_format=source_format, changes=changes,
                checkpoint=checkpoint.create(scientific, visible))
    return {**body, 'import_sha256': contract.digest(body)}


def restore(value):
    """Reconstruct both the original and target instead of trusting outer checksums."""
    fields = {'schema', 'kind', 'generation', 'source_text', 'source_sha256',
              'source_format', 'changes', 'checkpoint', 'import_sha256'}
    if (not isinstance(value, dict) or set(value) != fields or
            type(value['schema']) is not int or value['schema'] != 1 or
            value['kind'] != 'explicit_compound_import'):
        raise ValueError('Pacote de importação completo obrigatório.')
    if contract.encoded(value['generation']) != contract.encoded(generation()):
        raise ValueError('Geração do conversor diverge.')
    if not isinstance(value['source_text'], str):
        raise ValueError('Texto original obrigatório.')
    try:
        body = {k: v for k, v in value.items() if k != 'import_sha256'}
        if contract.digest(body) != value['import_sha256']:
            raise ValueError('Checksum da importação diverge.')
        raw = value['source_text'].encode('utf8')
        if hashlib.sha256(raw).hexdigest() != value['source_sha256']:
            raise ValueError('Hash dos bytes originais diverge.')
        scientific, visible, source_format, changes = _source(parse(raw))
        if value['source_format'] != source_format or value['changes'] != changes:
            raise ValueError('Relatório da conversão diverge da origem.')
        target = checkpoint.create(scientific, visible)
        if contract.encoded(target) != contract.encoded(value['checkpoint']):
            raise ValueError('Destino não conserva a referência e as visibilidades originais.')
    except (KeyError, TypeError, OverflowError, UnicodeError, RecursionError) as error:
        raise ValueError('Pacote de importação inválido.') from error
    return copy.deepcopy(scientific), dict(visible)


def describe(value):
    scientific, visible = restore(value)
    binding = scientific['spatial']['binding']
    return dict(source_format=value['source_format'], source_sha256=value['source_sha256'],
                import_sha256=value['import_sha256'], body_reference_id=binding['body_reference_id'],
                epoch=copy.deepcopy(binding['epoch']), visible=visible,
                scientific_sha256=contract.digest(scientific),
                magnetic_model=scientific['magnetic']['provenance']['model'],
                changes=list(value['changes']))
