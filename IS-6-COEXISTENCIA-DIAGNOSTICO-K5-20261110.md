# Investigação da pausa em K5A

## Correlação preservada

A candidata composta 0.21.1 segue com perfil recusado. O recibo
`is6-k5-hitch-correlation-20261110a.json` confere os hashes dos quadros,
auditoria, GPU e registros da sessão exata de 05/11. A identidade coincide
com motor3808, servidor31132 e launcher30372.

A amostra bruta de chave1265 mede580,568612ms. Ela corresponde ao
ordinal1264 da série auditada, cuja primeira amostra foi tratada pelo
auditor existente como intervalo inicial. A soma anterior dessa série é
16,845731s. Usando a hora de início recebida pelo cliente, o intervalo fica
aproximadamente entre16:46:34,683 e16:46:35,263UTC. Os quadros brutos têm
intervalos relativos, e a origem temporal exata de cada quadro ficou sem
registro. Incluir a primeira amostra desloca essa estimativa em7,7263ms.

A soma WDDM dedicada+compartilhada do produto ficou em3.224.891.392bytes nas
amostras próximas. A memória local DXGI do motor ficou em3.078.078.464bytes
nas quatro verificações da janela. Estas leituras medem bytes. O perfil
arquivado carece de rastreamento do escalonamento e das etapas desse pico.

Os registros HTTP dessa sessão omitem consultas de estado de camadas e
física. A janela estática possui zero comandos de visibilidade. Os canais
Windows System e Application conservaram eventos anteriores/posteriores
ao período, com zero entradas na consulta16:45–16:48UTC. Defender possuía
somente registros antigos, TaskScheduler estava vazio e
Diagnostics-Performance retornou acesso negado. A causa continua em aberto.

## Ensaio instrumentado previamente definido

Usar o mesmo executável9fdd4619…63f96d, candidata0.21.1, catálogo existente
e host Python próprio. O executor novo
`diagnose-is6-k5-native-hitch.py` reutiliza transporte, serviço, verificações
científicas, árvore temporal de processos e coletorPDH já empregados noK5A.
As fontes executadas doK5A permanecem seladas pelos hashes originais.
Preparação exige cinco fotografias iguais da árvore e uma préviaPDH de
três amostras na cópia orbital pausada.

Hipótese a investigar é uma espera na thread do motor ou na apresentação.
Uma segunda hipótese envolve coincidência com as consultas periódicas do
coletor. O rastreamento nativo já disponível mede parede por etapa e o
intervalo entre quadros. Seus escopos aninhados se sobrepõem. A interface
recebe um observador limitado a512longtasks e o executor conserva os tempos
CDP das consultas de estado das camadas.

Executar uma única sequência previamente selada, com30s de aquecimento e
60s de captura por janela, UI100% e1920×1080.

1. Terra estática com66amostrasPDH, preparando a mesma sequência de corpos.
2. Júpiter estático com66amostrasPDH.
3. A mesma referência de Júpiter, mantendo o coletor encerrado.

Fase pausada, câmera, flags, UI, RAM e métricas nativas são conferidas nos
segundos0/20/40/60. A malha65×96, exterior1–3Rref e ampliação200 seguem a
receita original. O conteúdo dos checkpoints e a sessão do dono recebem
comparação de hashes antes/depois. Encerramento exige quatro saídas zero.

As janelas2/3 permitem observar a região de uma eventual pausa sob duas
condições. A ordem fixa deixa idade do processo e aquecimento como
confundidores. Uma execução sem reprodução fornece diagnóstico
inconclusivo. Todos os quadros e eventos ficam preservados. Os resultados
serão usados para decidir uma correção dirigida ou a próxima medição
instrumentada, mantendo o aceite formal pendente.

## Snapshot local

O checkout irmão contém3.610arquivos conferidos pelo inventário do
sync20261105e. Os31caminhos preparados correspondem ao recibo anterior,
incluindo inventário. O Git aceitou os bytesCRLF das evidências com
`core.whitespace=cr-at-eol`. O remoto possui visibilidade pública e segue
no commit2ad84bb. A retomada conserva o trabalho novo no armazenamento local,
conforme a autorização de implementação local vigente.
