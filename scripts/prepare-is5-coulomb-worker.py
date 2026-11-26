"""Prepare an isolated artifact adapter; preserve the accepted CNO-II worker."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'output/is5-cno2-worker-staging'
TARGET = ROOT/'output/is5-coulomb-worker-staging'
if TARGET.exists():
    raise FileExistsError('Preserve Coulomb worker staging')
TARGET.mkdir()
source = (BASE/'is5_cno2_artifact.py').read_text(encoding='utf-8')
source = source.replace('is5_cno2','is5_coulomb').replace('output/is5-cno2-staging','output/is5-coulomb-network-staging')
source = source.replace('from is5_coulomb import parameters,active_channels\nfrom is5_coulomb import integrate_zone,generation as core_generation',
    'import is5_coulomb_network as core\nparameters,active_channels=core.base.parameters,core.base.active_channels\nintegrate_zone,core_generation=core.integrate_zone,core.generation')
source = source.replace("['is5_coulomb_artifact.py','is5_solar_source.py']",
    "['is5_coulomb_artifact.py','is5_solar_source.py','is5_coulomb_worker.py','is5_coulomb_calculate.py','is5_coulomb_client.py']")
source = source.replace("    return dict(core=core_generation(),artifact_code_sha256=dict(IMPORTED),schema=1)",
    "    science_path=ROOT/'evidence/is5-coulomb-science-20261028a.json'\n"
    "    science=json.loads(science_path.read_text(encoding='utf-8'))\n"
    "    if not science.get('accepted') or science['generation']!=core_generation():raise ValueError('Accepted Coulomb science differs')\n"
    "    return dict(core=core_generation(),artifact_code_sha256=dict(IMPORTED),schema=2,science_acceptance_sha256=hashlib.sha256(science_path.read_bytes()).hexdigest())")
old_start = source.index("        if not isinstance(configuration,dict) or set(configuration)!=")
old_end = source.index("        if generation()!=gen:",old_start)
source = source[:old_start]+'''        required={'parameters','acting','channel_switches','mode','include_coulomb','include_screening'}
        if not isinstance(configuration,dict) or set(configuration)!=required:raise ValueError('Complete Coulomb scenario configuration required')
        if not isinstance(configuration['acting'],dict) or not isinstance(configuration['channel_switches'],dict):raise ValueError('Explicit force/channel switches required')
        p=parameters(configuration['parameters'])
        a,c,enabled=active_channels(configuration['acting'],configuration['channel_switches'])
        mode=configuration['mode'];ce=configuration['include_coulomb'];sc=configuration['include_screening']
        if type(ce) is not bool or type(sc) is not bool or mode not in ('prescribed','isochoric') or sc and not ce:raise ValueError('Coulomb mode/options invalid')
        source=bind(source_phase);gen=generation()
        actual=integrate_zone(p,a,c,mode=mode,include_coulomb=ce,include_screening=sc)
        reference=actual if all(enabled.values()) else integrate_zone(p,mode=mode,include_coulomb=ce,include_screening=sc)
''' + source[old_end:]
source = source.replace("configuration=dict(parameters=p,acting=a,channel_switches=c,decay_basis=basis,mode=mode)",
                        "configuration=dict(parameters=p,acting=a,channel_switches=c,mode=mode,include_coulomb=ce,include_screening=sc)")
source = source.replace("'energy_available_J_m3','energy_neutrinos_J_m3'",
                        "'Coulomb_internal_energy_J_m3','energy_available_J_m3','energy_neutrinos_J_m3'")
source = source.replace("'mass_fractions':dict(zip(names,network['mass_fractions'][i]))",
                        "'screening_factors':dict(zip(channels,network['screening_factors'][i])),\n                'mass_fractions':dict(zip(names,network['mass_fractions'][i]))")
(TARGET/'is5_coulomb_artifact.py').write_text(source,encoding='utf-8')
(TARGET/'is5_solar_source.py').write_bytes((BASE/'is5_solar_source.py').read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest = dict(kind='isolated_Coulomb_artifact_from_CNOII',scientific_acceptance='is5-coulomb-science-20261028a',
                base_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in BASE.glob('*.py')},
                changes='Own schema/configuration/science generation, Coulomb U and screening probes. Store/seals/branches retained by merit.')
(TARGET/'base-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(prepared=True,folder=str(TARGET))))
