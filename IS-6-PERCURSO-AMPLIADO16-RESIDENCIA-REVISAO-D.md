# Revisão D — identidades com histórico nativo retido

A/B continuam recusados e intocados. O diagnóstico rápido na sessão nova
identificou utilitários Chromium ProcessorMetrics, Unzipper e DataDecoder,
com várias saídas0 comprovadas. O probeB também publicou FILETIME0 em
algumas observações: GetExitCodeProcess pode preceder a finalização nativa.
Essas observações não provam horário de saída. Nenhuma será corrigida no
recibo executado; a revisão nova exige handle sinalizado, código e tempos.

Antes do próximo perfil, iniciar um observador Toolhelp a100Hz nominal,
retendo handles de motor/servidor/descendentes e registrando criação,
ascendência temporal, caminho, saída e cadência real. Não exige admin ou
debugger. Windows conserva a identidade enquanto o handle fica aberto:
[referência Microsoft](https://devblogs.microsoft.com/oldnewthing/20110107-00/?p=11803).
Saída só é final com WaitForSingleObject sinalizado, GetProcessTimes válido
e código0. Código0 com FILETIME0 não recebe horário ou duração inventados.

Uma entrada Toolhelp de processo já conhecido e encerrado pode ser resolvida
pelo handle original e registrada como encerrada. Desconhecido, reuso,
parentesco incerto, órfão vivo ou saída nãozero continua recusando tudo.
Conservar a entrada bruta e a prova nativa; nenhum retry apaga uma linha.
O histórico não garante observar processos inteiros entre dois polls; essa
limitação fica explícita, e qualquer candidato não resolvido continua erro.

Processos próprios podem nascer/encerrar durante as dez cenas. O cenário
científico e a confirmação nativa permanecem fixos nos primeiros66registros
completos de cada janela; o total de processos e os caminhos PDH podem
variar entre registros, desde que cada identidade/caminho/tempo seja
auditável. Não exigir que auxiliares Chromium tenham a mesma duração que
uma janela de60s. Toda mudança é registrada e auditada contra o histórico.

RAM conserva as identidades vivas do inventário anterior e leituras reais;
processo que encerra antes de sua leitura deRAM recusa a linha inteira.
O inventário posterior pode diferir somente por nascimento/saída comprovada
no intervalo observado. O conjunto PDH continua idêntico antes/depois de
cada consulta; caminhos novos ou inválidos dentro dela continuam recusa.
PDH pode incluir contadores expostos de qualquer identidade própria retida,
mesmo após a saída, até o WDDM remover a alocação. Nunca somar outroPID ou
atribuir GPUzero a um PID sem contador. Registrar os não expostos.

Os limites16,7/25/50/100ms,8GiB RAM e5,5GiB WDDM, dez cenas,30s+60s,
66registros, fases reconhecidas, brutos completos,4saídaszero e restauração
do dono permanecem. Os picos são máximos das amostras, não máximos globais
entre amostras. O custo do observador integra o ensaio. Preparar regressões
de recusas e preflight antes de selar fontes e executar novos dados.

O debugger foi validado separadamente com processos de fixture, incluindo
uma saída7 deliberada. Ele altera o escalonamento e não será usado para
aceitar quadros normais do produto. WMI de processos retornou acesso negado;
nenhuma permissão do Windows foi alterada.
