"""Finite SI scalar/vector guards; exact SI c=299792458m/s, regime0.01c."""
import math
SPEED_LIMIT_M_S=.01*299792458.

def scalar(value):
    if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('Finite numeric SI value required')
    return float(value)

def vector(value):
    if not isinstance(value,(list,tuple)) or len(value)!=3:raise ValueError('Three SI components required')
    return tuple(scalar(v) for v in value)
