"""Independent raw-poll timing admission, including initial native discovery."""
import math
from c214_profile_contract import require
from expanded_residency_timing import stamp


def admit(polls,history,initialization=None,rows=None):
    require(type(polls) is list and len(polls)>=2,'Raw native poll history absent')
    require(len(polls)==history['polls'],'Raw native poll count differs')
    previous=None;gaps=[]
    for index,poll in enumerate(polls):
        require(type(poll['index']) is int and poll['index']==index and poll['completed'] is True,'Native poll missing, reordered or failed')
        start,finish=poll['started_filetime'],poll['finished_filetime']
        require(type(start) is int and type(finish) is int and 116444736000000000<start<=finish,'Native poll FILETIME invalid')
        duration=poll['duration_s'];monotonic=poll['started_monotonic_s']
        require(type(duration) in (int,float) and math.isfinite(duration) and 0<=duration<=.25,'Native poll duration exceeds cadence budget')
        require(type(monotonic) in (int,float) and math.isfinite(monotonic) and monotonic>=0,'Native monotonic poll clock invalid')
        require(abs((finish-start)/1e7-duration)<.01,'Native poll clocks disagree')
        if previous is None:require(poll['gap_s'] is None,'Initial native poll was discarded')
        else:
            gap=monotonic-previous['started_monotonic_s'];gaps.append(gap)
            require(0<gap<=.25 and abs(gap-poll['gap_s'])<1e-8,'Native poll gap exceeds bound or differs from raw starts')
            require(previous['finished_filetime']<=start and abs((start-previous['started_filetime'])/1e7-gap)<.01,'Native poll clocks overlap or diverge')
        previous=poll
    maximum=max(gaps)
    require(abs(maximum-history['maximum_poll_gap_s'])<1e-8,'Summarized native cadence differs from every raw poll')
    if initialization is not None:
        a=(polls[0]['started_filetime']-116444736000000000)/1e7
        b=(polls[-1]['finished_filetime']-116444736000000000)/1e7
        require(a<=stamp(initialization['started_utc'])<=stamp(initialization['finished_utc'])<=b,'Native polls do not cover the full initialization')
        if rows:
            require(a<=stamp(rows[0]['started_utc']) and stamp(rows[-1]['finished_utc'])<=b,'Native polls do not cover every raw sample')
    return dict(polls=len(polls),maximum_gap_s=maximum,maximum_duration_s=max(p['duration_s'] for p in polls),first_poll_s=polls[0]['duration_s'])
