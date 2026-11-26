"""Prepare separate full-server staging around the accepted point-lens CPU kernel."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT/'output/original-flow-hotfix-product0.28.4'
TARGET=ROOT/'output/c214-point-lens-service-staging'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def replace(text,before,after):
    assert text.count(before)==1,before[:80]
    return text.replace(before,after)


def main():
    assert not TARGET.exists()
    for name in ['c214-point-lens-offline-20261121b.json','c214-point-lens-geometry-20261121a.json']:
        gate=json.loads((ROOT/'evidence'/name).read_text());assert gate['accepted'] and gate['completed']
        assert all(sha(ROOT/n)==seal for n,seal in gate['source_sha256'].items())
    parent=json.loads((PARENT/'build-manifest.json').read_text())
    assert all(sha(PARENT/n)==seal for n,seal in parent['files_sha256'].items())
    for folder in ['app','data']:shutil.copytree(PARENT/folder,TARGET/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copy2(ROOT/'output/c214-point-lens-staging/point_lens.py',TARGET/'app/point_lens.py')
    shutil.copy2(ROOT/'scripts/point-lens-force-adapter.py',TARGET/'app/point_lens_force_adapter.py')
    forces=TARGET/'app/forces.py';text=forces.read_text()
    addition="""SCENARIOS['point-lens'] = {
    'name':'Lente pontual · fonte, lente e observador', 'force':'gravity',
    'parameters': {
        'mass_solar':(1, .0001, 1e8, 'Massa da lente / Sol nominal'),
        'observer_x_au':(0, -1e6, 1e6, 'Observador · X / au'),
        'observer_y_au':(0, -1e6, 1e6, 'Observador · Y / au'),
        'observer_z_kpc':(0, -100, 100, 'Observador · Z / kpc'),
        'lens_x_au':(0, -1e6, 1e6, 'Lente · X / au'),
        'lens_y_au':(0, -1e6, 1e6, 'Lente · Y / au'),
        'lens_z_kpc':(4, -100, 100, 'Lente · Z / kpc'),
        'source_x_au':(8, -1e6, 1e6, 'Fonte · X / au'),
        'source_y_au':(0, -1e6, 1e6, 'Fonte · Y / au'),
        'source_z_kpc':(8, -100, 100, 'Fonte · Z / kpc')},
    'effect_keys': {'gravity':['ray_bending']}}


"""
    text=replace(text,'def normalize(request):',addition+'def normalize(request):')
    text=replace(text,"    elif key == 'timelike-orbits':","    elif key == 'point-lens':\n        from point_lens_force_adapter import experiment\n        result = experiment(config['parameters'], config['controls'])\n    elif key == 'timelike-orbits':")
    forces.write_text(text,encoding='utf8')
    contract=TARGET/'app/science_contracts.py';text=contract.read_text()
    text=replace(text,"    'timelike-orbits':('schwarzschild", "    'point-lens':('point-mass-thin-lens-euclidean','static_observer_lens_source_cartesian',['app/point_lens.py','app/point_lens_force_adapter.py']),\n    'timelike-orbits':('schwarzschild")
    text=replace(text,"    'timelike-orbits':[],","    'timelike-orbits':[],\n    'point-lens':[],")
    text=replace(text,"if scenario=='timelike-orbits' else", "if scenario in ['timelike-orbits','point-lens'] else")
    addition="""    if scenario=='point-lens':
        return {'schema':1,'model_id':'cosmos2:'+model,'model_version':'0.1.0',
          'origin':'calculated_idealized_point_source_thin_lens','coordinate_frame':frame,
          'quantities':{'positions':'m; static Euclidean Cartesian observer/lens/source coordinates',
            'angles':'rad; paraxial slopes, geometric source angle reported separately',
            'magnification':'dimensionless; signed parity, total is sum of absolute image factors',
            'deflection':'rad; lens-equation alpha along impact, propagating photon turn has opposite transverse sign',
            'ray_vertices':'m; thin-lens broken lines, not integrated null geodesics'},
          'sampling':{'kind':'static_geometry','time_evolution':'none','epoch':None},
          'semantics':{'acting':'Direct unit-amplification intervention retains geometry and the full material reference',
            'visible':'presentation only','alignment':'Point-source caustic: ring, no preferred pair, no finite amplification',
            'cross_scenario_coupling':'none; no Atlas epoch or observed-body fit'},
          'domain':result['point_lens']['limits'],'units':result['units'],
          'numerical_error':'80digit Decimal geometry and Jacobian; independently checked against110digit numerical roots/derivatives',
          'source_uncertainty':'Idealized model; input coordinate spacing reported, observational uncertainty not propagated',
          'provenance':{'code_sha256':{p:FROZEN_HASHES[p] for p in SOURCE_PATHS[scenario]},
            'data_sha256':{},'runtime':RUNTIME,'sources':result['sources']}}
"""
    text=replace(text,"    if scenario=='timelike-orbits':",addition+"    if scenario=='timelike-orbits':")
    contract.write_text(text,encoding='utf8')
    files={p.relative_to(TARGET).as_posix():sha(p) for folder in ['app','data'] for p in (TARGET/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    changed=[n for n in parent['files_sha256'] if files[n]!=parent['files_sha256'][n]]
    added=[n for n in files if n not in parent['files_sha256']]
    assert sorted(changed)==['app/forces.py','app/science_contracts.py']
    assert sorted(added)==['app/point_lens.py','app/point_lens_force_adapter.py']
    proof=dict(accepted=True,completed=True,installed=False,native_user_flow_accepted=False,
      files_sha256=files,changed_app_files=changed,added_app_files=added,
      parent_manifest_sha256=sha(PARENT/'build-manifest.json'),preparation_script_sha256=sha(Path(__file__)),
      source_sha256={n:sha(ROOT/n) for n in ['output/c214-point-lens-staging/point_lens.py','scripts/point-lens-force-adapter.py','C2-14-LENTE-PONTUAL-SERVICO-20261121.md']},
      scope='Static full-server staging only: unchanged parent server/UI, new stateless point-lens adapter and kernel, catalog/contract extension. No live owner commands or UI promotion.')
    (TARGET/'preparation.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(prepared=True,changed=changed,added=added,installed=False)))


if __name__=='__main__':main()
