"""C2CLD002 position payload with an explicit Boris EM/SI population binding.

This transport has no gravity-session compatibility. Positions are SI float64;
the native receiver reports its separate float32 display quantization.
"""
from dataclasses import asdict
from pathlib import Path
import hashlib
import json
import math
import os
import re
import struct
import time
import uuid
import zlib
import numpy as np
from cloud_checkpoint import canonical, controls, generation, timestep, unique
from cloud_core import Phase, System, VERSION
from cloud_fields import positions

FRAME = 'synthetic_EM_inertial_cartesian_SI'
MAGIC = b'C2CLD002'
HEADER = struct.Struct('<8sI')
MAX_METADATA = 32768
MAX_PACKET = HEADER.size+MAX_METADATA+24*10000
KEYS = {'schema', 'model', 'system_id', 'edit_token', 'cloud_id', 'source_id',
        'sequence', 'time_model', 'time_s', 'time_unit_s', 'length_unit_m',
        'frame', 'count', 'positions', 'payload_sha256', 'payload_crc32'}


def identity(value):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{32}', value):
        raise ValueError('Explicit EM population identity required')


def source_identity(value):
    if type(value) is not str or not re.fullmatch('em-[0-9a-f]{64}', value):
        raise ValueError('Explicit hashed EM model/controls/timestep identity required')


def source_id(system, dt_s, acting):
    if not isinstance(system, System):
        raise ValueError('EM cloud system required')
    return 'em-'+hashlib.sha256(canonical({'model': asdict(system.model), 'dt_s': timestep(dt_s),
                                          'controls': controls(acting), 'generation': generation()})).hexdigest()


def encode(phase, system_id, edit_token, cloud_id, source_id, sequence):
    for value in (system_id, edit_token, cloud_id):
        identity(value)
    source_identity(source_id)
    if not isinstance(phase, Phase) or type(sequence) is not int or not 0 <= sequence < 2**63:
        raise ValueError('Confirmed EM phase and bounded sequence required')
    xyz = positions(phase.positions())
    payload = xyz.astype('<f8', copy=False).tobytes()
    metadata = {'schema': 2, 'model': VERSION, 'system_id': system_id, 'edit_token': edit_token,
                'cloud_id': cloud_id, 'source_id': source_id, 'sequence': sequence,
                'time_model': phase.time_s, 'time_s': phase.time_s, 'time_unit_s': 1., 'length_unit_m': 1.,
                'frame': FRAME, 'count': phase.count, 'positions': 'SI_m_float64_little_endian_xyz',
                'payload_sha256': hashlib.sha256(payload).hexdigest(), 'payload_crc32': zlib.crc32(payload)}
    header = canonical(metadata)
    return HEADER.pack(MAGIC, len(header))+header+payload, metadata


def decode(packet, system_id, edit_token, cloud_id, source_id, count, minimum_sequence=0):
    for value in (system_id, edit_token, cloud_id):
        identity(value)
    source_identity(source_id)
    if (type(count) is not int or not 1 <= count <= 10000 or type(minimum_sequence) is not int or
            not 0 <= minimum_sequence < 2**63):
        raise ValueError('Bounded population and sequence required')
    if not isinstance(packet, bytes) or not HEADER.size < len(packet) <= MAX_PACKET:
        raise ValueError('Invalid bounded EM position packet')
    magic, size = HEADER.unpack_from(packet)
    if magic != MAGIC or not 0 < size <= MAX_METADATA or len(packet) < HEADER.size+size:
        raise ValueError('Invalid EM position packet header')
    try:
        m = json.loads(packet[HEADER.size:HEADER.size+size], object_pairs_hook=unique,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite metadata')))
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ValueError('Invalid EM position metadata') from error
    if (not isinstance(m, dict) or set(m) != KEYS or type(m['schema']) is not int or m['schema'] != 2 or
            m['model'] != VERSION or m['frame'] != FRAME or any(m[k] != v for k, v in (
                ('system_id', system_id), ('edit_token', edit_token), ('cloud_id', cloud_id), ('source_id', source_id)))):
        raise ValueError('Stale or incompatible EM scientific population binding')
    if (type(m['count']) is not int or m['count'] != count or m['positions'] != 'SI_m_float64_little_endian_xyz' or
            type(m['sequence']) is not int or not minimum_sequence <= m['sequence'] < 2**63):
        raise ValueError('Invalid EM population/sequence/format')
    for key in ('time_model', 'time_s', 'time_unit_s', 'length_unit_m'):
        if type(m[key]) not in (int, float) or not math.isfinite(m[key]) or m[key] < 0:
            raise ValueError('Invalid EM SI time/scale')
    if m['time_unit_s'] != 1 or m['length_unit_m'] != 1 or m['time_model'] != m['time_s']:
        raise ValueError('EM requires explicit SI units1/1 and synchronized time')
    payload = packet[HEADER.size+size:]
    if (len(payload) != 24*count or type(m['payload_crc32']) is not int or
            m['payload_crc32'] != zlib.crc32(payload) or m['payload_sha256'] != hashlib.sha256(payload).hexdigest()):
        raise ValueError('Invalid EM position payload length/hash/CRC32')
    xyz = np.frombuffer(payload, dtype='<f8').reshape(count, 3)
    positions(xyz)
    return m, xyz


def publish(path, packet):
    if not isinstance(packet, bytes) or not HEADER.size < len(packet) <= MAX_PACKET:
        raise ValueError('Invalid bounded EM publication')
    path = Path(path)
    temporary = path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with temporary.open('xb') as stream:
            stream.write(packet)
            stream.flush()
        deadline = time.perf_counter()+.01
        while True:
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if time.perf_counter() >= deadline:
                    raise
                time.sleep(.0005)
    finally:
        temporary.unlink(missing_ok=True)


def read_packet(path):
    """Bound allocation and tolerate Windows atomic-replacement sharing races."""
    deadline = time.perf_counter()+.02
    while True:
        try:
            with Path(path).open('rb') as stream:
                packet = stream.read(MAX_PACKET+1)
            if len(packet) > MAX_PACKET:
                raise ValueError('Oversized EM position file')
            return packet
        except PermissionError:
            if time.perf_counter() >= deadline:
                raise
            time.sleep(.0005)
