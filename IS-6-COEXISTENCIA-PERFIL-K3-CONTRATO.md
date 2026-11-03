# K3 — perfil da interface coordenada final

Usar a 0.19.1 somente após jornada funcional, seis imagens revistas e saída
normal próprias. O perfil K2 mede outro host/UI e não pode ser transferido.
Quatro janelas de 30 s de aquecimento +60 s medidos em 1920×1080/UI100%:
Terra e Júpiter estáticos com ambas as camadas, depois Terra e Júpiter com
as quatro visibilidades a 2 Hz. Mesmos pontos, malha65×96,domínio1–3Rref,
planoXY e ampliação200 de K2; fonte orbital pausada e mesma época.

Criar cada par pela interface real antes da janela, consultar seu artefato
pela API e arquivar fonte, modelos, configuração, leitura e receita antes
da captura. Durante a janela ativa emitir 120 set_visibility pela API
/api/layers/command, usando a revisão confirmada anterior; manter a UI
real aberta, renderizada e consultando /api/layers/state. Registrar essa
distinção: é latência da API com UI em execução, não teste de digitação humana.

Medir combinações false/false,false/true,true/false,true/true, repetidas
30 vezes com intervalos0,5s. Confirmar visibilidades e digest invariável
em cada resposta. Consultar flags nativos e estado antes/depois nos instantes
0/20/40/60s; admitir o checkpoint somente se a revisão permanecer estável
ao redor da leitura. Preservar a fase e câmera. Registrar erros JS e
identidade/estado da UI; apenas body.inert bloqueia input durante a coleta.

Limites iguais a K2: mediana≤16,7ms,p95≤25ms,p99≤50ms,zeroquadros>100ms,
RAM≤8GiB,GPUdedicada+shared≤5,5GiB. Mais1000deltas válidos,semoverflow,
60±0,5s após descartar somente o primeirodelta. 120respostas porjanela,
≥90%concluídas em60s,p95≤0,5s,máximo≤1s. GPU schema3 com66amostras
válidas cobrindo a janela,processos/caminhos próprios constantes e status
brutos conferidos. Não substituir erros porzero ou misturar execuções.

Auditor próprio recalcula modelos, artefatos/receitas, estatísticas e recursos.
Conferir ZIP/hashes, remoção dos nós, restauração de câmera/flags, sessão do
dono, saída0/0 e ausência de PIDs. Persistência composta e migração continuam
pendentes após o perfil; não declarar IS6/v1 concluídos por esta prova.
