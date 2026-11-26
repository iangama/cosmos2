# Gravidade — critério numérico para uma massa isolada

Investigação pontual15/10UTC, antes da promoção dos instrumentos3.7.
REBOUND permanece fixado em5.2.2; IAS15 mantém epsilon1e-9.

O roteiro candidato de histórico apresentou dois avisos de iteração somente
no cenário de um corpo. A comparação com o controle mostrou o mesmo estado;
isso não bastava para aceitar o aviso. O código da versão fixada calcula o erro
de convergência global como variação de coeficiente dividida pela aceleração
máxima. Com uma massa isolada, os dois termos são zero: a divisão produz NaN,
impede a saída antecipada e acumula o contador que dispara o aviso. Essa é a
inferência do código, confirmada pelo ensaio isolado abaixo.
[Fonte REBOUND5.2.2](https://github.com/hannorein/rebound/blob/5.2.2/src/integrator_ias15.c).

verify-single-body-ias15.py comparou repouso e movimento inercial, cem tempos
alvo por caso. PRS23 acumulou201passos com máximo de iterações e um aviso por
caso. INDIVIDUAL ficou com contadorzero e nenhum aviso; posições e velocidades
coincidiram exatamente com PRS23 e com a referência inercial nesses ensaios.
Não se aplica esse resultado a corpos sujeitos a outras forças.

O candidato3.7 usa INDIVIDUAL somente para uma massa ativa, gravidade básica
pontual, sem forças adicionais. Com várias massas, conserva PRS23. Não escolhe
o critério a partir da presença de sondas, gráficos ou gravação. Não altera a
dependência ou o integrador nem descarta avisos por filtragem no produto.

verify-single-body-session.py passou criar/editar massa/estado, adicionar/
remover uma segunda massa, guardar/restaurar e migrar checkpoint3.6. O maior
desvio de posição contra movimento inercial foi4,441e-7m; velocidade exata e
nenhum aviso. A migração preserva fase/referências e registra explicitamente
PRS23→INDIVIDUAL. Um checkpoint declarado3.7 com critério antigo para uma massa
é recusado antes de instalar estado. P128 continuaPRS23. A jornada candidata
de histórico passou novamente fixture/Atlas/single, sem avisos.

Provas: evidence/single-body-ias15-check.json,
evidence/single-body-session-check.json e evidence/history-session-prototype-check.json.
Código ainda candidato em output/c211-history-staging; a presença destes
ensaios não comprova promoção nem jornada nativa do produto3.7.
