# K3 — primeira interface coordenada de camadas independentes

Construir em candidata 0.19.0 isolada, preservando a instalação 3.13, a 0.18.5
e todos os recibos anteriores. A execução nativa depende de K1C e K2 aceitos;
escrita e revisão do serviço podem avançar enquanto as provas anteriores rodam.

Um serviço próprio compartilha o proprietário de câmera/flags K1C. A interface
seleciona Terra/IGRF14 ou Júpiter/JRM33, cria o par, alterna cada visualização,
consulta suas leituras e fecha a vista com restauração confirmada. A física
orbital continua pausada. Não transformar a escolha de visibilidade em alteração
de atuação, nem combinar B com curvatura em uma quantidade nova.

O primeiro recorte usa a configuração K2 medida: corte espacial XY 65×96,
1–3 Rref, ampliação 200; IGRF14 e JRM33 grau 13. Configurações fora deste
recorte são recusadas explicitamente. Coordenadas da amostra magnética são
informadas e validadas nos domínios já adotados, sem inferir campo externo.

API própria /api/layers/state, /api/layers/command e /api/layers/cancel.
Comandos exatos: create(source_guard,body_id,configuration,magnetic),
set_visibility(visible), get_artifact e leave, todos com guard de sessão,
artefato e revisão. A API não aceita comandos internos. Objetos/booleans/
revisões exigem os tipos corretos; campos extras, NaN/Infinity, fonte alterada,
corpo sem modelo e ações simultâneas são recusados sem publicar estado novo.

Um ator serial prepara o par oculto, confirma as duas vistas e somente então
publica o artefato/guard. Cancelamento vale durante preparação, com ID próprio
e resultado apenas depois da limpeza; durante commit é recusado. Se a limpeza
ou rollback falhar, conservar o proprietário e bloquear alterações até leave
confirmado. Mensagens/status devem explicar a recuperação pendente.

Enquanto ativo, ocupado ou em recuperação, o par tem exclusividade diante
dos serviços antigos: eles mantêm suas recusas. Alterações orbitais, cópias,
partículas, zona solar, malha isolada e prévias antigas não podem retirar nós
ou tomar câmera/flags do par. O servidor serializa a admissão da fonte e dos
instrumentos. A interface acompanha a revisão e não aplica respostas antigas.

Mostrar duas legendas e leituras separadas, época/fonte e estado congelado;
posição em metros/GALACTIC, B em tesla, curvatura em m⁻⁴ e relógios em razão
adimensional. Manter controles e saída acessíveis em 100/150%, sem rolagem
horizontal. A amostra magnética não herda o domínio exterior da malha.

Provas próprias: contratos/recusas CPU do serviço, interface CEF real para
ambos os corpos, quatro visibilidades, troca/saída e cancelamento, fonte
inalterada, recuperação, PNG revistos e perfil da candidata final. Não usar
K2 como perfil de uma UI diferente. Salvar/reabrir/ramos/migração composta
seguem como próxima entrega obrigatória; K3 sozinho não encerra IS6/v1.
