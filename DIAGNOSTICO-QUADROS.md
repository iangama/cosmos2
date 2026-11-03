# C2-06 — pausas na regressão do motor

14/10/2026. Este diagnóstico impede o aceite completo do marco; não altera
os critérios de desempenho nem substitui tentativas rejeitadas.

A geração científica3.4.0 passou nos três percursos P128 do motorc308114c…,
com zero intervalos>100ms e pausaAPI<=36,944ms. Na regressão g0labels do mesmo
motor, os três percursos Atlas passaram; Atlas/P32background teve3intervalos
>100ms e P32visível teve5, pior1057,719ms. p95/p99 agregados continuaram dentro
da meta; isso não apaga os intervalos longos. Dados completos e failure.json
preservados. G0a37f248e… aprovado anteriormente permanece histórico.

Um observador auxiliar só normalizou o ritmo antes de resume (pausado,t=0),
e foi encerrado antes dos últimos percursosP32. As pausas ocorreram também
sem esse observador. Não há evidência de que ele seja a causa.

Diagnóstico independente60s com a mesma cena P32 em movimento, sem coletor
WDDM: frame-diagnostic-first.json. Uma pausa225,461ms foi reproduzida; o
RTT do motor atingiu210,293ms. PerformanceObserver do CEF não registrou
longtask; a função assíncrona updateState demorou109,7ms, incluindo rede.
CPU total do motor no intervalo do RTT longo foi62,5ms em~333ms de parede:
isso sugere espera, sem identificar ainda o local ou o recurso. CPU de todo
o processo inclui outras threads e não é uma medida da thread gráfica.

Windows Performance Recorder CPU/GPU recusou a política0xc5585011. Nenhuma
configuração de segurança/política foi alterada e não houve elevação. Segue
alternativa local: marcações de parede no motor, opt-in e com buffer limitado.

stage-tracing.patch adiciona duas APIs de desenvolvimento, desligadas por
padrão: cosmos2BeginStageTrace / cosmos2EndStageTrace. Registra totais/máximos
por etapa e até512intervalos>=50ms, com truncamento explícito. Abrange preSync,
servidor, callbacks de módulo, atualização da cena/renderer/interface/shader,
render, overlays, postDraw e intervalo entre quadros fora do OpenSpaceEngine.
Regiões aninhadas se sobrepõem; seus tempos não devem ser somados como custos
independentes. O intervalo externo inclui SGCT/swap/apresentação/eventos, sem
ser tempo de execução da GPU. Desligada, não coleta relógios nem dados.

Próxima captura usa diagnose-frame-hitches.py --stage-tracing, CPU dos PIDs
atuais e longtasksCEF. Comparar a etapa lenta com o intervalo bruto/RTT; depois
isolar apenas a região responsável e validar uma correção concreta. Não
repetir nove percursos apenas para escolher uma janela sem outliers.

Build de diagnóstico486dc343…887fd79 compilado/estagiado, mantendo os hashes
científicos3.4.0. Captura stages90s após reinício:6751intervalos, máximo28,456ms,
RTT40,856ms, zero longtasksCEF/zero>100ms. Região mais lenta foi postSync50,62ms
fora do intervalo bruto final; intervaloexterno máximo23,92ms. Isso não prova
uma correção: ainda não reproduziu a pausa neste processo novo. Próximo ensaio
recria128/32massas seisvezes para verificar dependência de acúmulo/tempo de uso,
e depois mede120s. InventárioCPU do script usa PIDsatuais, sem reutilizar G0.

Após seis ciclos128→32, stageschurn120s reproduziu269,423ms no intervalo64s;
a região engine_postSync consumiu256,830ms. As demais etapas ficaram abaixo
de3,783ms, e o intervalo externo abaixo19,173ms; zero longtasksCEF.
O detalhamento seguinte divide sincronização/scripts, assets e console, além
de cada execuçãoLua, gravação do log (inclusive abrir/fechar) e retornoWS.
LogScript upstream usa std::ofstream em append por script; o arquivo observado
já tinha34MB. É candidato deIO, não diagnóstico concluído. Captura original e
backups preservados; nenhuma atualização científica ou parâmetro do solver mudou.

Causa localizada em stagedetail120s/249cb9fa…: frame170,386ms em21,247s;
script_log_open_write_close155,808ms, script_run157,094ms, postSync157,425ms.
Lua máxima23,261ms, callback40,044ms, render3,326ms; zero longtasksCEF.
Esse evento localiza a espera no log síncrono, sem atribuir motivo ao sistema
de arquivos/antimalware por falta de rastreamento de kernel.

Correção implementada, ainda aguardando validação nativa: AsyncScriptLog em
header próprio, consumidor em thread separada e fila de até8MiB mais uma
entrada em drenagem. Mantém ordem e todo o conteúdo aceito. O arquivo abre
no worker e faz flush por entrada; fecha ao drenar no desligamento normal.
Fila cheia ou erro deIO conta entradas omitidas e comunica erro, sem fingir
um log completo. A fila não é checkpoint; histórico físico e salvamento
continuam no Session/worker. Nenhuma constante, tolerância ou massa mudou.

cosmos2ScriptLogStatus expõe accepted/written/dropped/queued_bytes/failed e
maior duração de escrita no worker. Regiões do profiler permanecem apenas
na thread principal; não há gravação concorrente no seu buffer. A região
script_log_submit mede somente a entrega à fila. Linuxg++/NDEBUG passou1001
entradas em ordem, produtor<0,1ms com sink bloqueado, drenagem/fechamento,
limite e falha deIO explícitos. TesteWindows e build nativo estão em andamento.
A aprovação só virá com diagnóstico após churn, zero perdas/erro, contrato de
ordemUTF8 no arquivo, jornadas de produto e novos percursos formais.

Contrato da fila reforçado para1024entradas além do teto8MiB de texto, inclusive
strings vazias (sem crescimento ilimitado por metadados). WindowsMSVCRelease
PASSOUde novo: submit0,0707ms/1001entradas, ordem/drain/erro/overflow/limite de
entradas vazias. HeaderSHAaa7bff07…e477. Buildasyncfinal e SDKmanifesto passaram;
estágio/validaçãoemapp seguintes ainda não são um aceite de desempenho.

Validação cfcd7fff…3eb218d6: asynclog120s após12recriações128/32 PASSOU
8994intervalos, máximo28,287ms/zero>100ms, RTT36,893ms e zero longtasksCEF.
Entregaàfila máxima0,1212ms; escrituras no worker até3,4348ms. Statusaceitou
4976novasentradas, dropped0/failedfalse/filaesperando0. accepted−written=1
na consulta é a própria consulta já aceita e ainda em drenagem; a fila de
espera não inclui a entrada que o worker está escrevendo.

verify-native-script-log passouUTF8/aspas/backslash e ordemexata noarquivo,
sem mudar física. O aplicativo encerrou normalmente e conservou os marcadores
ordenados após fechar/drenar o log. Fonte/teste/header/binary têm hashes nos
recibos. Isso valida a correção dirigida; faltam os perfis formais e jornadas
no build definitivo antes de aprovarC2-06. Novos rótulos de coleta previstos:
c206p128c e g0async. Nenhuma tentativa rejeitada foi removida.

Jornadas registry/atributos/edge/órbitas/experiências noEXEfinal passaram,
assim como P128c206p128c completo/auditado (p99máx24,600ms/zero>100ms).
G0g0async foi interrompido pela preferência temporária de uso da tela; depois
revogada explicitamente pelo dono. G0g0async2 teve CounterApiError do coletor
GPU na terceira rotaAtlas; as duas anteriores passaram, mas não houve aceite
global. O erro antigo não identificou o contador individual; não atribuir
origem ao motor/processos externos sem evidência. Novo coletor preserva todo
path/status/erro, mantém recusa de QUALQUER inválido e passou teste sintético
de falha mais leitura real3amostras. G0g0async3 mede as nove rotas novamente.
Essas falhas de coleta não são uma nova causa de hitch gráfico demonstrada.
