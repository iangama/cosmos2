"""Prepare an isolated worker only after accepted prescribed-density science."""
from pathlib import Path
import argparse
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/is5-coulomb-worker-v2-staging'
TARGET=ROOT/'output/is5-compression-worker-staging'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--science-receipt',default='evidence/is5-compression-fast-20261029a.json');args=parser.parse_args()
    science_path=(ROOT/args.science_receipt).resolve();assert science_path.is_relative_to(ROOT)
    science=json.loads(science_path.read_text());assert science['accepted'] and science['completed']
    assert science['generation']['id']=='is5:thermal-row-closed-baryon-prescribed-density-CNOII-PC-zone'
    parent_path=ROOT/'evidence/is5-coulomb-worker-artifact-20261029b.json'
    parent=json.loads(parent_path.read_text());assert parent['accepted']
    for receipt in [science,parent]:
        assert all(sha(ROOT/name)==value for name,value in receipt['source_sha256'].items())
    if TARGET.exists():raise FileExistsError('Preserve compression worker candidate')
    names=['is5_coulomb_artifact.py','is5_solar_source.py','is5_coulomb_worker.py',
           'is5_coulomb_calculate.py','is5_coulomb_client.py','is5_coulomb_process.py']
    texts={}
    for name in names:
        text=(BASE/name).read_text(encoding='utf-8')
        text=text.replace('import is5_coulomb_network as core','import is5_compression_fast as core')
        text=text.replace('output/is5-coulomb-network-staging','output/is5-compression-fast-staging')
        text=text.replace('is5_coulomb','is5_compression')
        texts[name.replace('is5_coulomb','is5_compression')]=text
    def change(name,old,new):
        assert old in texts[name],(name,old)
        texts[name]=texts[name].replace(old,new)
    artifact='is5_compression_artifact.py'
    change(artifact,"'evidence/is5-coulomb-science-20261028a.json'",repr(science_path.relative_to(ROOT).as_posix()))
    change(artifact,'Accepted Coulomb science differs','Accepted prescribed-density science differs')
    change(artifact,"{'parameters','acting','channel_switches','mode','include_coulomb','include_screening'}",
                    "{'parameters','density_history','acting','channel_switches','mode','include_coulomb','include_screening'}")
    change(artifact,"        p=parameters(configuration['parameters'])",'''        if not isinstance(configuration['parameters'],dict) or set(configuration['parameters'])!=set(core.base.DEFAULT_PARAMETERS):raise ValueError('Exact initial-zone parameter fields required')
        p=parameters(configuration['parameters'])
        history=core.density_program(configuration['density_history'],p)''')
    change(artifact,"mode not in ('prescribed','isochoric')","mode!='prescribed_density'")
    change(artifact,'actual=integrate_zone(p,a,c,mode=mode,include_coulomb=ce,include_screening=sc)',
                    'actual=integrate_zone(p,history,a,c,include_coulomb=ce,include_screening=sc)')
    change(artifact,'else integrate_zone(p,mode=mode,include_coulomb=ce,include_screening=sc)',
                    'else integrate_zone(p,history,include_coulomb=ce,include_screening=sc)')
    change(artifact,'configuration=dict(parameters=p,acting=a,','configuration=dict(parameters=p,density_history=history,acting=a,')
    a=texts[artifact].index("            scalar=['time_s'")
    b=texts[artifact].index('        return dict(index=i',a)
    texts[artifact]=texts[artifact][:a]+'''            scalar=['time_s','temperature_K','density_kg_m3','volume_m3','pressure_Pa','internal_energy_J_m3',
                'internal_energy_J','external_pressure_work_J','heat_capacity_J_m3_K','Coulomb_internal_energy_J_m3',
                'energy_available_J','energy_neutrinos_J','non_neutrino_energy_available_J',
                'nuclear_power_W','neutrino_power_W','external_pressure_power_W','neutrino_count',
                'produced_positrons','annihilated_electrons','captured_electrons']
            return {**{k:network[k][i] for k in scalar},
                'baryon_count':network['baryon_count'],'initial_internal_energy_J':network['initial_internal_energy_J'],
                'screening_factors':dict(zip(channels,network['screening_factors'][i])),
                'mass_fractions':dict(zip(names,network['mass_fractions'][i])),
                'number_per_baryon':dict(zip(names,network['number_per_baryon'][i])),
                **{field:dict(zip(channels,network[field][i])) for field in
                    ['event_rates_m3_s','event_rates_per_s','reaction_extents_count','reaction_extents_per_baryon']}}
''' +texts[artifact][b:]
    change('is5_compression_worker.py','CALCULATION_BUDGET_S=240.','CALCULATION_BUDGET_S=600.')
    change('is5_compression_worker.py','Calculation budget must be0.01..240s','Calculation budget must be0.01..600s')
    change('is5_compression_client.py','300 if calculation','660 if calculation')
    TARGET.mkdir()
    for name,text in texts.items():(TARGET/name).write_text(text,encoding='utf-8')
    manifest=dict(prepared=True,accepted=False,parent_worker_receipt_sha256=sha(parent_path),
                  science_receipt=science_path.relative_to(ROOT).as_posix(),science_receipt_sha256=sha(science_path),
                  recipe_sha256=sha(Path(__file__)),files_sha256={name:sha(TARGET/name) for name in texts},
                  calculation_budget_s=600,transport_budget_s=660)
    (TARGET/'preparation-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(stage=str(TARGET),files=len(texts),accepted=False)))


if __name__=='__main__':main()
