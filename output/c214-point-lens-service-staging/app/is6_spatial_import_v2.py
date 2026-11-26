"""Versioned import of legacy and current spatial exports without scientific resampling."""
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
import copy
import hashlib

import is6_spatial_import as legacy

ROOT=legacy.ROOT
artifact=legacy.artifact
parse=legacy.parse
MAX_SOURCE_BYTES=legacy.MAX_SOURCE_BYTES
MAX_PACKAGE_BYTES=legacy.MAX_PACKAGE_BYTES
MAX_ORIGIN_DEPTH=8
sha=lambda raw:hashlib.sha256(raw).hexdigest()
digest=artifact.digest
SOURCE=ROOT/'scripts/spatial-roundtrip-v2'
FILES=[SOURCE/name for name in ['is6_spatial_import_v2.py','is6_spatial_import_store_v2.py','is6_spatial_import_laboratory_v2.py','CONTRATO.txt']]
IMPORTED={path.relative_to(ROOT).as_posix():sha(path.read_bytes()) for path in FILES}
DEPTH=ContextVar('spatial_source_origin_depth',default=0)
PACKAGE_FIELDS={'schema','kind','generation','source_format','source_text','source_sha256','artifact','view','artifact_sha256','original_lineage','policy','package_sha256'}


def generation():
    if any(sha((ROOT/name).read_bytes())!=seal for name,seal in IMPORTED.items()):
        raise ValueError('Reinicie após alterar o importador espacial versionado.')
    if sha(Path(__file__).read_bytes())!=IMPORTED[(SOURCE/'is6_spatial_import_v2.py').relative_to(ROOT).as_posix()]:
        raise ValueError('O importador espacial difere da revisão congelada.')
    return dict(schema=1,id='cosmos2:is6-spatial-source-import-v2',version='0.2.0',source_sha256=dict(IMPORTED),legacy_source_import=legacy.generation())


@contextmanager
def bounded_origin():
    depth=DEPTH.get()
    if depth>=MAX_ORIGIN_DEPTH:raise ValueError('A cadeia de origem espacial excede o limite de8 referências.')
    token=DEPTH.set(depth+1)
    try:yield
    finally:DEPTH.reset(token)


def preview(raw):
    document=parse(raw)
    if document.get('schema')==1 and document.get('kind')=='is6_spatial_body_mesh_checkpoint':
        return legacy.preview(raw)
    if type(document.get('schema')) is not int or document['schema']!=2 or document.get('kind')!='is6_spatial_body_mesh_checkpoint_with_origin':
        raise ValueError('Formato espacial não reconhecido. Escolha um JSON exportado pela Malha espacial.')
    gen=generation()
    # Deferred import avoids a module-initialization cycle. Nested origins are bounded.
    import is6_spatial_import_store_v2 as storage
    with bounded_origin():reference=storage.decode(raw)
    record=reference.record
    body=dict(schema=2,kind='is6_spatial_source_import_package',generation=gen,
      source_format='spatial-checkpoint-with-origin-2',source_text=raw.decode('utf8'),source_sha256=sha(raw),
      artifact=reference.payload,view=reference.view,artifact_sha256=digest(reference.payload),
      original_lineage=dict(branch=copy.deepcopy(record['branch']),lineage_parent=record['lineage_parent']),
      policy=dict(destination_instrument='spatial',destination_parent=None,scientific_resampling=False,magnetic_sample_created=False))
    result={**body,'package_sha256':digest(body)}
    if len(artifact.encoded(result))>MAX_PACKAGE_BYTES:raise ValueError('A origem espacial excede o orçamento de importação.')
    if generation()!=gen:raise ValueError('O importador mudou durante a validação espacial.')
    return result


def open_package(raw):
    package=parse(raw,MAX_PACKAGE_BYTES)
    if type(package.get('schema')) is int and package['schema']==1:return legacy.open_package(raw)
    if set(package)!=PACKAGE_FIELDS or type(package.get('schema')) is not int or package['schema']!=2 or package['kind']!='is6_spatial_source_import_package':
        raise ValueError('A cápsula de origem espacial está incompleta ou tem formato incompatível.')
    if not isinstance(package['source_text'],str):raise ValueError('O texto original da referência é obrigatório.')
    if digest({key:value for key,value in package.items() if key!='package_sha256'})!=package['package_sha256']:
        raise ValueError('O selo da origem espacial difere do conteúdo.')
    expected=preview(package['source_text'].encode('utf8'))
    if digest(package)!=digest(expected):raise ValueError('A origem espacial difere do arquivo original validado.')
    return copy.deepcopy(expected)


def describe(package):
    accepted=open_package(artifact.encoded(package));binding=accepted['artifact']['binding']
    return dict(source_format=accepted['source_format'],source_sha256=accepted['source_sha256'],package_sha256=accepted['package_sha256'],
      body_reference_id=binding['body_reference_id'],epoch=copy.deepcopy(binding['epoch']),configuration=copy.deepcopy(accepted['artifact']['configuration']),
      view=copy.deepcopy(accepted['view']),artifact_sha256=accepted['artifact_sha256'],original_lineage=copy.deepcopy(accepted['original_lineage']),
      destination_instrument='spatial',magnetic_sample_created=False,scientific_resampling=False)
