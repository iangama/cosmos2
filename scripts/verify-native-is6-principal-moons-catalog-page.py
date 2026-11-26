"""Exercise all sixteen bodies and confirmed-epoch export through the native data page."""
import base64
import hashlib
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import sys
import traceback
from cef_page_v2 import Page

ROOT=Path(__file__).resolve().parents[1]
h=SourceFileLoader('moons_data_page_helpers',str(ROOT/'scripts/benchmark-body-points-native.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
TARGETS=['10','199','299','399','301','499','599','699','799','899','501','502','503','504','602','606']


def main():
    label=sys.argv[1]
    if not label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):raise ValueError('Invalid label')
    profile=json.loads((ROOT/'evidence/is6-principal-moons-navigation-profile-20261111a.json').read_text())
    assert profile['completed'] or profile.get('failure') and profile.get('owner_app_kept_open')
    folder=ROOT/f'output/is6-principal-moons-catalog-native-{label}';out=ROOT/f'evidence/is6-principal-moons-catalog-native-{label}.json'
    if folder.exists() or out.exists():raise FileExistsError('Preserve data-page verification')
    folder.mkdir();protected={name:sha(ROOT/name) for name in ['user/sessions/latest.json','Iniciar-Cosmos2.cmd']}
    report=dict(accepted=False,completed=False,bodies=[],captures=[],errors=[],script_sha256=sha(Path(__file__)))
    initial=h.get('/api/atlas/state');navigation=h.get('/api/navigation/state')
    try:
        with Page() as page:
            page.on('pageerror',report['errors'].append)
            page.goto('http://127.0.0.1:4700/content.html');page.locator('#planet-catalog-link').click()
            page.wait_for_function('document.getElementById("catalog-body")?.options.length===16')
            page.evaluate('document.getElementById("catalog-utc").value="2000-01-01T12:00:00"')
            page.locator('#catalog-query').click()
            page.wait_for_function('document.getElementById("catalog-epoch").textContent.startsWith("2000-01-01T12:00:00.000Z")&&!document.getElementById("catalog-query").disabled')
            confirmed=page.locator('#catalog-epoch').inner_text()
            page.evaluate('document.getElementById("catalog-utc").value="1994-12-31T12:00:00"')
            page.locator('#catalog-query').click()
            page.wait_for_function('document.getElementById("catalog-status").textContent.includes("1995")&&!document.getElementById("catalog-query").disabled')
            assert page.locator('#catalog-epoch').inner_text()==confirmed
            page.evaluate('document.getElementById("catalog-utc").value="2000-01-01T12:00:00"')
            for target in TARGETS:
                page.locator('#catalog-body').select_option(target)
                title=page.locator('#catalog-title').inner_text();assert title.endswith('sol:naif:'+target)
                assert page.locator('.property-card').count()==5
                report['bodies'].append(dict(target=target,title=title))
            page.locator('#catalog-export').click()
            page.wait_for_function('document.getElementById("catalog-export-path").textContent.length>0')
            exported=Path(page.locator('#catalog-export-path').inner_text());state=json.loads(exported.read_text(encoding='utf8'))
            assert len(state['bodies'])==16 and state['epoch']['utc']=='2000-01-01T12:00:00.000Z'
            assert state['kind']=='eight_planets_and_principal_moons_geometric_reference'
            report['export']=dict(path=exported.as_posix(),sha256=sha(exported))
            for scale in [1,1.5]:
                page.evaluate('document.body.style.zoom='+json.dumps(str(scale)))
                page.evaluate('new Promise(requestAnimationFrame)')
                assert page.evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth')
                image=page.call('Page.captureScreenshot',{'format':'png'})
                path=folder/('catalog-'+str(scale)+'.png');path.write_bytes(base64.b64decode(image['data']))
                report['captures'].append(dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),scale=scale))
            for query in ['', '?utc=true','?utc=2026-02-30T00:00:00','?utc=2026-10-11T12:00:00&utc=2026-10-11T12:00:00','?utc=2026-10-11T12:00:00&extra=1']:
                import urllib.request,urllib.error
                try:urllib.request.urlopen('http://127.0.0.1:4700/api/planet-reference'+query)
                except urllib.error.HTTPError as error:assert error.code==400
                else:raise AssertionError('Invalid query admitted')
            assert not report['errors']
        after=h.get('/api/atlas/state');assert after['epoch']==initial['epoch'] and after['bodies']==initial['bodies']
        report.update(accepted=True,completed=True,atlas_epoch_and_bodies_unchanged=True)
    except Exception:report['failure']=traceback.format_exc()
    finally:
        try:
            with Page() as page:
                page.goto('http://127.0.0.1:4700/');page.wait_for_function('navigationState&&atlasState')
                page.evaluate('selectTarget('+json.dumps(navigation['target'])+',true)')
            report['protected_unchanged']={name:sha(ROOT/name)==seal for name,seal in protected.items()}
            assert all(report['protected_unchanged'].values())
        except Exception:report['cleanup_failure']=traceback.format_exc();report['accepted']=False
        out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(accepted=report['accepted'],bodies=len(report['bodies']),failure=report.get('failure'),cleanup_failure=report.get('cleanup_failure'))))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
