# Precisão temporal na comparação com Horizons

A consultaA foi concluída com seis respostas preservadas. Os cabeçalhos
retornaram`jup365_merged` e`sat441l`, enquanto as fontes locais se chamam
JUP365/SAT441. A igualdade de nome de modelo não foi afirmada. A avaliação
local usou o JD impresso na resposta, que contém menos casas decimais do
que o TLIST enviado. As diferenças chegaram a0,70m e2,89e−5m/s.

O diagnóstico reutilizou as seis respostas, sem novas consultas. Converteu
o texto decimal exato do TLIST para segundosTDB desdeJ2000 usandoDecimal:
`ET=(JD−2451545)×86400`. Conservou separadamente o JD impresso. A diferença
temporal chegou a40,29274µs. Avaliar no instante enviado reduziu os desvios
para≤4,6567e−7m e≤5,408e−12m/s nos trinta casos. Essa observação identifica
a perda de precisão temporal da avaliação anterior; não renomeia os modelos.

A revisãoB formaliza essa avaliação do instante exato enviado. Preservar
respostas, parâmetros e reciboA. Manter os limites1m e1e−5m/s. Exigir seis
alvos e cinco épocas por alvo, verificar hashes das duas fontes completas
e das respostas e registrar os dois nomes de fonte. O aceite é concordância
numérica dos vetores com os kernels locais fixados; não afirma identidade
dos pacotes publicados nem igualdade literal dos nomes de modelo.

Diagnóstico: `is6-principal-moons-horizons-time-diagnostic-20261111a.json`.
O procedimento usa fontes completas para que o arredondamento de JD perto
das bordas não provoque consultas fora dos recortes. A cena0.24 é preservada.
