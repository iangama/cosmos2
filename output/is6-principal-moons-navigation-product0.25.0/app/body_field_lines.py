"""Bounded, frozen integral curves of a trusted body's internal magnetic field."""
import math

import geomagnetism as igrf
import jrm33


class Boundary(Exception):
    pass


class NullField(Exception):
    pass


def vector(value):
    if not isinstance(value, (list, tuple)) or len(value) != 3 or any(
            type(v) not in (int, float) or not math.isfinite(v) for v in value):
        raise ValueError('Informe três componentes cartesianas finitas.')
    return [float(v) for v in value]


def geodetic(position):
    x, y, z = vector(position)
    rho = math.hypot(x, y)
    if math.hypot(rho, z) < igrf.WGS_B/2:
        raise ValueError('Inversão geodética restrita ao exterior próximo da Terra.')
    if rho == 0:
        return math.copysign(90., z), 0., abs(z)-igrf.WGS_B
    e2 = igrf.WGS_F*(2-igrf.WGS_F)
    latitude = math.atan2(z, rho*(1-e2))
    for _ in range(12):
        sine = math.sin(latitude)
        n = igrf.WGS_A/math.sqrt(1-e2*sine*sine)
        updated = math.atan2(z+e2*n*sine, rho)
        if abs(updated-latitude) < 2e-16:
            latitude = updated
            break
        latitude = updated
    sine, cosine = math.sin(latitude), math.cos(latitude)
    height = rho*cosine+z*sine-igrf.WGS_A*math.sqrt(1-e2*sine*sine)
    return math.degrees(latitude), math.degrees(math.atan2(y, x)), height


class Model:
    def __init__(self, reading):
        self.reading = reading
        if reading.get('kind') == 'scene_Earth_IGRF14_passive_point':
            self.name, self.radius = 'IGRF14', igrf.WGS_A
            self.year = reading['epoch']['decimal_UTC_year']
            igrf.coefficients(self.year)
            self.degree = 13
        elif reading.get('kind') == 'scene_Jupiter_JRM33_passive_point':
            self.name, self.radius, self.degree = 'JRM33', jrm33.R, reading['degree']
            if type(self.degree) is not int or self.degree not in (1, 13, 18):
                raise ValueError('Truncamento joviano não adotado.')
        else:
            raise ValueError('Leitura corporal confirmada ausente.')

    def clearance(self, position):
        p = vector(position)
        if self.name == 'IGRF14':
            if math.hypot(*p) < igrf.WGS_B/2:
                return -self.radius
            height = geodetic(p)[2]
            result = min(height, 1e6-height)
            return 0. if abs(result) <= 1e-6 else result
        r = math.hypot(*p)
        result = min(r-self.radius, 20*self.radius-r)
        return 0. if abs(result) <= 2e-15*max(r, self.radius) else result

    def field(self, position):
        p = vector(position)
        tolerance = 1e-6 if self.name == 'IGRF14' else 2e-15*self.radius*20
        if self.clearance(p) < -tolerance:
            raise ValueError('Ponto fora do domínio magnético adotado.')
        if self.name == 'JRM33':
            return jrm33.sample(p, self.degree)['field_SystemIII_T']
        x, y, z = p
        radius = math.hypot(*p)
        theta, phi = math.atan2(math.hypot(x, y), z), math.atan2(y, x)
        br, bt, bp = igrf.spherical(self.year, radius, theta, phi)
        s, c, cl, sl = math.sin(theta), math.cos(theta), math.cos(phi), math.sin(phi)
        return [(br*s+bt*c)*cl*1e-9-bp*sl*1e-9,
                (br*s+bt*c)*sl*1e-9+bp*cl*1e-9, (br*c-bt*s)*1e-9]


def trace(field, clearance, seed_m, radius_m, direction=1, *, tolerance=1e-9,
          max_step=.04, min_step=1e-7, boundary_distance=1e-6,
          max_arc=16., max_steps=2048, max_evaluations=100000):
    seed = vector(seed_m)
    parameters = [radius_m, tolerance, max_step, min_step, boundary_distance, max_arc]
    if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in parameters):
        raise ValueError('Parâmetros de integração devem ser positivos e finitos.')
    if min_step > max_step or boundary_distance < min_step:
        raise ValueError('Escalas de integração inconsistentes.')
    if max_step > .04 or max_arc > 16:
        raise ValueError('Escala solicitada excede o orçamento do traçado.')
    if type(direction) is not int or direction not in (-1, 1):
        raise ValueError('Sentido deve ser +1 ou -1.')
    if type(max_steps) is not int or not 1 <= max_steps <= 2048:
        raise ValueError('Limite de passos fora do orçamento.')
    if type(max_evaluations) is not int or not 1 <= max_evaluations <= 100000:
        raise ValueError('Limite de avaliações fora do orçamento.')
    def checked_clearance(position):
        result = clearance(position)
        if type(result) not in (int, float) or not math.isfinite(result):
            raise ValueError('Distância ao domínio deve ser finita.')
        return result
    if checked_clearance(seed) < 0:
        raise ValueError('Semente fora do domínio adotado.')
    calls = 0
    def sample(position):
        nonlocal calls
        if checked_clearance(position) < 0:
            raise Boundary()
        calls += 1
        if calls > max_evaluations:
            raise ValueError('Orçamento de avaliações do traçado excedido.')
        return vector(field(position))
    def unit(y):
        b = sample([v*radius_m for v in y])
        norm = math.hypot(*b)
        if not math.isfinite(norm):
            raise ValueError('Norma magnética não finita.')
        if norm == 0:
            raise NullField()
        return [direction*v/norm for v in b]
    def add(y, k, h):
        return [y[i]+h*k[i] for i in range(3)]
    def rk4(y, h):
        k1 = unit(y)
        k2 = unit(add(y, k1, h/2))
        k3 = unit(add(y, k2, h/2))
        k4 = unit(add(y, k3, h))
        result = [y[i]+h*(k1[i]+2*k2[i]+2*k3[i]+k4[i])/6 for i in range(3)]
        if checked_clearance([v*radius_m for v in result]) < 0:
            raise Boundary()
        return result
    y = [v/radius_m for v in seed]
    points, arcs = [seed], [0.]
    h, arc, steps, rejected = max_step, 0., 0, 0
    reason = 'step_budget'
    while steps < max_steps:
        h = min(h, max_arc-arc)
        if h <= 1e-14:
            reason = 'arc_limit'
            break
        try:
            coarse = rk4(y, h)
            fine = rk4(rk4(y, h/2), h/2)
        except Boundary:
            rejected += 1
            h /= 2
            if h < min_step:
                reason = 'domain_boundary'
                break
            continue
        except NullField:
            reason = 'null_field'
            break
        error = max(abs(a-b) for a, b in zip(coarse, fine))/15
        if error > tolerance:
            rejected += 1
            h *= max(.2, .9*(tolerance/error)**.2)
            if h < min_step:
                raise ValueError('Tolerância exigiu passo abaixo do mínimo adotado.')
            continue
        y = fine
        arc += h
        steps += 1
        points.append([v*radius_m for v in y])
        arcs.append(arc*radius_m)
        if checked_clearance(points[-1]) <= boundary_distance*radius_m:
            reason = 'domain_boundary'
            break
        h = min(max_step, h*(2 if error == 0 else min(2, .9*(tolerance/error)**.2)))
    fields = [sample(p) for p in points]
    if reason == 'domain_boundary' and checked_clearance(points[-1]) > boundary_distance*radius_m:
        raise ValueError('Término de borda sem proximidade confirmada.')
    return {'direction': direction, 'points_m': points, 'field_T': fields,
            'arc_m': arcs, 'termination': reason, 'accepted_steps': steps,
            'rejected_steps': rejected, 'rhs_evaluations': calls,
            'endpoint_clearance_m': checked_clearance(points[-1]),
            'parameters': {'reference_radius_m': radius_m, 'tolerance_R': tolerance,
                'max_step_R': max_step, 'min_step_R': min_step,
                'boundary_distance_R': boundary_distance, 'max_arc_R': max_arc,
                'max_steps': max_steps, 'max_evaluations': max_evaluations}}


def bundle(reading):
    model = Model(reading)
    point = reading['point_ITRF93_m' if model.name == 'IGRF14' else 'point_SystemIII_m']
    seeds = [vector(point)]
    for longitude in [0, 90, 180, 270]:
        if model.name == 'IGRF14':
            seed = list(igrf.geodetic_position(0., float(longitude if longitude <= 180 else longitude-360), 500000.))
        else:
            phi = math.radians(longitude)
            seed = [1.5*model.radius*math.cos(phi), 1.5*model.radius*math.sin(phi), 0.]
        if not any(math.dist(seed, existing) < 1e-8*model.radius for existing in seeds):
            seeds.append(seed)
    lines = []
    for seed in seeds:
        negative = trace(model.field, model.clearance, seed, model.radius, -1)
        positive = trace(model.field, model.clearance, seed, model.radius, 1)
        vertices = list(reversed(negative['points_m']))+positive['points_m'][1:]
        lines.append({'seed_m': seed, 'negative': negative, 'positive': positive,
                      'points_m': vertices, 'orientation': 'Negative endpoint through seed toward +B.'})
    return {'schema': 1, 'model': model.name, 'degree': model.degree,
            'epoch': reading['epoch'], 'lines': lines,
            'domain': 'WGS84 height0..1000km' if model.name == 'IGRF14' else 'geocentric1..20Rj',
            'policy': 'Frozen internal-model integral curves. Domain/arc/effort stops explicitly recorded; no assumed closure, plasma trajectory, external field or neutral-body force.',
            'observational_uncertainty': None}
