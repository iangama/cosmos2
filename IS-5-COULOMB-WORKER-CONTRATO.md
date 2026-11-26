# IS5 — artefato e trabalhador Coulomb, contrato28/10/2026

Preparação anterior ao código. Implementar somente após aceite da evolução.
Arquivos novos em `output/is5-coulomb-worker-staging`, sem editar os
trabalhadores aceitos. Reutilizar isolamento, selos, transações e ramos CNO-II
por mérito, com tipos de protocolo/checkpoint próprios e sem migração tácita.

Configuração completa: parameters, acting, channel_switches, mode,
include_coulomb e include_screening. Modes prescribed/isochoric;
screening=True com Coulomb=False recusado. Base beta NUBASE fixa, Q atômico
AME2020, Be7EC SFII. Cada artefato arquiva fonte Solar e geração completa
da EOS e rede. Cenário e referência completa usam MESMA EOS, screening,
parâmetros e modo, variando somente gates de reação.

Criação/configuração/load/restart recalculam tudo antes de publicar um
artefato novo; falha preserva integralmente o último aceito, preferências,
token e revisão. Tipos antigos CNO-II/ppIII/ppII recusados. Restauração em
processo novo e digest de cenário/referência integralmente conferidos.

Sonda0..240:16 frações/18 fluxos/extensões, T/P/U/Cv, energia nuclear/ν,
captura/aniquilação e−, U_Coulomb e18 fatores adicionais de screening.
Os cinco canais de um corpo (quatro beta+EC) mantêm fator1; o valor não
substitui a lei de plasma EC. Prescrito expõe a EOS naquele T, mas não
declara conservação entre depósito nuclear e reservatório de T fixo.
Curvas completas sob requisição, resumo público pequeno e leitura exata
dos241 nós, sem fingir integração em tempo real.

Não herdar o timeout35s do cliente antigo: a nova EOS tem custo maior,
medido nos testes científicos. Antes de aceitar o trabalhador, fixar e
testar prazo de cálculo/ack suficiente para a condição padrão, com limite
explícito. Timeout de transporte não pode publicar um cálculo tardio como
se tivesse falhado atomicamente. Se houver processo de cálculo adicional,
ele precisa terminar antes do ack de falha e no fechamento do trabalhador.
Não prometer cancelamento ou responsividade ainda não medidos.

Decisão anterior aos testes: protocolo próprio2; cálculo em filho com
orçamento padrão240s, transporte300s. Pedido pode REDUZIR o orçamento para
teste/operação, nunca aumentar acima240s; esse orçamento não pertence à
configuração física selada. Enquanto calcula, dono do protocolo responde
state e quit e recusa mutações adicionais, sem enfileirar cálculo tardio.
Timeout mata/aguarda o filho antes do ack de erro; quit cancela/aguarda o
filho antes de encerrar normalmente. O filho vigia a existência do pai,
inclusive após término abrupto do trabalhador. Cliente correlaciona até16
replies por ID e permite state/quit durante create/configure.

Revisão V2 anterior ao testeB: A excedeu240s e ficou reprovada. A cadeia
venv.exe→Python real foi confirmada; usar o interpretador base diretamente
com `-S` e somente site-packages do ambiente científico fixado, validando a
mesma geração. Um Job Object Windows com KILL_ON_JOB_CLOSE substitui a
thread Python de vigilância. O filho devolve seu PID real, que deve ser
exatamente o PID de Popen antes de qualquer publicação. Não executar o
cálculo com bibliotecas do Python base; a guarda já recusou essa mistura.
FontesA e diagnósticos permanecem preservados, não aceitos. Referência
primária de API: Microsoft Learn, JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
SetInformationJobObject e AssignProcessToJobObject, consultadas29/10UTC.

Aceite deve medir resposta state durante cálculo, recusa de mutação busy,
deadline reduzido preservando artefato/view/token/revisão, quit durante
cálculo e ausência de filho após morte abrupta do pai. Os prazos da ponte
nativa terão de respeitar essa ordem antes de aceitar a candidata.

Manter fila16, máximo16MiB,32 ramos com parent/visibilidade/índice,
locks Windows, exportação completa, fechamento normal e guardas
worker_id/artifact_id/edit_token/revision. Testar mudança dos dois controles
separados, mutações no disco, abuso de tipos, resíduos/EC/taxa nu, parentes,
newprocess e saída integral do domínio sem troca de estado.

Só depois: candidata0.15.0 isolada da0.14.0, controles identificando o modelo
e suas aproximações, CEF/capturas/perfil próprios. Não herdar aceites de
produto/perfil das candidatas anteriores nem promover instalado3.13.
