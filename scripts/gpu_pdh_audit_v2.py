"""Independent schema4 admission from integer PDH raw records, without PDH calls."""
import datetime as dt
import math
import re

PROCESS = re.compile(r'\\gpu process memory\((pid_(\d+)_[^)]+)\)\\(dedicated usage|shared usage)')
ADAPTER = re.compile(r'\\gpu adapter memory\(([^)]+)\)\\dedicated usage')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def stamp(value):
    require(isinstance(value,str),'UTC timestamp string required')
    result = dt.datetime.fromisoformat(value.replace('Z','+00:00'))
    require(result.tzinfo is not None and result.utcoffset() == dt.timedelta(0),'Explicit UTC offset required')
    return result


def integer(value, *, minimum=0):
    require(type(value) is int and minimum <= value < 2**63,'Nonnegative64-bit integer required')
    return value


def parse_path(path):
    require(isinstance(path,str) and path == path.lower(),'Canonical lowercase GPU path required')
    process = PROCESS.fullmatch(path)
    if process:
        return dict(instance=process[1],pid=int(process[2]),counter=process[3],kind='product')
    adapter = ADAPTER.fullmatch(path)
    require(adapter is not None,'Unknown canonical GPU path')
    return dict(instance=adapter[1],pid=None,counter='dedicated usage',kind='adapter')


def sample(sample, configured, owned):
    require(type(sample) is dict,'PDH sample required')
    query = stamp(sample['utc'])
    before,after = stamp(sample['call_started_utc']),stamp(sample['call_finished_utc'])
    require(before <= after and (before-query).total_seconds() <= .1 and (query-after).total_seconds() <= .1,
            'PDH query time outside its call interval')
    local_filetime = integer(sample['query_filetime'],minimum=116444736000000001)
    filetime = integer(sample['query_utc_filetime'],minimum=116444736000000001)
    require(sample['time_basis'] == 'PDH local FILETIME converted by LocalFileTimeToFileTime','Explicit native timezone conversion required')
    delta = (filetime-local_filetime)/10000000
    require(type(sample['local_to_utc_seconds']) in (int,float) and sample['local_to_utc_seconds'] == delta
            and abs(delta) <= 14*3600 and delta % 60 == 0,'Local FILETIME conversion differs')
    reconstructed = dt.datetime(1601,1,1,tzinfo=dt.timezone.utc)+dt.timedelta(microseconds=filetime//10)
    require(reconstructed == query,'PDH query FILETIME and UTC differ')
    rows = sample['raw_counter_samples']
    require(type(rows) is list and len(rows) == len(configured),'Selected PDH row count differs')
    by_path = {row['path']:row for row in rows}
    require(set(by_path) == set(configured) and len(by_path) == len(rows),'Selected PDH path set differs')
    products,adapters = [],[]
    for path,row in by_path.items():
        identity = parse_path(path)
        for key in ['raw_api_status','formatted_api_status']:
            require(type(row[key]) is int and row[key] == 0,'PDH API call failed')
        for key in ['raw_status','formatted_status']:
            require(type(row[key]) is int and row[key] in {0,1},'PDH counter data invalid')
        require(row['raw_type'] == row['formatted_type'] == 0x10100,'PDH counter is not a64-bit byte gauge')
        require(type(row['raw_type']) is int and type(row['formatted_type']) is int,'Numeric counter types required')
        require(type(row['format']) is int and row['format'] == (0x400|0x1000),'Unscaled integer PDH format required')
        raw = integer(row['raw_first_value'])
        require(integer(row['formatted_bytes']) == raw,'Formatted GPU bytes differ from raw count')
        integer(row['raw_timestamp_filetime'],minimum=1)
        integer(row['raw_multi_count'])
        require(type(row['raw_second_value']) is int and -(2**63) <= row['raw_second_value'] < 2**63,'PDH second raw value differs')
        projected = dict(pid=identity['pid'],instance=identity['instance'],counter=identity['counter'],bytes=raw)
        if identity['kind'] == 'product':
            require(identity['pid'] in owned,'Unowned GPU process was sampled')
            products.append(projected)
        else:
            adapters.append(projected)
    require(products and adapters,'Owned GPU and adapter counters required')
    for product in products:
        prefix='\\gpu process memory('+product['instance']+')\\'
        require(all(prefix+counter in configured for counter in ['dedicated usage','shared usage']),
                'Incomplete dedicated/shared GPU pair')
    dedicated = sum(row['bytes'] for row in products if row['counter'] == 'dedicated usage')
    total = sum(row['bytes'] for row in products)
    return dict(products=products,adapters=adapters,product_dedicated_sum_bytes=dedicated,
                product_dedicated_plus_shared_sum_bytes=total)


def audit(report, *, expected_samples=None, coverage=None, expected_session=None, engine_sha256=None, generation=None):
    require(report['schema'] == 4 and type(report['schema']) is int,'Native PDH schema4 required')
    require(report['valid'] is True and report['failure'] is None,'PDH collection was refused')
    require(report['method'] == 'Windows PDH ctypes; selected owned byte gauges','Unknown GPU collection method')
    if expected_session is not None:
        require(report['session'] == expected_session,'GPU collector session differs from the owned host')
    if engine_sha256 is not None:
        require(report['engine_sha256'] == engine_sha256,'GPU collector executable differs')
    if generation is not None:
        require(report['generation'] == generation,'GPU collector generation differs')
    configured = report['configured_counter_paths']
    require(type(configured) is list and len(set(configured)) == len(configured),'Duplicate configured PDH paths')
    require(configured == report['counter_paths_after'],'GPU path set changed during collection')
    owned = report['owned_processes']
    require(type(owned) is list and len(set(owned)) == len(owned) and all(type(p) is int and p>0 for p in owned),'Owned process identities differ')
    require(report['session']['app'] in owned and report['session']['server'] in owned,'Engine/server absent from owned set')
    inventories = []
    for inventory in [report['inventory_before'],report['inventory_after']]:
        by_pid = {row['pid']:row for row in inventory}
        require(set(by_pid) == set(owned) and len(inventory) == len(owned),'Owned process inventory differs')
        inventories.append(by_pid)
    require(inventories[0] == inventories[1],'Owned process identity changed')
    exposed = set()
    for path in configured:
        pid = parse_path(path)['pid']
        if pid is not None:
            require(pid in owned,'Unowned configured GPU path')
            exposed.add(pid)
    require(exposed == set(report['owned_gpu_processes']),'Exposed GPU identity set differs')
    require(set(owned)-exposed == set(report['owned_without_exposed_gpu_counter']),'Missing exposed GPU paths were assigned zero')
    require(any(parse_path(p)['pid'] == report['session']['app'] and parse_path(p)['counter'] == 'dedicated usage' for p in configured),'Engine dedicated counter absent')
    metadata = report['counter_metadata']
    require(set(metadata) == set(configured),'PDH counter metadata differs')
    require(all(row['kind'] == 0x10100 for row in metadata.values()),'Incompatible GPU metadata type')
    for path,row in metadata.items():
        parsed = parse_path(path)
        require(row['instance'] == parsed['instance'] and row['pid'] == parsed['pid']
                and row['counter'] == parsed['counter'],'GPU counter metadata identity differs')
        require(row['object'] == ('GPU Process Memory' if parsed['kind'] == 'product' else 'GPU Adapter Memory'),
                'GPU counter metadata object differs')
    for key in ['app','server']:
        require(report['session'][key] in inventories[0],'Session process not in native inventory')
    rows = report['samples']
    require(type(rows) is list and len(rows) == report['requested_samples'],'PDH sample loss')
    if expected_samples is not None:
        require(len(rows) == expected_samples,'PDH sample count differs from the frozen plan')
    require(1 <= len(rows) <= 120,'PDH sample budget differs')
    scenario = report['scenario_before']
    require(scenario == report['scenario_after'],'Final renderer/scenario changed')
    require(scenario['mode'] == report['expected_mode'] and scenario['renderer_confirmed'] is True,'Renderer/scenario unconfirmed')
    if report['expected_worker'] == 'paused':
        require(scenario['paused'] is True,'Paused worker required')
    times,monotonic,peak = [],[],0
    offsets = set()
    for row in rows:
        totals = sample(row,configured,owned)
        require(all(row[key] == value for key,value in totals.items()),'GPU projection/sum differs from raw samples')
        require(row['scenario'] == scenario,'Renderer/scenario changed during GPU sampling')
        times.append(stamp(row['utc']))
        offsets.add(row['local_to_utc_seconds'])
        require(type(row['monotonic_offset_s']) in (int,float) and math.isfinite(row['monotonic_offset_s'])
                and row['monotonic_offset_s'] >= 0,'Sampling offset differs')
        monotonic.append(row['monotonic_offset_s'])
        peak=max(peak,totals['product_dedicated_plus_shared_sum_bytes'])
    for index in range(1,len(rows)):
        gap=monotonic[index]-monotonic[index-1]
        require(.5 <= gap <= 1.5,'GPU sampling interval outside adopted bounds')
        require(abs((times[index]-times[index-1]).total_seconds()-gap) <= .2,'UTC/monotonic sampling clocks diverge')
    require(len(offsets) == 1,'Windows timezone changed during native collection')
    if coverage:
        require(times[0] <= stamp(coverage[0]) and times[-1] >= stamp(coverage[1]),'GPU samples do not cover the frame window')
    return dict(samples=len(rows),paths=len(configured),owned_processes=len(owned),
                peak_dedicated_plus_shared_bytes=peak,scope='WDDM sum per process; shared allocations can be counted more than once.')
