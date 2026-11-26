# IS-4 — transporte próprio da trajetória ampliada

Contrato anterior à construção e aos testes do receptor. O runtime V2 e o
produto0.7.1 permanecem preservados. Novo runtime `.runtime-is4-stream`.
O receptor opcional de RenderableConstellationLines não calcula forças.

Cada pacote contém até129 amostras reais `(t_s,x/L,y/L,z/L)` em float64
little endian, com início `C2IS4T01`, tamanho uint32 do cabeçalho JSON e
payload32bytes/amostra. Cabeçalho exato: schema1, model
`is4_magnified_trajectory_v1`, binding_sha256, sequence, revision, time_s,
count, positions=`normalized_float64_txyz_le`, payload_sha256 e payload_crc32.
JSON plano, sem chaves duplicadas; até32768bytes, pacote até36908bytes.

BindingSHA256 sela descritor completo separado: worker, experimento, token,
snapshot, geração científica, origem de lançamento, unidade física L,
matrizes e âncora. A escala e os dados de desenho são declarados: coordenadas
normalizadas NÃO são posições SI. O pacote científico e o descritor com SI
permanecem do lado Python, associados ao hash exato do payload confirmado.
Nenhum pacote é rotulado como IAS15, nuvem EM ou distância física original.

Python valida identidades/ortogonalidade/origens/tempos, seloSHA256+CRC32 e
limite de quantização já adotado. Publica por substituição atômica. Native
confere estrutura/binding/sequência estritamente crescente/revisão e tempo
não decrescentes, tempos reais crescentes e último tempo igual a time_s,
finitude/extentnormalizada≤1e8 e CRC32. SHA256 nativo é declaração; verificação
criptográfica independente fica no Python. Recusa preserva buffer anterior.
Load/restart com novo token exige outro binding/nó; não zerar sequência
silenciosamente no receptor anterior.

Um VBO limitado armazena linha e marcador final; ambos vêm da MESMA fase
de upload, sem marcador científico adiantado. Registro distingue upload de
submissão de desenho: `gpu_buffer_uploaded` e `draw_submitted_sequence`.
Submissão não é prova de apresentação física por monitor; captura revista
complementa essa evidência. Âncora de navegação é auxiliar e não altera SI.

Verificar encode/decode/refusassem publicação, fluxo de worker real,
pacotes obsoletos/corrompidos e buffer anterior, visibilidade separada,
save/load/rebind/futuro exato, encerramento, PNG100/150 e perfil próprio.
Antes de perfil, fixar cenários e limites. Nenhum aceite IS4 completo ou
integração de vento solar/MHD resulta apenas desta fatia.
