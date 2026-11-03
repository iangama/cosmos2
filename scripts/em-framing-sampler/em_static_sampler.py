"""Frozen-source field reads through the verified cloud ABI1, never its step API.

The evolving experiment remains in its original worker/core. Snapshot fences
confirm its paused phase before and after every local <=128-point read.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import importlib.util
import math
import sys
import numpy as np
from em_experiment import Experiment
from em_fields import K_E, MU_0, vector

BASE=Path(__file__).resolve().parents[1]
HELPER=BASE/'em-cloud'
for name in ('constants.json','em_fields.py'):
    if (BASE/'em'/name).read_bytes()!=(HELPER/name).read_bytes():raise RuntimeError('EM field definitions differ between phase and static sampler')
spec=importlib.util.spec_from_file_location('_cosmos2_frozen_static_helper_abi1',HELPER/'cloud_native.py')
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
CRITICAL=('system_id','edit_token','revision','frame','time_s','paused','experiment','scientific_generation')
VERSION='0.1.1'

class StaticSampler:
    def __init__(self,read_state,worker_query):
        self.read_state,self.worker_query=read_state,worker_query
        self.initial=self.model=self.packed=self.identity=None

    def begin(self,initial):
        self.initial=deepcopy(initial)
        if initial.get('paused') is not True:raise ValueError('Pause before static field sampling')
        ex=Experiment.from_payload(initial['experiment'])
        self.model=ex.model if ex.mode=='test_particle' else ex.model.field_snapshot(ex.phase)
        self.packed=native.pack(self.model)
        files=[Path(__file__),*[HELPER/name for name in ('cloud_native.py','cloud_kernel.cpp','CMakeLists.txt','cosmos2_em_cloud.dll','build-receipt.json','constants.json','em_fields.py')]]
        self.identity={'kind':'verified_static_EM_helper_abi1','version':VERSION,'thread_count':1,
                       'all_declared_sources':len(self.model.sources),'field_queries_in_worker':False,
                       'domain_policy':'Original scalar intermediate field domain retained, including zero-moment magnetic prefactor.',
                       'boundary_policy':'Original scalar reference within32ULPs outside an exclusion boundary; compiled reads elsewhere.',
                       'phase_confirmation':'Paused worker snapshot before and after every local batch; phase core and integration unchanged.',
                       'files_sha256':{str(p.relative_to(BASE)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
        return deepcopy(self.identity)

    def _confirm(self):
        ack=self.worker_query({'command':'snapshot'});now=self.read_state()
        if (ack.get('type')!='ack' or ack.get('paused') is not True or ack.get('time_s')!=self.initial['time_s'] or
                any(now.get(k)!=self.initial[k] for k in CRITICAL)):
            raise ValueError('Static sampler phase fence changed; discard the complete read')

    def query(self,request):
        expected={'command','system_id','edit_token','revision','frame','expected_time_s','points_m'}
        if (set(request)!=expected or request['command']!='field_map' or
                any(request[k]!=self.initial[k] for k in ('system_id','edit_token','revision','frame')) or
                request['expected_time_s']!=self.initial['time_s']):raise ValueError('Exact frozen static sampling guard required')
        points=request['points_m']
        if not isinstance(points,list) or not 1<=len(points)<=128:raise ValueError('Static sampler needs1..128 explicit points')
        self._confirm()
        samples=self.evaluate(points)
        self._confirm()
        metadata={k:self.initial[k] for k in ('system_id','edit_token','revision','frame','time_s')}
        return {'type':'sample_ack','time_s':self.initial['time_s'],'paused':True,'result':{**metadata,'samples':samples}}

    def evaluate(self,points):
        samples=[];valid=[];indices=[];scales=[]
        for index,raw in enumerate(points):
            point=vector(raw);excluded=[];geometry=[];boundary=False
            for source in self.model.sources:
                delta=[a-b for a,b in zip(point,source.position_m)];radius=math.hypot(*delta)
                if not math.isfinite(radius):raise ValueError('Unrepresentable static source distance')
                if radius<=source.exclusion_radius_m:excluded.append(source.id)
                elif radius-source.exclusion_radius_m<=32*max(math.ulp(radius),math.ulp(source.exclusion_radius_m)):boundary=True
                geometry.append((source,delta,radius))
            if excluded:
                samples.append({'valid':False,'position_m':list(point),'reason':'inside_or_on_source_exclusion','source_ids':excluded});continue
            es=[math.hypot(*self.model.uniform_E_V_m)];bs=[math.hypot(*self.model.uniform_B_T)]
            potential_scale=[abs(math.fsum(a*b for a,b in zip(point,self.model.uniform_E_V_m)))]
            for source,delta,radius in geometry:
                direction=[v/radius for v in delta]
                e=(K_E*source.charge_C/radius)/radius
                es.append(math.hypot(*(e*v for v in direction)));potential_scale.append(abs(K_E*source.charge_C/radius))
                magnetic_factor=((MU_0/(4*math.pi)/radius)/radius)/radius
                if not math.isfinite(magnetic_factor):raise ValueError('Fields outside representable SI domain')
                if any(source.magnetic_moment_A_m2):
                    moment=source.magnetic_moment_A_m2;along=math.fsum(a*b for a,b in zip(direction,moment));f=magnetic_factor
                    bs.append(math.hypot(*(f*(3*direction[k]*along-moment[k]) for k in range(3))))
            values=(math.fsum(es),math.fsum(bs),math.fsum(potential_scale))
            if not all(math.isfinite(v) for v in values):raise ValueError('Static reference scales outside finite SI domain')
            if boundary:
                sample=self.model.evaluate(point);sample['potential_scale_V']=values[2];sample['numeric_provider']='scalar_boundary_reference';samples.append(sample);continue
            samples.append(None);valid.append(point);indices.append(index);scales.append(values)
        if valid:
            e,b,phi=native.evaluate(self.packed,native.immutable(valid),potential=True,thread_count=1)
            for row,index in enumerate(indices):
                samples[index]={'numeric_provider':'compiled_static_helper_abi1','valid':True,'position_m':list(valid[row]),'electric_field_V_m':e[row].tolist(),
                    'magnetic_field_T':b[row].tolist(),'electric_potential_V':float(phi[row]),
                    'electric_scale_V_m':scales[row][0],'magnetic_scale_T':scales[row][1],
                    'potential_scale_V':scales[row][2],
                    'potential_zero':'uniform term at coordinate origin; charge terms at infinity',
                    'source_ids':[s.id for s in self.model.sources]}
        return samples
