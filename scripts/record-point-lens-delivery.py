"""Consolidate the original-launcher point-lens delivery without rerunning science."""
from pathlib import Path
import hashlib
import json
import os
import time
import urllib.request
from cef_page_v2 import Page

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / 'output/original-flow-hotfix-product0.29.0'
OUT = ROOT / 'evidence/point-lens-delivery-20261121a.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not OUT.exists(), 'Preserve the delivery receipt'
    names = ['c214-point-lens-offline-20261121b.json',
             'c214-point-lens-geometry-20261121a.json',
             'c214-point-lens-http-20261121a.json',
             'c214-point-lens-ui-20261121b.json',
             'native-point-lens-20261121a.json',
             'native-point-lens-large-plot-20261121a.json',
             'working-product-switch-20261121d.json',
             'original-flow-entry-point-lens-20261121a.json']
    for name in names:
        proof = json.loads((ROOT / 'evidence' / name).read_text(encoding='utf8'))
        assert proof['accepted'] and proof['completed'], name
    manifest = json.loads((PRODUCT / 'build-manifest.json').read_text(encoding='utf8'))
    assert all(sha(PRODUCT / name) == digest
               for name, digest in manifest['files_sha256'].items())
    session = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
    assert Path(session['serverScript']).parent.parent == PRODUCT
    receipt = dict(accepted=True, completed=True, version='0.29.0', session=session,
                   overall_product_accepted=False, scientific_milestones_promoted=False,
                   scientific_python_unchanged=141, scientific_python_extended=2,
                   scientific_python_added=2,
                   manifest_sha256=sha(PRODUCT / 'build-manifest.json'),
                   evidence_sha256={name: sha(ROOT / 'evidence' / name) for name in names},
                   shortcuts=[])
    with Page() as page:
        assert page.evaluate('location.pathname==="/"&&appState.mode==="atlas"&&Number(getComputedStyle(document.body).zoom)===1')
        for kind in ['spatial', 'layers']:
            state = json.load(urllib.request.urlopen(
                'http://127.0.0.1:4700/api/' + kind + '/state', timeout=30))
            assert not state['active'] and not state['busy'] and not state['recovery_required']
        for name in ['Abrir-Planetas.cmd', 'Abrir-Planetas-e-Luas.cmd']:
            os.startfile(str(ROOT / name))
            time.sleep(1)
            current = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
            assert current['app'] == session['app'] and current['serverScript'] == session['serverScript']
            receipt['shortcuts'].append(dict(name=name, reused_app=session['app'], sha256=sha(ROOT / name)))
    receipt['script_sha256'] = sha(Path(__file__))
    receipt['scope'] = ('Local point-lens delivery through original launcher and Forces panel, '
        'with actual Windows mouse/keyboard at100/150%, image picking, editable source/lens/observer, '
        'ray construction, parity/flux, singular ring, error/recovery and confirmed-state persistence. '
        'Original owner phase, camera, epoch and favorites preserved by native proof. '
        'Full ring readable by ordinary150% scrolling. CPU composition retains original refused '
        'out-of-domain scaling fixture. Prior orbit performance is not transferred. '
        'No whole C2-14 or final integration acceptance.')
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(accepted=True, version='0.29.0', native_checks=8,
                          large_plot_at150=True, original_shortcuts=3)))


if __name__ == '__main__':
    main()
