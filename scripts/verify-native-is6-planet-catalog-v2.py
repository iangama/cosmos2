"""Exercise the catalogue through its native data-page entry point."""
import argparse
import base64
import hashlib
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import traceback
import urllib.error
import urllib.request

from cef_page_v2 import Page
from is6_owned_profile_host import Host

ROOT = Path(__file__).resolve().parents[1]
h = SourceFileLoader('planet_native_helpers', str(ROOT / 'scripts/benchmark-body-points-native.py')).load_module()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    label = parser.parse_args().label
    if not label or len(label) > 20 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):
        parser.error('Invalid label')
    folder = ROOT / 'output' / f'is6-planet-catalog-native-{label}'
    receipt = ROOT / 'evidence' / f'is6-planet-catalog-native-{label}.json'
    if folder.exists() or receipt.exists():
        raise FileExistsError('Preserve native catalogue verification')
    folder.mkdir()
    owner = ROOT / 'user/sessions/latest.json'
    owner_sha = sha(owner)
    result = dict(completed=False, functional_accepted=False, page_errors=[], bodies=[], captures=[],
                  script_sha256=sha(Path(__file__)), scope='Native data page, API and export; visual review and own profiles pending')
    host = Host(folder, h, candidate='output/is6-planet-catalog-product0.23.1',
                launcher='scripts/launch-is6-planet-catalog-candidate-v2.py')
    try:
        result['session'] = host.start()
        with Page() as page:
            page.on('pageerror', result['page_errors'].append)
            page.goto('http://127.0.0.1:4700/content.html')
            page.locator('#planet-catalog-link').click()
            page.wait_for_function('document.getElementById("catalog-body")?.options.length===10')
            assert page.evaluate('location.pathname') == '/planet-catalog.html'
            assert page.evaluate('document.getElementById("catalog-utc").type') == 'text'
            page.evaluate('document.getElementById("catalog-utc").value="2000-01-01T12:00:00"')
            page.locator('#catalog-query').click()
            page.wait_for_function('document.getElementById("catalog-epoch").textContent.startsWith("2000-01-01T12:00:00.000Z")&&!document.getElementById("catalog-query").disabled')
            confirmed_epoch = page.locator('#catalog-epoch').inner_text()
            page.evaluate('document.getElementById("catalog-utc").value="1994-12-31T12:00:00"')
            page.locator('#catalog-query').click()
            page.wait_for_function('document.getElementById("catalog-status").textContent.includes("1995")&&!document.getElementById("catalog-query").disabled')
            assert page.locator('#catalog-epoch').inner_text() == confirmed_epoch
            page.evaluate('document.getElementById("catalog-utc").value="2000-01-01T12:00:00"')
            for target in ['10', '199', '299', '399', '301', '499', '599', '699', '799', '899']:
                page.locator('#catalog-body').select_option(target)
                title = page.locator('#catalog-title').inner_text()
                assert title.endswith('sol:naif:' + target)
                assert page.locator('.property-card').count() == 5
                result['bodies'].append(dict(target=target, title=title))
            page.locator('#catalog-export').click()
            page.wait_for_function('document.getElementById("catalog-export-path").textContent.length>0')
            exported = Path(page.locator('#catalog-export-path').inner_text())
            data = json.loads(exported.read_text(encoding='utf8'))
            assert data['kind'] == 'eight_planet_geometric_reference' and len(data['bodies']) == 10
            assert data['epoch']['utc'] == '2000-01-01T12:00:00.000Z'
            result['export'] = dict(path=exported.as_posix(), sha256=sha(exported))
            for scale in [1, 1.5]:
                page.evaluate('document.body.style.zoom=' + json.dumps(str(scale)))
                page.evaluate('new Promise(requestAnimationFrame)')
                bounds = page.evaluate('({scroll:document.documentElement.scrollWidth,width:document.documentElement.clientWidth})')
                assert bounds['scroll'] <= bounds['width'], bounds
                capture = folder / ('catalog-' + str(scale).replace('.', '-') + '.png')
                shot = page.call('Page.captureScreenshot', {'format': 'png'})
                capture.write_bytes(base64.b64decode(shot['data']))
                result['captures'].append(dict(path=capture.relative_to(ROOT).as_posix(),
                                               sha256=sha(capture), scale=scale, bounds=bounds))
            for query in ['', '?utc=true', '?utc=2026-02-30T00:00:00',
                          '?utc=2026-10-11T12:00:00&utc=2026-10-11T12:00:00',
                          '?utc=2026-10-11T12:00:00&extra=1']:
                try:
                    urllib.request.urlopen('http://127.0.0.1:4700/api/planet-reference' + query)
                except urllib.error.HTTPError as error:
                    assert error.code == 400
                else:
                    raise AssertionError('Invalid catalogue query admitted: ' + query)
            assert not result['page_errors']
        result.update(completed=True, functional_accepted=True)
    except Exception:
        result['failure'] = traceback.format_exc()
    finally:
        try:
            result['processes'] = host.close()
            assert len(result['processes']) == 4 and set(result['processes'].values()) == {0}
            result['owner_unchanged'] = sha(owner) == owner_sha
            assert result['owner_unchanged']
        except Exception:
            result['cleanup_failure'] = traceback.format_exc()
            result['functional_accepted'] = False
        receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(completed=result['completed'], functional_accepted=result['functional_accepted'],
                          bodies=len(result['bodies']), captures=len(result['captures']),
                          failure=result.get('failure'), cleanup_failure=result.get('cleanup_failure'))), flush=True)
    return 0 if result['functional_accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
