# IS-3 — vetor magnético nativo em bancada temporária

A geometria passou nos seis vetores analíticos, 102 leituras IGRF/JRM33,
rotação, serialização das malhas e seis recusas. Erro máximo de matriz:
4,45e−16; quantização dos vértices: 3,83e−7 do raio de referência.
Recibo: evidence/is3-body-field-geometry-check-20261023a.json.

A bancada nativa C também passou nas confirmações mecânicas: centro e
ponto locais dentro de 1 mm, coordenadas mundiais dentro do limite de
arredondamento previamente definido, fase física preservada, nós temporários
removidos, marcadores restaurados e Atlas/fontes/owner intactos. Cada captura
teve 70 quadros posteriores confirmados. Recibo:
evidence/is3-native-body-vector-20261023c.json.

A tentativa A permaneceu recusada por exigir 1 mm na subtração mundial,
embora LabRoot tenha offset de 1e14 m e ULP de 1,5625 cm. A regra local de
1 mm continua; o limite mundial é calculado por ULP de cada componente.
B passou nessa confirmação, mas foi recusada por contar a tabela de amostras
com o operador Lua #; ela tem chaves string. C usa o contador explícito,
como os runners nativos anteriores. Fontes A/B/C estão arquivadas.

O aceite visual foi RECUSADO na revisão das quatro imagens: em 100% há
elipsoide/esfera, ponto amarelo e seta verde; em 150% o IGRF desaparece e o
JRM33 fica parcialmente cortado, sem seta/rótulo. Não é ausência de quadros
novos. A leitura numérica continua legível. Esse comportamento também apareceu
na captura anterior do marcador de Júpiter em 150%, sem causa estabelecida.
Recibo: evidence/is3-native-body-vector-20261023c-visual-review.json.

A próxima ação é um diagnóstico dirigido de 100/150% na mesma cena fixa:
registrar câmera, transformações e propriedades de visibilidade a cada escala,
depois comparar CEF visível/oculto. Não presumir que trocar runtime resolve.
Não refazer síntese, worker ou os perfis J imutáveis já aceitos.

Código em output/is3-body-vector-staging; harness
scripts/verify-native-body-field-prototype.py. Nenhum botão permanente ou
camada foi adicionado aos arquivos do produto. A bancada mede uma amostra
fixa, sem força sobre centros neutros, linhas de campo ou desempenho próprio.
Júpiter usa esfera de referência do harmônico, não superfície física;
Terra usa elipsoide WGS84 de referência. A seta tem comprimento gráfico.

CORREÇÃO24/10 — SUPERSEDE A RECUSA VISUAL POR DESAPARECIMENTO
A leitura inicial das prévias reduzidas estava errada. Comparação exata da
região central850×700 dá RGBAIDÊNTICO em100/150 tanto paraEarth quantoJupiter;
diferençaRGBmáximaZERO. ROIda seta ampliada confirma aparência igual.
Prova evidence/is3-visibility-pixel-comparison-20261024a.json e figura
output/is3-visibility-forensic-20261024/comparison.png. Recibo de correção
is3-native-body-vector-20261023c-visual-correction-20261024.json substitui a
conclusão anterior; originais preservados. Não hábase para corrigir renderer.
Voltar a integrar controles/lifecycle do vetor na candidata. A bancada
temporária passou, masfeaturepersistente e desempenho próprio ainda pendem.
BuildGLdiagnóstico opt-in em runtime separado foi preparado sem correção
gráfica; não promover nem usar para justificar hipótese refutada. Assim que
stager terminar, restaurar quatro fontes e remover apenas header novo a
partir de output/render-state-diagnostic-staging/before epreparation.json,
preservandoartefato diagnóstico e runtimes medidos.
