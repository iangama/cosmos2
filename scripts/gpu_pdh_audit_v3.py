"""Schema4 raw-byte admission plus temporally proven process ownership."""
import gpu_pdh_audit_v2 as base


def audit(report,**options):
    result=base.audit(report,**options)
    base.require(report['ownership_method']=='Toolhelp snapshot plus GetProcessTimes parent identity',
                 'Native temporal ownership proof required')
    roots={report['session']['app'],report['session']['server']}
    for rows in [report['inventory_before'],report['inventory_after']]:
        by_pid={row['pid']:row for row in rows}
        for pid,row in by_pid.items():
            base.integer(row['created_filetime'],minimum=116444736000000001)
            base.require(row['scope_root'] is (pid in roots),'Owned scope root differs')
            reconstructed=(row['created_filetime']-116444736000000000)/10000000
            base.require(abs(reconstructed-row['started_unix'])<=5e-6,'Creation FILETIME and process time differ')
            if pid not in roots:
                parent=by_pid.get(row['parent'])
                base.require(parent is not None,'Owned process parent unavailable')
                base.require(row['parent_created_filetime']==parent['created_filetime']<=row['created_filetime'],
                             'GPU child predates the current parent identity')
            visited=set()
            cursor=pid
            while cursor in by_pid:
                base.require(cursor not in visited,'Cycle in owned GPU process identity')
                visited.add(cursor)
                cursor=by_pid[cursor]['parent']
        base.require(abs(by_pid[report['session']['app']]['started_unix']-report['engine_started_unix'])<=5e-6,
                     'Engine creation time differs from owned scope')
    for key in ['excluded_old_parent_links_before','excluded_old_parent_links_after']:
        for row in report[key]:
            base.require(row['created_filetime']<row['parent_created_filetime'],'Excluded candidate was not older than its parent')
            base.require(row['pid'] not in report['owned_processes'],'Excluded stale parent candidate is still counted')
            base.require(set(row)=={'pid','parent','created_filetime','parent_created_filetime','reason'},
                         'Unexpected unowned process detail in diagnostic')
    return result


sample=base.sample
