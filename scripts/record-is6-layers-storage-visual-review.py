"""Record the agent's direct review of the twelve 0.20.1 native captures."""
from pathlib import Path
import hashlib
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
out = ROOT / 'evidence/is6-layers-storage-visual-20261104f.json'
if out.exists():
    raise FileExistsError('Preserve visual review')
sources = {Path(__file__).relative_to(ROOT).as_posix(): sha(Path(__file__))}
captures = []
for label in ['20261104e', '20261104f']:
    path = ROOT / ('evidence/is6-layers-storage-native-' + label + '.json')
    record = json.loads(path.read_text())
    assert record['accepted'] and record['completed'] and len(record['captures']) == 6
    sources[path.relative_to(ROOT).as_posix()] = sha(path)
    for item in record['captures']:
        image, rgb = ROOT / item['path'], ROOT / item['RGB']
        assert sha(image) == item['sha256'] and sha(rgb) == item['RGB_sha256']
        with Image.open(image) as original, Image.open(rgb) as archived:
            assert original.size == archived.size == (1920, 1080)
            assert original.convert('RGB').tobytes() == archived.convert('RGB').tobytes()
        layout = item['layout']
        assert layout['scroll'] == layout['client'] and not layout['error']
        sources[item['path']] = item['sha256']
        sources[item['RGB']] = item['RGB_sha256']
        storage = '-storage-' in image.name
        note = ('Salvar e restaurar têm fundo azul escuro e texto legível; nome, lista de ramos, '
                'restauração e exportação estão legíveis em 150%; rolagem e saída acessíveis.'
                if storage else
                'Malha ciano/violeta, seta verde e ponto dourado distinguíveis; legenda, corpo, '
                'referência arquivada quando aplicável e unidades legíveis; painel rolável e saída acessível.')
        captures.append(dict(path=item['path'], sha256=item['sha256'], phase=record['phase'],
                             accepted=True, observations=note))
result = dict(accepted=True, completed=True, candidate='0.20.1', source_sha256=sources,
              method='Inspeção visual direta das doze imagens via view_image pelo agente, antes deste registro; validações de hash e layout são complementares.',
              captures=captures,
              scope='Revisão visual das jornadas E/F em 100% e 150%, incluindo armazenamento; sem aceite de desempenho ou IS6/v1 inteira.')
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print(json.dumps(dict(accepted=True, reviewed_images=len(captures))))
