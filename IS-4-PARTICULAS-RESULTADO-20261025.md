# IS4 — cargas-teste em snapshots corporais,25/10/2026

Candidata local0.8.1 passou no escopo de uma partícula em campos corporais
congelados. Mantém origem+deslocamento SI, massa/carga com procedência,
IGRF14 ou JRM33, quatro monopolos gravitacionais e E=0 prescrito. Não avança
silenciosamente o relógio orbital. A fatia de ambiente/vento solar continua
pendente; estes resultados não encerramIS4 nem promovem o instalado.

A validação numérica compara onze trajetórias com DOP853 e refinamento do
passo, incluindo um caso sintético em que gravidade e Lorentz são comparáveis.
A trajetória nativa usa até129 amostras reais normalizadas por unidade física
explícita. Receptor próprio confirma identidade, fase e upload antes de
atualizar a vista; linha e marcador usam o mesmo VBO. Upload e submissão de
desenho permanecem separados de apresentação no monitor.

A jornada0.8.1 passou quatro casos: próton terrestre, neutra terrestre,
elétron JRM13 e próton JRM18. Pausas CEF199–240ms, limite500ms. Controles
físicos independentes de visibilidade e sonda. Avanço oculto confirma dados;
restauração de dois ramos reproduz futuro64 passos. Fase, unidade gráfica e
visibilidade são salvas atomicamente no mesmo envelope e restauradas em
novo worker. Nove recusas de armazenamento incluem corrupção, orçamento de
32 ramos e bloqueios reais de arquivo no Windows. Falha de atualização nativa
injetada provoca pausa após2s, preserva a fase confirmada e permite recuperação.
Seis capturas100/150 foram revistas; controles inferiores exigem rolagem150%.

Perfil fixado antes de executar: Terra próton500km e Júpiter elétron1,5Rj,
visível/oculto, pitch90°,200passos/s,30s aquecimento e60s medidos por janela.
CEF real1920×1080; captura SGCT bruta e inventário próprio de memória/GPU.

| Janela | Mediana ms | p95 ms | p99 ms | Ritmo / solicitado |
|---|---:|---:|---:|---:|
| Terra visível |13,327|14,024|14,528|0,999765|
| Terra oculta |13,362|13,919|14,358|0,999688|
| Júpiter visível |13,362|13,890|14,329|1,000153|
| Júpiter oculta |13,358|13,922|14,347|0,999348|

Nenhum quadro>100ms. Pico RAM1,23586GiB e GPU dedicada conservadora2,96454GiB;
atraso amostrado máximo de confirmação0,205s. Memória soma processos do produto
e pode contar alocações compartilhadas mais de uma vez. Não generalizar para
múltiplas cargas, todas as velocidades, camadas simultâneas, plasma ou MHD.

Evidências principais:
- evidence/is4-body-trajectories-20261025e.json
- evidence/is4-native-stream-20261025b.json
- evidence/is4-product-store-20261025a.json
- evidence/is4-native-product081-20261025a.json
- evidence/is4-product-0.8.1-visual-review-20261025a.json
- evidence/is4-particle-profile-20261025a.json
- evidence/is4-particle-profile-audit-20261025c.json

AuditoriasA/B falharam por caminhos Windows no WSL e strings esperadas pelo
novo auditor; preservadas. C usa os mesmos dados brutos, sem repetir o perfil,
alterar produto ou ampliar limites. Fontes executadas estão em ZIP com hashes.
