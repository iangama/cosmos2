"""Explicit EM/SI wire contract, exact doubles and adversarial packet binding."""
from pathlib import Path
import hashlib
import json
import struct
import subprocess
import sys
import tempfile
import zlib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT/'output/c212-em-cloud-transport-staging'
sys.path.insert(0, str(STAGE))
import cloud_transport as wire
from cloud_core import Phase
from cloud_presets import create

cases, refused = [], []
ids = ('1'*32, '2'*32, '3'*32)
for count in (1, 128, 10000):
    s, p, dt, acting = create('crossed', count)
    for _ in range(7):
        p, _ = s.step(p, dt, **acting)
    source = wire.source_id(s, dt, acting)
    packet, metadata = wire.encode(p, *ids, source, 17)
    decoded, xyz = wire.decode(packet, *ids, source, count, 17)
    assert decoded == metadata and xyz.tobytes() == p._x and not xyz.flags.writeable
    _, size = wire.HEADER.unpack_from(packet)
    raw = packet[wire.HEADER.size+size:]
    assert struct.unpack_from('<ddd', raw, (count-1)*24) == tuple(p.positions()[-1])
    assert metadata['model'] == 'SI_prescribed_EM_test_cloud_boris_v2'
    assert metadata['time_model'] == metadata['time_s'] == p.time_s
    assert metadata['length_unit_m'] == metadata['time_unit_s'] == 1
    assert source != wire.source_id(s, dt*2, acting)
    assert source != wire.source_id(s, dt, {**acting, 'magnetic_acting': False})
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder)/'packet.bin'
        wire.publish(path, packet)
        assert wire.read_packet(path) == packet
        assert list(Path(folder).glob('*.tmp')) == []
    cases.append({'count': count, 'packet_bytes': len(packet), 'all_f64_SI_positions_exact': True,
                  'read_only_decoded_buffer': True, 'source_controls_timestep_binding_distinct': True})

def rewrite(m, payload=raw):
    header = json.dumps(m, separators=(',', ':'), allow_nan=True).encode('ascii')
    return wire.HEADER.pack(wire.MAGIC, len(header))+header+payload


def reject(label, value):
    try:
        wire.decode(value, *ids, source, 10000, 17)
    except (ValueError, ArithmeticError, TypeError):
        refused.append(label)
    else:
        raise AssertionError(label)


for key, bad in (
        ('schema', True), ('schema', 1), ('model', 'massless_central_ias15_v1'),
        ('system_id', '0'*32), ('edit_token', '0'*32), ('cloud_id', '0'*32),
        ('source_id', 'em-'+'0'*64), ('frame', 'gravity'), ('count', True), ('count', 9999),
        ('sequence', True), ('sequence', 16), ('sequence', 2**63), ('sequence', -1),
        ('time_model', -1), ('time_s', 0), ('time_unit_s', 0), ('time_unit_s', True),
        ('time_unit_s', 2), ('length_unit_m', 1e9), ('length_unit_m', True),
        ('positions', 'float32'), ('payload_sha256', '0'*64), ('payload_crc32', True),
        ('time_s', float('nan')), ('time_s', float('inf')), ('gravity', True)):
    changed = {**metadata, key: bad}
    reject(key+':'+str(bad), rewrite(changed))
reject('payload-bitflip', rewrite(metadata, raw[:-1]+bytes([raw[-1]^1])))
reject('truncated payload', packet[:-8])
reject('extra payload', packet+b'12345678')
reject('magic', b'C2CLD001'+packet[8:])
for value in (float('nan'), float('inf'), np.nextafter(1e17, float('inf'))):
    changed_xyz = xyz.copy()
    changed_xyz[9999, 0] = value
    changed_raw = changed_xyz.astype('<f8').tobytes()
    changed = {**metadata, 'payload_sha256': hashlib.sha256(changed_raw).hexdigest(),
               'payload_crc32': zlib.crc32(changed_raw)}
    reject('resealed coordinate '+str(value), rewrite(changed, changed_raw))
header = wire.canonical(metadata)
duplicate = b'{"schema":2,'+header[1:]
reject('duplicate key', wire.HEADER.pack(wire.MAGIC, len(duplicate))+duplicate+raw)
reject('oversized header', wire.HEADER.pack(wire.MAGIC, 32769)+header+raw)
reject('oversized packet', b'x'*(wire.MAX_PACKET+1))

# The component-wise SI domain is intentional and differs from the legacy
# gravity radial domain. Its physical solver proof is separate.
edge = Phase([[1e17, -1e17, 1e17]], [[0, 0, 0]])
edge_packet, edge_metadata = wire.encode(edge, *ids, source, 18)
_, edge_xyz = wire.decode(edge_packet, *ids, source, 1)
assert edge_xyz.tobytes() == edge._x

# Run the installed gravitational decoder in its own module environment;
# it must reject this truthful EM packet rather than accepting an IAS15 alias.
with tempfile.TemporaryDirectory() as folder:
    path = Path(folder)/'EM.bin'
    path.write_bytes(packet)
    program = '''import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import cloud_transport as gravity
try: gravity.decode(Path(sys.argv[2]).read_bytes(),*sys.argv[3:7],sys.argv[7],10000,17)
except ValueError: print('gravity_refused_explicit_EM')
else: raise AssertionError('Legacy gravity accepted EM')
'''
    child = subprocess.run([sys.executable, '-X', 'utf8', '-c', program, str(ROOT/'app'),
                            str(path), *ids, source, wire.FRAME], check=True,
                           capture_output=True, text=True, encoding='utf-8')
    assert child.stdout.strip() == 'gravity_refused_explicit_EM' and not child.stderr
report = {
    'status': 'explicit_EM_C2CLD002_SI_positions_and_population_binding_verified', 'cases': cases,
    'corrupt_or_incompatible_packets_refused': refused,
    'legacy_installed_gravity_decoder_refuses_EM': True,
    'SI_component_domain_edge_exact': True,
    'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in (*STAGE.glob('*.py'), STAGE/'constants.json', Path(__file__))},
    'scope': 'Wire contract only. No native GPU, renderer, UI,128-source or native performance approval.'}
(ROOT/'evidence/em-cloud-transport-check.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({'status': report['status'], 'cases': len(cases), 'refusals': len(refused),
                  'legacy_gravity_refused_EM': True}, indent=2))
