"""Discrete colored sample glyphs; no interpolation into unsampled field domains."""
import math

from body_field_geometry import product
from body_field_lines import vector

PALETTE=[[.267,.005,.329],[.275,.195,.496],[.212,.36,.552],[.153,.497,.558],
         [.122,.633,.53],[.288,.758,.428],[.627,.855,.223],[.993,.906,.144]]


def build(data,representation):
    if representation not in ('shell','cut'):raise ValueError('Mapa magnético não adotado.')
    source=data[representation];rows=source['samples']
    expected=(19,37) if representation=='shell' else (65,65)
    if len(rows)!=expected[0] or any(len(row)!=expected[1] for row in rows):raise ValueError('Grade magnética incompatível.')
    radius=6378137. if data['model']=='IGRF14' else 71492000.
    samples=[p for row in rows for p in row if p is not None]
    if not samples:raise ValueError('Mapa sem amostras disponíveis.')
    for p in samples:
        vector(p['position_model_m']);vector(p['field_model_T'])
        v=p['field_norm_T']
        if type(v) not in (int,float) or not math.isfinite(v) or v<0 or abs(v-math.hypot(*p['field_model_T']))>2e-18:
            raise ValueError('Módulo magnético incompatível com a amostra.')
    low=min(p['field_norm_T'] for p in samples);high=max(p['field_norm_T'] for p in samples)
    bins=[{'color_rgb':color,'segments_m':[],'cells':[]} for color in PALETTE]
    radius_of_view=max(math.hypot(*p['position_model_m']) for p in samples)+.02*radius
    glyph_half=.008*radius;drawn=0
    for row_index,row in enumerate(rows):
        for column,p in enumerate(row):
            if p is None:continue
            # Identical seam/polar coordinates are single display symbols;
            # the complete original scientific matrix remains unchanged.
            if representation=='shell' and (column==expected[1]-1 or row_index in (0,expected[0]-1) and column>0):continue
            ratio=0. if high==low else (p['field_norm_T']-low)/(high-low)
            index=max(0,min(7,int(8*ratio)))
            item=bins[index];item['cells'].append([row_index,column]);drawn+=1
            point=p['position_model_m']
            for axis in range(3):
                first=list(point);last=list(point);first[axis]-=glyph_half;last[axis]+=glyph_half
                item['segments_m'].append([first,last])
    return {'schema':1,'representation':representation,'bins':bins,'shape':list(expected),
        'minimum_sampled_T':low,'maximum_sampled_T':high,'palette_rgb':PALETTE,
        'sample_count':len(samples),'drawn_symbols':drawn,'glyph_half_length_m':glyph_half,
        'view_radius_m':radius_of_view,'reference_radius_m':radius,
        'legend':'Discrete eight-bin internal |B| sampled values; symbol size is graphic. Masked/unavailable points are absent, not zero.'}


def view(data,display):
    radius=display['reference_radius_m'];point=data['probe']['position_model_m']
    distance=3.4*max(display['view_radius_m'],math.hypot(*point)+.3*radius)
    if display['representation']=='cut':
        u=data['cut']['u_axis_model'];position=[u[1]*distance,-u[0]*distance,0.];up=[0.,0.,1.]
    else:
        from body_field_geometry import build as point_geometry
        initial=point_geometry(data['reading'])['view'];scale=distance/initial['distance_m']
        return {'distance_m':distance,'position_render_relative_m':[v*scale for v in initial['position_render_relative_m']],
                'up_render':initial['up_render']}
    return {'distance_m':distance,'position_render_relative_m':product(data['body_to_render'],position),
            'up_render':product(data['body_to_render'],up)}
