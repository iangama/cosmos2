# Revisão G — RAM pelo objeto de processo retido

E20261114a permanece recusado com40amostras completas e a linha40falha.
DataDecoderService/CEF PID35824 nasceu e encerrou com códigozero. O leitor
psutil tomou17.633.280bytes de working set130,5267ms após o FILETIME que
posteriormente ficou associado à saída sinalizada. A evidência não contém
Wait imediatamente antes dessa leitura; não reconstruir tal prova depois.
Quatrohandles do aplicativo encerraramzero e o dono foi restaurado.
Fontes,ZIPs,JSONL e recibosE permanecem imutáveis e recusados.

O protocolo novo passa a consultar RAM pelo mesmo handle nativo cuja criação
foi retida. [GetProcessMemoryInfo](https://learn.microsoft.com/en-us/windows/win32/api/psapi/nf-psapi-getprocessmemoryinfo)
recebe esse handle e fornece working set/private usage; sucesso deve ser real.
GetProcessTimes declara o conteúdo de
[lpExitTime indefinido enquanto o processo não saiu](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes).
Por isso a prova de encerramento segue exigindo
[objeto sinalizado](https://learn.microsoft.com/en-us/windows/win32/procthread/terminating-a-process),
códigozero e FILETIME válido, sem inferir saída apenas de um campo intermediário.

Antes de cada consulta, registrar GetProcessTimes/GetExitCodeProcess/Wait0
do handle. Se ele já estiver sinalizado, conservar prova de saída0 em
completed_before_read e não chamar a API de RAM. Esse registro não recebe
bytes zero: é uma exclusão explícita de um objeto cujo encerramento foi provado.
O conjunto medido mais o conjunto encerrado deve cobrir exatamente o inventário
anterior, sem duplicatas. Raízes e identidades continuam obrigatórias.

Se não estiver sinalizado, executar GetProcessMemoryInfo uma única vez,
conservando todos os campos brutos, status e tempos; registrar novamente o
estado nativo no mesmo handle. Qualquer erro da API recusa a linha inteira,
inclusive na corrida de saída. Nenhuma leitura é repetida ou descartada.
Somar todos os working sets retornados com sucesso. Uma saída durante a
leitura fica explícita e seus bytes medidos permanecem nessa soma conservadora.
O campo exitTime de uma observação não sinalizada fica bruto e não é usado
para inventar a ordem da consulta. Saída nãozero ou identidade divergente
continuam recusando o ensaio inteiro.

A auditoria exige os tempos de RAM entre as duas observações nativas,
ambas dentro do inventário bruto. Valores projetados devem coincidir com
PROCESS_MEMORY_COUNTERS_EX. Provas sinalizadas devem coincidir exatamente
com a saída nativa final. O observador continua ativo; GPU,bootstrap,FPS,
cadência e limites de memória não mudam. Nenhuma mudança de produto científico.

Antes de nova coleta: fixture Windows com filho próprio medido vivo e excluído
depois de saída0, recusas offline de identidades/tempos/status/bytes e API falha,
preflight30novo e fontes/plano novos selados. Esse protocolo não prova picos
entre consultas nem processos com vida menor que a resolução do observador.
