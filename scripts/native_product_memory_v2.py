"""Strict working-set sum using the same temporal ownership as native GPU data."""
import psutil
from owned_process_snapshot import snapshot


def product_memory(session):
    tree=snapshot(session)
    rows=[]
    for identity in tree['owned']:
        process=psutil.Process(identity['pid'])
        if abs(process.create_time()-identity['started_unix'])>5e-6:
            raise ValueError('RAM process identity changed after owned snapshot')
        memory=process.memory_info()
        rows.append(dict(pid=identity['pid'],name=identity['name'],working_set_bytes=memory.rss,
                         private_bytes=memory.private,created_filetime=identity['created_filetime']))
    return dict(processes=rows,sum_working_set_bytes=sum(row['working_set_bytes'] for row in rows),
        ownership=tree,method='GetProcessMemoryInfo via psutil; strict temporally checked owned tree. Working sets can count shared DLL pages more than once.')
