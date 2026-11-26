"""Explicit, pinned EM0.1 -> EM0.2 conversion; never overwrites the source."""
from pathlib import Path
import hashlib
from em_experiment import Experiment, generation, read_envelope

LEGACY_GENERATION = {
    'model': 'cosmos2:SI-electromagnetic-prototype', 'version': '0.1.0', 'files_sha256': {
        'em_fields.py': '483944d524fbebd78f5d1c0b0d048858e6720d5bc19fcb55671cf3cf240d3381',
        'em_particles.py': 'f7c957fd877c9222ecb27a2201673c2f9d3b58efcdd0f93cf6731308c26e4e97',
        'em_mutual.py': 'c7354e43e470f323eb1cb033a49317446fbcc3ac6e9a45e32ca659e704a1d3ab',
        'em_experiment.py': '3a88b65efd9b1f8181489e919cafc58852fdad9ad250113be1d5483cf2c33cbd',
        'constants.json': 'c94ce4f333542f8a7276a7785b86a646fb6284055d9a7816eec07b51aeb8c49e'}}


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
    parser = argparse.ArgumentParser(); parser.add_argument('source', type=Path); parser.add_argument('destination', type=Path)
    args = parser.parse_args(); migrate_legacy(args.source, args.destination)
