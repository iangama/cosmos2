"""C2-11 spherical sample sites and normalized direction arrows."""
import math

def shell(center_m,radius_m,count=96):
    if not isinstance(center_m,list) or len(center_m)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in center_m):raise ValueError('Centro inválido.')
    if type(radius_m) not in (int,float) or not math.isfinite(radius_m) or not .001<=radius_m<=1e17 or type(count) is not int or not 8<=count<=128:raise ValueError('Casca fora do domínio.')
    golden=math.pi*(3-math.sqrt(5));points=[]
    for i in range(count):
        z=1-2*(i+.5)/count;rho=math.sqrt(max(0,1-z*z));point=[center_m[0]+radius_m*rho*math.cos(golden*i),center_m[1]+radius_m*rho*math.sin(golden*i),center_m[2]+radius_m*z]
        if math.hypot(*point)>1e17:raise ValueError('Amostra fora do domínio do editor.')
        points.append(point)
    return points

def arrows(samples,length_m):
    if type(length_m) not in (int,float) or not math.isfinite(length_m) or length_m<=0:raise ValueError('Escala gráfica inválida.')
    result=[]
    for sample in samples:
        index=sample['index']
        if not sample['valid']:result.append({'index':index,'drawn':False,'reason':sample['reason']});continue
        vector=sample['acceleration_m_s2'];norm=math.hypot(*vector)
        if norm==0:result.append({'index':index,'drawn':False,'reason':'Campo nulo; direção indefinida.'});continue
        direction=[v/norm for v in vector];axis=min(range(3),key=lambda k:abs(direction[k]));basis=[float(k==axis) for k in range(3)]
        side=[direction[1]*basis[2]-direction[2]*basis[1],direction[2]*basis[0]-direction[0]*basis[2],direction[0]*basis[1]-direction[1]*basis[0]];s=math.hypot(*side);side=[v/s for v in side]
        tail=sample['position_m'];tip=[tail[k]+length_m*direction[k] for k in range(3)];base=[tip[k]-.25*length_m*direction[k] for k in range(3)];left=[base[k]+.12*length_m*side[k] for k in range(3)];right=[base[k]-.12*length_m*side[k] for k in range(3)]
        result.append({'index':index,'drawn':True,'acceleration_norm_m_s2':norm,'segment_m':[list(tail),tip,left,tip,right]})
    return {'length_m':length_m,'scale':'direction_only_uniform_graphic_length_not_force_magnitude','arrows':result}
