# IS6 — perfil nativo próprio,limites prévios02/11/2026

Executar apenas após nativo/visual0.18.1 próprios aceitos. Sem promoção.
Quatro janelas independentes:malha65anéis visível,257visível,sondas exatas
257visível a2comandos/s,e visibilidade alternada257 a2comandos/s.
FonteSol,1–8Rref,planoXY,altura200,dinâmica pausada,UI100%,1920×1080.
30s de aquecimento e60s medidos por janela. Novos caminhos/receitas antes
de cada execução;congelar fontes/contratos/limites/receitas emZIP.

Mesmos limites de fluidez/recursos já adotados pelo projeto:mediana≤16,7ms,
p95≤25ms,p99≤50ms,zero quadros>100ms,RAM somada≤8GiB,GPU dedicada+shared
≤5,5GiB. Captura nativa12000quadros,sem overflow,sem amostras inválidas,
mais1000quadros e duração60s±0,5s após descartar o primeiro delta de borda.
ColetorGPU Windows deve abranger toda janela e identificar os processos
do host0.18.1. RAM pelo processo do motor/servidor/descendentes,com possível
dupla contagem de páginas compartilhadas identificada. Sem alegar readbackGPU
de vértices ou throughput de integração GR.

Nos dois percursos ativos,120comandos programados a2Hz;≥90% concluídos no
intervalo,zero erros,p95 de confirmação≤0,5s e máximo≤1s. Cada resposta deve
preservar artefatoSHA,fase/época/GM e conferir vista/amostra exatas contra
sondas científicas pré-calculadas fora da janela. Visibilidade:bool explícito,
readback nativo nos quatro checkpoints temporais. Sondas:índices inteiros
radial/azimutal/receptor dentro da malha,sem reconstruir o artefato.

Estado/source/RAM/GPUengine nos segundos0/20/40/60. Sem mudanças de fonte,
regeneração,load ou troca de cena dentro da janela. UI renderizada e consultada;
body.inert=true apenas bloqueia input externo durante medição. Registrar
errosCEF,dono,identidade/geração do executável e remoção dos nós/saída normal.
Auditor separado recalcula estatísticas dos deltas brutos,intervalosGPU,
sondas/view/artefato/fase e orçamento antes do aceite do perfil.
