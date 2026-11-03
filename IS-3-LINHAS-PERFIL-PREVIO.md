# IS-3 — perfil nativo das linhas magnéticas congeladas

Contrato anterior à captura desta candidata0.5. Duas janelas próprias de
60s, uma com IGRF14 e outra com JRM33 grau13, depois de30s de aquecimento
cada. Resolução1920×1080, CEF100%, cópias novas dos quatro centros na época
original, IAS15epsilon1e−9, ritmo canônico0,1. Linhas construídas pausadas e
congeladas depois; gravitação evolui sem reconsultar o campo fora da época.
Conjuntos padrão: cinco curvas terrestres e quatro jovianas, vetores de
direção, ponto e grade. Uma camada corporal por vez.

Três vistas de20s por janela: ponto, lateral e polar. TransporteLua
persistente. Guardar todos os intervalosSGCT, sem filtrar picos; mediana
≤16,7ms,p95≤25ms,p99≤50ms,nenhum>100ms,ritmo medido/solicitado≥0,9.
RAM dos processos próprios≤8GiB; dedicadaWDDM somada≤5,5GiB e abaixo do
orçamentoDXGI da placa física. Cada janela exige66amostrasWDDM válidas
cobrindo começo e fim. Somas podem repetir alocações compartilhadas.
Energia,momento e momento angular normalizados≤1e−8. Auditar janela e cada
vista contra os dados brutos, hashes de fontes e executável preservados.

Confirmar no motor a existência/Enabled dos cinco meshes da camada,
âncora, marcador corporal ocultado, id e leitura constantes nas três vistas.
Auditor confere reciboSI das linhas e hashes de todos os arquivos gráficos.
Nenhum perfilJ/IS12/vetor único é herdado. Arquivar receita/contrato/fontes
antes de capturar. Não modificar a candidata durante a captura.

Este recorte não mede atualização contínua, mapas/cortes, múltiplas camadas,
partículas/Lorentz ou comparação sustentada ligado/desligado. A jornada
verifica que ocultar/remover e reconstruir não muda a solução pausada;
o requisito geral de perfis simultâneos/ligado-desligado segue pendente.
