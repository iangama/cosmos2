"""Scientific state, explicit interventions, and atomic checkpoint publication."""
from pathlib import Path
import hashlib
import json
import math
import uuid
import copy
import rebound
import body_attributes as attributes
import orbital_diagnostics as orbital
import gravity_instruments as instruments
import field_layers as fields
import instrument_history as history
from physics import CONTRACT, PHYSICAL_SCALE, fixture, snapshot
from body_registry import (MAX_BODIES,CUSTOM_CONTRACT,atlas_metadata,fixture_metadata,
                           validate_registry,valid_system,phases_si,scene_nodes,
                           validate_population,validate_user_seed,
                           name as body_name,digest,generation as editable_generation)

class Session:
    def __init__(self, directory, count=32):
        self.directory = Path(directory)
        self._branch_catalog=None
        self._branch_error=None
        self.reset(count)

    def reset(self, count):
        replacement = fixture(count)
        replacement.exit_min_distance=1e-12
        self.sim = replacement
        self.initial_energy = replacement.energy()
        self.interventions = []
        self.revision = 0
        self.fixture_count = count
        self.atlas_initial = None
        self.system_id=uuid.uuid4().hex
        self.edit_token=uuid.uuid4().hex
        self.registry=fixture_metadata(count)
        self.body_attributes={b['id']:attributes.defaults(b) for b in self.registry}
        self.issued_ids=[b['id'] for b in self.registry]
        self.topology_revision=0
        self.seed={'kind':'fixture','count':count}
        self.restoration=None
        encoded = json.dumps(snapshot(replacement, self.initial_energy), sort_keys=True, separators=(',', ':')).encode()
        self.fixture_sha256 = hashlib.sha256(encoded).hexdigest()
        self.conservation_reference=self._reference(replacement,self.registry,'initial_condition')
        self.instruments=instruments.empty()
        self.field_layers=fields.empty()
        self.instrument_history=history.empty()
        self._history_last_wall=None

    def state(self):
        state = {**snapshot(self.sim, self.initial_energy), 'contract': self.contract(),
                'revision': self.revision, 'fixture_count': self.fixture_count,
                'fixture_sha256': self.fixture_sha256, 'interventions': self.interventions,
                'system_id':self.system_id,'edit_token':self.edit_token,'origin_kind':self.seed['kind'],
                'scientific_generation':editable_generation(self.seed['kind']),
                'topology_revision':self.topology_revision,
                'instruments':instruments.public(self.instruments),
                'field_layers':fields.public(self.field_layers),
                'instrument_history':history.public(self.instrument_history),
                'branches':self._branch_summary(),
                'numerical_policy':{'ias15_adaptive_mode':self.sim.integrator.adaptive_mode,
                    'single_body_policy':'INDIVIDUAL error criterion for exactly one active mass with zero force; PRS23 for multiple masses',
                    'probe_backreaction':False},
                'integration_boundary':{'minimum_separation_m':.001,'policy':'pause near point-mass singularity; no collision response or merger'},
                'population_contract':{'active_ids':[b['id'] for b in self.registry],
                                       'active_mass_count':self.sim.N if self.sim.N_active==2**64-1 else self.sim.N_active,
                                       'all_active_masses_gravitate':self.sim.N_active in (2**64-1,self.sim.N) and self.sim.N_var==0,'source_initial_population_preserved':True}}
        for body,meta in zip(state['bodies'],self.registry):
            body.update(copy.deepcopy(meta));body.update(scene_nodes(meta['id']))
            body['applied_GM_m3_s2']=body['mass']*PHYSICAL_SCALE['nominal_GM_unit_m3_s2']
            body['attributes']=copy.deepcopy(self.body_attributes[body['id']])
            body['attributes']['orientation_wxyz']=attributes.orientation(body['attributes'],self.sim.t)
        if self.atlas_initial is not None:
            state['atlas_initial'] = self.atlas_initial
        if self.restoration:state['restoration']=self.restoration
        state['conservation']=orbital.conservation(state['bodies'],self.sim.t,self.conservation_reference,self.initial_energy,self.sim.energy())
        if self.seed.get('scenario'):
            import gravity_experiments
            state['experiment']=gravity_experiments.evaluate(state['bodies'],self.seed,self.issued_ids,self.sim.t,self.interventions)
            state['display_min_view_distance_m']=self.seed['scenario']['display_min_view_distance_m']
            for b in state['bodies']:b['display_marker_radius_m']=self.seed['scenario']['display_marker_radius_m']
        return state

    def _branches(self):
        if self._branch_error:raise ValueError(self._branch_error)
        if self._branch_catalog is None:
            from branch_store import Store
            self._branch_catalog=Store(self.directory/'branches')
        active=self._branch_catalog.records.get(self._branch_catalog.active_id)
        if active and active['system_id']!=self.system_id:self._branch_catalog.active_id=None
        return self._branch_catalog

    def _branch_summary(self):
        try:return self._branches().public()
        except (ValueError,OSError,KeyError) as error:
            self._branch_error='Catálogo de ramos indisponível: '+str(error)
            return {'maximum_branches':32,'active_id':None,'branches':[],'error':self._branch_error}

    def create_branch(self,request):return self._branches().create(self,request)
    def load_branch(self,request):return self._branches().load(self,request)
    def compare_branches(self,request):return self._branches().compare(self,request)

    @staticmethod
    def _validate_solver(sim,allow_legacy_single=False):
        if (sim.G!=1 or str(sim.integrator)!='ias15' or sim.integrator.epsilon!=1e-9 or str(sim.gravity)!='basic'
            or sim.softening!=0 or str(sim.collision)!='none' or sim.N_active not in (2**64-1,sim.N) or sim.N_var!=0
            or bool(sim._additional_forces) or sim.integrator.adaptive_mode not in (('INDIVIDUAL','PRS23') if sim.N==1 and allow_legacy_single else ('INDIVIDUAL',) if sim.N==1 else ('PRS23',))):
            raise ValueError('Contrato do solver incompatível com massas pontuais ativas.')

    @staticmethod
    def _bodies(sim,registry):
        return [{'id':b['id'],**Session._phase(p)} for p,b in zip(sim.particles,registry)]

    @staticmethod
    def _reference(sim,registry,policy):
        return {**orbital.integrals(Session._bodies(sim,registry),sim.t,sim.energy()),'policy':policy,
                'active_ids':[b['id'] for b in registry],'energy_reference_time':None if policy=='legacy_checkpoint_new_momentum_reference' else sim.t}

    def contract(self):
        return self.atlas_initial['contract'] if self.atlas_initial else CUSTOM_CONTRACT if self.seed['kind']=='user_system' else CONTRACT

    def import_atlas(self, initial):
        from atlas_import import validate
        initial = validate(initial)
        replacement = rebound.Simulation()
        replacement.G = 1.0
        replacement.integrator = 'ias15'
        replacement.integrator.epsilon = 1e-9
        replacement.exit_min_distance=1e-12
        for b in initial['bodies']:
            replacement.add(m=b['mass'], x=b['position'][0], y=b['position'][1], z=b['position'][2],
                            vx=b['velocity'][0], vy=b['velocity'][1], vz=b['velocity'][2])
        baseline = replacement.energy()
        if not math.isfinite(baseline) or baseline == 0:
            raise ValueError('Energia inicial do subconjunto inválida.')
        # All validation/construction precedes the atomic session replacement.
        self.sim, self.initial_energy = replacement, baseline
        self.interventions, self.revision, self.fixture_count = [], 0, None
        self.atlas_initial = initial
        self.fixture_sha256 = initial['initial_state_sha256']
        self.restoration = None
        self.system_id=uuid.uuid4().hex;self.seed={'kind':'atlas_copy'}
        self.edit_token=uuid.uuid4().hex
        self.registry=atlas_metadata(initial);self.issued_ids=[b['id'] for b in self.registry];self.topology_revision=0
        self.body_attributes={b['id']:attributes.defaults(b,initial) for b in self.registry}
        self.conservation_reference=self._reference(replacement,self.registry,'initial_condition')
        self.instruments=instruments.empty()
        self.field_layers=fields.empty()
        self.instrument_history=history.empty()
        self._history_last_wall=None

    def set_mass(self, identifier, mass):
        identifiers = [b['id'] for b in self.registry]
        if not isinstance(identifier, str) or identifier not in identifiers:
            raise ValueError('Unknown body identifier')
        index = identifiers.index(identifier)
        if type(mass) not in (int, float) or not math.isfinite(mass) or not 1e-12 <= mass <= 100:
            raise ValueError('Mass must be finite and between 1e-12 and 100 canonical units')
        replacement=self.sim.copy()
        body = next(p for i,p in enumerate(replacement.particles) if i == index)
        old = body.m
        before = replacement.energy()
        velocity = [body.vx, body.vy, body.vz]
        body.m = mass
        # The intervention invalidates cached force derivatives in the integrator.
        replacement.integrator = 'ias15'
        replacement.integrator.epsilon = 1e-9
        if replacement.N==1:replacement.integrator.adaptive_mode='INDIVIDUAL'
        after = replacement.energy()
        if not math.isfinite(after):raise ValueError('Energia não finita após alterar a massa.')
        reference=self._reference(replacement,self.registry,'external_intervention')
        radius=[body.x,body.y,body.z];delta_mass=mass-old
        dl=[delta_mass*(radius[(k+1)%3]*velocity[(k+2)%3]-radius[(k+2)%3]*velocity[(k+1)%3]) for k in range(3)]
        self.revision += 1
        event = {'revision': self.revision, 'time': self.sim.t, 'body': identifier,
                 'type': 'set_mass', 'old_mass': old, 'new_mass': mass,
                 'policy': 'preserve_position_and_velocity', 'external_energy_delta': after-before,
                 'external_momentum_delta': [(mass-old)*v for v in velocity]}
        event['system_id']=self.system_id
        event.update(external_mass_delta=delta_mass,external_angular_momentum_delta=dl)
        u=PHYSICAL_SCALE;punit=u['mass_unit_kg']*u['velocity_unit_m_s']
        event.update(external_mass_delta_kg=delta_mass*u['mass_unit_kg'],external_energy_delta_J=(after-before)*punit*u['velocity_unit_m_s'],
                     external_momentum_delta_kg_m_s=[v*punit for v in event['external_momentum_delta']],external_angular_momentum_delta_kg_m2_s=[v*punit*u['length_unit_m'] for v in dl])
        self.interventions.append(event)
        # Numerical drift is measured after the explicit physical intervention.
        self.sim,self.initial_energy = replacement,after
        self.conservation_reference=reference
        return event

    def _expect(self, request):
        if request.get('system_id')!=self.system_id or request.get('edit_token')!=self.edit_token:
            raise ValueError('Sistema reiniciado ou restaurado; carregue novamente o estado do editor.')
        if type(request.get('revision')) is not int or request['revision']!=self.revision:
            raise ValueError('Revisão antiga; carregue novamente o estado do editor.')
        time=request.get('expected_time')
        if type(time) not in (int,float) or not math.isfinite(time) or time!=self.sim.t:
            raise ValueError('O sistema evoluiu; pause e carregue novamente o estado do editor.')
        if request.get('frame')!=self.contract()['frame']:
            raise ValueError('Referencial incompatível com o sistema ativo.')

    @staticmethod
    def _phase(p):
        return {'mass':p.m,'position':[p.x,p.y,p.z],'velocity':[p.vx,p.vy,p.vz]}

    @staticmethod
    def _build(phases, time=0):
        replacement=rebound.Simulation();replacement.G=1.0;replacement.integrator='ias15';replacement.integrator.epsilon=1e-9
        if len(phases)==1:replacement.integrator.adaptive_mode='INDIVIDUAL'
        replacement.exit_min_distance=1e-12
        for b in phases:
            r,v=b['position'],b['velocity']
            replacement.add(m=b['mass'],x=r[0],y=r[1],z=r[2],vx=v[0],vy=v[1],vz=v[2])
        replacement.t=time
        if not math.isfinite(replacement.energy()):raise ValueError('Energia não finita no sistema proposto.')
        return replacement

    @staticmethod
    def _separated(position, phases):
        if any(math.dist(position,b['position'])<1e-12 for b in phases):
            raise ValueError('Partículas devem ficar separadas por pelo menos 1 mm neste editor.')

    def new_system(self, request):
        self._expect(request)
        return self._new_system(request)

    def _new_system(self, request):
        label=body_name(request.get('name'));phase=phases_si(request)
        return self._new_population([{'name':label,**phase}])

    def _new_population(self, initial, scenario=None):
        initial=validate_population(initial);replacement=self._build(initial);system=uuid.uuid4().hex
        registry=[{'id':'exp:'+system+':body:'+uuid.uuid4().hex,'name':b['name'],'origin':{'kind':'user_model'}} for b in initial]
        seed={'kind':'user_system','initial':initial if scenario or len(initial)>1 else initial[0]}
        if scenario:seed['scenario']=copy.deepcopy(scenario)
        validate_user_seed(seed);reference=self._reference(replacement,registry,'initial_condition')
        self.sim,self.initial_energy=replacement,replacement.energy()
        self.system_id,self.edit_token=system,uuid.uuid4().hex
        self.registry=registry
        self.body_attributes={b['id']:attributes.defaults(b) for b in registry}
        self.issued_ids=[b['id'] for b in registry];self.seed=seed;self.fixture_count=None;self.atlas_initial=None
        self.fixture_sha256=digest(seed);self.revision=0;self.topology_revision=0;self.interventions=[];self.restoration=None
        self.conservation_reference=reference

        self.instruments=instruments.empty()
        self.field_layers=fields.empty()
        self.instrument_history=history.empty()
        self._history_last_wall=None

    def load_experiment(self, request):
        self._expect(request)
        from gravity_experiments import model
        initial,scenario=model(request.get('scenario_id'));self._new_population(initial,scenario)

    def restart_seed(self):
        if self.seed['kind']=='fixture':self.reset(self.seed['count'])
        elif self.seed['kind']=='atlas_copy':self.import_atlas(self.atlas_initial)
        else:self._new_population(validate_user_seed(self.seed),self.seed.get('scenario'))

    def _topology(self, request, remove):
        self._expect(request)
        phases=[self._phase(p) for p in self.sim.particles];registry=copy.deepcopy(self.registry)
        if remove:
            if len(phases)==1:raise ValueError('Não é possível remover o último corpo.')
            identifiers=[b['id'] for b in registry]
            if request.get('body') not in identifiers:raise ValueError('Corpo desconhecido na remoção.')
            index=identifiers.index(request['body']);phase=phases.pop(index);meta=registry.pop(index);sign=-1
        else:
            if len(phases)>=MAX_BODIES:raise ValueError('Limite de128 corpos ativos atingido.')
            phase=phases_si(request);label=body_name(request.get('name'));self._separated(phase['position'],phases)
            identifier='exp:'+self.system_id+':body:'+uuid.uuid4().hex
            while identifier in self.issued_ids:identifier='exp:'+self.system_id+':body:'+uuid.uuid4().hex
            meta={'id':identifier,'name':label,'origin':{'kind':'user_model'}}
            registry.append(meta);phases.append(phase);sign=1
        replacement=self._build(phases,self.sim.t);before=self.sim.energy();after=replacement.energy()
        r,v,m=phase['position'],phase['velocity'],phase['mass'];dp=[sign*m*x for x in v]
        dl=[sign*m*(r[(k+1)%3]*v[(k+2)%3]-r[(k+2)%3]*v[(k+1)%3]) for k in range(3)]
        u=PHYSICAL_SCALE;punit=u['mass_unit_kg']*u['velocity_unit_m_s'];lunit=punit*u['length_unit_m']
        event={'type':'remove_body' if remove else 'create_body','revision':self.revision+1,'time':self.sim.t,
               'system_id':self.system_id,'body':meta['id'],'metadata':meta,'old':phase if remove else None,
               'new':None if remove else phase,'frame':self.contract()['frame'],
               'external_mass_delta':sign*m,'external_mass_delta_kg':sign*m*u['mass_unit_kg'],
               'external_energy_delta':after-before,'external_energy_delta_J':(after-before)*punit*u['velocity_unit_m_s'],
               'external_momentum_delta':dp,'external_momentum_delta_kg_m_s':[x*punit for x in dp],
               'external_angular_momentum_delta':dl,'external_angular_momentum_delta_kg_m2_s':[x*lunit for x in dl],
               'policy':'explicit external matter intervention; fixed origin/axes; point masses; no recenter'}
        if remove:event['removed_attributes']=copy.deepcopy(self.body_attributes[meta['id']])
        reference=self._reference(replacement,registry,'external_intervention')
        self.sim,self.initial_energy,self.registry=replacement,after,registry
        if remove:self.body_attributes.pop(meta['id'])
        else:
            self.issued_ids.append(meta['id']);self.body_attributes[meta['id']]=attributes.defaults(meta)
        self.revision+=1;self.topology_revision+=1;self.interventions.append(event)
        self.conservation_reference=reference
        return event

    def create_body(self, request):return self._topology(request,False)
    def remove_body(self, request):return self._topology(request,True)

    def set_attributes(self, request):
        self._expect(request);identifier=request.get('body')
        if identifier not in self.body_attributes:raise ValueError('Corpo desconhecido na edição de raio/spin.')
        old=copy.deepcopy(self.body_attributes[identifier]);new=attributes.proposed(old,request,self.sim.t)
        event={'type':'set_attributes','revision':self.revision+1,'time':self.sim.t,'body':identifier,
               'system_id':self.system_id,'frame':self.contract()['frame'],'old_attributes':old,'new_attributes':new,
               'external_energy_delta':0.,'external_momentum_delta':[0.,0.,0.],'external_angular_momentum_delta':[0.,0.,0.],
               'external_mass_delta':0.,
               'spin_energy_evaluated':False,'policy':'geometric radius and kinematic spin; translational phase/baseline unchanged; no internal energy, inertia or torques modeled'}
        self.body_attributes[identifier]=new;self.revision+=1;self.interventions.append(event)
        return event

    def save(self, directory=None):
        destination=Path(directory) if directory is not None else self.directory
        self._validate_solver(self.sim)
        instruments.validate(self.instruments,self.issued_ids)
        fields.validate(self.field_layers,self.issued_ids,self.sim.t)
        history.validate(self.instrument_history,self.issued_ids,self.sim.t,self.system_id,self.revision,self.instruments['revision'],self.contract()['frame'])
        validate_registry(self.registry,self.issued_ids,self.system_id,self.fixture_count,self.atlas_initial)
        for b in self.registry:attributes.validate(self.body_attributes[b['id']],b,self.atlas_initial,self.sim.t)
        destination.mkdir(parents=True, exist_ok=True)
        identifier = uuid.uuid4().hex
        binary = destination / (identifier + '.bin')
        self.sim.save_to_file(str(binary))
        binary_digest = hashlib.sha256(binary.read_bytes()).hexdigest()
        manifest = {'schema': 3, 'rebound': rebound.__version__, 'binary': binary.name,
                    'sha256': binary_digest, 'initial_energy': self.initial_energy,
                    'revision': self.revision, 'interventions': self.interventions,
                    'fixture_count': self.fixture_count, 'fixture_sha256': self.fixture_sha256,
                    'contract': self.contract(),'body_count':self.sim.N,
                    'system_id':self.system_id,'registry':self.registry,'issued_ids':self.issued_ids,
                    'body_attributes':self.body_attributes,
                    'conservation_reference':self.conservation_reference,
                    'instruments':self.instruments,
                    'field_layers':self.field_layers,
                    'instrument_history':self.instrument_history,
                    'seed':self.seed,'topology_revision':self.topology_revision,
                    'saved_generation':editable_generation(self.seed['kind'])}
        manifest['physical_scale']=PHYSICAL_SCALE
        if self.atlas_initial is not None:
            manifest['atlas_initial']=self.atlas_initial
        manifest['manifest_sha256'] = digest(manifest)
        temporary = destination / (identifier + '.json.tmp')
        temporary.write_text(json.dumps(manifest, indent=2, allow_nan=False)+'\n', encoding='utf-8')
        # The previous checkpoint stays referenced until this single atomic replace.
        temporary.replace(destination / 'latest.json')
        return {'checkpoint': identifier, 'time': self.sim.t, 'sha256': binary_digest}

    def set_body(self, request):
        """Atomic SI intervention in the fixed simulation frame, with revision guard."""
        self._expect(request);frame=self.contract()['frame']
        identifiers=[b['id'] for b in self.registry]
        if request.get('body') not in identifiers:raise ValueError('Corpo desconhecido na edição.')
        proposed=phases_si(request)
        index=identifiers.index(request['body']);replacement=self.sim.copy()
        body=next(p for i,p in enumerate(replacement.particles) if i==index)
        def phase(p):return {'mass':p.m,'position':[p.x,p.y,p.z],'velocity':[p.vx,p.vy,p.vz]}
        old=phase(body);position,velocity=proposed['position'],proposed['velocity']
        for i,p in enumerate(replacement.particles):
            if i!=index and math.hypot(*(v-x for v,x in zip(position,[p.x,p.y,p.z])))<1e-12:
                raise ValueError('Partículas devem ficar separadas por pelo menos 1 mm neste editor.')
        before=replacement.energy();body.m=proposed['mass']
        body.x,body.y,body.z=position;body.vx,body.vy,body.vz=velocity
        after=replacement.energy()
        if not math.isfinite(after):raise ValueError('Energia não finita após a edição.')
        new=phase(body)
        dp=[new['mass']*b-old['mass']*a for a,b in zip(old['velocity'],new['velocity'])]
        def angular(b):
            r,v=b['position'],b['velocity'];return [b['mass']*(r[(k+1)%3]*v[(k+2)%3]-r[(k+2)%3]*v[(k+1)%3]) for k in range(3)]
        dl=[b-a for a,b in zip(angular(old),angular(new))]
        eunit=PHYSICAL_SCALE['mass_unit_kg']*PHYSICAL_SCALE['velocity_unit_m_s']**2
        punit=PHYSICAL_SCALE['mass_unit_kg']*PHYSICAL_SCALE['velocity_unit_m_s'];lunit=punit*PHYSICAL_SCALE['length_unit_m']
        event={'type':'set_body_si','revision':self.revision+1,'time':replacement.t,'body':request['body'],
               'frame':frame,'system_id':self.system_id,'old':old,'new':new,'input_SI':{k:copy.deepcopy(request[k]) for k in ['body','system_id','edit_token','revision','expected_time','frame','mass_kg','position_m','velocity_m_s']},'external_energy_delta':after-before,
               'external_momentum_delta':dp,'external_angular_momentum_delta':dl,
               'external_energy_delta_J':(after-before)*eunit,'external_momentum_delta_kg_m_s':[v*punit for v in dp],
               'external_angular_momentum_delta_kg_m2_s':[v*lunit for v in dl],
               'policy':'fixed initial origin/axes; no recenter; explicit external intervention; point masses'}
        replacement.integrator='ias15';replacement.integrator.epsilon=1e-9
        if replacement.N==1:replacement.integrator.adaptive_mode='INDIVIDUAL'
        reference=self._reference(replacement,self.registry,'external_intervention')
        event.update(external_mass_delta=new['mass']-old['mass'],external_mass_delta_kg=(new['mass']-old['mass'])*PHYSICAL_SCALE['mass_unit_kg'])
        self.sim,self.initial_energy=replacement,after;self.revision+=1;self.interventions.append(event)
        self.conservation_reference=reference
        return event

    def probe(self,request):
        import gravity_field
        self._expect(request)
        return {**gravity_field.evaluate(self._bodies(self.sim,self.registry),request.get('position_m')),
                'system_id':self.system_id,'edit_token':self.edit_token,'revision':self.revision,
                'time':self.sim.t,'frame':self.contract()['frame'],'scientific_generation':editable_generation(self.seed['kind'])}

    def _expect_instruments(self,request):
        self._expect(request)
        revision=request.get('instruments_revision')
        if type(revision) is not int or revision!=self.instruments['revision']:
            raise ValueError('Os instrumentos mudaram; carregue novamente o formulário.')

    def configure_instruments(self,request):
        self._expect_instruments(request)
        replacement=instruments.configure(self.instruments,request,[b['id'] for b in self.registry],self.issued_ids)
        self.instruments=replacement
        return instruments.public(replacement)

    def sample_instruments(self,request):
        import gravity_field
        self._expect_instruments(request)
        physical={'bodies':self._bodies(self.sim,self.registry),'system_id':self.system_id,
                  'edit_token':self.edit_token,'revision':self.revision,'time':self.sim.t,
                  'contract':self.contract(),'scientific_generation':editable_generation(self.seed['kind'])}
        return instruments.sample(self.instruments,physical,gravity_field.evaluate)

    def _expect_fields(self,request):
        self._expect(request)
        revision=request.get('fields_revision')
        if type(revision) is not int or revision!=self.field_layers['revision']:
            raise ValueError('O mapa de campo mudou; prepare novamente o formulário.')

    def _expect_history(self,request):
        self._expect_instruments(request)
        if type(request.get('history_revision')) is not int or request['history_revision']!=self.instrument_history['revision']:
            raise ValueError('O histórico mudou; carregue novamente os controles.')

    def configure_history(self,request):
        self._expect_history(request)
        if request.get('recording') and not self.instruments['probes']:
            raise ValueError('Crie pelo menos uma sonda antes de gravar suas leituras.')
        self.instrument_history=history.configure(self.instrument_history,request)
        self._history_last_wall=None
        return history.public(self.instrument_history)

    def clear_history(self,request):
        self._expect_history(request)
        self.instrument_history=history.clear(self.instrument_history)
        self._history_last_wall=None
        return history.public(self.instrument_history)

    def collect_history(self,physical_state,wall_time):
        if not self.instrument_history['recording'] or not self.instruments['probes']:
            return False
        rows=self.instrument_history['samples']
        if rows and rows[-1]['reading']['time']==self.sim.t:return False
        elapsed=0. if self._history_last_wall is None else wall_time-self._history_last_wall
        if self._history_last_wall is not None and elapsed<self.instrument_history['cadence_wall_s']:return False
        replacement=history.append(self.instrument_history,self.instruments,physical_state,elapsed)
        self.instrument_history=replacement
        self._history_last_wall=wall_time
        return True

    def _history_identity(self,request):
        if request.get('system_id')!=self.system_id or request.get('edit_token')!=self.edit_token:
            raise ValueError('Histórico pertence a outra sessão; consulte novamente o estado.')

    def history_curves(self,request):
        self._history_identity(request)
        return history.curves(self.instrument_history)

    def history_export(self,request):
        self._history_identity(request)
        return copy.deepcopy(self.instrument_history)

    def history_point(self,request):
        self._history_identity(request)
        sequence=request.get('sequence')
        if type(sequence) is not int:raise ValueError('Índice histórico inválido.')
        row=next((v for v in self.instrument_history['samples'] if v['sequence']==sequence),None)
        if row is None:raise ValueError('Esta amostra saiu da janela histórica disponível.')
        return copy.deepcopy(row)

    def configure_fields(self,request):
        self._expect_fields(request)
        replacement=fields.configure(self.field_layers,request,[b['id'] for b in self.registry],self.sim.t)
        # Validate actual sites before publishing a definition, including follow centers.
        cfg=replacement['settings'];origin=fields.center(cfg,self._bodies(self.sim,self.registry))
        if cfg['shell_enabled']:fields.shell(origin,cfg['shell_radius_m'],cfg['shell_count'])
        if cfg['cut_enabled']:
            u,v,normal=fields.axes(cfg['cut_orientation_deg'])
            fields.plane([origin[k]+normal[k]*cfg['cut_offset_m'] for k in range(3)],cfg['cut_half_width_m'],u,v,cfg['cut_resolution'])
        self.field_layers=replacement
        return fields.public(replacement)

    def sample_fields(self,request):
        import gravity_field
        self._expect_fields(request)
        physical={'bodies':self._bodies(self.sim,self.registry),'system_id':self.system_id,
                  'edit_token':self.edit_token,'revision':self.revision,'time':self.sim.t,
                  'contract':self.contract(),'scientific_generation':editable_generation(self.seed['kind'])}
        return fields.sample(self.field_layers,physical,gravity_field.evaluate_points)

    def orbit(self, request):
        self._expect(request);bodies=self._bodies(self.sim,self.registry)
        ids=[b['id'] for b in self.registry]
        if request.get('body') not in ids or request.get('primary') not in ids or request.get('body')==request.get('primary'):raise ValueError('Selecione dois corpos ativos distintos.')
        result={'system_id':self.system_id,'edit_token':self.edit_token,'revision':self.revision,'time':self.sim.t,'frame':self.contract()['frame'],
                'minimum_view_distance_m':self.seed.get('scenario',{}).get('display_min_view_distance_m',1e9),
                'names':{'body':next(b['name'] for b in self.registry if b['id']==request.get('body')),'primary':next(b['name'] for b in self.registry if b['id']==request.get('primary'))},
                'before':orbital.pair(bodies,request.get('body'),request.get('primary')),
                'before_escape':orbital.escape_test_particle(bodies,request.get('body')),'after':None,'after_escape':None,
                'global':orbital.conservation(bodies,self.sim.t,self.conservation_reference,self.initial_energy,self.sim.energy())}
        proposed=request.get('proposed')
        if proposed is not None:
            if not isinstance(proposed,dict):raise ValueError('Estado proposto inválido.')
            candidate=phases_si(proposed);index=[b['id'] for b in bodies].index(request['body'])
            self._separated(candidate['position'],[b for i,b in enumerate(bodies) if i!=index])
            changed=copy.deepcopy(bodies);changed[index].update(candidate)
            test=self._build(changed,self.sim.t)
            result.update(after=orbital.pair(changed,request['body'],request['primary']),after_escape=orbital.escape_test_particle(changed,request['body']),
                          proposed_SI=copy.deepcopy(proposed),after_integrals=orbital.integrals(changed,self.sim.t,test.energy()))
        return result

    def load(self, directory=None):
        destination=Path(directory) if directory is not None else self.directory
        manifest = json.loads((destination / 'latest.json').read_text(encoding='utf-8'))
        if not isinstance(manifest,dict):raise ValueError('Invalid checkpoint metadata')
        if manifest.get('schema')==3:return self._load_registry(manifest,destination)
        return self._load_legacy(manifest,destination)

    def _load_legacy(self, manifest, directory=None):
        source=Path(directory) if directory is not None else self.directory
        if manifest.get('schema') not in (1,2) or manifest.get('rebound') != rebound.__version__:
            raise ValueError('Unsupported checkpoint version')
        imported = None
        restoration = None
        if manifest['schema'] == 2:
            from atlas_import import validate, digest, generation
            if manifest.get('manifest_sha256') != digest({k: v for k, v in manifest.items() if k != 'manifest_sha256'}):
                raise ValueError('Checkpoint metadata checksum mismatch')
            imported = validate(manifest.get('atlas_initial'))
            if manifest.get('contract') != imported['contract'] or manifest.get('body_count') != 3 or manifest.get('fixture_sha256') != imported['initial_state_sha256']:
                raise ValueError('Checkpoint imported model does not match')
            current = generation()
            restoration = {'status': 'same_generation' if manifest.get('saved_generation') == current else 'changed_generation',
                           'saved_generation': manifest.get('saved_generation'), 'current_generation': current}
        elif manifest.get('contract') != CONTRACT:
            raise ValueError('Checkpoint units or model do not match')
        if 'physical_scale' in manifest and manifest['physical_scale']!=PHYSICAL_SCALE:
            raise ValueError('Checkpoint SI binding does not match')
        if imported is not None and manifest.get('physical_scale') != PHYSICAL_SCALE:
            raise ValueError('Imported checkpoint SI binding missing')
        name = manifest.get('binary', '')
        if not isinstance(name, str) or len(name) != 36 or not name.endswith('.bin') or any(c not in '0123456789abcdef' for c in name[:-4]):
            raise ValueError('Invalid checkpoint filename')
        binary = source / name
        if hashlib.sha256(binary.read_bytes()).hexdigest() != manifest.get('sha256'):
            raise ValueError('Checkpoint checksum mismatch')
        replacement = rebound.Simulation(str(binary))
        self._validate_solver(replacement)
        baseline = manifest.get('initial_energy')
        revision = manifest.get('revision')
        count = manifest.get('fixture_count')
        if (imported is None and (type(count) is not int or count not in (2,32,128) or replacement.N != count)) or (imported is not None and (count is not None or replacement.N != 3)):
            raise ValueError('Invalid checkpoint body count')
        if type(baseline) not in (int,float) or not math.isfinite(baseline):
            raise ValueError('Invalid checkpoint energy reference')
        if type(revision) is not int or revision < 0 or not isinstance(manifest.get('interventions'),list) or len(manifest['interventions'])!=revision:
            raise ValueError('Invalid checkpoint intervention history')
        original_ids={b['id'] for b in atlas_metadata(imported) if imported} if imported else {b['id'] for b in fixture_metadata(count)}
        for index,event in enumerate(manifest['interventions'],1):
            if not isinstance(event,dict) or event.get('revision')!=index or event.get('body') not in original_ids or event.get('type') not in ('set_mass','set_body_si'):
                raise ValueError('Invalid legacy intervention event')
        if replacement.G!=1 or str(replacement.integrator)!='ias15' or str(replacement.collision)!='none' or not math.isfinite(replacement.t) or replacement.t<0 or not math.isfinite(replacement.energy()):
            raise ValueError('Invalid legacy integration contract')
        for p in replacement.particles:
            if not all(math.isfinite(v) for v in (p.m,p.x,p.y,p.z,p.vx,p.vy,p.vz)) or p.m <= 0:
                raise ValueError('Invalid checkpoint physical state')
        self.sim, self.initial_energy = replacement, baseline
        self.revision, self.interventions = revision, manifest['interventions']
        self.fixture_count, self.fixture_sha256 = count, manifest['fixture_sha256']
        self.atlas_initial, self.restoration = imported, restoration
        self.system_id,self.edit_token=uuid.uuid4().hex,uuid.uuid4().hex
        self.registry=atlas_metadata(imported) if imported else fixture_metadata(count)
        self.issued_ids=[b['id'] for b in self.registry];self.topology_revision=0
        self.seed={'kind':'atlas_copy'} if imported else {'kind':'fixture','count':count}
        self.body_attributes={b['id']:attributes.defaults(b,imported) for b in self.registry}
        self.sim.exit_min_distance=1e-12
        self.conservation_reference=self._reference(replacement,self.registry,'legacy_checkpoint_new_momentum_reference')
        self.instruments=instruments.empty()
        self.field_layers=fields.empty()
        self.instrument_history=history.empty()
        self._history_last_wall=None
        if self._branch_catalog:self._branch_catalog.active_id=None
        return {'time': self.sim.t, 'revision': revision}

    def _load_registry(self, manifest, directory=None):
        source=Path(directory) if directory is not None else self.directory
        if manifest.get('rebound')!=rebound.__version__:raise ValueError('Unsupported checkpoint version')
        if manifest.get('manifest_sha256')!=digest({k:v for k,v in manifest.items() if k!='manifest_sha256'}):raise ValueError('Checkpoint metadata checksum mismatch')
        if not isinstance(manifest.get('saved_generation'),dict):raise ValueError('Invalid checkpoint generation')
        from atlas_import import validate
        imported=validate(manifest['atlas_initial']) if 'atlas_initial' in manifest else None
        seed=manifest.get('seed');count=manifest.get('fixture_count')
        if not isinstance(seed,dict) or seed.get('kind') not in ('fixture','atlas_copy','user_system'):raise ValueError('Invalid checkpoint seed')
        kind=seed['kind'];source_hash=manifest.get('fixture_sha256')
        if kind=='fixture':
            if imported is not None or type(count) is not int or count not in (2,32,128) or seed!={'kind':'fixture','count':count}:raise ValueError('Invalid fixture seed')
            original=fixture(count);expected_hash=hashlib.sha256(json.dumps(snapshot(original,original.energy()),sort_keys=True,separators=(',',':')).encode()).hexdigest()
            same_physics=manifest.get('saved_generation',{}).get('code_sha256',{}).get('app/physics.py')==editable_generation(kind)['code_sha256']['app/physics.py']
            if not isinstance(source_hash,str) or len(source_hash)!=64 or any(c not in '0123456789abcdef' for c in source_hash) or same_physics and source_hash!=expected_hash:raise ValueError('Fixture source checksum mismatch')
            contract=CONTRACT
        elif kind=='atlas_copy':
            if imported is None or count is not None or seed!={'kind':'atlas_copy'} or source_hash!=imported['initial_state_sha256']:raise ValueError('Invalid Atlas seed')
            contract=imported['contract']
        else:
            if imported is not None or count is not None:raise ValueError('Invalid user-system seed')
            user_initial=validate_user_seed(seed)
            if source_hash!=digest(seed):raise ValueError('User-system source checksum mismatch')
            contract=CUSTOM_CONTRACT
        if manifest.get('contract')!=contract or manifest.get('physical_scale')!=PHYSICAL_SCALE:raise ValueError('Checkpoint units or model do not match')
        system=valid_system(manifest.get('system_id'));issued=manifest.get('issued_ids')
        registry=validate_registry(manifest.get('registry'),issued,system,count,imported)
        revision,topology=manifest.get('revision'),manifest.get('topology_revision');events=manifest.get('interventions')
        if type(revision) is not int or revision<0 or type(topology) is not int or not 0<=topology<=revision or not isinstance(events,list) or len(events)!=revision:raise ValueError('Invalid checkpoint intervention history')
        for i,event in enumerate(events,1):
            if not isinstance(event,dict) or event.get('revision')!=i or event.get('body') not in issued or event.get('type') not in ('set_mass','set_body_si','create_body','remove_body','set_attributes'):raise ValueError('Invalid checkpoint intervention event')
            if event.get('system_id',system)!=system:raise ValueError('Intervention system mismatch')
            t=event.get('time')
            if type(t) not in (int,float) or not math.isfinite(t) or t<0:raise ValueError('Invalid intervention time')
        if sum(e['type'] in ('create_body','remove_body') for e in events)!=topology:raise ValueError('Topology history mismatch')
        # Replay identity events, independently of current particle order. A valid seal
        # alone cannot make a duplicate, reassigned source or reused identity valid.
        if kind=='fixture':original_registry=fixture_metadata(count)
        elif imported:original_registry=atlas_metadata(imported)
        else:
            if len(issued)<len(user_initial):raise ValueError('Missing initial user identities')
            original_registry=[{'id':identifier,'name':body['name'],'origin':{'kind':'user_model'}} for identifier,body in zip(issued,user_initial)]
        active=copy.deepcopy(original_registry);expected_issued=[b['id'] for b in active]
        for event in events:
            identifier=event['body'];identifiers=[b['id'] for b in active]
            if event['type']=='create_body':
                meta=event.get('metadata')
                if identifier in expected_issued or not isinstance(meta,dict) or meta.get('id')!=identifier or meta.get('origin')!={'kind':'user_model'}:raise ValueError('Invalid creation identity history')
                active.append(meta);expected_issued.append(identifier)
                if len(active)>MAX_BODIES:raise ValueError('Invalid historical population')
            else:
                if identifier not in identifiers:raise ValueError('Intervention refers to an inactive identity')
                if event['type']=='remove_body':
                    index=identifiers.index(identifier)
                    if len(active)==1 or event.get('metadata')!=active[index]:raise ValueError('Invalid removal identity history')
                    active.pop(index)
            for key in ('external_energy_delta',):
                value=event.get(key)
                if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('Invalid intervention balance')
            for key in ('external_momentum_delta',):
                value=event.get(key)
                if not isinstance(value,list) or len(value)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in value):raise ValueError('Invalid intervention vector balance')
        if expected_issued!=issued or active!=registry:raise ValueError('Checkpoint identity history does not match active registry')
        filename=manifest.get('binary','')
        if not isinstance(filename,str) or len(filename)!=36 or not filename.endswith('.bin') or any(c not in '0123456789abcdef' for c in filename[:-4]):raise ValueError('Invalid checkpoint filename')
        binary=source/filename
        if hashlib.sha256(binary.read_bytes()).hexdigest()!=manifest.get('sha256'):raise ValueError('Checkpoint checksum mismatch')
        replacement=rebound.Simulation(str(binary));self._validate_solver(replacement,allow_legacy_single=True);baseline=manifest.get('initial_energy')
        if type(manifest.get('body_count')) is not int or replacement.N!=manifest['body_count'] or replacement.N!=len(registry):raise ValueError('Invalid checkpoint body count')
        if type(baseline) not in (int,float) or not math.isfinite(baseline):raise ValueError('Invalid checkpoint energy reference')
        if replacement.G!=1 or str(replacement.integrator)!='ias15' or str(replacement.collision)!='none' or not math.isfinite(replacement.t) or replacement.t<0:raise ValueError('Invalid checkpoint integration contract')
        for p in replacement.particles:
            if p.m<=0 or not all(math.isfinite(x) for x in (p.m,p.x,p.y,p.z,p.vx,p.vy,p.vz)):raise ValueError('Invalid checkpoint physical state')
        if not math.isfinite(replacement.energy()) or any(e['time']>replacement.t for e in events):raise ValueError('Invalid checkpoint energy/time')
        current=editable_generation(kind)
        saved=manifest.get('saved_generation')
        if not isinstance(saved,dict) or saved.get('model_id')!=current['model_id'] or saved.get('model_version') not in ('3.0.0','3.1.0','3.2.0','3.3.0','3.4.0','3.5.0','3.6.0','3.7.0'):raise ValueError('Invalid editable model generation')
        restored_attributes=attributes.restore(manifest,original_registry,events,registry,imported,replacement.t)
        if saved['model_version'] in ('3.2.0','3.3.0','3.4.0','3.5.0','3.6.0','3.7.0'):
            reference=orbital.validate_reference(manifest.get('conservation_reference'),self._bodies(replacement,registry),replacement.t,baseline)
        else:reference=self._reference(replacement,registry,'legacy_checkpoint_new_momentum_reference')
        restored_instruments=instruments.restore(manifest,issued)
        if saved['model_version']=='3.7.0' and ('field_layers' not in manifest or 'instruments' not in manifest):raise ValueError('Instrumentos/mapas ausentes no checkpoint3.7.')
        restored_fields=fields.restore(manifest,issued,replacement.t)
        restored_history=history.validate(manifest['instrument_history'],issued,replacement.t,system,revision,restored_instruments['revision'],contract['frame']) if 'instrument_history' in manifest else history.empty()
        if saved['model_version']=='3.7.0' and 'instrument_history' not in manifest:raise ValueError('Histórico ausente no checkpoint3.7.')
        restoration={'status':'same_generation' if saved==current else 'changed_generation','saved_generation':saved,'current_generation':current}
        if replacement.N==1:
            saved_mode=replacement.integrator.adaptive_mode
            if saved['model_version']=='3.7.0' and saved_mode!='INDIVIDUAL':raise ValueError('Critério numérico do checkpoint3.7 de1corpo incompatível.')
            if saved_mode!='INDIVIDUAL':
                replacement.integrator.adaptive_mode='INDIVIDUAL'
                restoration['numerical_migration']={'domain':'one active point mass; zero external force',
                    'saved_ias15_adaptive_mode':saved_mode,'current_ias15_adaptive_mode':'INDIVIDUAL','physical_phase_preserved':True}
        self.sim,self.initial_energy=replacement,baseline;self.registry,self.issued_ids=registry,copy.deepcopy(issued)
        self.system_id,self.edit_token=system,uuid.uuid4().hex;self.seed=copy.deepcopy(seed)
        self.revision,self.topology_revision,self.interventions=revision,topology,copy.deepcopy(events)
        self.fixture_count,self.fixture_sha256,self.atlas_initial,self.restoration=count,source_hash,imported,restoration
        self.body_attributes=restored_attributes
        self.conservation_reference=copy.deepcopy(reference)
        self.instruments=restored_instruments
        self.field_layers=restored_fields
        self.instrument_history=restored_history
        self._history_last_wall=None
        self.sim.exit_min_distance=1e-12
        if self._branch_catalog:self._branch_catalog.active_id=None
        return {'time':self.sim.t,'revision':revision}
