# IS-4 — experimento estático e checkpoint da partícula

Construir em staging próprio sobre o núcleo numérico da rodada E. Uma
partícula por experimento, com massa, carga, passo e condições iniciais em
SI; E/B/gravidade têm controles físicos independentes. O snapshot guarda
a fase orbital original pausada e a leitura corporal necessária para
reconstruir o provedor. O relógio da partícula não avança a fase orbital.

Cada comando avança de 1 a 256 passos, com orçamento total de um milhão.
Um passo recusado conserva a fase anterior; passos aceitos antes da recusa
continuam válidos. Publicar motivo e instante da última fase aceita, sem
alegar uma intersecção exata da superfície. Manter apenas os 513 estados
mais recentes para o desenho e indicar a limitação desse histórico.

Mudar a atuação física cria uma revisão e um evento com instante próprio;
reinicia a referência de energia e acumuladores de trabalho. Os campos
prescritos permanecem os mesmos. Limitar o histórico de intervenções a 128
nesta primeira versão. O passo é fixo nesta fatia; mudar massa/carga/estado
inicial exige novo experimento. Evolução não recebe reação das fontes.

O checkpoint selado inclui fase completa: posição publicada, origem fixa,
deslocamento acumulado, velocidade e tempo sincronizado. Inclui parâmetros,
controles, referência de energia, acumuladores compensados de trabalho,
contador de passos, eventos, histórico recente e procedência. JSON conserva
os float64 no roundtrip. Gravar temporário, sincronizar e substituir o
manifesto atomicamente; uma falha mantém o arquivo anterior. Armazenamento
obrigatoriamente próprio em output, sem tocar sessões do dono.

Carregar constrói um candidato separado, verifica selo, geração/fontes,
snapshot, domínio, tipos, limites, origem/deslocamento e sequência temporal
antes de entregá-lo ao controlador. Preservar identidade do experimento e
trocar token de edição. Recusar geração diferente sem migração silenciosa.
Não alegar reconstrução de todos os passos históricos a partir do arquivo.

Verificar continuação exata após JSON e após processo novo, inclusive os
componentes pequenos da posição e acumuladores. Testar controles/referência,
recusas de comandos e checkpoints corrompidos, parada com última fase
válida e publicação com arquivo Windows realmente bloqueado. Isso não dá
aceite a worker, cena, interface ou desempenho.

Antes de testar: conferir a consistência entre variação de energia cinética
e trabalho acumulado desde a referência, com limite de 1e−9 da escala das
duas energias cinéticas + |trabalho|, mais oito ulps. Esse limite de carga
considera acúmulo de arredondamento até o orçamento total; não altera os
limites por passo já medidos. Não aceitar energia não representável.
