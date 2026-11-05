"""Strict, CPU-only import capsules for known spatial-only checkpoints."""
from pathlib import Path
import copy
import hashlib
import json
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'AGENTS.md').is_file())
sys.path.insert(0, str(ROOT / 'output/is6-spatial-artifact-staging'))
import is6_spatial_artifact as artifact

SOURCE = ROOT / 'output/is6-spatial-import-staging/is6_spatial_import.py'
CONTRACT = ROOT / 'IS-6-IMPORTACAO-ESPACIAL-K5D-CONTRATO.md'
MAX_SOURCE_BYTES = 16 * 1024 * 1024
MAX_PACKAGE_BYTES = 64 * 1024 * 1024
sha = lambda raw: hashlib.sha256(raw).hexdigest()
IMPORTED = {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in [SOURCE, CONTRACT]}
digest = artifact.digest


def generation():
    if any(sha((ROOT / p).read_bytes()) != seal for p, seal in IMPORTED.items()):
        raise ValueError('Restart after spatial-import source changes')
    if sha(Path(__file__).read_bytes()) != IMPORTED[SOURCE.relative_to(ROOT).as_posix()]:
        raise ValueError('Spatial-import code differs from its frozen source')
    return dict(schema=1, id='cosmos2:is6-spatial-only-source-import', version='0.1.0',
                source_sha256=dict(IMPORTED), spatial_artifact=artifact.generation())


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate spatial import JSON key')
        result[key] = value
    return result


def parse(raw, maximum=MAX_SOURCE_BYTES):
    if type(raw) is not bytes or not 0 < len(raw) <= maximum:
        raise ValueError('Spatial import byte budget differs')
    try:
        value = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite spatial import JSON')))
        if not isinstance(value, dict):
            raise ValueError('Spatial import object required')
        artifact.encoded(value)  # Also rejects finite spellings that overflow to infinity.
    except (UnicodeError, RecursionError) as error:
        raise ValueError('Invalid spatial import JSON encoding/depth') from error
    return value


def open_source(raw):
    record = parse(raw)
    keys = {'schema', 'kind', 'artifact', 'view', 'branch', 'lineage_parent', 'record_sha256'}
    if set(record) != keys or type(record['schema']) is not int or record['schema'] != 1 or record['kind'] != 'is6_spatial_body_mesh_checkpoint':
        raise ValueError('Known spatial-only checkpoint required')
    if digest({k: v for k, v in record.items() if k != 'record_sha256'}) != record['record_sha256']:
        raise ValueError('Spatial source checkpoint seal differs')
    lineage, branch = record['lineage_parent'], record['branch']
    if lineage is not None:
        artifact.identity(lineage)
    if branch is not None:
        if not isinstance(branch, dict) or set(branch) != {'id', 'parent', 'name'}:
            raise ValueError('Spatial source branch fields differ')
        artifact.identity(branch['id'])
        if lineage != branch['id']:
            raise ValueError('Spatial source branch lineage differs')
        if branch['parent'] is not None:
            artifact.identity(branch['parent'])
            if branch['parent'] == branch['id']:
                raise ValueError('Spatial source branch is its own parent')
        name = branch['name']
        if not isinstance(name, str) or not 1 <= len(name) <= 80 or name != name.strip():
            raise ValueError('Spatial source branch name differs')
        name.encode('utf8')
    # Legacy IDs are evidence, never paths to resolve against the destination.
    run = artifact.Run.restore(record['artifact'])
    view = artifact.view(record['view'], run.payload['configuration'])
    return run, view, record


def preview(raw):
    gen = generation()
    run, view, record = open_source(raw)
    payload = dict(schema=1, kind='is6_spatial_source_import_package', generation=gen,
                   source_format='spatial-checkpoint-1', source_text=raw.decode('utf8'),
                   source_sha256=sha(raw), artifact=run.payload, view=view,
                   artifact_sha256=digest(run.payload),
                   original_lineage=dict(branch=copy.deepcopy(record['branch']), lineage_parent=record['lineage_parent']),
                   policy=dict(destination_instrument='spatial', destination_parent=None,
                               scientific_resampling=False, magnetic_sample_created=False))
    result = {**payload, 'package_sha256': digest(payload)}
    if len(artifact.encoded(result)) > MAX_PACKAGE_BYTES:
        raise ValueError('Spatial import package budget exceeded')
    if generation() != gen:
        raise ValueError('Spatial import generation changed during preview')
    return result


def open_package(raw):
    package = parse(raw, MAX_PACKAGE_BYTES)
    keys = {'schema', 'kind', 'generation', 'source_format', 'source_text', 'source_sha256',
            'artifact', 'view', 'artifact_sha256', 'original_lineage', 'policy', 'package_sha256'}
    if set(package) != keys or type(package['schema']) is not int or package['schema'] != 1 or package['kind'] != 'is6_spatial_source_import_package':
        raise ValueError('Spatial import package schema differs')
    if not isinstance(package['source_text'], str):
        raise ValueError('Exact spatial source text required')
    if digest({k: v for k, v in package.items() if k != 'package_sha256'}) != package['package_sha256']:
        raise ValueError('Spatial import package seal differs')
    expected = preview(package['source_text'].encode('utf8'))
    if digest(package) != digest(expected):
        raise ValueError('Reconstructed spatial import package differs')
    return copy.deepcopy(expected)


def describe(package):
    accepted = open_package(artifact.encoded(package))
    source = accepted['artifact']['binding']
    return dict(source_format=accepted['source_format'], source_sha256=accepted['source_sha256'],
                package_sha256=accepted['package_sha256'], body_reference_id=source['body_reference_id'],
                epoch=copy.deepcopy(source['epoch']), configuration=copy.deepcopy(accepted['artifact']['configuration']),
                view=copy.deepcopy(accepted['view']), artifact_sha256=accepted['artifact_sha256'],
                original_lineage=copy.deepcopy(accepted['original_lineage']), destination_instrument='spatial',
                magnetic_sample_created=False, scientific_resampling=False)
