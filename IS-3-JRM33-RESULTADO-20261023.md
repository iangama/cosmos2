# IS-3 — JRM33 ligado a Júpiter e ao relógio da cena

Dados originais PDS adquiridos emJRM33.MOD (30.232bytes,SHA1960a025ea38d8ee604fb69882b95484df55c31c2e5ba3d1c1ebd011af7170be).
O parser preserva960coeficientes internos e três externos, com resolução
diagonal separada de incerteza.13/18 usam195/360coeficientes bitiguais aos
valores explícitos da referênciaPSH, commitcf7e712e39a45a14905d13d21978043026089a4e.
Código/licençaGPL-3.0/citação dessa referência foram preservados; a síntese
local usa recorrênciaSchmidt própria do projeto, sem chamarPSH no produto.

Recebos de dados: evidence/is3-jrm33-reference-acquisition-20261023.json,
is3-jrm33-pds-model-20261023.json e is3-jrm33-coefficients-20261023.json.
O arquivo éJRM33.MOD em maiúsculas; tentativasTXT/minúsculas retornaram404
e continuam registradas. O rótuloPDS anunciaPRODUCT_ID=JRM33.TXT, mas o
arquivo real éMOD. Não repetir descoberta já resolvida.

A candidata científica está emoutput/is3-jrm33-staging/jrm33.py; dados em
jrm33-coefficients.json e fonte original em pds-cache. Contrato prévio:
IS-3-JRM33-CONTRATO.md. A síntese aceita foi depois copiada para a candidata; ver ligação abaixo.

`evidence/is3-jrm33-check-20261023a.json` accepted=true:

-160casos para13/18, raios1;1,5;2,5;10Rj,pontos esféricos/cartesianos,
 erro máximo de componente contraPSH9,31323e−10nT(limite1e−4).
-Grau1 analítico: erro relativo≤9,68e−16 e lei1/r³ confirmada.
-B=−gradienteV por stencil de cinco pontos/passo1000m em seis casos:
 erro máximo2,29629e−6nT(limite1e−3).
-Polos/período de longitude passaram; nove recusas de domínio/tipo.
-Fontes,oráculos,dados eowner preservados; tudo arquivado antes da execução.

Mapas científicos foram gerados e revistos emoutput/is3-jrm33-figures-20261023
(PNG/PDF/SVG,grade eprocedência). Esfera de1Rj,2701pontos: módulo grau13
amostrado1,78234–18,54950Gauss; diferença vetorial18vs13 atingiu13,52484%
nessa grade. São recortes de modelo; não são máximos globais comprovados,
barra de incerteza, observações ou mapa sobre elipsoide achatado.

## Orientação e ligação já verificadas

Contrato prévio: IS-3-JRM33-ORIENTACAO-CONTRATO.md. A documentaçãoLASP v12
associa S3RH aIAU_JUPITER; longitude leste, Y=Z×X e colatitude do norte.
Os oito grupos completos de parâmetrosJúpiter599/sistema5 são numericamente
idênticos emPCK00010 ePCK00011, inclusive os15ângulos de nutação/precessão.
Recibo evidence/is3-jupiter-orientation-acquisition-20261023b.json.
A tentativaA ficou incompleta porque o parser incluiu exemplos textuais;
B lê somentebegindata. Nenhum kernel antigo foi carregado no produto.

Wrapper output/is3-jrm33-staging/jupiter_magnetism.py e cópia na candidata
usam posiçãoEVOLUÍDA deJúpiter599, ET0+t, SistemaIII→J2000→GALACTIC.
Centro é somado somente à posição; vetoresB não recebem translação.
Hashes e parâmetros efetivos da pool são conferidos; concorrência dePCK
binário recusada. Aplicação adota2000-01-01 a2030-01-01 inclusive,
raio geocêntrico esférico1..20Rj, sem afirmar domínio observacional do
campo total. Os coeficientes continuam estáticos da época2019.

PASSOU evidence/is3-jupiter-field-check-20261023a.json:

-72leituras: seis épocas × seis pontos × graus13/18.
-MatrizesPCK10/PCK11 bitiguais; construção independente por ângulosIAU
 com erro máximo7,92833e−12(limite prévio1e−10).
-Ortogonalidade3,33067e−16; posição ida/volta66,326µm; normaB2,16841e−19T.
-Direção inercial fixa: longitude leste decresce, taxa870,5360008°/dia.
-Evolução6h, centro atual, translação, polos/longitude0/360 e15recusas,
 incluindo parâmetro efetivo da pool conflitante. Fontes/pool/owner intactos.

## Worker, API e UI da candidata

Antes de acrescentarJRM33, a candidata inteira foi arquivada em
output/is3-tides-product/before-jupiter-field.zip. Registro de preparação:
evidence/is3-jupiter-integration-prepared-20261023.json. IS12/instalado não
foram alterados. Geração da candidatais3-body-fields0.3 inclui sínteses,
coeficientes, PCK/LSK e recibos. CheckpointIGRF anterior abre como geração
mudada, com fonte/fase preservadas. Parâmetros/leituras da consulta são locais
e não são persistidos no checkpoint; recargaCEF limpa derivados.

Nova rota /api/solar/jupiter-field, comandojupiter_field e formulário no
painel de corpos: raioRj, latitudeplanetocêntrica, longitudeLESTE e grau.
Metadados mostram época da cena, grau13padrão/18exploratório/1dipolo,
coeficientes2019 estáticos, componente interna e incerteza não propagada.
Só599habilitado; nenhuma força aplicada aos centros neutros.

PASSOU evidence/is3-jupiter-worker-20261023a.json:29recusas de pedido/fase,
graus, regressõesIGRF/maré, evolução, restauração exata, tokenantigo e
checkpointIGRF copiado preservando a origem. A limpezaCSS posterior só
acrescentou apresentação de leitura; a fonte realmente executada está nozip.

PASSOU evidence/is3-native-jupiter-20261023a.json: leituraCEF=API, época/
centro atuais, controles100/150%, grau18/polo, regressãoEarth,15recusasHTTP,
evolução/amostrafixa, salvar/restaurar, limpezaCEF, limite2030 e coeficientes
2019 explícitos. Atlas/época/fase saudável da candidata restaurados;
IS12, fontes eowner preservados. Exemplo a1,5Rj,latitude0°,longitudeLESTE0°:
|B|=104.075,39nT. Isso não é precisão observacional.

Capturas100/150foram revistas: textos legíveis, mas a captura150original
não mostrou o marcador. Diagnóstico dirigido sem editar produto
scripts/diagnose-solar-repeat-view.py guardou quatro focos alternando100/150,
com mesma posição/up/anchor, raio eEnabled; capturas posteriores mostram o
marcador em ambas. Não atribuir causa sem prova nem declarar aceite visual
final. Marcador continua ciano ampliado; não há vetorB/linha/mapa nativo,
Lorentz, plasma ou campo total da magnetosfera.

## Próxima ação autorizada

Antes das novas camadas nativas, concluir o diagnósticoC2-12/J exigido no
plano: preflight curto na candidataJ com coletores-diagnostic e mesmos
predicados; depois eventual perfil controlado próprio. Não executar coletorEM
contra a candidata solar e não herdar perfisIS12 para os campos novos.
Maré/IGRF/JRM permanecem emoutput/is3-tides-product, armazenamento próprio,
sem promoção. Ler C2-12-DIAGNOSTICO-J-20261022.md apenas na fatia final ativa.
