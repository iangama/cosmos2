# Residência0.27.0 — ensaios recusados e diagnóstico

Não há aceite de residência geral. Produto científico permanece inalterado;
V1 segue7/21, IS6 incompleto e K5A original recusado.

A20261113a conservou102amostras completas e uma linha falha. O coletor2
normalizou uma publicação intermediária sem atlas_initial na entrada16.
Uma janela Atlas terminou:4508intervalos úteis/60,14s, mediana13,32ms,
p9514,67ms,p9915,21ms,máximo27,13ms,zeroacima100ms. São dados parciais
sem aceite das dezjanelas. Diagnóstico próprio aponta fontes/brutos porSHA.
Quatrohandles encerraramzero;hostA recusou Upescalar. Retorno conferido
separadamente:campos exatos e deltaUp1,665e-15 dentro do orçamento1e-12.

RevisãoC conserva respostas deAPI cruas e registra projeções indisponíveis
somente em prepare/transition/cleanup. Nenhum dado dePDH/RAM/quadro sai da
trilha. Treze recusas offline e preflightC de trêsamostras foram aceitos.

B20261113b conservou53amostras completas. A54ªfalhou em inventory_after:
PID11208/PPID38224 retornouWinError87 aoabrir oprocesso. A identidade não
foi comprovada; o ensaio inteiro ficou recusado. Não há prova para atribuir
aCEF,crash ou reuso dePPID. Os quatrohandles encerraramzero e a vista do
dono voltou,sem cleanup_failure. Não repetir A/B automaticamente.

Um diagnóstico próprio de120s/2Hz conserva os nomes/PPIDs deToolhelp em
caso de recusa de identidade. Não medeGPU, não altera a cena e não relaxa
as regras. Consultar evidence/is6-expanded-process-diagnosis-20261113a.json
para seu estado real antes de prosseguir. Próximo passo:resolver atribuição
decriação/saída antes de preparar qualquer novo perfil; preservar todos os
executores,ZIPs eJSONL originais. Backupv19 preparado, ainda nãoexecutado.
