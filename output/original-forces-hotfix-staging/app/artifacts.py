"""Write a reviewable local JSON artifact, including in native CEF without downloads."""
from pathlib import Path
import datetime
import json
import os
import re
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]


def export_json(name, payload):
    if not re.fullmatch('[a-z-]+', name):
        raise ValueError('Nome de artefato inválido.')
    folder = ROOT / 'user/exports'
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    path = folder / f'cosmos2-{name}-{stamp}-{uuid.uuid4().hex[:8]}.json'
    result = {**payload, 'ok': True, 'export_file': str(path)}
    content = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    descriptor, temporary = tempfile.mkstemp(prefix='export-', suffix='.tmp', dir=folder)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return result
