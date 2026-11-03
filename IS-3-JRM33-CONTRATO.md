# IS-3 — JRM33 em staging, antes da ligação a Júpiter

O [modelo original](https://doi.org/10.1029/2021JE007055) fornece uma solução
de grau30; termos até13 são melhor determinados e18 permitem exploração
com resolução menor dos coeficientes altos. A primeira implementação adota
13 por padrão, acompanhando a [referência comunitária LASP](https://lasp.colorado.edu/mop/missions/juno/community-code/).
O número33 identifica a missão até o perijove33, não o grau do harmônico.

## Dados e convenções fixados

Usar o arquivo original [JRM33.MOD noPDS](https://pds-ppi.igpp.ucla.edu/data/JNO-J-3-FGM-CAL-V1.0/DATA/MODEL/JRM33.MOD),
30.232bytes,SHA1960a025ea38d8ee604fb69882b95484df55c31c2e5ba3d1c1ebd011af7170be.
Guardar rótulo/SIS junto da fonte. O [SIS addendum2](https://pds-ppi.igpp.ucla.edu/data/JNO-J-3-FGM-CAL-V1.0/DOCUMENT/SIS-addendum-2.pdf)
define coeficientesSchmidt emnT e o campo de resolução. A resolução diagonal
não é variância nem incerteza local. Manter960coeficientes internosg/h e
três externosG/H separados; a primeira síntese usa apenas os internos.

Confirmar todos os coeficientes usados em13/18 com os valores explícitos da
referênciaPSH, fixada no commitcf7e712e39a45a14905d13d21978043026089a4e.
Código/licençaGPL-3.0/citação PSH ficam preservados como referência emstaging.
A síntese usa a recorrênciaSchmidt própria já existente no projeto, com
limites adequados ao grau18. O algoritmoPSH será executado separadamente
como oráculo após inspeção do código baixado.

Coordenadas: SistemaIII(1965) destrógiro, raio de referência71.492km,
colatitude0..π e longitudeLESTE0..2π. SaídasSI emTesla. É um modelo
interno estático da época2019; variação secular não é adotada. Campo externo
e correntes do disco continuam componentes distintos. Não equivaler um
estadoB=0 à ausência de dados. A associação aIAU_JUPITER/J2000 na época da
cena exige contrato próprio de orientação antes de integrarAPI/UI.

Domínio numérico desta bancada:1≤r/Rj≤20, com tolerância de arredondamento
de2e−15relativa nas bordas. Esse limite é escolha do instrumento para a
componente interna, sem afirmar precisão do campo total em toda essa região.
Grau18 é leitura exploratória identificada; grau1 é referência didática.

## Verificações antes de aceitar a síntese candidata

Fixar hashes de dados,fontes,oráculo e limites antes da execução. Comparar
13/18 em quatro raios(1;1,5;2,5;10Rj),cinco colatitudes(0,π/6,π/2,5π/6,π)
e quatro longitudes(0,π/2,π,3π/2):160casos. Limite prévio de1e−4nT por
componente versusPSH em coordenadas esféricas e cartesianas. São códigos
distintos com os mesmos coeficientes, não precisão observacional.

Também conferir grau1 por fórmula cartesiana analítica, lei1/r³ para esse
recorte, longitude periódica e vetor cartesiano único nos polos. Calcular
potencial e compararB=−gradienteV por stencil independente de cinco pontos
com passo1000m em pontos interiores ao domínio; limite1e−3nT/componente.
Recusar booleanos, não finitos, vetores inválidos, raio fora do domínio e
graus não adotados. Nenhum teste modifica produto/Atlas/sessões do dono.

O aceite dessa bancada não liga o campo à rotação/posição deJúpiter599,
não simulaLorentz ou plasma e não valida campos das luas. Esses percursos,
camadas visuais e perfis próprios permanecem exigidos nas respectivas fatias.
