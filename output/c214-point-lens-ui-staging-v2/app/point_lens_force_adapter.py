"""Convert the curated bench units to the accepted SI point-lens kernel."""
import copy
import math

import point_lens

AU_M=149597870700.0
PC_M=AU_M*648000/math.pi
KPC_M=1000*PC_M
GM_SUN_NOMINAL=1.3271244e20
UNIT_SOURCES=['https://aa.usno.navy.mil/faq/asa_glossary',
              'https://arxiv.org/abs/1510.06262','https://arxiv.org/abs/1510.07674']


def geometry(parameters):
    result=dict(GM_m3_s2=parameters['mass_solar']*GM_SUN_NOMINAL)
    for kind in ['observer','lens','source']:
        result[kind+'_m']=[parameters[kind+'_x_au']*AU_M,parameters[kind+'_y_au']*AU_M,
                          parameters[kind+'_z_kpc']*KPC_M]
    return result


def experiment(parameters,controls):
    control=controls['gravity'];acting=control['acting'] and control['effects']['ray_bending']
    value=point_lens.experiment(geometry(parameters),bending=acting)
    current=value['actual'];g=value['geometry'];images=current['images']
    measurements=[dict(label='Raio angular de Einstein',value=g['einstein_angle_rad']*648000000/math.pi,unit='mas'),
      dict(label='Desalinhamento da fonte / raio de Einstein',value=g['u'],unit=''),
      dict(label='Separação das imagens',value=None if current['image_separation_rad'] is None else current['image_separation_rad']*648000000/math.pi,unit='mas'),
      dict(label='Amplificação total aplicada',value=current['magnification_total'],unit='vezes'),
      dict(label='Excesso de amplificação sobre1',value=current['magnification_total_minus_unity'],unit=''),
      dict(label='Raio de Schwarzschild da lente',value=g['schwarzschild_radius_m'],unit='m')]
    for image in images:
        label='Imagem externa' if image['label']=='outer' else 'Imagem interna' if image['label']=='inner' else 'Imagem direta hipotética'
        measurements.append(dict(label=label+' · amplificação absoluta',value=image['magnification_abs'],unit='vezes'))
        measurements.append(dict(label=label+' · desvio no plano',value=image['physical_deflection_rad']*648000000/math.pi,unit='mas'))
    limit=(current['status']=='aligned_point_source_caustic')
    reference_limit=(value['reference']['status']=='aligned_point_source_caustic')
    if limit:
        message='Fonte pontual alinhada: há um anel de Einstein e o modelo não fornece amplificação finita. Afaste a fonte para obter duas imagens.'
    elif reference_limit:
        message='A imagem aplicada é a hipótese sem desvio. A referência da fonte pontual está alinhada e não possui amplificação finita.'
    else:message=''
    return dict(model='Lente pontual em campo fraco · planos finos e óptica geométrica.',
      domain='Fonte pontual e lente transparente estáticas em fundo euclidiano. Ângulos paraxiais≤0,01rad e impactos≥1000rs nas duas imagens. Sem fonte extensa, difração, ocultação, Kerr ou distâncias cosmológicas. Amplificação no alinhamento é singular; não representa brilho observado infinito.',
      parameter_note='Massa usa GM solar nominal; X/Y em au e Z em kpc no mesmo referencial. Geometria idealizada, sem época ou objetos do Atlas.',
      influences=['gravity'],time_s=[0.],time_display=dict(unit='estado estático',seconds_per_unit=1,symbol=''),
      point_lens=value,point_lens_message=message,measurements=measurements,
      reference=dict(channel_dependencies='Fonte, lente e observador são posições estáticas editáveis. A atuação suprimida mantém a geometria material e a referência completa.'),
      units=dict(au_m=AU_M,pc_m=PC_M,kpc_m=KPC_M,nominal_solar_GM_m3_s2=GM_SUN_NOMINAL,
                 angular_mas_per_rad=648000000/math.pi,sources=UNIT_SOURCES),
      sources=point_lens.SOURCES+UNIT_SOURCES)
