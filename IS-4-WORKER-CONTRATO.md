# IS-4 — worker da partícula em snapshot estático

Processo próprio, protocolo JSON por linha, armazenamento obrigatório em
output. A fila de entrada tem 32 comandos e cada mensagem até 4 MiB. O
controlador deve drenar a saída continuamente; contrapressão interrompe a
publicação e o avanço, sem acumular uma fila ilimitada de snapshots.

O worker começa sem experimento e pausado. Comandos: criar, consultar,
pausar, retomar, avançar de 1 a 256 passos, trocar atuação física, ajustar
ritmo de reprodução, salvar, carregar, ler a amostra e encerrar. Mutação de
experimento exige pausa, identidade do worker/experimento, token, revisão,
referencial e tempo próprio confirmados. Pausar aceita um tempo anterior
publicado para interromper a evolução. Construir carga/substituição em
candidato separado; falha conserva o experimento ativo.

Quando executando, avançar no máximo 16 passos por quantum e conferir
orçamento de 20 ms entre passos. Não há interrupção forçada dentro de uma
chamada de campo. O passo físico permanece fixo; o ritmo solicitado é em
segundos da partícula por segundo de relógio real. Medir o ritmo efetivo
separadamente. Publicação pretendida em 20 Hz, sem promessa de desempenho
antes dos testes. Ao atingir domínio, velocidade, giro ou orçamento,
pausar na última fase aceita e publicar o motivo.

Cada publicação tem sequência própria, identidade e fase científica com
posição, origem, deslocamento, velocidade e tempo sincronizado. Levar
modelo, época congelada, matrizes, centro/origem e unidades. Enviar no
máximo 129 amostras do histórico recente de até 513 estados, com seus
instantes reais. Isso não é confirmação de upload ou desenho no motor.

Verificar fluxo real do processo, guardas e recusas sem mutação, execução/
pausa/ritmo, alterações de atuação e mesma fonte, save/load e novo processo
com futuro exato, parada de domínio e encerramento limpo. Medir latências e
quanta destes cenários; não herdar perfis de C2-12 ou dos mapas. Cena,
confirmação nativa, interface e desempenho ficam em etapas próprias.

Antes da primeira execução: salvar o ritmo de reprodução no mesmo manifesto
atômico da fase. Carregar preserva esse ritmo e começa pausado. A preferência
de execução não muda o passo físico nem constitui uma força. Os testes de
checkpoint devem usar uma geração nova e manter os arquivos anteriores.

Critérios do primeiro cenário, fixados antes de executar: em JRM13 com uma
partícula e ritmo solicitado de 200 passos físicos por segundo real,
pausar deve responder em até 250 ms; registrar também latência das demais
operações e quantum máximo observado. O limite observado do quantum é
50 ms neste teste, incluindo a última chamada indivisível. Nenhum desses
números substitui um perfil do produto com a cena nativa.
