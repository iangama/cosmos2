"""Seal the four K1C images after the recorded manual visual inspection."""
from pathlib import Path
import argparse
import hashlib
import json
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if args.label != '20261103c':
        parser.error('Manual inspection was performed for 20261103c only; inspect new images before a new review implementation')
    source = ROOT / ('evidence/is6-native-layer-pair-' + args.label + '.json')
    out = ROOT / ('evidence/is6-layer-pair-visual-' + args.label + '.json')
    if out.exists():
        raise FileExistsError('Preserve visual review')
    r = json.loads(source.read_text())
    assert r['accepted'] and r['completed'] and len(r['captures']) == 4
    assert len(r['cases']) == 2 and len(r['faults']) == 4 and not r['page_errors']
    assert not r.get('failure') and not r.get('cleanup_failure')
    hashes = {**r['source_sha256'], source.relative_to(ROOT).as_posix(): sha(source),
              Path(__file__).relative_to(ROOT).as_posix(): sha(Path(__file__))}
    assert all(sha(ROOT / p) == seal for p, seal in hashes.items())
    for capture in r['captures']:
        path, rgb = ROOT / capture['path'], ROOT / capture['RGB']
        assert sha(path) == capture['sha256'] and sha(rgb) == capture['RGB_sha256']
        original, reviewed = Image.open(path).convert('RGB'), Image.open(rgb).convert('RGB')
        assert original.size == reviewed.size == (1920, 1080)
        assert ImageChops.difference(original, reviewed).getbbox() is None
        hashes[capture['path']] = capture['sha256']
        hashes[capture['RGB']] = capture['RGB_sha256']
    result = dict(accepted=True, completed=True, candidate='0.18.5', source_sha256=hashes,
        native_receipt=source.relative_to(ROOT).as_posix(), captures=r['captures'], reviewed_count=4,
        method='Manual visual inspection of both Earth images together, then both Jupiter images together; hashes and RGB pixels independently checked.',
        observations=['Terra e Júpiter mostram malha ciano/violeta, graticulado magnético, seta verde e ponto dourado na mesma vista.',
            'Legendas identificam modelo, época, unidades, ampliação gráfica, origem independente e limite do domínio em 100/150%.',
            'Texto, seleção de escala e rodapé legíveis; seta e ponto permanecem fora da legenda nas quatro imagens.',
            'A legenda ampliada cobre uma pequena borda esquerda da malha em 150%; o objeto central e a amostra continuam visíveis. A interface de produto terá layout próprio.'],
        scope='Experimental K1C coexistence captures only; no final product UI, performance, persistence, migration or v1 acceptance.')
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(accepted=True, reviewed_count=4)))


if __name__ == '__main__':
    main()
