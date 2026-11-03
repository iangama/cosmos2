"""Versioned interpretation and provenance for bounded scientific exports.

Hashes are frozen when this module loads. Deploy scientific code/data as one
generation and restart the backend; live UI changes do not change the science.
"""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import platform

ROOT=Path(__file__).resolve().parents[1]
MODELS={
    'decays':('evaluated-linear-decay-chains','homogeneous_atomic_reference_state',['app/decays.py']),
    'fusion':('reaclib-forward-isolated-mixtures','homogeneous_prescribed_zone',['app/fusion.py','app/nuclear_energies.py','app/nuclei.py']),
    'geomagnetic':('igrf14-internal-main-field-instrument','earth_fixed_ecef_wgs84',['app/geomagnetism.py']),
    'dipole':('static-dipole-newton-classical-test-particle','planet_centered_cartesian_inertial',['app/dipole.py']),
    'gravity':('newtonian-single-test-particle','barycentric_inertial',[]),
    'binary':('circular-restricted-three-body-spatial','barycentric_corotating',['app/binary_gravity.py']),
    'electromagnetic':('uniform-field-lorentz-classical','cartesian_inertial',[]),
    'strong':('dt-forward-reaction-fixed-zone','homogeneous_prescribed_zone',[]),
    'weak':('evaluated-decay-expected-population','homogeneous_reference_state',[]),
    'stellar':('pp-i-forward-fixed-zone','homogeneous_prescribed_zone',['app/stellar.py']),
    'cno':('cno-i-forward-fixed-zone','homogeneous_prescribed_zone',['app/stellar.py','app/cno.py']),
    'relativity':('schwarzschild-exterior-null-ray','schwarzschild_areal_radius_equatorial',['app/relativity.py']),
}
SOURCE_PATHS={name:['app/forces.py','app/science_contracts.py',*extra] for name,(_,_,extra) in MODELS.items()}
DATA_PATHS={
    'decays':['data/science/decays.json',
              *[str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'data/science').glob('decays-*') if p.is_file()]],
    'fusion':['data/science/fusion.json','data/science/ame2020-mass-original.txt',
              *[str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'data/science').glob('fusion-*-reaclib.txt')]],
    'geomagnetic':['data/science/igrf14coeffs.txt'],
    'dipole':[],
    'gravity':[],'binary':[],'electromagnetic':[],
    'strong':['data/science/nuclear.json','data/science/dt-reaclib.txt'],
    'weak':['data/science/nuclear.json'],
    'stellar':['data/science/pp1.json',*[str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'data/science').glob('pp1-*-reaclib.txt')]],
    'cno':['data/science/cno1.json',*[str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'data/science').glob('cno1-*-reaclib.txt')]],
    'relativity':[],
}
FROZEN_HASHES={path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
               for path in sorted({path for paths in [*SOURCE_PATHS.values(),*DATA_PATHS.values()] for path in paths})}
RUNTIME={'python':platform.python_version(),**{name:importlib.metadata.version(name) for name in ('numpy','scipy')}}

def scientific_generation(scenario):
    """Recorded code/data and declared library versions; no claim of bit identity."""
    model,_,_=MODELS[scenario]
    return {'schema':1,'model_id':'cosmos2:'+model,'model_version':'1.0.0',
            'code_sha256':{p:FROZEN_HASHES[p] for p in SOURCE_PATHS[scenario]},
            'data_sha256':{p:FROZEN_HASHES[p] for p in DATA_PATHS[scenario]},
            'runtime':dict(RUNTIME)}

def generation_difference(saved,current):
    differences=[]
    for key in ('schema','model_id','model_version'):
        if saved.get(key)!=current.get(key):
            differences.append({'kind':'model','name':key,'saved':saved.get(key),'current':current.get(key)})
    for key,kind in [('code_sha256','code'),('data_sha256','data'),('runtime','runtime')]:
        old,new=saved.get(key,{}),current.get(key,{})
        if not isinstance(old,dict):raise ValueError('Registro de geração científica inválido.')
        for name in sorted(set(old)|set(new)):
            if old.get(name)!=new.get(name):
                differences.append({'kind':kind,'name':name,'saved':old.get(name),'current':new.get(name)})
    return differences

def contract(scenario,result):
    model,frame,_=MODELS[scenario]
    if scenario=='geomagnetic':
        return {'schema':1,'model_id':'cosmos2:'+model,'model_version':'1.0.0',
                'origin':'calculated_model_from_IAGA_coefficients','coordinate_frame':frame,
                'quantities':{'epoch':{'unit':'decimal Gregorian year','value':result['geomagnetic']['year_decimal'],
                                     'kind':'explicit static model epoch','coverage':[1900,2030],'atlas_epoch':'not inherited'},
                              'position_ecef_m':'m; WGS84 ellipsoid, X=Greenwich equator, Y=90deg east equator, Z=north',
                              'field_ecef_T':'T; Earth-fixed Cartesian','field_ned_T':'T; geodetic north,east,down',
                              'field_ned_nT':'nT; geodetic north,east,down','F_nT':'nT; total','H_nT':'nT; horizontal',
                              'D_deg':'degree; east positive, undefined if H approaches zero','I_deg':'degree; down positive',
                              'magnetic_force_ned_N':'N; instantaneous applied qv cross B, no integrated trajectory',
                              'magnetic_power_W':'W','velocity_ned_m_s':'m/s; local prescribed velocity',
                              'secular_ned_nT_year':'nT/year; piecewise model rate, not instantaneous observed secular variation',
                              'comparison':'degree1 truncation of same IGRF epoch and coefficients'},
                'sampling':{'kind':'spatial_snapshot','states':len(result['geomagnetic']['grid'])+1,
                            'latitude_step_deg':10,'longitude_step_deg':10,'epoch':result['geomagnetic']['year_decimal'],
                            'altitude_m':result['geomagnetic']['altitude_m'],'time_evolution':'none'},
                'semantics':{'acting':'suppresses instantaneous magnetic operator with coefficients/planet retained',
                             'visible':'presentation only','reference':'complete internal main-field model',
                             'cross_scenario_coupling':'none','atlas_epoch':'not inherited'},
                'numerical_error':'independent implementation difference, not observational accuracy',
                'source_uncertainty':'not locally propagated; external/local fields omitted; never assumed zero',
                'provenance':{'code_sha256':{p:FROZEN_HASHES[p] for p in SOURCE_PATHS[scenario]},
                              'data_sha256':{p:FROZEN_HASHES[p] for p in DATA_PATHS[scenario]},
                              'runtime':RUNTIME,'sources':result['sources']}}
    positions='positions' in result
    time_kind='normalized_affine_parameter' if scenario=='relativity' else 'elapsed_model_time'
    quantities={'time_s':{'unit':'s','kind':time_kind,'epoch':None,'calendar_scale':None},
                'measurements':{'unit':'per_item','origin':'calculated_model','source_uncertainty':'not_propagated'}}
    if positions:
        quantities.update(positions={'unit':'normalized_length','metres_per_unit':result['position_unit_m'],
                                     'frame':frame,'representation':'areal-radius Cartesian display' if scenario=='relativity' else 'Cartesian physical coordinates'},
                          field={'vector_unit':result.get('field_unit'),'kind':'full_acting_reference' if result['field'] else 'no_classical_vector_field',
                                 'sample_count':len(result['field']),'arrows':'directions normalized for display; magnitudes remain in exported data'})
    else:
        quantities['curves']={'unit':'conventional_baryon_mass_fraction' if result.get('network') else 'fraction_of_initial_population',
                              'definition':'X_i=A_i n_i/(rho/m_u)' if result.get('network') else 'population/initial_population'}
    if result.get('network'):
        quantities['network']={'event_rates_m3_s':'reactions/(m^3 s)','reaction_extents_m3':'reactions/m^3',
                               'energy_available_J_m3':'J/m^3','energy_neutrinos_J_m3':'J/m^3',
                               'energy_deposited_J_m3':'J/m^3','number_per_baryon':'n_i/(rho/m_u)',
                               'neutrino_count_m3':'expected neutrinos/m^3','temperature_density':'prescribed, no feedback',
                               'Q_atomic':'includes local positron annihilation where applicable; neutrino energy is separate'}
    if scenario=='fusion':
        quantities['curves']={'unit':'conventional_baryon_mass_fraction','definition':'A_i*n_i/sum(A_j*n_j_initial)'}
        quantities['fusion']={'number_density_m3':'nuclei/m^3','event_rates_m3_s':'reactions/(m^3 s)',
                              'reaction_extents_m3':'reactions/m^3','energy_available_J_m3':'J/m^3; REACLIB Q, not deposition',
                              'energy_deposited_J_m3':'unknown; no transport or thermal model',
                              'photon_count_m3':'photons/m^3; one per radiative capture, not a spectrum',
                              'Q_AME_keV':'neutral-atom mass-excess difference; independent mass uncertainties only',
                              'temperature_volume':'prescribed; isolated channels, no secondary product reactions'}
    if scenario=='decays':
        quantities['curves']={'unit':'fraction_of_initial_nuclear_population','definition':'N_i/total_nuclei_initial'}
        quantities['decays']={'populations':'expected nuclei, not stochastic event realization',
                              'activity_s':'Bq; parent order declared, applied partial widths only',
                              'channel_event_counts':'expected events, integrated feeding included',
                              'event_rates_s':'events/s','lepton_counts':'expected leptons per species; EC consumes atomic electron',
                              'energy_available_J':'J; same ENSDF atomic Q generation as branches',
                              'energy_neutrino_J':'J; source beta mean, nominal energy_ec approximation for EC',
                              'energy_non_neutrino_available_J':'J; remainder available, not deposition or electron-only kinetic energy',
                              'daughter_excitation':'keV per branch; no resolved EM relaxation',
                              'normalization':'printed complete branch intensities divided by printed total; factor retained',
                              'NUBASE2020':'explicit comparison only, not mixed into operational ENSDF generation'}
    if scenario=='relativity':
        quantities['time_s']['normalization']='E_infinity=1; lambda=L*r_s/c; neither observer coordinate time nor photon proper time'
        quantities['metric_probes']={'static_clock_ratio':'s/s relative to static infinity',
                                    'kretschmann_m_minus4':'m^-4','radius_rs':'r/r_s'}
    if scenario=='binary':
        quantities['field']['frame']='barycentric_corotating; inertial view rotates vectors without recalculating physics'
        quantities['binary']={'potential_m2_s2':'m^2/s^2, zero at infinity',
                              'tidal_eigenvalues_s2':'s^-2; eigenvalues of spatial acceleration gradient',
                              'velocities_rotating':'n*a','jacobi':'dimensionless rotating invariant; not inertial energy',
                              'boundary':'0.02 separation, numerical model limit, not physical radius'}
    if scenario=='electromagnetic':
        quantities['particle_readings']={'velocity_m_s':'m/s','electric_force_N':'N',
                                        'magnetic_force_N':'N','total_force_N':'N',
                                        'kinetic_energy_J':'J','electric_work_J':'J',
                                        'electric_power_W':'W','magnetic_power_W':'W'}
    if scenario=='dipole':
        quantities['field'].update(vector_unit='per_item',units={'magnetic':'T','gravity':'m/s^2'},
                                   frame=frame,source='prescribed static ideal dipole and nominal GM; not IGRF')
        quantities['particle_readings']={'velocity_m_s':'m/s','magnetic_field_T':'T','gravity_force_N':'N',
                                        'magnetic_force_N':'N','total_force_N':'N','kinetic_energy_J':'J',
                                        'potential_energy_J':'J; applied gravitational operator only',
                                        'total_energy_J':'J; K+U_applied','magnetic_power_W':'W',
                                        'parallel_velocity_m_s':'m/s; along reference B', 'pitch_deg':'degree; 0 to 180',
                                        'magnetic_moment_J_T':'J/T; adiabatic diagnostic, not exact invariant'}
        quantities['trajectory']={'trace_time_s':'s','reference_time_s':'s; separate full-reference duration',
                                  'position':'prescribed planetary radius; metres_per_unit in positions',
                                  'sampling':'local gyroperiod from interval endpoints and midpoint, 5% margin, 20 samples per cycle; measurement instants included, <=12001 points',
                                  'limits':'1R or10R stops model, no collision product'}
        quantities['curves']={'unit':'dimensionless','definition':'B/B0, pitch/90deg, K/K0, (K+U)/(K0+U0), magnetic moment ratio'}
    return {'schema':1,'model_id':'cosmos2:'+model,'model_version':'1.0.0',
            'origin':'calculated_model','coordinate_frame':frame,'quantities':quantities,
            'sampling':{'states':len(result['time_s']),'start_s':result['time_s'][0],
                        'end_s':result['time_s'][-1],'interpolation':'presentation only, no new scientific states'},
            'semantics':{'acting':'suppresses selected operators with reference sources/material fixed',
                         'visible':'presentation only','reference':'complete acting model',
                         'cross_scenario_coupling':'none','atlas_epoch':'not inherited'},
            'numerical_error':'reported diagnostics; different from source uncertainty',
            'source_uncertainty':'not propagated; absent values are unknown, never zero',
            'provenance':{'code_sha256':{p:FROZEN_HASHES[p] for p in SOURCE_PATHS[scenario]},
                          'data_sha256':{p:FROZEN_HASHES[p] for p in DATA_PATHS[scenario]},
                          'runtime':RUNTIME,'sources':result['sources']}}

def physics_fingerprint(configuration,result,model_contract):
    # Presentation controls belong in configuration_sha256 but not in science.
    record={'model':model_contract,'parameters':configuration['parameters'],
            'applied_effects':result['applied_effects']}
    return hashlib.sha256(json.dumps(record,sort_keys=True,allow_nan=False).encode()).hexdigest()
