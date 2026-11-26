"""Bounded confirmed SI float64 positions, separate from JSON and IAS15 archives."""
import hashlib
import json
import math
import os
import struct
import uuid
import zlib
import time
from pathlib import Path
import numpy as np
from cloud_driver import VERSION
from physics import PHYSICAL_SCALE as U
from test_cloud import identity

MAGIC=b'C2CLD002'
HEADER=struct.Struct('<8sI')
MAX_METADATA=32768
MAX_COUNT=10000
MAX_PACKET=HEADER.size+MAX_METADATA+24*MAX_COUNT
_KEYS={'schema','model','system_id','edit_token','cloud_id','source_id','sequence',
       'time_model','time_s','time_unit_s','length_unit_m','frame','count',
       'positions','payload_sha256','payload_crc32'}


def encode(cloud,system_id,edit_token,sequence,frame):
    identity(system_id);identity(edit_token);identity(cloud.id)
    if type(sequence) is not int or not 0<=sequence<2**63:
        raise ValueError('Sequência confirmada da nuvem inválida.')
    if not isinstance(frame,str) or not 1<=len(frame)<=128 or not frame.isascii():
        raise ValueError('Referencial inercial explícito requerido.')
    xyz=cloud.driver.positions()*U['length_unit_m']
    if xyz.shape!=(cloud.driver.configuration['count'],3) or not np.isfinite(xyz).all() or np.max(np.linalg.norm(xyz,axis=1))>1e17:
        raise ValueError('Fase da nuvem fora do domínio SI.')
    payload=xyz.astype('<f8',copy=False).tobytes()
    metadata={'schema':2,'model':VERSION,'system_id':system_id,'edit_token':edit_token,
        'cloud_id':cloud.id,'source_id':cloud.driver.source_id,'sequence':sequence,
        'time_model':cloud.driver.sim.t,'time_s':cloud.driver.sim.t*U['time_unit_s'],
        'time_unit_s':U['time_unit_s'],'length_unit_m':U['length_unit_m'],
        'frame':frame,'count':len(xyz),'positions':'SI_m_float64_little_endian_xyz',
        'payload_sha256':hashlib.sha256(payload).hexdigest(),'payload_crc32':zlib.crc32(payload)}
    header=json.dumps(metadata,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
    if len(header)>MAX_METADATA:raise ValueError('Metadados da nuvem excedem o limite.')
    return HEADER.pack(MAGIC,len(header))+header+payload,metadata


def decode(packet,system_id,edit_token,cloud_id,source_id,frame,count,minimum_sequence=0):
    for value in (system_id,edit_token,cloud_id):identity(value)
    if type(count) is not int or not 1<=count<=MAX_COUNT or type(minimum_sequence) is not int or not 0<=minimum_sequence<2**63:
        raise ValueError('Vínculo de população/sequência inválido.')
    if not isinstance(packet,bytes) or not HEADER.size<len(packet)<=MAX_PACKET:
        raise ValueError('Tamanho do pacote da nuvem inválido.')
    magic,size=HEADER.unpack_from(packet)
    if magic!=MAGIC or not 0<size<=MAX_METADATA or len(packet)<HEADER.size+size:
        raise ValueError('Cabeçalho do pacote da nuvem inválido.')
    try:m=json.loads(packet[HEADER.size:HEADER.size+size])
    except (ValueError,UnicodeError) as error:raise ValueError('JSON do pacote da nuvem inválido.') from error
    if not isinstance(m,dict) or set(m)!=_KEYS or type(m['schema']) is not int or m['schema']!=2 or m['model']!=VERSION:
        raise ValueError('Modelo/esquema do pacote da nuvem incompatível.')
    if any(m[k]!=v for k,v in [('system_id',system_id),('edit_token',edit_token),('cloud_id',cloud_id),('source_id',source_id),('frame',frame)]):
        raise ValueError('Pacote obsoleto: sistema, sessão, população, fonte ou referencial distintos.')
    if type(m['count']) is not int or m['count']!=count or m['positions']!='SI_m_float64_little_endian_xyz':
        raise ValueError('Contagem/formato de coordenadas incompatível.')
    if type(m['sequence']) is not int or not minimum_sequence<=m['sequence']<2**63:
        raise ValueError('Sequência de nuvem obsoleta ou inválida.')
    for key in ('time_model','time_s','time_unit_s','length_unit_m'):
        if type(m[key]) not in (int,float) or not math.isfinite(m[key]) or m[key]<0:
            raise ValueError('Tempo/escala da nuvem inválidos.')
    if m['time_unit_s']!=U['time_unit_s'] or m['length_unit_m']!=U['length_unit_m'] or m['time_s']!=m['time_model']*m['time_unit_s']:
        raise ValueError('Vínculo SI/tempo incompatível.')
    payload=packet[HEADER.size+size:]
    if len(payload)!=24*count or type(m['payload_crc32']) is not int or zlib.crc32(payload)!=m['payload_crc32'] or hashlib.sha256(payload).hexdigest()!=m['payload_sha256']:
        raise ValueError('Tamanho/selo do buffer de posições inválido.')
    xyz=np.frombuffer(payload,dtype='<f8').reshape(count,3)
    if not np.isfinite(xyz).all() or np.max(np.linalg.norm(xyz,axis=1))>1e17:
        raise ValueError('Buffer da nuvem fora do domínio SI.')
    return m,xyz


def publish(path,packet):
    if not isinstance(packet,bytes) or not HEADER.size<len(packet)<=MAX_PACKET:
        raise ValueError('Pacote de publicação fora do limite.')
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with temporary.open('xb') as stream:
            stream.write(packet)
            stream.flush()
        deadline=time.perf_counter()+.010
        while True:
            try:
                os.replace(temporary,path)
                break
            except PermissionError:
                if time.perf_counter()>=deadline:raise
                time.sleep(.0005)
    finally:temporary.unlink(missing_ok=True)
