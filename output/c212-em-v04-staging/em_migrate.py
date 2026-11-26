"""Explicit pinned migrations; originals survive each scientific generation."""
from pathlib import Path
import hashlib
import json
from em_experiment import Experiment, generation, read_envelope

LEGACY_GENERATION = {
    'model': 'cosmos2:SI-electromagnetic-prototype', 'version': '0.1.0', 'files_sha256': {
        'em_fields.py': '483944d524fbebd78f5d1c0b0d048858e6720d5bc19fcb55671cf3cf240d3381',
        'em_particles.py': 'f7c957fd877c9222ecb27a2201673c2f9d3b58efcdd0f93cf6731308c26e4e97',
        'em_mutual.py': 'c7354e43e470f323eb1cb033a49317446fbcc3ac6e9a45e32ca659e704a1d3ab',
        'em_experiment.py': '3a88b65efd9b1f8181489e919cafc58852fdad9ad250113be1d5483cf2c33cbd',
        'constants.json': 'c94ce4f333542f8a7276a7785b86a646fb6284055d9a7816eec07b51aeb8c49e'}}

LEGACY_02_GENERATION={
    'model':'cosmos2:SI-electromagnetic-prototype','version':'0.2.0','files_sha256':{
        **LEGACY_GENERATION['files_sha256'],
        'em_experiment.py':'7250d8061e790470499e61ebf333f1796fa243d4cdfaf1f585375c67524d277a',
        'em_editor.py':'5c636c43365a19c1cfeb8bb6b5bc0535df4e95c7cfb9db3108472e3e49bca9da',
        'em_migrate.py':'fa6a92207a36e8c1bfa96f9a2a384032c438a4a1be7b9b7bbeadf781fce19269'}}


def migrate_v02(source,destination):
    from copy import deepcopy
    from em_editor import validate_editor
    source,destination=Path(source),Path(destination)
    if source.resolve()==destination.resolve() or destination.exists():raise ValueError('Migration requires a new destination; original retained')
    record=read_envelope(source)
    if record['schema']!=2 or record['generation']!=LEGACY_02_GENERATION:raise ValueError('Only the frozen, verified EM0.2 generation may be migrated')
    trial=Experiment.from_payload(record['payload']);editor=deepcopy(record['editor'])
    validate_editor(trial,editor)
    editor['migration']={'schema':2,'generation':LEGACY_02_GENERATION,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'previous':editor['migration']}
    trial.editor=validate_editor(trial,editor);trial.save(destination)
    return trial


LEGACY_03_GENERATION=json.loads((Path(__file__).resolve().parent/'legacy_0_3_generation.json').read_bytes())

def migrate_v03(source,destination):
    from copy import deepcopy
    from em_editor import validate_editor
    source,destination=Path(source),Path(destination)
    if source.resolve()==destination.resolve() or destination.exists():raise ValueError('Migration requires a new destination; original retained')
    record=read_envelope(source)
    if record['schema']!=3 or record['generation']!=LEGACY_03_GENERATION:raise ValueError('Only the frozen, verified EM0.3 generation may be migrated')
    trial=Experiment.from_payload(record['payload']);editor=deepcopy(record['editor']);validate_editor(trial,editor)
    editor['migration']={'schema':2,'generation':LEGACY_03_GENERATION,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'previous':editor['migration']}
    trial.editor=validate_editor(trial,editor);trial.save(destination)
    return trial


def migrate_legacy(source, destination):
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve() or destination.exists():
        raise ValueError('Migration requires a new destination; original is retained')
    record = read_envelope(source)
    if record['schema'] != 1 or record['generation'] != LEGACY_GENERATION:
        raise ValueError('Only the frozen, verified EM0.1 generation may be migrated')
    current = generation()['files_sha256']
    for name in ('em_fields.py', 'em_particles.py', 'em_mutual.py', 'constants.json'):
        if current[name] != LEGACY_GENERATION['files_sha256'][name]:
            raise ValueError('EM kernels differ; independent scientific migration required')
    trial = Experiment.from_payload(record['payload'])
    trial.editor['migration'] = {'schema': 1, 'generation': LEGACY_GENERATION,
                                 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
    trial.save(destination)
    return trial


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser();parser.add_argument('--from-v02',action='store_true');parser.add_argument('--from-v03',action='store_true'); parser.add_argument('source', type=Path); parser.add_argument('destination', type=Path)
    args = parser.parse_args(); (migrate_v03 if args.from_v03 else migrate_v02 if args.from_v02 else migrate_legacy)(args.source, args.destination)
