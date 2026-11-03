# C2-12 — recusas J e contexto de CPU,22/10local (23/10UTC)

J128 c212j128a aprovado. Jpotencial c212jpota e nuvem c212jsrca recusados.
As fontes, dados brutos, archives e auditores permanecem preservados;
nenhum limite foi ampliado e nenhum recorte foi promovido.

Potencial: as três rotas passaram nos valores SI1089/128 e nos quadros.
A rota2 excedeu o limite API3000ms: numerico672ms/API3249.5413ms.
Todas as amostragens numericas ficaram abaixo do budget2s. O cronometro
formal inclui consulta do guard antes do POST e leitura/parse da resposta;
a diferenca API−numerico nao identifica sozinha a etapa responsavel.

Nuvem: tres rotas concluídas. Auditor independente conferiu integridade,
campos, referenciaDOP853(erro<=3.079e-5) eenergiaestatica(<=4.516e-12).
Taxa/quadros/uma pausa recusados: minrate0.732003752,p95max29.668990ms,
p99max64.788572ms,22quadros>100ms nas3rotas,pausamax250.4925>250ms.

Contexto medido nos contadores brutos de CPU (nao e prova de causa unica):
I aceita: CPUtotal84.6–85.1%,produto7.82–7.84cores equivalentes;
restante da atividade2.31–2.39cores equivalentes.
J recusada: CPUtotal93.8–96.2%,produto5.76–6.66cores equivalentes;
restante4.59–5.70cores equivalentes. As janelas sao aproximadamente60s.
Nao somar interrupt/DPC outra vez nem usar children_* para duplicarCPU.
O restante inclui outros processos/atividade do sistema e pequenas
 diferencas entre intervalos dos contadores. Nao identifica outro aplicativo.

Proximos passos limitados:3diagnosticos HTTP com mesmo fixture/grade/fontes/
64registros e budget2s,segmentando guard/headers/transfer/parse eCPUcontexto.
Conferir reinicio normal antes de escolher correcao. Nao repetir capturas
formais indefinidamente ou atribuir retrospectivamente a falha ao contexto.

Diagnostico current1:3POSTs completos com guard ficaram em
1482,6313/1439,8575/1334,3897ms; numerico719/672/516ms.
Guard6–15ms,transfer1,5–3,6ms,parse23–40ms; maior parte antesdosheaders.
Nao reproduziu a falha,sem atribui-la a uma etapa interna nao instrumentada.
CPUtotalconcurrente61–67%,produto~1,34–1,47coresduranteamostragempausada.
Jfechou normalmente;abertura nova e3diagnosticos fresh1pendentes.
Nenhuma alteracao em produto/config/runners.

Fresh1aposreinicionormal:API958,0499/943,7294/1074,0141ms,
numerico468/469/515ms,nenhumdisplayerror,fase/ownerpreservados.
MesmafonteJ/config/helper/fixture/33²/128/64/budget2s.
Uma repeticaoformalcontrolada dopotencialc212jpotb iniciada,commesmos
limites eguarddoauditor;Apermanece recusa. Semcausaexataestabelecida.

## Resultado da repetição e nova prioridade —23/10 UTC

`c212jpotb` TERMINOU INCOMPLETO, não está ativo e não foi aprovado.
A primeira rota passou nos quadros (p95 17,047249ms, nenhum >100ms).
As duas amostragens completas tiveram API950,447/973,858ms e numérico453/421ms.
Antes da segunda captura, o coletor GPU recusou a confirmação do cenário
nativo. O erro genérico não guardou qual predicado falhou nem o snapshot
rejeitado. O estado consultado após cleanup não prova o estado da recusa.
Preservar bruto e fontes; próximo diagnóstico deve registrar predicados e
snapshot no momento da falha, mantendo todos os critérios. Não iniciar outra
repetição formal sem resolver essa lacuna. `c212jsrcb` não foi executado.

O dono pediu revisão das quatro forças com exemplos e plano de integração
Sol/Terra/Lua/Júpiter. Relatório `RELATORIO-TESTES-FORCAS-20261023.md` e plano
`PLANO-INTEGRACAO-SISTEMA-SOLAR.md` governam o novo trabalho. A suíte científica
de 14 grupos passou na raiz, sem herdar aceite de desempenho para J.


## Diagnóstico preparado e testado23/10 — sem nova capturaJ

Foram criados forks dos coletores de potencial/nuvem com sufixo
`-diagnostic.ps1`, preservando os originais e todos os predicados de aceite.
No instante de uma recusa eles salvam JSON com snapshot completo, expectativas,
cada predicado, lista dos que falharam, razão, UTC, sessão e hash do coletor.
Uma falhaHTTP antes de obter estado também produz diagnóstico, com snapshot
nulo e sem fingir que houve confirmação. Diário/contadores continuam iguais.

TesteWindows offline `scripts/verify-em-gpu-diagnostics.ps1 -Label20261023b`
PASSOU39casos comparando as funções dos coletores antigos com os novos.
Toda mudança isolada dos predicados e a falhaHTTP recusaram como antes;
fixtures positivas passaram; as recusas guardaram o snapshot exato.
Recibo evidence/em-gpu-diagnostic-tests-20261023b.json accepted=true e fontes
arquivadas no recibo em-gpu-diagnostic-archive-20261023b.json. A tentativaA
conserva uma falha do próprio harness por colisão de nomes entre duas famílias
de fixture; corrigida usando contador único. Não foi falha de produtoJ.

Isso fecha a lacuna de instrumentação em fixtures, sem demonstrar a causa
histórica de c212jpotb. Antes de outro perfilJ, usar o novo coletor em um
preflight curto na candidataJ com label novo, verificar registro real e só
então apontar uma execução controlada para esse coletor. O launcher solar
está ativo neste ciclo: não executar o coletorEM contra ele nem tratar testes
offline como aceite nativoJ. Não repetir labels antigos, não promoverJ.

## Preflight real e repetição controlada —23/10, nova janela

A candidataJ original foi aberta comstart-c212-em-viewport-candidate.ps1;
fontes deproduto e motor coincidem comc212jpotb. Nenhuma edição emJ/I/F/G.
Preflightjpdiag20261023a: potencial passou nas três rotas, três amostrasWDDM
por rota. Recusa provocada(pausa real versus expectativaexecutando) guardou
snapshot real e somenteexpected_worker=false. Na partecloud o harness
enviou guards ao comando de pausa, recusados pelaAPI;Ageral permanece
accepted=false. Corrigido só o harness para seguir o protocolo existente.

Preflightjpdiag20261023b --familycloud PASSOU três rotas, nove amostrasWDDM
e recusa provocada comsnapshot exato/somenteexpected_worker. Não repetiu
o potencial já medido. Recibos em evidence/em-native-preflight-jpdiag20261023{a,b}.json.
Isso valida a instrumentação real e não identifica a causa de c212jpotb.

Quatro forks de runners/auditores com sufixo-diagnostic só substituem
identidades do coletor/própria fonte. Texto eAST voltam exatamente aos
originais ao reverter essas substituições; todos os limites, fixtures,
durações e cálculos são preservados. Fontes antes/depois arquivadas no
recibo evidence/em-diagnostic-profile-forks-20261023.json.

Sequência controlada preparada: potencialC(c212jpotc), depois nuvemB
(c212jsrcb), sem repetirJ128aceito. Driver run-em-j-diagnostic-profiles.py
para na primeira recusa/incompletude; estado vivo no recibo
evidence/em-j-diagnostic-profile-sequence-20261023.json. Consultar esse
recibo/log antes de retomar, sem abrir outra sessão concorrente.

### TentativaC e correção da chamada de memória

A sequênciaV1 parou noc212jpotc antes de registrar a primeira rota: helper
native_product_memory.py extraído emIS2 exige uma sessão explícita, mas o
runner herdado chamava product_memory() sem argumento. Ccontinua incompleto.
As169fontes configuradas foram recuperadas DEPOIS da execução e coincidem
com todos os hashes prévios; recibo source-recovered registra essa ordem,
sem acrescentar aceite ao bruto. Captura residual foi encerrada.

V2preserva helper, originais eV1. Só adiciona product_memory(session) nos
novos runners-diagnostic-v2, além dos nomes de coletor/fonte já declarados.
Reverter essas alterações recupera texto/AST originais; fixtures, limites
e critérios ficam iguais. TesteWin32 real passou três chamadas, quatroPIDs
exigidos e soma exata, em evidence/em-diagnostic-memory-call-20261023.json.
Nova sequência23/10b: potencialD(c212jpotd), depois nuvemB(c212jsrcb) só se
Dpassar. Recibo vivo em-j-diagnostic-profile-sequence-20261023b.json.
Não confundir Cparada porrunner com falha física/desempenho da candidata.

### Potencial D aprovado; nuvem B em medição

A captura `c212jpotd` terminou e a auditoria independente aceitou as três
rotas, com os critérios originais. Foram 4.499 intervalos por rota, sem
quadros acima de 100 ms. Os resultados máximos ou mínimos relevantes:

- p95 máximo: 17.152430 ms; p99 máximo: 18.306318 ms.
- Ritmo mínimo: 0.99818478 para 1 solicitado.
- Pausa máxima: 47.824 ms; API de potencial: 1029.187 ms.
- Amostragem numérica máxima: 516.000 ms.
- Soma RAM máxima: 1.2376 GiB; soma WDDM dedicada: 2.9917 GiB.

Recibo `evidence/native-em128-c212jpotd-review.json`, accepted=true; fontes
congeladas no archive próprio. As somas de memória podem repetir alocações
compartilhadas; não equivalem a memória física exclusiva. A permanece
recusada, B/C incompletas. Não há prova retroativa da causa da recusa B.

A sequência iniciou `c212jsrcb`, ainda sem aceite. O resultado D cobre
apenas o fixture declarado de 128 cargas, campo e potencial congelados;
não aprova a nuvem de 10 mil partículas nem os campos planetários.

### Nuvem B aprovada; sequência finalizada

`c212jsrcb` também terminou e passou na auditoria independente, com os
critérios originais. As três rotas tiveram 4.499 intervalos cada e nenhum
quadro acima de 100 ms. p95 máximo: 18,353841 ms; p99: 19,403504 ms.
Ritmo mínimo: 1,00256677 para 1 solicitado; pausa máxima: 201,174 ms.
Soma RAM: 1,2318 GiB; WDDM dedicada: 2,9793 GiB, sujeitas às ressalvas já
registradas de páginas/alocações compartilhadas.

A referência DOP853 independente passou nos pontos adotados, com erro
normalizado máximo de posição/velocidade abaixo de 3,477e−5 e erro relativo
de energia abaixo de 1,197e−11. Fontes, dados, ODE e recursos constam em
`evidence/native-emcloud-c212jsrcb-review.json`. A sequência23/10b terminou
completed=true/accepted=true. O launcher J foi encerrado normalmente.

Isso fecha os perfis J pendentes nos fixtures declarados, preservando os
resultados A/B/C anteriores. Não demonstra a causa histórica da recusa B,
não promove o instalado e não transfere desempenho para campos planetários.
A próxima fatia IS-3 pode seguir para geometria e jornada nativa próprias.
