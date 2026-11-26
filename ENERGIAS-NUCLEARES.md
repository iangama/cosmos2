# Energias nucleares e limiares — contrato prévio

FatiaC2-18,13/10/2026. Instrumento de referência AME2020 independente da
evolução da bancada: energiasQ, separaçãoSn/Sp/S2n/Sα e limiares de reações
com alvo em repouso. Liga-se ao acervo e aos palcos existentes. Não inferir
taxa, seção de choque, meia-vida, deposição ou estabilidade só pelo sinalQ.

Massas: estados originais AME2020, sem isômeros/excitação. Usar excessos de
massa tabulados emkeV e aritméticaDecimal para somasQ; A eZ precisam conservar
em reações fortes/eletromagnéticas. Convenção de átomos neutros; n é partícula
livre eγ tem massa de repouso0. Elétrons se cancelam na contagem deZ, mas as
energias de ligação eletrônica fazem parte das massas neutras: não alegarQ
exato de íons totalmente despidos sem correção. Mesmo estado repetido é a
mesma variável de massa, somar coeficientes antes de propagar erro.

Restenergy para cinemática: A·u·c²+ME, comu·c²=931494.10242keV da avaliação
AME2020 fixado como conversão. Q usa apenasME quandoA conserva. Coeficientes
de massa com valor/uncertainty ausente permanecem desconhecidos; flags# e
resolução de impressão são próprias de cada termo. σQindep por somaquadrática
dos coeficientes, declarando correlações não disponíveis; não chamar esse
resultado de incerteza completa da avaliação. Incerteza da conversãouc² não
propagada nos limiares/cinemática; fonte de massas é registrada na exportação.

Dois incidentes (projétil+alvo massivo emrepouso), produtos com massas positivas
e fótons de massa0. Limiar cinemático relativístico paraQ<0:
Tlim=[(ΣEf_rest)²−(Ea_rest+EA_rest)²]/(2EA_rest)
=−Q·[2(Ea_rest+EA_rest)−Q]/(2EA_rest).
ParaQ≥0, limiar cinemático0; isso não elimina barreiraCoulomb nem regras
quânticas/taxa. Exibir também aproximação não relativística
−Q·(1+Ea_rest/EA_rest), mantendo nomes/convenções separados. γ incidente é
permitido, γ como alvo é recusado. Energia do projétil0–100MeV altera energia
disponível no centro de momento, sem alteração deQ ou massas de referência.
Não desenhar posições nucleares clássicas ou evento falso de reação.

Nove exemplos: D+T→He4+n; D+D→He3+n; D+D→T+H1; D+H1→He3+γ;
He3+He3→He4+2H1; Li7+H1→2He4; C12+He4→O16+γ; N14+n→N13+2n;
C12+γ→3He4. Editor declarativo de projétil/alvo/produtos, conservandoA/Z,
com IDs originais e contagens limitadas. Separações do estado selecionado
consultam massas do remanescente e das partículas; remanescente ausente não
vira energia0. Sn/Sp negativos não fornecem taxa de emissão.

Salvar/retomar seleção da reação/energia/núcleo, com hash/geração; exportar
JSONlocal incluindo termos/flags/σindep/convenção/fontes/resultados. Referência
não depende dos gates de atuação dos palcos. Não promover instrumento a
solver de redes ou aceite completoC2-18.

Critérios antes da implementação:
- NoveQ conferidos por coluna de massa atômica independente e NNDCQCalc2020,
  tolerância pela resolução publicada de cada resposta. Manter desvios reais.
- Limiar relativístico contra invariantes de energia/momento e solução
  independente; varrer abaixo/no/acima do limiar, compararaproximaçãoNR eγ.
- Mesmo estado repetido/cancelado tratado por coeficiente líquido; σindep
  conferida por derivadas independentes. Flags# e remanescentes ausentes claros.
- Inputfora de domínio, ID inexistente, A/Znão conservados e alvoγ recusados
  sem mudar seleção/sessão/cena; persistência/geração/export reais verificados.
- UIEdge/720 eCEFnativo, controles/cliques/modelo legível/zeroJS e imagensrevistas.

Referências primárias: AME2020 deNUCLEOS/F74; [NNDCQCalc](https://www.nndc.bnl.gov/qcalc/)
usaAME2020 e informa não incluir covariâncias; [LBL reações](https://www2.lbl.gov/abc/wallchart/chapters/07/0.html)
conservaçãoA/Z/energia/momento; [UCSD Física200A §15.7.3](https://courses.physics.ucsd.edu/2009/Fall/physics200a/LECTURES/CH15.pdf)
equações15.177–180 derivam limiar de alvofixo pelo invariante (energia total,
subtrair repouso do projétil para obterT). Não copiar longos trechos dos textos.

Recibo independente nndc-qcalc-reference.json com consultas/respostas originais.
Há diferença relevante no limiarN14(n,2n):NNDC11314.175keV versus nosso limiar
relativístico derivado11317.829292keV (NR11313.560059keV). Numericamente a
respostaNNDC coincide com−Q(1+Ea/(EA+Q)), uma inferência de uma resposta, sem
prova do algoritmo do serviço. Não forçar igualdade alterando a cinemática
nem chamar o desvio de incerteza da fonte. CompararQ comNNDC e limiar com a
derivaçãoinvariante. C12(α,γ)O16 NNDC arredondaQ a0,1keV eerro a0; não importar
esse zero como erroAME, pois a tabela original preservaσnãozero.

Implementado em13/10: app/nuclear_energies.py, UI/nuclear-energy.*, API dedicada.
Editor conservaA/Z e exige2–8partículas finais, no máximo4da mesma espécie;
2→1 recusado pois exigiria tratamento de ressonância, sem limiar contínuo.
σ do limiar propaga linearmente as massas independentes; massa do fóton é
fixa, não uma variávelAME. Perto deQ=0 a propagação por trechos é limitada.
Conversão fixa e covariâncias ausentes seguem explícitas. Energia incidente
altera a curvaCM sem mudarQ ou identidade da reação. Exportação real emuser/exports.

verify-nuclear-energies passou noveQ contra colunaatômica/NNDC e limiares
contra invariante independente,14separações e16entradas inválidas; também
derivadas da incerteza, cancelamento/repetição de massas e persistência/geração.
Diferença máxima entre Q pelas colunas originais0,00056128keV, dentro da
resolução impressa combinada. As incertezas retornadas peloNNDC também diferem
da propagação independente dos excessosAME; ambas ficam registradas, sem
atribuir causa não demonstrada. ExemploD+T:σindep0,00047194keV versusNNDC0,00015.
Limiarγ+C12:7277,11486210keV versusNNDC7277,11485, diferença preservada.
UIEdge eCEF nativo passaram seleção/editor/energia/limiar/save/load/export,
flags, ausências, recusa sem mutação e cena preservada; zeroJS e720semoverflow.
PNGEdge limiar/720 e nativosDT/estimativa revisados, legíveis. Fatia concluída;
avaliar o escopoC2-18 completo antes de atribuir seu aceite.
