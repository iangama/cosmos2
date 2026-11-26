# C2-14 — caminhos PDH e vida nativa do processo

A tentativa A fica recusada e intacta: 107 amostras completas, uma linha
recusada, primeira janela registrada e nenhuma aceitação de desempenho.
As duas sessões encerraram pelos oito handles com código 0 e a vista do dono
foi restaurada. O auxiliar CEF GPU PID39328 nasceu durante o ensaio; seus
gauges ainda mediram 5.656.576 bytes dedicados e 348.160 compartilhados. O
par desapareceu após a consulta, enquanto o handle ainda não estava
sinalizado no último testemunho arquivado. A linha não possui prova final
suficiente e não será reclassificada.

Antes de novos dados, a revisão B troca somente coletor/auditor/controlador
do perfil. Produto científico e interface 0.28.2 permanecem idênticos.
Limites de frames, memória, cadência, duração e cobertura permanecem.

Por padrão, o conjunto PDH deve ser idêntico antes/depois. Uma mudança só
é admissível nas duas situações abaixo, com pares dedicado/compartilhado
completos e sem mudanças em contadores de adaptador ou raízes:

1. Par removido: todos os valores selecionados foram realmente medidos com
   API/status/tipo válidos; seus timestamps locais, convertidos pelo offset
   nativo registrado, estão dentro da chamada; o handle retido tem criação
   idêntica, saída 0 e estado sinalizado. A saída deve ser posterior às duas
   leituras brutas e anterior à observação final. O PID não aparece no
   inventário final. Os bytes medidos continuam na soma, sem substituir por 0.
2. Par acrescentado: o PID pertence a um novo descendente retido, com criação
   comprovadamente posterior ao fim de toda a chamada PDH. Não atribuir zero
   a esse processo: registrar que nasceu depois da consulta. Novo contexto
   de GPU em um processo já existente continua causando recusa.

Uma remoção pode aguardar no máximo 250 ms apenas por testemunha de saída
no mesmo handle, preservando o primeiro inventário/histórico. Não repetir
gauge, descoberta, bootstrap ou linha. A duração total continua menor que
1 s. Espera expirada, saída não zero, evidência ausente, par parcial ou
qualquer outra mudança recusam toda a tentativa.

A auditoria reproduz essa regra diretamente dos corpos brutos, inventários,
históricos, status e FILETIMEs. A verificação offline inclui a recusa da linha
A original e fixtures explicitamente sintéticas para as exceções delimitadas.

O timestamp retornado por [PdhCollectQueryDataWithTime](https://learn.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhcollectquerydatawithtime)
refere-se ao primeiro contador recuperado. Cada [PDH_RAW_COUNTER](https://learn.microsoft.com/en-us/windows/win32/api/pdh/ns-pdh-pdh_raw_counter)
também registra seu horário local de coleta. Esta regra usa os timestamps
individuais e não presume que a consulta seja um snapshot atômico global.
