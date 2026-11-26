"""Prepare0.27.0 and a pinned two-origin journey inventory; no service/UI execution."""
import copy
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/is6-dynamics16-product0.26.2'
TARGET=ROOT/'output/is6-expanded-journey-product0.27.0'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    receipt=ROOT/'evidence/is6-expanded-journey-preparation-20261112a.json'
    assert not TARGET.exists() and not receipt.exists(),'Preserve prepared journey'
    manifest_path=BASE/'build-manifest.json';parent=json.loads(manifest_path.read_text(encoding='utf8'))
    actual={p.relative_to(BASE/'app').as_posix():sha(p) for p in (BASE/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    assert actual==parent['files_sha256']
    gates=[ROOT/'evidence'/n for n in ['is6-dynamics16-profile-audit-v2-20261112a.json','is6-dynamics16-reopen-20261112a.json',
        'is6-dynamics16-visual-20261112b.json','is6-dynamics16-service-20261112c.json','is6-dynamics16-http-20261112c.json',
        'github-source-local-20261112b.json']]
    assert all(json.loads(p.read_text())['accepted'] for p in gates)
    old_path=ROOT/'evidence/is6-integrated-journey-20261102e.json';old=json.loads(old_path.read_text())
    assert old['accepted'] and old['completed']
    protected={n:sha(ROOT/n) for n in ['user/sessions/latest.json','output/session.json','Iniciar-Cosmos2.cmd','Abrir-Planetas-e-Luas.cmd','Abrir-Dinamica16.cmd']}
    files=[Path(__file__),manifest_path,old_path,ROOT/'IS-6-PERCURSO-AMPLIADO16-CONTRATO.md',
           ROOT/'IS-6-PERCURSO-INTEGRADO-CONTRATO-PREVIO.md',*gates]
    sources={**parent['source_sha256'],**{p.relative_to(ROOT).as_posix():sha(p) for p in files}}
    assert all(sha(ROOT/n)==s for n,s in sources.items())
    inventory=dict(schema=1,candidate='0.27.0',prepared=True,service_executed=False,native_executed=False,
        origins=[dict(kind='solar_sixteen_physical_centers',version='0.1.0',count=16,
                      role='Own point-mass dynamics, per-source gravity, checkpoint and parent/child branches'),
                 dict(kind='solar_four_physical_centers',version='1.0.0',count=4,
                      role='One common paused four-center phase across established magnetic, test-particle and nuclear instruments')],
        phase_policy='Same confirmed Atlas epoch, two explicit scientific origins; each checkpoint retains its own population/frame/GM/IDs. Preserve the single common phase within the four-body group.',
        guard_fields=['system_id','edit_token','revision','expected_time','frame'],
        magnetic_admission=dict(sixteen=False,four=True),nuclear_planetary_coupling=False,
        legacy_recipe=copy.deepcopy(old['recipe_before_execution']),
        recipe_source=dict(path=old_path.relative_to(ROOT).as_posix(),sha256=sha(old_path)),
        pending=['Prepare and verify service16->4->16 with exact restoration and stale-guard refusals',
                 'Pin particle/solar/layer service configurations and archives',
                 'Prepare own native launcher, full journey and original captures',
                 'Plan residency/transition performance before measuring'])
    shutil.copytree(BASE/'app',TARGET/'app',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    assert {p.relative_to(TARGET/'app').as_posix():sha(p) for p in (TARGET/'app').rglob('*') if p.is_file()}==actual
    (TARGET/'journey-inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    packet=dict(candidate='0.27.0',accepted=False,promoted=False,source_sha256=sources,files_sha256=actual,changed=[],
        base_manifest=manifest_path.relative_to(ROOT).as_posix(),scene_profile=parent['scene_profile'],
        inherited_service=copy.deepcopy(parent['inherited_service']),
        journey_inventory_sha256=sha(TARGET/'journey-inventory.json'),
        scope='Unmodified scientific/UI files in a new isolated namespace. Journey inventory only; no service or native execution, promotion or new scientific coupling.')
    (TARGET/'build-manifest.json').write_text(json.dumps(packet,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    assert all(sha(ROOT/n)==s for n,s in protected.items())
    result=dict(prepared=True,accepted=False,candidate='0.27.0',app_byte_identical=True,source_sha256=sources,
        inventory_sha256=sha(TARGET/'journey-inventory.json'),protected_sha256=protected,protected_unchanged=True,
        service_executed=False,native_executed=False,next='Prepare the16->4->16 service verifier in its own temporary storage.')
    receipt.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(prepared=True,candidate='0.27.0',app_byte_identical=True,service_executed=False,owner_app_unchanged=True)),flush=True)


if __name__=='__main__':main()
