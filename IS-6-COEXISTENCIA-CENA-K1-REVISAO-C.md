# K1C — ponto científico e transformação gráfica

K1B recusou a preparação oculta. O diagnóstico nativo de 03/11 reproduziu
o arredondamento da transformação StaticRotation: o motor guarda ângulos em
Vec3Property e cria quaternion/matriz em float. O ponto sob essa transformação
difere da rotação científica em até 0,449 m na Terra e 2,844 m em Júpiter.
Isso está dentro dos limites gráficos já publicados pelo gerador de malhas,
mas não satisfaz o contrato de posição científica de 1 mm mais ULPs globais.
Fontes e recibos A/B ficam preservados, sem reclassificar as falhas.

A revisão C usa a translação relativa GALACTIC em double para o ponto
científico, como o rótulo corporal já aceito. Exige erro local ≤1 mm e
erro de diferença world ≤ulp(ponto)+ulp(centro)+1 mm. Não aumenta esses limites.
Mantém uma segunda sonda sob a rotação/escala gráfica e verifica seu erro
contra o limite de exibição já declarado pelo gerador, acrescido dos ULPs
da subtração global. Também exige os ângulos nativos iguais aos ângulos
solicitados arredondados para float32; arquivos e escalas continuam selados.

Não há alteração dos modelos, leituras SI, geometria ou candidata 0.18.5.
O diagnóstico está em evidence/is6-magnetic-transform-diagnostic-20261103a.json.
Módulo novo is6_layer_scene_v3.py, verificador v3, driver v12 e recibo C.
Os demais critérios K1 permanecem, incluindo falhas reais e limpeza nativa.
Ainda não há aceite de produto, persistência composta, perfil ou toda IS6.
