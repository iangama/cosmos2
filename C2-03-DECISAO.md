# C2-03 — decisão local de qualidade visual

13/10/2026, Windows/RX7600/1920×1080, buildOpenSpace0.22 e CEF nativo.
**Aprovado localmente C2-03**, após revisão das capturas dos três mundos,
ajuste da aproximação e ensaios de navegação/desempenho. Contrato anterior:
QUALIDADE-VISUAL.md. A aprovação é revisão do agente; não atribuir ao dono
uma opinião estética que ele não forneceu.

Terra tem elipsoide WGS84, superfície/noite NASA e atmosfera de espalhamento
adaptada do upstream. Lua usa esfera1737,4km e mapa LRO WAC, sem atmosfera.
Não há relevo nesta etapa, e a iluminação originalmente registrada no mapa
lunar não se transforma em sombras de crateras calculadas em tempo real.
Saturno usa centro699 SAT441 +DE442s, elipsoide PCK e mapa visualOpenSpace
2880×1440. Cinco perfis radiais1500×1 formam os anéis74.500–140.445km.
Oclusão pelo planeta e sombras planeta→anéis/anéis→globo são renderizadas.
Não são dinâmica de partículas, fotometria ou transporte radiativo.

Cada mundo oferece visão geral iluminada, terminador com ângulo câmera/Sol
75°, polo norte e órbita próxima. Saturno mostra o lado dos anéis iluminado
na época adotada; o polo norte pode estar escuro. Todas as vistas preservam
época e estados. Exposição0,5–5 e céu didático (estrelas ampliadas) têm controles
próprios, com limites de resolução/modelo visíveis. Não existe ampliação dos
raios dos planetas/anéis. Indicadores respeitam projeção/oclusão elipsoidal;
corpos não selecionados menores que um pixel não enchem a vista de rótulos.

A primeira aproximação exagerava o mapa terrestre: foi rejeitada e limitada
a3,1R nos rochosos/2,8R em Saturno. Registros iniciais preservados em
visual-controls-initial.json e *detail-initial.png. A órbita próxima final
mantém continentes/crateras/bandas legíveis e retorna à visão geral. Terreno
e aproximação de superfície mais detalhada continuam emC2-05.

verify-visuals passou12vistas+exposição/céu desligado, geometria75°,
vetores/época/worker/câmera preservados nos ajustes de exibição, fonte do mapa
ativo e zero errosJS. Treze capturas foram revistas e seus hashes constam em
evidence/visual-review.json. verify-navigation passou de novo, incluindo
filtros/árvore/favorito livre, cliques150%, foco/tecladoWindows e oclusão.
Dados/fontes também passaram no Edge, incluindo720px;13pacotes/72arquivos,
904806371bytes, recibos e SHA conferidos.

atlas-route-c203b: três vistas aquecidas15s1080p com interface/consultas,
74,943–75,019FPS medianos; p95máximo15,083ms, p99máximo15,381ms,
zero pausas>100ms. DXGI cobre o motor, não todo o produto. A coleta separada
gpu-memory-c203mem possui3amostras/10processos do produto, soma dedicada
máxima3.190.489.088bytes (~2,97GiB); páginas compartilhadas podem duplicar
nessa soma. RAM tem snapshot próprio emproduct-memory-c203. Esses controles
complementam G0 e não substituem suas nove rotas nem provam orçamento para
todo o catálogo futuro.

Os mapas/perfisOpenSpace não têm origem observacional/época confirmadas nesta
curadoria. Crédito/URLs/arquivos/termos locais estão nos recibos/pacote e
TERCEIROS.md. O mapaNASA ficcional anterior permanece como alternativa inativa.
Não converter MIT do código numa licença presumida para imagens. Publicação
segue fora do escopo autorizado.

Próxima etapa: C2-06, editor gravitacional. C2-03 não aprova editor, terreno,
expansão do Atlas ou a candidata final.
