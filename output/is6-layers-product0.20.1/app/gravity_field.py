"""Read-only Newtonian point samples of the active float64 population."""
import math
from physics import PHYSICAL_SCALE
from j2_field import correction
from equilibrium_tide import frozen_field

def evaluate(bodies,position_m):
    if not isinstance(position_m,list) or len(position_m)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in position_m) or math.hypot(*position_m)>1e17:
        raise ValueError('Posição da sonda inválida; use três coordenadas SI finitas no domínio do editor.')
    length=PHYSICAL_SCALE['length_unit_m'];gm_unit=PHYSICAL_SCALE['nominal_GM_unit_m3_s2']
    point=[v/length for v in position_m];sources=[]
    for body in bodies:
        delta=[body['position'][k]-point[k] for k in range(3)];r=math.hypot(*delta)
        if r*length<.001:raise ValueError('Sonda a menos de 1 mm de uma fonte pontual; campo singular fora do domínio.')
        gm=body['mass'];g=[gm*v/r**3*gm_unit/length**2 for v in delta]
        tensor=[[gm*(3*(delta[j]*delta[k])/r**5-(1. if j==k else 0.)/r**3)*gm_unit/length**3 for k in range(3)] for j in range(3)]
        potential=-gm/r*gm_unit/length
        model=body.get('j2')
        if model is not None:
            data=correction(gm*gm_unit,model['radius_eq_m'],model['j2'],model['axis'],
                            [position_m[k]-body['position'][k]*length for k in range(3)])
            g=[a+b for a,b in zip(g,data['acceleration_m_s2'])];potential+=data['potential_J_kg']
            tensor=[[tensor[j][k]+data['tidal_tensor_s_2'][j][k] for k in range(3)] for j in range(3)]
        material=body.get('tide')
        if material is not None:
            if model is not None:raise ValueError('J2 prescrito e maré material não podem ser combinados.')
            data=frozen_field(material['quadrupole_stf_kg_m2'],material['parameters']['radius_m'],[position_m[k]-body['position'][k]*length for k in range(3)])
            g=[a+b for a,b in zip(g,data['acceleration_m_s2'])];potential+=data['potential_J_kg']
            tensor=[[tensor[j][k]+data['tidal_tensor_s_2'][j][k] for k in range(3)] for j in range(3)]
        sources.append({'id':body['id'],'distance_m':r*length,'acceleration_m_s2':g,'potential_J_kg':potential,'tidal_tensor_s_2':tensor})
    total=[math.fsum(s['acceleration_m_s2'][k] for s in sources) for k in range(3)]
    return {'position_m':list(position_m),'acceleration_m_s2':total,'acceleration_norm_m_s2':math.hypot(*total),
            'potential_J_kg':math.fsum(s['potential_J_kg'] for s in sources),'sources':sources,
            'tidal_tensor_s_2':[[math.fsum(s['tidal_tensor_s_2'][j][k] for s in sources) for k in range(3)] for j in range(3)],
            'model':'Newtonian monopoles plus frozen induced material quadrupole; passive reading does not induce a new tide; effective orbital energy includes response cost separately' if any(b.get('tide') for b in bodies) else 'Newtonian monopoles plus exterior J2 with prescribed inertial axes; potential zero at infinity; no probe backreaction' if any(b.get('j2') for b in bodies) else 'Newtonian point masses; potential zero at infinity; no probe backreaction',
            'minimum_source_distance_m':.001}


def evaluate_points(bodies,positions_m):
    """Finite bounded samples; singular points retain their index and reason."""
    if not isinstance(positions_m,list) or not 1<=len(positions_m)<=512:
        raise ValueError('Use de 1 a 512 posições por lote.')
    results=[]
    for index,point in enumerate(positions_m):
        try:results.append({'index':index,'valid':True,**evaluate(bodies,point)})
        except ValueError as error:results.append({'index':index,'valid':False,'position_m':point if isinstance(point,list) and len(point)==3 and all(type(v) in (int,float) and math.isfinite(v) for v in point) else None,'reason':str(error)})
    return results
