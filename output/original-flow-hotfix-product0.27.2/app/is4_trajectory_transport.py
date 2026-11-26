"""Bounded own-protocol normalized txyz; never relabel plot coordinates as SI."""
from pathlib import Path
import copy
import hashlib
import json
import math
import struct
import zlib
import numpy as np
from is4_particle_scene import geometry,identity
from is4_body_snapshot import digest
from is4_values import scalar

MAGIC=b'C2IS4T01'
HEADER=struct.Struct('<8sI')
MAX_METADATA=32768
MAX_COUNT=129
MAX_PACKET=HEADER.size+MAX_METADATA+MAX_COUNT*32
MODEL='is4_magnified_trajectory_v1'
KEYS={'schema','model','binding_sha256','sequence','revision','time_s','count','positions','payload_sha256','payload_crc32'}


def descriptor(state,g):
    exp=state['experiment']
    return {'schema':1,'kind':MODEL,'worker_id':state['worker_id'],'experiment_id':exp['id'],'edit_token':exp['edit_token'],
        'snapshot_configuration_sha256':exp['snapshot_configuration_sha256'],'scientific_generation':copy.deepcopy(exp['scientific_generation']),
        'source_frame':state['frame'],'plot_frame':'normalized_frozen_model_axes',
        **{k:copy.deepcopy(g[k]) for k in ['plot_origin_model_m','physical_unit_m','graphic_unit_m','model_to_render','anchor_relative_LabRoot_m']}}


def encode(state,physical_unit_m,initial_field_T):
    g=geometry(state,physical_unit_m,initial_field_T,require_paused=False)
    sequence=state['sequence'];revision=state['experiment']['revision']
    if sequence>=2**63 or revision>=2**63:raise ValueError('Publication/revision exceeds native integer budget')
    d=descriptor(state,g);binding=digest(d)
    rows=np.column_stack((g['sample_times_s'],g['vertices_normalized']))
    if not np.isfinite(rows).all() or np.max(np.linalg.norm(rows[:,1:],axis=1))>1e8:raise ValueError('Normalized plot exceeds native bound')
    payload=rows.astype('<f8',copy=False).tobytes()
    m={'schema':1,'model':MODEL,'binding_sha256':binding,'sequence':sequence,'revision':revision,'time_s':g['phase']['time_s'],
        'count':len(rows),'positions':'normalized_float64_txyz_le','payload_sha256':hashlib.sha256(payload).hexdigest(),'payload_crc32':zlib.crc32(payload)}
    header=json.dumps(m,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
    if len(header)>MAX_METADATA:raise ValueError('Trajectory metadata exceeds budget')
    return HEADER.pack(MAGIC,len(header))+header+payload,{'metadata':m,'descriptor':d,'geometry':g,'scientific_state':copy.deepcopy(state)}


def unique_pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate trajectory JSON key')
        result[key]=value
    return result


def decode(packet,binding,minimum_sequence=0,minimum_time_s=0.,minimum_revision=0):
    identity(binding,64)
    for value in [minimum_sequence,minimum_revision]:
        if type(value) is not int or not 0<=value<2**63:raise ValueError('Invalid trajectory sequence/revision bound')
    minimum_time=scalar(minimum_time_s)
    if minimum_time<0:raise ValueError('Invalid minimum trajectory time')
    if not isinstance(packet,bytes) or not HEADER.size<len(packet)<=MAX_PACKET:raise ValueError('Trajectory packet size outside bounds')
    magic,n=HEADER.unpack_from(packet)
    if magic!=MAGIC or not 0<n<=MAX_METADATA or HEADER.size+n>len(packet):raise ValueError('Invalid trajectory header')
    try:m=json.loads(packet[HEADER.size:HEADER.size+n],object_pairs_hook=unique_pairs)
    except (ValueError,UnicodeError) as e:raise ValueError('Invalid trajectory JSON') from e
    if not isinstance(m,dict) or set(m)!=KEYS or type(m['schema']) is not int or m['schema']!=1 or m['model']!=MODEL or m['binding_sha256']!=binding or m['positions']!='normalized_float64_txyz_le':raise ValueError('Trajectory schema/binding differs')
    for key,low,high in [('sequence',minimum_sequence,2**63-1),('revision',minimum_revision,2**63-1),('count',1,MAX_COUNT)]:
        if type(m[key]) is not int or not low<=m[key]<=high:raise ValueError('Trajectory '+key+' outside bounds')
    time=scalar(m['time_s'])
    if time<minimum_time:raise ValueError('Trajectory clock went backward')
    identity(m['payload_sha256'],64);payload=packet[HEADER.size+n:]
    if len(payload)!=m['count']*32 or type(m['payload_crc32']) is not int or zlib.crc32(payload)!=m['payload_crc32'] or hashlib.sha256(payload).hexdigest()!=m['payload_sha256']:raise ValueError('Trajectory payload seal/size differs')
    rows=np.frombuffer(payload,dtype='<f8').reshape(m['count'],4)
    if not np.isfinite(rows).all() or np.any(rows[:,0]<0) or np.any(np.diff(rows[:,0])<=0) or rows[-1,0]!=time or np.max(np.linalg.norm(rows[:,1:],axis=1))>1e8:raise ValueError('Trajectory sample/domain/time differs')
    return m,rows


def publish(path,packet,binding,minimum_sequence=0,minimum_time_s=0.,minimum_revision=0):
    metadata,_=decode(packet,binding,minimum_sequence,minimum_time_s,minimum_revision)
    # Reuse only the established bounded atomic Windows file replacement primitive.
    from cloud_transport import publish as atomic_publish
    atomic_publish(Path(path),packet)
    return metadata
